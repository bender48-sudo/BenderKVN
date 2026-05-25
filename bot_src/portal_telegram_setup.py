"""Signed setup page for Telegram users (Mini App / portal) — not email trial."""
from __future__ import annotations

import logging

from shop_bot.setup_url_service import get_setup_url_for_user
from shop_bot.subscription_resolve import subscription_unavailable
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
        setup_page_url, reason = await get_setup_url_for_user(tid)
    except Exception as exc:
        logger.exception("telegram_setup failed tid=%s", tid)
        return {"ok": False, "error": "upstream_failed", "detail": str(exc)[:120]}

    if not setup_page_url:
        if reason == "no_subscription":
            return {"ok": False, **subscription_unavailable(tid)}
        return {
            "ok": False,
            "error": reason or "token_failed",
            "message": "Не удалось подготовить страницу настройки. Напиши в поддержку.",
        }

    from shop_bot.subscription_cache import get_subscription_url_cached

    sub_url = await get_subscription_url_cached(tid)
    return {
        "ok": True,
        "setup_page_url": setup_page_url,
        "sub_url": sub_url,
        "telegram_id": tid,
    }
