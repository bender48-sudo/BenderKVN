"""Auto-notify users to refresh VPN subscription after server config changes."""
from __future__ import annotations

import asyncio
import logging
import random
import time

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter

from shop_bot.bot import user_messages
from shop_bot.config import SUB_REFRESH_JITTER_MAX_SEC
from shop_bot.data_manager import database

logger = logging.getLogger(__name__)

SUB_REFRESH_BATCH = 50
SUB_REFRESH_SEND_INTERVAL_SEC = 0.035


async def _send_with_rate_limit(bot: Bot, user_id: int, text: str) -> None:
    """Send one notify; honor Telegram 429 with backoff."""
    while True:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        except TelegramRetryAfter as e:
            wait = float(getattr(e, "retry_after", 1)) + 0.5
            logger.warning("sub refresh 429 user=%s sleep %.1fs", user_id, wait)
            await asyncio.sleep(wait)


async def run_sub_refresh_notify_batch(bot: Bot) -> tuple[int, int]:
    """Notify up to SUB_REFRESH_BATCH users behind current sub_config_generation.

    Returns (sent_ok, sent_fail).
    """
    current_gen = database.get_sub_config_generation()
    if current_gen <= 0:
        return 0, 0

    pending = database.list_users_pending_sub_refresh(current_gen, limit=SUB_REFRESH_BATCH)
    if not pending:
        return 0, 0

    if SUB_REFRESH_JITTER_MAX_SEC > 0:
        delay = random.uniform(0, SUB_REFRESH_JITTER_MAX_SEC)
        logger.info("sub refresh notify jitter %.1fs before batch gen=%s", delay, current_gen)
        await asyncio.sleep(delay)

    profile = (database.get_setting("vpn_profile_name") or "").strip()
    text = user_messages.msg_sub_config_refresh(profile or "🚀 BenderVPN Auto")
    ok = fail = 0
    batch_t0 = time.monotonic()
    for user_id in pending:
        try:
            await _send_with_rate_limit(bot, user_id, text)
            database.update_sub_refresh_notified_generation(user_id, current_gen)
            ok += 1
        except Exception as e:
            logger.warning("sub refresh notify failed for %s: %s", user_id, e)
            fail += 1
        await asyncio.sleep(SUB_REFRESH_SEND_INTERVAL_SEC)

    if ok or fail:
        elapsed = time.monotonic() - batch_t0
        logger.info(
            "sub refresh notify batch gen=%s ok=%s fail=%s elapsed=%.1fs",
            current_gen,
            ok,
            fail,
            elapsed,
        )
    return ok, fail
