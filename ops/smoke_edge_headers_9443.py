#!/usr/bin/env python3
"""Smoke HSTS on :9443 apex blocks (P2-RED-EDGE-HEADERS-02)."""
from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.request

TARGETS = (
    "https://lv.conntest.xyz:9443/",
    "https://conntest.xyz:9443/",
)


def _head(url: str) -> dict[str, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}


def main() -> int:
    ok = True
    for url in TARGETS:
        try:
            headers = _head(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"FAIL {url}: {exc}")
            ok = False
            continue
        hsts = headers.get("strict-transport-security", "")
        if "max-age" not in hsts.lower():
            print(f"FAIL {url}: missing HSTS ({hsts!r})")
            ok = False
        else:
            print(f"OK {url}: HSTS present")
    if ok:
        print("EDGE_HEADERS_9443_OK")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
