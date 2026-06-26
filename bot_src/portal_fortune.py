"""In-app Fortune wheel API (GAME-FORTUNE-001, P5).

Thin request layer over ``fortune`` (server-authoritative engine). Telegram-keyed identity.
``status`` is safe to serve always (honest zeros + fortune_live flag); ``spin`` is gated by
``FORTUNE_LIVE`` (no spins/credits until owner OK) and is fully server-authoritative — the
client never decides the outcome.
"""
from __future__ import annotations

from shop_bot.data_manager.database import get_user
from shop_bot.web_trial_db import (
    get_claim_by_customer_id,
    get_web_trial_claim,
    normalize_contact_email,
)


def _resolve(telegram_id, customer_id, email) -> tuple[int | None, str | None]:
    if telegram_id and int(telegram_id) > 0:
        if not get_user(int(telegram_id)):
            return None, "not_found"
        return int(telegram_id), None
    claim = None
    em = normalize_contact_email(email)
    if em:
        claim = get_web_trial_claim(em)
    if not claim and customer_id:
        claim = get_claim_by_customer_id(customer_id)
    if not claim:
        return None, "not_found"
    tid = claim.get("telegram_id")
    if not tid:
        return None, "needs_telegram_bind"
    if not get_user(int(tid)):
        return None, "not_found"
    return int(tid), None


def status(*, telegram_id=None, customer_id="", email="") -> dict:
    uid, err = _resolve(telegram_id, customer_id, email)
    if err:
        return {"ok": False, "error": err}
    from shop_bot import fortune

    return fortune.status(uid)


def spin(*, telegram_id=None, customer_id="", email="") -> dict:
    uid, err = _resolve(telegram_id, customer_id, email)
    if err:
        return {"ok": False, "error": err}
    from shop_bot import fortune

    return fortune.spin(uid)
