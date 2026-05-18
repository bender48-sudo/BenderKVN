"""Read-only web cabinet snapshot (P3-FLOW-15)."""
from __future__ import annotations

from shop_bot.config import DAILY_RATE, balance_to_days, telegram_bind_url
from shop_bot.data_manager.database import get_user
from shop_bot.web_trial_db import (
    ensure_bind_token,
    format_customer_id,
    get_claim_by_customer_id,
    get_web_trial_claim,
    is_web_surrogate_id,
    normalize_contact_email,
)


def cabinet_snapshot(*, customer_id: str = "", email: str = "") -> dict:
    """Balance/days for web trial user (no secrets)."""
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
    bind_token = ensure_bind_token(web_uid) if not tg_bound else ""
    out = {
        "ok": True,
        "customer_id": format_customer_id(web_uid),
        "balance_rub": round(balance, 2),
        "days_left": days,
        "daily_rate": DAILY_RATE,
        "telegram_bound": tg_bound,
        "web_only": is_web_surrogate_id(web_uid) and not tg_bound,
    }
    if bind_token:
        out["bind_url"] = telegram_bind_url(bind_token)
    return out
