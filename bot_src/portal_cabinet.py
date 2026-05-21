"""Read-only web cabinet snapshot (P3-FLOW-15)."""
from __future__ import annotations

from shop_bot.config import DAILY_RATE, balance_to_days
from shop_bot.data_manager.database import get_user
from shop_bot.web_trial_db import (
    format_customer_id,
    get_claim_by_customer_id,
    get_web_trial_claim,
    is_web_surrogate_id,
    normalize_contact_email,
)


def _bot_open_url() -> str:
    import os

    username = (os.getenv("TELEGRAM_BOT_USERNAME") or "Bender_KVN_bot").strip().lstrip("@")
    return f"https://t.me/{username}"


def _cabinet_for_telegram(telegram_id: int) -> dict:
    """Balance for bot user opened Mini App from Telegram."""
    user = get_user(telegram_id)
    if not user:
        return {
            "ok": False,
            "error": "not_found",
            "message": "Нажмите /start в боте, затем «Принимаю».",
            "bot_url": _bot_open_url(),
        }
    if not user.get("agreed_to_terms"):
        return {
            "ok": False,
            "error": "terms_required",
            "message": (
                "Сначала в боте примите условия («Принимаю»), "
                "затем «Начать бесплатно» или «Мой VPN»."
            ),
            "bot_url": _bot_open_url(),
        }
    balance = float(user.get("balance") or 0)
    days = balance_to_days(balance)
    return {
        "ok": True,
        "customer_id": f"TG-{telegram_id}",
        "balance_rub": round(balance, 2),
        "days_left": days,
        "daily_rate": DAILY_RATE,
        "telegram_bound": True,
        "web_only": False,
        "source": "telegram",
        "bot_url": _bot_open_url(),
    }


def cabinet_snapshot(
    *,
    customer_id: str = "",
    email: str = "",
    telegram_id: int | None = None,
) -> dict:
    """Balance/days for web trial or Telegram bot user (no secrets)."""
    tid = int(telegram_id) if telegram_id else 0
    if tid > 0:
        return _cabinet_for_telegram(tid)

    claim = None
    em = normalize_contact_email(email)
    if em:
        from shop_bot.web_trial_db import get_web_trial_claim

        claim = get_web_trial_claim(em)
    if not claim and customer_id:
        claim = get_claim_by_customer_id(customer_id)
    if not claim:
        return {"ok": False, "error": "not_found"}

    web_uid = int(claim["web_user_id"])
    user = get_user(web_uid)
    if not user and claim.get("telegram_id"):
        user = get_user(int(claim["telegram_id"]))
    balance = float(user["balance"]) if user and user.get("balance") is not None else 0.0
    days = balance_to_days(balance)
    tg_bound = bool(claim.get("telegram_id"))
    out = {
        "ok": True,
        "customer_id": format_customer_id(web_uid),
        "balance_rub": round(balance, 2),
        "days_left": days,
        "daily_rate": DAILY_RATE,
        "telegram_bound": tg_bound,
        "web_only": is_web_surrogate_id(web_uid) and not tg_bound,
    }
    if not tg_bound and is_web_surrogate_id(web_uid):
        out["needs_telegram_bind"] = True
    return out
