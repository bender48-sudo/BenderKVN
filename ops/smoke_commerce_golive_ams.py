#!/usr/bin/env python3
"""P2-COM-MONETIZE-04 gate smoke (run inside remna-shop-bot on AMS). Exit 0 = go-live OK."""
from __future__ import annotations

import os
import sys


def main() -> int:
    from shop_bot.config import BOT_PAYMENTS_LIVE, DAILY_RATE, TOPUP_PRESETS, balance_to_days
    from shop_bot.data_manager.database import get_setting

    if not BOT_PAYMENTS_LIVE:
        print("FAIL: BOT_PAYMENTS_LIVE", file=sys.stderr)
        return 1
    if float(DAILY_RATE) != 6.67:
        print(f"FAIL: DAILY_RATE={DAILY_RATE}", file=sys.stderr)
        return 2
    if balance_to_days(200) < 29:
        print(f"FAIL: balance_to_days(200)={balance_to_days(200)}", file=sys.stderr)
        return 3
    print(f"OK: payments live, DAILY_RATE={DAILY_RATE}, presets={list(TOPUP_PRESETS.keys())}")

    stub = "не установлена"
    terms = get_setting("terms_url") or ""
    privacy = get_setting("privacy_url") or ""
    support = get_setting("support_user") or ""
    for name, val in [("terms", terms), ("privacy", privacy), ("support", support)]:
        if not val or stub in val or (name != "support" and not val.startswith("http")):
            print(f"FAIL: {name}={val!r}", file=sys.stderr)
            return 4
    print("OK: legal URLs in SQLite")

    stars = os.getenv("STARS_ENABLED", "true").lower() == "true"
    if not stars:
        print("FAIL: STARS_ENABLED", file=sys.stderr)
        return 5
    print("OK: STARS_ENABLED")
    print("COM-MONETIZE_GO_LIVE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
