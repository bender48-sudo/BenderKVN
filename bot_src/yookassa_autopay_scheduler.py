"""Run due YooKassa card autopay charges."""
from __future__ import annotations

import logging

from aiogram import Bot

from shop_bot.config import BOT_PAYMENTS_LIVE
from shop_bot.data_manager.database import (
    list_yookassa_autopay_due,
    get_yookassa_payment_method_id,
    set_yookassa_autopay_error,
    set_yookassa_autopay_enabled,
)
from shop_bot.yookassa_autopay import create_recurring_charge

logger = logging.getLogger(__name__)


async def run_yookassa_autopay_batch(bot: Bot, limit: int = 15) -> int:
    """Initiate recurring charges for users past next_at. Returns count started."""
    # BILL-AUTOPAY-LIVE-GUARD-001: defense in depth. The scheduler only starts the
    # autopay loop when BOT_PAYMENTS_LIVE, but a direct call (future code / tests)
    # must never charge real cards unless payments are explicitly live.
    if not BOT_PAYMENTS_LIVE:
        logger.info("yookassa autopay batch skipped: BOT_PAYMENTS_LIVE is false")
        return 0
    due = list_yookassa_autopay_due(limit=limit)
    started = 0
    for user_id in due:
        pm_id = get_yookassa_payment_method_id(user_id)
        if not pm_id:
            continue
        pay_id, err = create_recurring_charge(user_id, pm_id)
        if pay_id:
            started += 1
            logger.info("yookassa autopay started user=%s payment=%s", user_id, pay_id)
        else:
            set_yookassa_autopay_error(user_id, err or "charge_failed")
            set_yookassa_autopay_enabled(user_id, False)
            try:
                from shop_bot.bot import user_messages

                await bot.send_message(
                    user_id,
                    user_messages.msg_autopay_failed(),
                    parse_mode="HTML",
                )
            except Exception:
                pass
    return started
