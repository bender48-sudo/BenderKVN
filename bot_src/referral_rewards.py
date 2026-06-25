"""Idempotent referral / partner reward accrual (REF-LEDGER-001).

Gated by ``config.referral_rewards_active()`` (default OFF). Every credit goes through
``database.credit_ledger`` → exactly one ``balance_ledger`` row per (user, ref) plus the
matching ``users.balance`` bump, so an event can never double-pay. These functions mutate
balance, so flipping the gate live is a separate owner OK; until then they are no-ops and the
referral screen's ``earned_rub`` stays an honest 0.

Canon reward model:
* friend (invitee): +``REFERRAL_FRIEND_BONUS_RUB`` on registration   (ref ``ref_welcome``)
* referrer: +``REFERRAL_REFERRER_PCT`` % of the invitee's FIRST top-up (ref ``ref_first:<id>``)
* partner 50/10: deferred — no partner-approval system yet (hook shape only).
"""
from __future__ import annotations

import json
import logging

from shop_bot.config import (
    REFERRAL_FRIEND_BONUS_RUB,
    REFERRAL_REFERRER_PCT,
    referral_rewards_active,
)
from shop_bot.data_manager.database import (
    credit_ledger,
    get_user,
    get_user_by_ref_code,
)

logger = logging.getLogger(__name__)


def credit_referral_welcome(invitee_id: int) -> bool:
    """+REFERRAL_FRIEND_BONUS_RUB ₽ to a newly-registered invitee. Idempotent; gated OFF.

    Fires only for a user who joined via a referral code (``referred_by`` set) and has agreed to
    terms (anti-abuse: real registration). ref=``ref_welcome`` → once per user, ever.
    """
    if not referral_rewards_active():
        return False
    user = get_user(invitee_id)
    if not user or not (user.get("referred_by") or "").strip():
        return False
    if not user.get("agreed_to_terms"):
        return False
    kopeks = int(REFERRAL_FRIEND_BONUS_RUB) * 100
    if kopeks <= 0:
        return False
    meta = json.dumps({"reason": "welcome", "referred_by": user.get("referred_by")})
    return credit_ledger(invitee_id, "referral_reward", kopeks, "ref_welcome", meta=meta)


def credit_referrer_first_topup(invitee_id: int, topup_rub: float) -> bool:
    """+REFERRAL_REFERRER_PCT % of the invitee's FIRST top-up to the referrer. Idempotent; gated.

    The caller is responsible for only invoking this on the invitee's first top-up; ref
    ``ref_first:<invitee_id>`` makes a duplicate call a no-op regardless.
    """
    if not referral_rewards_active():
        return False
    invitee = get_user(invitee_id)
    if not invitee:
        return False
    ref_code = (invitee.get("referred_by") or "").strip()
    if not ref_code:
        return False
    referrer = get_user_by_ref_code(ref_code)
    if not referrer:
        return False
    referrer_id = int(referrer["telegram_id"])
    if referrer_id == invitee_id:
        return False
    reward_kopeks = round(float(topup_rub) * 100 * int(REFERRAL_REFERRER_PCT) / 100)
    if reward_kopeks <= 0:
        return False
    meta = json.dumps(
        {"reason": "first_topup", "from_user": invitee_id, "pct": int(REFERRAL_REFERRER_PCT)}
    )
    return credit_ledger(
        referrer_id, "referral_reward", int(reward_kopeks), f"ref_first:{invitee_id}", meta=meta
    )
