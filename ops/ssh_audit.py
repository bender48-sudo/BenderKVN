#!/usr/bin/env python3
"""P1-RED-SSH-01: audit authorized_keys blast radius across prod hosts."""
from __future__ import annotations

import base64
import hashlib
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# EU prod hosts (SSH config aliases). Relay excluded — separate blast domain.
PROD_HOSTS = ("bvpn-lv", "bvpn-ams", "bvpn-nl")

# Per-host operator keys (P1-RED-SSH-01); override via env if needed.
_HOST_IDENTITY: dict[str, Path] = {
    "bvpn-lv": Path.home() / ".ssh" / "bvpn_lv_ed25519",
    "bvpn-ams": Path.home() / ".ssh" / "bvpn_ams_ed25519",
    "bvpn-nl": Path.home() / ".ssh" / "bvpn_nl",
}

KEY_LINE = re.compile(
    r"^(?:(?:no-)?[-a-z]+(?:,(?:no-)?[-a-z]+)*\s+)?"
    r"(ssh-(?:ed25519|rsa)|ecdsa-sha2-nistp256)\s+([A-Za-z0-9+/=]+)"
    r"(?:\s+.*)?$"
)


@dataclass(frozen=True)
class PubKey:
    key_type: str
    blob_b64: str
    restricted: bool
    comment: str

    @property
    def fp_sha256(self) -> str:
        raw = base64.b64decode(self.blob_b64)
        digest = hashlib.sha256(raw).digest()
        return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")

    @property
    def material(self) -> str:
        return f"{self.key_type} {self.blob_b64}"


def _fetch_authorized(host: str, timeout: int = 12) -> str:
    # Full `cat` can hang on some hosts (sshd/audit); head is enough for audit.
    # LV: `head -n` can hang; byte cap is reliable.
    remote = "head -c 4096 /root/.ssh/authorized_keys 2>/dev/null || true"
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout}",
           "-o", "StrictHostKeyChecking=accept-new"]
    ident = _HOST_IDENTITY.get(host)
    if ident and ident.is_file():
        cmd.extend(["-i", str(ident), "-o", "IdentitiesOnly=yes"])
    cmd.extend([host, remote])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 and not out:
        raise RuntimeError(
            f"{host}: ssh failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    return out + "\n"


def _parse_keys(text: str) -> list[PubKey]:
    keys: list[PubKey] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = KEY_LINE.match(line)
        if not m:
            continue
        restricted = line.lstrip().startswith(("command=", "from=", "restrict", "no-pty"))
        comment = ""
        parts = line.split()
        if len(parts) >= 3 and not parts[-1].startswith("="):
            comment = parts[-1]
        keys.append(
            PubKey(
                key_type=m.group(1),
                blob_b64=m.group(2),
                restricted=restricted,
                comment=comment,
            )
        )
    return keys


def _local_operator_keys(ssh_dir: Path) -> dict[str, str]:
    """Map local private key path stem -> pubkey SHA256 (if .pub exists)."""
    out: dict[str, str] = {}
    for pub in ssh_dir.glob("*.pub"):
        try:
            line = pub.read_text(encoding="utf-8").strip().splitlines()[0]
        except OSError:
            continue
        m = KEY_LINE.match(line)
        if not m:
            continue
        pk = PubKey(m.group(1), m.group(2), False, pub.stem)
        out[pub.name] = pk.fp_sha256
    return out


def audit_remote() -> tuple[bool, list[str]]:
    by_material: dict[str, set[str]] = defaultdict(set)
    host_keys: dict[str, list[PubKey]] = {}
    lines: list[str] = []

    for host in PROD_HOSTS:
        raw = _fetch_authorized(host)
        keys = _parse_keys(raw)
        host_keys[host] = keys
        lines.append(f"{host}: {len(keys)} key(s)")
        for k in keys:
            tag = "restricted" if k.restricted else "login"
            lines.append(f"  [{tag}] {k.fp_sha256} {k.comment or '(no comment)'}")
            by_material[k.material].add(host)

    ok = True
    for material, hosts in sorted(by_material.items(), key=lambda x: -len(x[1])):
        if len(hosts) < 2:
            continue
        fp = PubKey(*material.split(" ", 1), False, "").fp_sha256  # type: ignore[arg-type]
        # Restricted probe keys may legitimately differ; flag only unrestricted dupes.
        sample = next(
            (k for h in hosts for k in host_keys[h] if k.material == material),
            None,
        )
        if sample and sample.restricted:
            lines.append(
                f"NOTE: restricted key {fp} on {', '.join(sorted(hosts))} (expected for probes)"
            )
            continue
        ok = False
        lines.append(
            f"FAIL: same operator key {fp} on multiple hosts: {', '.join(sorted(hosts))}"
        )

    return ok, lines


def audit_local(ssh_dir: Path) -> tuple[bool, list[str]]:
    fps = _local_operator_keys(ssh_dir)
    if not fps:
        return True, ["local: no ~/.ssh/*.pub found (skip)"]

    lines = [f"local: {len(fps)} public key file(s) in {ssh_dir}"]
    for name, fp in sorted(fps.items()):
        lines.append(f"  {name}: {fp}")

    # Legacy blast radius: one id_ed25519 used for LV+AMS in config.example
    lv_pub = ssh_dir / "bvpn_lv_ed25519.pub"
    ams_pub = ssh_dir / "bvpn_ams_ed25519.pub"
    legacy = ssh_dir / "id_ed25519.pub"
    ok = True
    if legacy.exists() and lv_pub.exists():
        m_legacy = KEY_LINE.match(legacy.read_text(encoding="utf-8").strip())
        m_lv = KEY_LINE.match(lv_pub.read_text(encoding="utf-8").strip())
        if m_legacy and m_lv and m_legacy.group(2) == m_lv.group(2):
            ok = False
            lines.append("FAIL: bvpn_lv_ed25519.pub is still the same as id_ed25519.pub")
    if legacy.exists() and ams_pub.exists():
        m_legacy = KEY_LINE.match(legacy.read_text(encoding="utf-8").strip())
        m_ams = KEY_LINE.match(ams_pub.read_text(encoding="utf-8").strip())
        if m_legacy and m_ams and m_legacy.group(2) == m_ams.group(2):
            ok = False
            lines.append("FAIL: bvpn_ams_ed25519.pub is still the same as id_ed25519.pub")
    if lv_pub.exists() and ams_pub.exists():
        m_lv = KEY_LINE.match(lv_pub.read_text(encoding="utf-8").strip())
        m_ams = KEY_LINE.match(ams_pub.read_text(encoding="utf-8").strip())
        if m_lv and m_ams and m_lv.group(2) == m_ams.group(2):
            ok = False
            lines.append("FAIL: bvpn_lv_ed25519.pub equals bvpn_ams_ed25519.pub")
    if ok and lv_pub.exists() and ams_pub.exists():
        lines.append("OK: distinct local operator keys for LV and AMS")
    return ok, lines


def main() -> int:
    ssh_dir = Path.home() / ".ssh"
    print("=== SSH audit (P1-RED-SSH-01) ===")
    try:
        remote_ok, remote_lines = audit_remote()
    except Exception as exc:
        print(f"FAIL: remote audit: {exc}", file=sys.stderr)
        return 1
    for line in remote_lines:
        print(line)

    local_ok, local_lines = audit_local(ssh_dir)
    print("---")
    for line in local_lines:
        print(line)

    if remote_ok and local_ok:
        print("SSH_AUDIT_OK")
        return 0
    print("SSH_AUDIT_FAIL", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
