"""In-app Mini App referral (P3): invite link, counts, invitees, partner block.

MINI-APP-BUILD-001 / MINI-APP-MIGRATION-PLAN-2026-06-25 (P3). READ-ONLY snapshot:

* **Link + code reuse existing attribution.** ``users.ref_code`` and the ``referrals``
  table are the same identity the bot deep-links (``?start=ref_<code>``) and the portal
  carries (``?ref=<code>``). No new attribution path is introduced.
* **Earnings are real, from the ledger — never fabricated.** ``earned_rub`` is the sum of this
  referrer's ``referral_reward``/``partner_reward`` rows in ``balance_ledger``; each invitee's
  ``reward_rub`` is its credited ``ref_first:<id>`` row, or ``None`` if nothing was credited yet.
  Accrual is gated by ``referral_rewards_active()`` (default OFF), so until an owner enables it
  these are an honest ``0.0`` / ``None`` — not a guessed number. Per-invitee status (``paid`` vs
  ``registered``) is a real fact from the invitee's top-up history. Empty state is honest: 0
  friends → empty ``invitees`` and zero counts.
* **Partner tier is dormant.** No partner approval system exists (DEC-IMPL-006/007), so
  ``partner.is_partner`` is always False today. The block's shape is defined so the
  read-only partner screen can be built, but ``withdraw_enabled`` is False — the withdraw
  form (reqs → ticket) waits on the ticket system (P4).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from shop_bot.config import (
    REFERRAL_FRIEND_BONUS_RUB,
    REFERRAL_PARTNER_FIRST_PCT,
    REFERRAL_PARTNER_MIN_WITHDRAW_RUB,
    REFERRAL_PARTNER_RECURRING_PCT,
    REFERRAL_REFERRER_PCT,
    referral_rewards_active,
)
from shop_bot.data_manager.database import (
    ensure_user_ref_code,
    get_referral_invitees,
    get_referral_rewards_by_invitee,
    get_user,
    sum_ledger_kinds,
)
from shop_bot.web_trial_db import (
    get_claim_by_customer_id,
    get_web_trial_claim,
    normalize_contact_email,
)

logger = logging.getLogger(__name__)


def _iso_utc(raw) -> str | None:
    """referrals/user_actions timestamps are 'YYYY-MM-DD HH:MM:SS' (SQLite UTC)."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    candidate = text.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


# -------------------- Invite link --------------------
def _bot_invite_url(ref_code: str) -> str:
    username = (os.getenv("TELEGRAM_BOT_USERNAME") or "Bender_KVN_bot").strip().lstrip("@")
    return f"https://t.me/{username}?start=ref_{ref_code}"


def _invite_url(ref_code: str) -> str:
    """Portal-first share link (carries ?ref=); falls back to the bot deep link."""
    try:
        from shop_bot.public_urls import portal_page_url

        return portal_page_url("", query={"ref": ref_code})
    except Exception:
        return _bot_invite_url(ref_code)


# -------------------- Invitee display --------------------
def _display_name(username: str | None) -> str:
    name = (username or "").strip().lstrip("@")
    return name if name else "Без имени"


def _avatar_letter(username: str | None) -> str:
    name = (username or "").strip().lstrip("@")
    return name[0].upper() if name else "?"


# -------------------- Program / partner blocks --------------------
def _program() -> dict:
    """Advertised terms (server-driven, not hardcoded in the front). Display-only."""
    return {
        # False until real accrual is wired — the front must not render earned ₽ as final.
        "rewards_active": referral_rewards_active(),
        "friend_bonus_rub": REFERRAL_FRIEND_BONUS_RUB,
        "referrer_pct": REFERRAL_REFERRER_PCT,
        "partner": {
            "first_pct": REFERRAL_PARTNER_FIRST_PCT,
            "recurring_pct": REFERRAL_PARTNER_RECURRING_PCT,
            "friend_bonus_rub": REFERRAL_FRIEND_BONUS_RUB,
            "min_withdraw_rub": REFERRAL_PARTNER_MIN_WITHDRAW_RUB,
        },
    }


