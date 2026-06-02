#!/usr/bin/env python3
"""Credit missed YooKassa topups (payment.succeeded) and notify user. Run in remna-shop-bot."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from yookassa import Configuration, Payment


async def main() -> int:
    from aiogram import Bot
    from shop_bot.bot.handlers import process_topup_payment
    from shop_bot.data_manager.database import has_action

    sid = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
    sec = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not sid or not sec or not token:
        print("FAIL: missing YOOKASSA or TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    Configuration.account_id = sid
    Configuration.secret_key = sec
    bot = Bot(token=token)

    since = datetime.now(timezone.utc) - timedelta(hours=48)
    params = {
        "created_at.gte": since.isoformat(),
        "status": "succeeded",
        "limit": 20,
    }
    try:
        payments = Payment.list(params)
    except Exception as e:
        print(f"FAIL: Payment.list: {e}", file=sys.stderr)
        return 1

    items = getattr(payments, "items", None) or []
    credited = 0
    for pay in items:
        meta = getattr(pay, "metadata", None) or {}
        if meta.get("t") != "topup":
            continue
        pid = getattr(pay, "id", None)
        if not pid:
            continue
        idem = f"yookassa:{pid}"
        user_id = int(meta.get("user_id") or meta.get("u") or 0)
        amount = float(meta.get("amount") or meta.get("a") or 0)
        if user_id <= 0 or amount <= 0:
            print(f"SKIP {pid}: bad meta")
            continue
        if has_action(user_id, idem):
            print(f"SKIP {pid}: already credited")
            continue
        ok = await process_topup_payment(
            bot, user_id, amount, idempotency_key=idem, notify=True
        )
        print(f"{'OK' if ok else 'WARN'} {pid} user={user_id} +{amount}RUB")
        credited += 1

    await bot.session.close()
    print(f"RECONCILE_DONE credited={credited}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
