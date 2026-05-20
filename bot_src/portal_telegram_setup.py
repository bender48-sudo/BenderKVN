"""Signed setup page for Telegram users (Mini App / portal) — not email trial."""
from __future__ import annotations

import logging

from shop_bot.bot import portal_links
from shop_bot.subscription_resolve import resolve_subscription_url, subscription_unavailable
from shop_bot.web_trial_db import is_web_surrogate_id

logger = logging.getLogger(__name__)


async def telegram_setup_for_user(telegram_id: int) -> dict:
    """
    Return personal /setup/?t= URL for an existing Telegram bot user.
    Does not create trials — only existing panel subscription.
    """
    tid = int(telegram_id)
    if tid <= 0 or is_web_surrogate_id(tid):
        return {
            "ok": False,
            "error": "invalid_telegram",
            "message": "Эта страница для аккаунта Telegram из бота. Введите email только на сайте в обычном браузере.",
        }

    try:
        sub_url = await resolve_subscription_url(tid)
    except Exception as exc:
        logger.exception("telegram_setup failed tid=%s", tid)
        return {"ok": False, "error": "upstream_failed", "detail": str(exc)[:120]}

    if not sub_url:
        return {"ok": False, **subscription_unavailable(tid)}

    setup_page_url = portal_links.setup_url_for_sub(sub_url)
    if not setup_page_url:
        return {
            "ok": False,
            "error": "token_failed",
            "message": "Не удалось подготовить страницу настройки. Напишите в поддержку.",
        }

    return {
        "ok": True,
        "setup_page_url": setup_page_url,
        "sub_url": sub_url,
        "telegram_id": tid,
    }
