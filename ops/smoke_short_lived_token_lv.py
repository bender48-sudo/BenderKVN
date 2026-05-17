#!/usr/bin/env python3
"""P1-RED-SEC-01 smoke: short-lived credential broker on LV."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Deployed beside this script on LV
sys.path.insert(0, "/opt/scripts")
from remna_credential_broker import (  # noqa: E402
    AUDIT_LOG,
    get_panel_token,
    refresh_consumers,
    verify_panel_api,
)


def main() -> int:
    consumer = "smoke"
    before = AUDIT_LOG.stat().st_size if AUDIT_LOG.is_file() else 0

    t1 = get_panel_token(consumer, ttl=120, force=True)
    if not t1.startswith("eyJ"):
        print(f"FAIL: expected JWT, got {t1[:20]!r}", file=sys.stderr)
        return 1

    t2 = get_panel_token(consumer, ttl=120, force=False)
    if t1 != t2:
        print("FAIL: cache miss on second get", file=sys.stderr)
        return 2

    if not verify_panel_api(t1):
        print("FAIL: panel API verify", file=sys.stderr)
        return 3

    refresh_consumers(["ru-monitor", "balancer"], ttl=3600)
    after = AUDIT_LOG.stat().st_size if AUDIT_LOG.is_file() else 0
    if after <= before:
        print("FAIL: audit log did not grow", file=sys.stderr)
        return 4

    tail = AUDIT_LOG.read_text(encoding="utf-8").splitlines()[-3:]
    events = [json.loads(x).get("event") for x in tail if x.strip()]
    if "issue" not in events and "cache_hit" not in events:
        print(f"FAIL: unexpected audit events {events}", file=sys.stderr)
        return 5

    print("OK: cache + audit + panel verify")
    print("SHORT_LIVED_TOKEN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
