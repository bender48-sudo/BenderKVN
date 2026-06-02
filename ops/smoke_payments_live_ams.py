#!/usr/bin/env python3
"""Smoke P2-COM-MONETIZE-02 on AMS (run inside remna-shop-bot container or with same env).

Checks: BOT_PAYMENTS_LIVE, Stars disabled, YooKassa configured, topup idempotency.
Exit 0 on success.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime

# When run via: docker exec remna-shop-bot python /tmp/smoke_payments_live_ams.py


async def _panel_expire(telegram_id: str) -> str | None:
    import aiohttp
    from shop_bot.modules import remnawave_api

    async with aiohttp.ClientSession() as session:
        user = await remnawave_api.get_user_by_telegram_id(session, telegram_id)
        return (user or {}).get("expireAt")


async def main() -> int:
    from shop_bot.config import BOT_PAYMENTS_LIVE, DAILY_RATE

    if not BOT_PAYMENTS_LIVE:
        print("FAIL: BOT_PAYMENTS_LIVE is false", file=sys.stderr)
        return 1
    print("OK: BOT_PAYMENTS_LIVE=true")

    stars = os.getenv("STARS_ENABLED", "false").lower() in ("1", "true", "yes")
    if stars:
        print("FAIL: STARS_ENABLED must be false (Stars removed)", file=sys.stderr)
        return 2
    print("OK: STARS_ENABLED=false")

    sid = (os.getenv("YOOKASSA_SHOP_ID") or "").strip()
    sec = (os.getenv("YOOKASSA_SECRET_KEY") or "").strip()
    if not sid or not sec:
        print("FAIL: YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY missing", file=sys.stderr)
        return 3
    print("OK: YooKassa credentials present")

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("FAIL: TELEGRAM_BOT_TOKEN missing", file=sys.stderr)
        return 4

    from aiogram import Bot

    bot = Bot(token=token)
    try:
        admin_id = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
        if admin_id and os.getenv("SMOKE_PANEL_EXPIRE", "1") == "1":
            from shop_bot.bot.handlers import process_topup_payment
            from shop_bot.data_manager.database import get_balance

            before = await _panel_expire(admin_id)
            idem = f"smoke_topup_{datetime.utcnow().strftime('%Y%m%d')}"
            synced = await process_topup_payment(
                bot,
                int(admin_id),
                float(DAILY_RATE),
                idempotency_key=idem,
                notify=False,
            )
            after = await _panel_expire(admin_id)
            bal = get_balance(int(admin_id))
            print(f"OK: panel expireAt before={before}")
            print(f"OK: panel expireAt after={after} synced={synced} balance={bal:.2f}")
            if not after:
                print("FAIL: expireAt missing after topup smoke", file=sys.stderr)
                return 5
            dup = await process_topup_payment(
                bot, int(admin_id), float(DAILY_RATE), idempotency_key=idem, notify=False
            )
            if dup:
                print("FAIL: duplicate idempotency key was processed twice", file=sys.stderr)
                return 6
            print("OK: duplicate topup ignored (idempotency)")
    finally:
        await bot.session.close()

    print("SMOKE: payments live OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
