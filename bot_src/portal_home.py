"""In-app Mini App home summary (P-HOME): aggregating entry-point snapshot.

MINI-APP-BUILD-001 / design/mockups/home_mockup.html. READ-ONLY. Composes the existing
``cabinet_snapshot`` (access + balance) and ``referral_snapshot`` (friends + ₽) into one
compact payload for the home screen — no new data source, no mutation.

Honest-UI:
* Access status, days, device count, balance and referral counters are all real, from the
  same builders the dedicated screens use.
* The «ёмкость» widget has **no live counter yet** → ``capacity.counter_available`` is False and
  there is no fill number to fabricate; the UI shows «счётчик скоро».
* ``unread`` is 0 until the ticket system (P4) lands — the bell shows no fake badge.
* The Fortune banner is surfaced in an ``in_development`` state (GAME-FORTUNE-001), gated by a
  flag — it links nowhere live.
"""
from __future__ import annotations

from datetime import datetime, timezone

from shop_bot.config import CAPACITY_SOFT_LIMIT, FORTUNE_BANNER_ENABLED
from shop_bot.portal_cabinet import cabinet_snapshot
from shop_bot.portal_referral import referral_snapshot

# billing_profile (from cabinet) → home access status + RU labels.
_ACCESS_MAP = {
    "trial": ("trial", "Триал", "Триал активен"),
    "wallet": ("active", "Активен", "Доступ активен"),
    "legacy": ("active", "Активен", "Доступ активен"),
    "expired": ("paused", "Пауза", "Доступ на паузе"),
    "unknown": ("unknown", "Статус", "Статус уточняется"),
}


def _days_until(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - datetime.now(timezone.utc)
    days = delta.days + (1 if delta.seconds or delta.microseconds else 0)
    return max(days, 0)


def _build_access(cab: dict) -> dict:
    profile = (cab.get("billing_profile") or cab.get("access_profile") or "unknown").strip()
    status, status_label, card_title = _ACCESS_MAP.get(profile, _ACCESS_MAP["unknown"])
    device_count = int(cab.get("active_config_count") or 0)
    expires_iso = cab.get("access_expires_at_iso")
    days_left = _days_until(expires_iso)
    if days_left is None:
        days_left = int(cab.get("days_left") or 0)
    has_access = status in ("trial", "active") and device_count > 0
    return {
        "status": status,
        "status_label": status_label,
        "card_title": card_title,
        "days_left": days_left,
        "expires_at_iso": expires_iso,
        "expires_at": cab.get("access_expires_at"),
        "device_count": device_count,
        "traffic_unlimited": True,  # BenderVPN has no per-device traffic cap (honest, fixed policy)
        "has_access": has_access,
    }


def _build_referral_summary(ref: dict) -> dict:
    if not ref or not ref.get("ok") or ref.get("available") is False:
        return {"friends_count": 0, "earned_rub": 0.0, "available": False}
    return {
        "friends_count": int(ref.get("friends_count") or 0),
        "earned_rub": float(ref.get("earned_rub") or 0.0),
        "available": True,
    }


def _compose(cab: dict, ref: dict) -> dict:
    access = _build_access(cab)
    profile = cab.get("profile") or {}
    return {
        "ok": True,
        "profile": {
            # first_name is not stored server-side; the UI prefers Telegram initData for the
            # greeting and falls back to username here.
            "name": None,
            "username": profile.get("username"),
            "language": profile.get("language") or "ru",
        },
        "unread": 0,  # bell badge — 0 until tickets (P4)
        "access": access,
        "balance": {
            "balance_rub": float(cab.get("balance_rub") or 0.0),
            "days_left": int(cab.get("days_left") or 0),
        },
        "referral": _build_referral_summary(ref),
        "capacity": {
            "counter_available": False,  # no live active-subscription counter yet → «счётчик скоро»
            "cap_limit": CAPACITY_SOFT_LIMIT,
        },
        "banners": {
            "referral": True,
            "fortune": {"show": bool(FORTUNE_BANNER_ENABLED), "state": "in_development"},
            "access_card": True,
        },
    }


def home_snapshot(
    *, telegram_id: int | None = None, customer_id: str = "", email: str = ""
) -> dict:
    """Aggregated home payload. Propagates cabinet errors (not_found / terms_required)."""
    cab = cabinet_snapshot(telegram_id=telegram_id, customer_id=customer_id, email=email)
    if not cab.get("ok"):
        # Entry point: surface the same actionable error/bot_url the cabinet returns.
        return cab
    ref = referral_snapshot(telegram_id=telegram_id, customer_id=customer_id, email=email)
    return _compose(cab, ref)
