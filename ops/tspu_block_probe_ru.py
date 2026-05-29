#!/usr/bin/env python3
"""P1-RED-TSPU-BLOCK-RU-01: edge probe from RU via relay check.py (forced-command SSH)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OPS = Path(__file__).resolve().parent


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


def _relay_endpoints(cfg: dict[str, str]) -> list[tuple[str, str, int, str, str]]:
    """Return (label, host, port, user, key_path) for each configured RU relay."""
    specs = (
        ("relay1", "RELAY_HOST", "RELAY_SSH_PORT", "RELAY_SSH_USER", "RELAY_SSH_KEY"),
        ("relay2", "RELAY2_HOST", "RELAY2_SSH_PORT", "RELAY2_SSH_USER", "RELAY2_SSH_KEY"),
    )
    defaults = {
        "RELAY_HOST": "72.56.0.145",
        "RELAY_SSH_PORT": "3344",
        "RELAY_SSH_USER": "bvpncheck",
        "RELAY_SSH_KEY": "/root/.ssh/id_ed25519",
    }
    endpoints: list[tuple[str, str, int, str, str]] = []
    for label, host_k, port_k, user_k, key_k in specs:
        env_prefix = "RU_" if label == "relay1" else "RU_"
        host = os.environ.get(f"{env_prefix}{host_k}") or cfg.get(host_k) or defaults.get(host_k)
        if not host:
            continue
        port = int(
            os.environ.get(f"{env_prefix}{port_k}")
            or cfg.get(port_k)
            or defaults.get(port_k, "22")
        )
        user = (
            os.environ.get(f"{env_prefix}{user_k}")
            or cfg.get(user_k)
            or defaults.get(user_k, "bvpncheck")
        )
        key = (
            os.environ.get(f"{env_prefix}{key_k}")
            or cfg.get(key_k)
            or defaults.get(key_k, "/root/.ssh/id_ed25519")
        )
        endpoints.append((label, host, port, user, key))
    return endpoints


def _probe_via_relay(
    label: str,
    relay_host: str,
    relay_port: int,
    relay_user: str,
    relay_key: str,
    host: str,
    https_port: int,
    legacy_port: int,
) -> dict:
    if not Path(relay_key).is_file():
        raise FileNotFoundError(f"{label}: missing relay SSH key: {relay_key}")

    targets = [
        {"address": host, "port": legacy_port, "sni": host},
        {"address": host, "port": https_port, "sni": host},
    ]
    cmd = [
        "ssh",
        "-4",
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
            f"{label} relay SSH failed exit={proc.returncode}: {proc.stderr.strip()[:200]}"
        )
    return json.loads(proc.stdout)


def _evaluate_probe(label: str, host: str, https_port: int, legacy_port: int, data: dict) -> bool:
    by_port: dict[int, dict] = {}
    for row in data.get("results") or []:
        by_port[int(row["port"])] = row

    ok = True
    for check_label, port, need_tls in (
        ("tcp_legacy", legacy_port, False),
        ("tcp_https", https_port, False),
        ("tls_https", https_port, True),
    ):
        row = by_port.get(port)
        if not row:
            print(f"{label} {check_label} {host}:{port} -> FAIL (no result)")
            ok = False
            continue
        if row.get("error"):
            print(f"{label} {check_label} {host}:{port} -> FAIL ({row['error']})")
            ok = False
            continue
        if need_tls and not row.get("tls_handshake_ok"):
            print(f"{label} {check_label} {host}:{port} -> FAIL (tls handshake)")
            ok = False
            continue
        ms = row.get("tcp_connect_ms")
        print(f"{label} {check_label} {host}:{port} -> OK ({ms}ms tcp)")
    return ok


def main() -> int:
    host = os.environ.get("TSPU_PROBE_HOST", "k9x2m1.conntest.xyz")
    https_port = int(os.environ.get("EDGE_PUBLIC_PORT", "8443"))
    legacy_port = int(os.environ.get("TSPU_LEGACY_PORT", "2053"))
    cfg = _relay_env()
    endpoints = _relay_endpoints(cfg)
    if not endpoints:
        print("TSPU_BLOCK_PROBE_RU_FAIL: no relay endpoints configured", file=sys.stderr)
        return 1

    all_ok = True
    for label, relay_host, relay_port, relay_user, relay_key in endpoints:
        print(f"--- {label} {relay_host}:{relay_port} ---")
        try:
            data = _probe_via_relay(
                label, relay_host, relay_port, relay_user, relay_key,
                host, https_port, legacy_port,
            )
        except Exception as e:
            print(f"TSPU_BLOCK_PROBE_RU_FAIL: {e}", file=sys.stderr)
            all_ok = False
            continue
        if not _evaluate_probe(label, host, https_port, legacy_port, data):
            all_ok = False

    if all_ok and len(endpoints) >= 1:
        print("TSPU_BLOCK_PROBE_RU_OK")
        return 0
    print("TSPU_BLOCK_PROBE_RU_WARN", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
