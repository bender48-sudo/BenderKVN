#!/usr/bin/env python3
"""P1-RED-SUB-VERIFY-3010-01: verify AMS subscription ports are not open to the world."""
from __future__ import annotations

import socket
import sys

AMS_IP = "168.100.11.140"
LV_IP = "176.126.162.158"
PORTS = (3010, 3011)
TIMEOUT = 5.0


def _probe(host: str, port: int) -> tuple[bool, str]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    try:
        s.connect((host, port))
        s.close()
        return True, "open"
    except (TimeoutError, socket.timeout):
        return False, "timeout"
    except OSError as exc:
        return False, str(exc)[:80]


def main() -> int:
    # External (this workstation) must not reach sub backends directly.
    for port in PORTS:
        ok, detail = _probe(AMS_IP, port)
        if ok:
            print(
                f"SUB_PORTS_FIREWALL_FAIL: {AMS_IP}:{port} reachable from here ({detail})",
                file=sys.stderr,
            )
            return 1
    # LV edge sub URL must still work (via Caddy).
    try:
        import ssl
        import urllib.request

        import site_urls

        url = site_urls.sub_monitor_probe_url()
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "Happ/1.9.4"})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            if r.status not in (200, 304):
                print(f"SUB_PORTS_FIREWALL_FAIL: sub edge {r.status}", file=sys.stderr)
                return 1
    except Exception as exc:
        print(f"SUB_PORTS_FIREWALL_FAIL: sub edge {exc}", file=sys.stderr)
        return 1

    print("SUB_PORTS_FIREWALL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
