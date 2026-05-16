"""Auto-notify users to refresh VPN subscription after server config changes."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ParseMode

from shop_bot.bot import user_messages
from shop_bot.data_manager import database

logger = logging.getLogger(__name__)

# Telegram ~30 msg/s; stay conservative inside the 5-minute monitor cycle.
SUB_REFRESH_BATCH = 15


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

    text = user_messages.MSG_SUB_CONFIG_REFRESH
    ok = fail = 0
    for user_id in pending:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            database.update_sub_refresh_notified_generation(user_id, current_gen)
            ok += 1
        except Exception as e:
            logger.warning("sub refresh notify failed for %s: %s", user_id, e)
            fail += 1

    if ok or fail:
        logger.info(
            "sub refresh notify batch gen=%s ok=%s fail=%s pending_left=%s",
            current_gen,
            ok,
            fail,
            max(0, len(pending) - ok),
        )
    return ok, fail
