#!/usr/bin/env python3
"""P6-RED-PAY-01 smoke: webhook idempotency + duplicate topup (run in remna-shop-bot)."""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime


def test_webhook_claim() -> bool:
    from shop_bot.data_manager.database import (
        claim_webhook_delivery,
        count_webhook_dlq,
        mark_webhook_done,
        mark_webhook_failed,
    )

    key = f"smoke_wh_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    s1 = claim_webhook_delivery(key, "smoke", "{}")
    s2 = claim_webhook_delivery(key, "smoke", "{}")
    if s1 != "new" or s2 not in ("in_progress", "duplicate"):
        print(f"FAIL: claim s1={s1} s2={s2}", file=sys.stderr)
        return False
    mark_webhook_done(key)
    s3 = claim_webhook_delivery(key, "smoke", "{}")
    if s3 != "duplicate":
        print(f"FAIL: after done expected duplicate, got {s3}", file=sys.stderr)
        return False
    fail_key = key + "_fail"
    claim_webhook_delivery(fail_key, "smoke", "{}")
    mark_webhook_failed(fail_key, "smoke test")
    if count_webhook_dlq() < 1:
        print("FAIL: DLQ count", file=sys.stderr)
        return False
    print("OK: webhook claim + DLQ")
    return True


async def test_topup_duplicate() -> bool:
    import os

    from aiogram import Bot
    from shop_bot.bot.handlers import process_topup_payment
    from shop_bot.config import DAILY_RATE
    from shop_bot.data_manager.database import get_balance

    admin_id = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
    if not admin_id:
        print("SKIP: topup duplicate (no ADMIN_TELEGRAM_ID)")
        return True

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    bot = Bot(token=token)
    try:
        idem = f"smoke_wh_topup_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        bal0 = get_balance(int(admin_id))
        ok1 = await process_topup_payment(
            bot, int(admin_id), float(DAILY_RATE), idempotency_key=idem, notify=False
        )
        bal1 = get_balance(int(admin_id))
        ok2 = await process_topup_payment(
            bot, int(admin_id), float(DAILY_RATE), idempotency_key=idem, notify=False
        )
        bal2 = get_balance(int(admin_id))
        if not ok1 or ok2 or abs(bal2 - bal1) > 0.01:
            print(
                f"FAIL: topup dup ok1={ok1} ok2={ok2} bal0={bal0} bal1={bal1} bal2={bal2}",
                file=sys.stderr,
            )
            return False
        print("OK: duplicate topup ignored")
        return True
    finally:
        await bot.session.close()


async def main() -> int:
    if not test_webhook_claim():
        return 1
    if not await test_topup_duplicate():
        return 2
    print("WEBHOOK_PAY_IDEMPOTENCY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
