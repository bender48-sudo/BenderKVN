"""Resolve Happ subscription URL for a Telegram bot user."""
from __future__ import annotations

import logging
import os
from datetime import datetime

from shop_bot.data_manager.database import get_user, get_user_keys
from shop_bot.modules.remnawave_api import (
    get_user_by_email,
    get_user_by_telegram_id,
    remna_client_session,
)
from shop_bot.public_urls import normalize_subscription_url

logger = logging.getLogger(__name__)


def _bot_open_url() -> str:
    username = (os.getenv("TELEGRAM_BOT_USERNAME") or "Bender_KVN_bot").strip().lstrip("@")
    return f"https://t.me/{username}"


async def resolve_subscription_url(telegram_id: int) -> str | None:
    """Panel lookup by telegram_id, then by vpn_keys.key_email."""
    tid = int(telegram_id)
    async with remna_client_session() as session:
        remote = await get_user_by_telegram_id(session, str(tid))
        sub = normalize_subscription_url((remote or {}).get("subscriptionUrl") or "")
        if sub:
            return sub

        keys = get_user_keys(tid)
        seen: set[str] = set()
        ordered = sorted(
            keys,
            key=lambda k: k.get("expiry_date") or "",
            reverse=True,
        )
        for key in ordered:
            em = (key.get("key_email") or "").strip()
            if not em or em in seen:
                continue
            seen.add(em)
            try:
                panel_user = await get_user_by_email(session, em)
            except Exception as exc:
                logger.warning("resolve sub by email %s: %s", em, exc)
                continue
            sub = normalize_subscription_url((panel_user or {}).get("subscriptionUrl") or "")
            if sub:
                return sub
    return None


def subscription_unavailable(telegram_id: int) -> dict:
    """Error payload for UI when resolve_subscription_url() is None."""
    tid = int(telegram_id)
    bot_url = _bot_open_url()
    user = get_user(tid)
    keys = get_user_keys(tid)
    if user and not user.get("agreed_to_terms"):
        return {
            "error": "terms_required",
            "message": (
                "Сначала в боте нажмите «Принимаю», затем «Начать бесплатно» в главном меню."
            ),
            "bot_url": bot_url,
        }
    trial_used = bool(user and user.get("trial_used"))
    now = datetime.now()
    active = [
        k
        for k in keys
        if datetime.fromisoformat(k["expiry_date"]) > now
    ]

    if active:
        return {
            "error": "panel_unreachable",
            "message": (
                "Ключ на сервере есть, но ссылку сейчас не получить. "
                "Подождите минуту и нажмите снова или напишите в поддержку."
            ),
            "bot_url": bot_url,
        }
    if keys and trial_used:
        return {
            "error": "subscription_expired",
            "message": (
                "Срок доступа истёк. В боте: «Мой VPN» → «Пополнить баланс». "
                "Кнопки «Начать бесплатно» у вас уже нет — trial был использован."
            ),
            "bot_url": bot_url,
        }
    if keys:
        return {
            "error": "no_subscription",
            "message": "Не удалось получить ссылку. Откройте бота → «Мой VPN» или поддержку.",
            "bot_url": bot_url,
        }
    if not trial_used:
        return {
            "error": "no_subscription",
            "message": "Сначала в боте нажмите «Начать бесплатно» (главное меню).",
            "bot_url": bot_url,
        }
    return {
        "error": "no_subscription",
        "message": "В боте: «Пополнить баланс» в разделе «Мой VPN».",
        "bot_url": bot_url,
    }