def _partner_block() -> dict:
    """Dormant partner state — no approval system exists yet (DEC-IMPL-006/007).

    Shape is defined so the read-only partner screen (screen 2) can be built, but every
    figure is zero/none today and withdraw is gated (waits on the ticket system, P4).
    """
    return {
        "is_partner": False,
        "status": "none",  # none | pending | approved
        "slug": None,  # /p/{slug} once approved
        "display_name": None,
        "clients_count": 0,
        "total_earned_rub": 0.0,
        "available_rub": 0.0,  # «доступно к выводу»
        "withdraw_enabled": False,  # gated → waits on ticket system (P4)
        "min_withdraw_rub": REFERRAL_PARTNER_MIN_WITHDRAW_RUB,
    }


# -------------------- Identity resolution (Telegram-keyed) --------------------
def _resolve_referral_user(
    telegram_id: int | None, customer_id: str, email: str
) -> tuple[int | None, str | None]:
    """Resolve to the Telegram user_id that owns the ref_code. (user_id, error)."""
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
        # Referral attribution is Telegram-keyed; web-only users have no ref_code yet.
        return None, "needs_telegram_bind"
    if not get_user(int(tid)):
        return None, "not_found"
    return int(tid), None


def build_referral(user_id: int) -> dict:
    ref_code = ensure_user_ref_code(user_id)
    if not ref_code:
        return {"ok": False, "error": "ref_code_unavailable"}

    invite_url = _invite_url(ref_code)
    # Real per-invitee credited rewards from the ledger (empty while accrual is gated OFF).
    rewards_by_invitee = get_referral_rewards_by_invitee(user_id)
    invitees: list[dict] = []
    paid_count = 0
    for row in get_referral_invitees(ref_code):
        first_topup = row.get("first_topup_at")
        paid = bool(first_topup)
        if paid:
            paid_count += 1
        inv_id = row.get("referred_user_id")
        reward_kopeks = rewards_by_invitee.get(int(inv_id)) if inv_id is not None else None
        invitees.append(
            {
                "user_id": inv_id,
                "name": _display_name(row.get("username")),
                "avatar_letter": _avatar_letter(row.get("username")),
                "status": "paid" if paid else "registered",
                "joined_at_iso": _iso_utc(row.get("joined_at")),
                "first_topup_at_iso": _iso_utc(first_topup) if paid else None,
                # Real credited reward for this invitee (None until accrual is live → no fake ₽).
                "reward_rub": round(reward_kopeks / 100, 2) if reward_kopeks else None,
            }
        )

    # Real total credited to this referrer (ref_first:* + partner rows). 0 while gated OFF.
    earned_kopeks = sum_ledger_kinds(user_id, ("referral_reward", "partner_reward"))

    return {
        "ok": True,
        "available": True,
        "ref_code": ref_code,
        "invite_url": invite_url,  # portal-first share link (?ref=)
        "bot_invite_url": _bot_invite_url(ref_code),  # t.me deep-link alternate
        "qr_url": invite_url,  # what the QR should encode
        "friends_count": len(invitees),
        "friends_paid_count": paid_count,
        # Real, from the ledger — never fabricated. Honest 0.0 until accrual is enabled.
        "earned_rub": round(max(earned_kopeks, 0) / 100, 2),
        "invitees": invitees,
        "program": _program(),
        "partner": _partner_block(),
    }


def referral_snapshot(
    *, telegram_id: int | None = None, customer_id: str = "", email: str = ""
) -> dict:
    """Referral snapshot for a Telegram bot user or a Telegram-bound web claim."""
    user_id, err = _resolve_referral_user(telegram_id, customer_id, email)
    if err == "needs_telegram_bind":
        # Web-only user: no ref_code to show until they bind Telegram. Honest gated state.
        return {
            "ok": True,
            "available": False,
            "needs_telegram_bind": True,
            "program": _program(),
            "partner": _partner_block(),
        }
    if err:
        return {"ok": False, "error": err}
    return build_referral(user_id)
