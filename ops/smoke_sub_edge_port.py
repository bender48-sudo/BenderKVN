#!/usr/bin/env python3
"""P2-RED-EDGE-PORT-01: repo defaults and optional live curl on :8443."""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ops"))
import site_urls  # noqa: E402


def _repo_ok() -> bool:
    if site_urls.EDGE_PUBLIC_PORT != "8443":
        print("SUB_EDGE_PORT_FAIL: EDGE_PUBLIC_PORT != 8443", file=sys.stderr)
        return False
    for url in (
        site_urls.PANEL_URL,
        site_urls.SUB_PUBLIC_ORIGIN,
        site_urls.SUB_ALT_PUBLIC_ORIGINS[0],
    ):
        if ":8443" not in url:
            print(f"SUB_EDGE_PORT_FAIL: expected :8443 in {url!r}", file=sys.stderr)
            return False
    caddy = (ROOT / "Caddyfile-latvia-full.txt").read_text(encoding="utf-8")
    for host in ("p4n7q.conntest.xyz:8443", "k9x2m1.conntest.xyz:8443"):
        if host not in caddy:
            print(f"SUB_EDGE_PORT_FAIL: Caddy missing {host}", file=sys.stderr)
            return False
    print("OK: repo defaults and Caddy :8443 blocks")
    return True


def _live_ok() -> bool:
    if os.getenv("SUB_EDGE_PORT_SKIP_LIVE", "").strip().lower() in ("1", "true", "yes"):
        print("SKIP: live curl (SUB_EDGE_PORT_SKIP_LIVE)")
        return True
    portal = f"{site_urls.PANEL_URL}/portal/"
    sub = site_urls.sub_monitor_probe_url()
    for label, url in (("portal", portal), ("sub", sub)):
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status not in (200, 304):
                    print(f"SUB_EDGE_PORT_FAIL: {label} HTTP {resp.status}", file=sys.stderr)
                    return False
        except Exception as e:
            print(f"SUB_EDGE_PORT_FAIL: {label} curl {url!r}: {e}", file=sys.stderr)
            return False
        print(f"OK: live {label} {url} -> 200/304")
    return True


def main() -> int:
    if not _repo_ok():
        return 1
    if not _live_ok():
        return 2
    print("SUB_EDGE_PORT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
