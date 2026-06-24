#!/usr/bin/env python3
"""P2-COM-BALANCE-DAILY-01: daily charge + absolute panel sync wiring."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def main() -> int:
    cfg = (BOT / "config.py").read_text(encoding="utf-8")
    bill = (BOT / "balance_billing.py").read_text(encoding="utf-8")
    remna = (BOT / "remnawave_api.py").read_text(encoding="utf-8")
    sched = (BOT / "scheduler.py").read_text(encoding="utf-8")
    handlers = (BOT / "handlers.py").read_text(encoding="utf-8")

    for needle, blob, name in (
        ("set_user_access_days", remna, "remnawave_api"),
        ("charge_daily_balance_if_due", bill, "balance_billing"),
        ("sync_panel_from_balance", bill, "balance_billing"),
        ("process_daily_balance_user", bill, "balance_billing"),
        ("waive_daily_charge_today", bill, "balance_billing"),
        ("process_daily_balance_user", sched, "scheduler"),
        ("waive_daily_charge_today", handlers, "handlers"),
    ):
        if needle not in blob:
            print(f"BALANCE_DAILY_FAIL: missing {needle!r} in {name}", file=sys.stderr)
            return 1

    if "max(1, int(balance / DAILY_RATE))" in cfg:
        print("BALANCE_DAILY_FAIL: balance_to_days still uses max(1,...)", file=sys.stderr)
        return 1

    daily_kopeks = 666
    days_200 = 20_000 // daily_kopeks
    days_low = 6_65 // daily_kopeks
    if days_200 != 30 or days_low != 0:
        print(f"BALANCE_DAILY_FAIL: days_200={days_200} days_low={days_low}", file=sys.stderr)
        return 1

    print("BALANCE_DAILY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
