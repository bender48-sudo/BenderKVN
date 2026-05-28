#!/usr/bin/env python3
"""Warn if ops probes use legacy :2053 subscription origin (VPN edge policy).

Canonical public sub edge is :8443. :2053 may work but is worse under RU DPI
(429/timeouts in load probes).

Exit 0 always (warning only). Fails only with --strict.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="exit 1 on legacy port")
    args = ap.parse_args()

    origin = site_urls.SUB_PUBLIC_ORIGIN
    port = site_urls.EDGE_PUBLIC_PORT
    issues: list[str] = []
    if ":2053" in origin:
        issues.append(f"SUB_PUBLIC_ORIGIN uses :2053 ({origin})")
    if port == "2053":
        issues.append(f"EDGE_PUBLIC_PORT={port}")

    if not issues:
        print(f"AUDIT_SUB_ORIGIN_OK ({origin})")
        return 0

    for msg in issues:
        print(f"WARN: {msg} — set ops/site.env EDGE_PUBLIC_PORT=8443", file=sys.stderr)
    print("AUDIT_SUB_ORIGIN_WARN", file=sys.stderr)
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
