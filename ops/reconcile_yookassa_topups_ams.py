#!/usr/bin/env python3
"""Credit missed YooKassa topups (payment.succeeded) and notify user.

Run inside remna-shop-bot only. Default: dry-run (no balance changes).
Pass --apply only after explicit owner approval — mutates balances.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from yookassa import Configuration, Payment


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reconcile missed YooKassa top-up credits")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Credit missed topups (default: dry-run only)",
    )
    p.add_argument(
        "--hours",
        type=int,
        default=48,
        metavar="N",
        help="Look back N hours for succeeded payments (default: 48)",
    )
    return p.parse_args()


def _already_credited(user_id: int, payment_id: str, has_action) -> bool:
    from shop_bot.payment_idempotency import (
        LEGACY_YOOKASSA_RECONCILE_PREFIX,
        yookassa_topup_action_key,
    )

    canonical = yookassa_topup_action_key(payment_id)
    if has_action(user_id, canonical):
        return True
    legacy = f"{LEGACY_YOOKASSA_RECONCILE_PREFIX}{payment_id}"
    return has_action(user_id, legacy)


async def main() -> int:
    from aiogram import Bot
    from shop_bot.bot.handlers import process_topup_payment
    from shop_bot.data_manager.database import has_action
    from shop_bot.payment_idempotency import yookassa_topup_action_key

    args = _parse_args()
    if not args.apply:
        print(
            "DRY_RUN: no balance changes. Pass --apply only with explicit owner approval.",
            file=sys.stderr,
        )

    sid = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
    sec = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not sid or not sec or not token:
        print("FAIL: missing YOOKASSA or TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    Configuration.account_id = sid
    Configuration.secret_key = sec
    bot = Bot(token=token)

    since = datetime.now(timezone.utc) - timedelta(hours=max(1, args.hours))
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
        idem = yookassa_topup_action_key(str(pid))
        user_id = int(meta.get("user_id") or meta.get("u") or 0)
        amount = float(meta.get("amount") or meta.get("a") or 0)
        if user_id <= 0 or amount <= 0:
            print(f"SKIP {pid}: bad meta")
            continue
        if _already_credited(user_id, str(pid), has_action):
            print(f"SKIP {pid}: already credited ({idem})")
            continue
        if not args.apply:
            print(f"DRY_RUN WOULD_CREDIT {pid} user={user_id} +{amount}RUB key={idem}")
            continue
        ok = await process_topup_payment(
            bot, user_id, amount, idempotency_key=idem, notify=True
        )
        print(f"{'OK' if ok else 'WARN'} {pid} user={user_id} +{amount}RUB key={idem}")
        credited += 1

    await bot.session.close()
    if args.apply:
        print(f"RECONCILE_APPLY_DONE credited={credited}")
    else:
        print(f"RECONCILE_DRY_RUN_DONE would_credit={credited}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
