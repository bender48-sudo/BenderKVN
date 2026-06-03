#!/usr/bin/env python3
"""Smoke backup subscription edge (NL jurisdiction origin)."""
from __future__ import annotations

import os
import subprocess
import sys

import site_urls

if str(__import__("pathlib").Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))


def main() -> int:
    origin = (site_urls.SUB_JURISDICTION_BACKUP_ORIGIN or "").strip().rstrip("/")
    if not origin:
        print("SKIP: SUB_JURISDICTION_BACKUP_ORIGIN unset")
        return 0

    url = site_urls.sub_monitor_probe_url_for_origin(origin)
    print(f"probe: {url}")
    try:
        null_out = "NUL" if os.name == "nt" else "/dev/null"
        curl = "curl.exe" if os.name == "nt" else "curl"
        out = subprocess.check_output(
            [curl, "-sS", "-m", "20", "-o", null_out, "-w", "%{http_code}", url],
            stderr=subprocess.STDOUT,
            text=True,
        )
        code = int(out.strip() or "0")
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"FAIL: curl {e}", file=sys.stderr)
        return 1

    if code not in (200, 304):
        print(f"FAIL: HTTP {code} (DNS/Caddy on NL?)", file=sys.stderr)
        return 1

    print("SUB_JURISDICTION_BACKUP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
