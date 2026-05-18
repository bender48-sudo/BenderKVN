#!/usr/bin/env python3
"""P1-RED-TSPU-BLOCK-01: probe RU-side edge block patterns (ports>990, TLS handshake)."""
from __future__ import annotations

import argparse
import socket
import ssl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ops"))
import site_urls  # noqa: E402


def _tcp_connect(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "ok"
    except OSError as e:
        return False, str(e)


def _tls_handshake(host: str, port: int, timeout: float) -> tuple[bool, str]:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return True, "ok"
    except OSError as e:
        return False, str(e)


def main() -> int:
    ap = argparse.ArgumentParser(description="RU TSPU block probe (run from RU relay)")
    ap.add_argument("--host", default="k9x2m1.conntest.xyz")
    ap.add_argument("--https-port", type=int, default=int(site_urls.EDGE_PUBLIC_PORT))
    ap.add_argument("--high-port", type=int, default=2053, help="legacy edge for comparison")
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()

    ok = True
    for label, port, fn in (
        ("tcp_high", args.high_port, _tcp_connect),
        ("tcp_https", args.https_port, _tcp_connect),
        ("tls_https", args.https_port, _tls_handshake),
    ):
        passed, detail = fn(args.host, port, args.timeout)
        status = "OK" if passed else "FAIL"
        print(f"{label} {args.host}:{port} -> {status} ({detail})")
        if not passed and label.startswith("tls"):
            ok = False

    if ok:
        print("TSPU_BLOCK_PROBE_OK")
        return 0
    print("TSPU_BLOCK_PROBE_WARN", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
