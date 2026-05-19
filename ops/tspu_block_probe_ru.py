#!/usr/bin/env python3
"""P1-RED-TSPU-BLOCK-RU-01: edge probe from RU via relay check.py (forced-command SSH)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OPS = Path(__file__).resolve().parent
ROOT = OPS.parent


def _load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _relay_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for p in (Path("/etc/bvpn/ru-monitor.env"), OPS / "site.env"):
        env.update(_load_env(p))
    return env


def _probe_via_relay(host: str, https_port: int, legacy_port: int) -> dict:
    cfg = _relay_env()
    relay_host = os.environ.get("RU_RELAY_HOST") or cfg.get("RELAY_HOST", "72.56.0.145")
    relay_port = int(os.environ.get("RU_RELAY_SSH_PORT") or cfg.get("RELAY_SSH_PORT", "3344"))
    relay_user = os.environ.get("RU_RELAY_SSH_USER") or cfg.get("RELAY_SSH_USER", "bvpncheck")
    relay_key = os.environ.get("RU_RELAY_SSH_KEY") or cfg.get(
        "RELAY_SSH_KEY", "/root/.ssh/id_ed25519"
    )
    if not Path(relay_key).is_file():
        raise FileNotFoundError(f"missing relay SSH key: {relay_key}")

    targets = [
        {"address": host, "port": legacy_port, "sni": host},
        {"address": host, "port": https_port, "sni": host},
    ]
    cmd = [
        "ssh",
        "-p",
        str(relay_port),
        "-i",
        relay_key,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{relay_user}@{relay_host}",
    ]
    proc = subprocess.run(
        cmd,
        input=json.dumps(targets),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"relay SSH failed exit={proc.returncode}: {proc.stderr.strip()[:200]}"
        )
    return json.loads(proc.stdout)


def main() -> int:
    host = os.environ.get("TSPU_PROBE_HOST", "k9x2m1.conntest.xyz")
    https_port = int(os.environ.get("EDGE_PUBLIC_PORT", "8443"))
    legacy_port = int(os.environ.get("TSPU_LEGACY_PORT", "2053"))

    try:
        data = _probe_via_relay(host, https_port, legacy_port)
    except Exception as e:
        print(f"TSPU_BLOCK_PROBE_RU_FAIL: {e}", file=sys.stderr)
        return 1

    by_port: dict[int, dict] = {}
    for row in data.get("results") or []:
        by_port[int(row["port"])] = row

    ok = True
    for label, port, need_tls in (
        ("tcp_legacy", legacy_port, False),
        ("tcp_https", https_port, False),
        ("tls_https", https_port, True),
    ):
        row = by_port.get(port)
        if not row:
            print(f"{label} {host}:{port} -> FAIL (no result)")
            ok = False
            continue
        if row.get("error"):
            print(f"{label} {host}:{port} -> FAIL ({row['error']})")
            ok = False
            continue
        if need_tls and not row.get("tls_handshake_ok"):
            print(f"{label} {host}:{port} -> FAIL (tls handshake)")
            ok = False
            continue
        ms = row.get("tcp_connect_ms")
        print(f"{label} {host}:{port} -> OK ({ms}ms tcp)")

    if ok:
        print("TSPU_BLOCK_PROBE_RU_OK")
        return 0
    print("TSPU_BLOCK_PROBE_RU_WARN", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
