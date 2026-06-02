"""Classify users: legacy manual panel / bot trial / paid wallet (P2-COM-ACCESS-PROFILE-01)."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from shop_bot.config import DAILY_RATE, balance_to_days
from shop_bot.data_manager.database import get_balance, get_user, has_action

# Panel expiry farther than this = ручной «вечный» доступ, не трогаем.
LEGACY_PANEL_MIN_DAYS = int(os.getenv("LEGACY_PANEL_MIN_DAYS", "400"))
LEGACY_PANEL_MIN_YEAR = int(os.getenv("LEGACY_PANEL_MIN_YEAR", "2030"))


def _parse_iso(dt_raw: str | None) -> datetime | None:
    if not dt_raw:
        return None
    try:
        dt = datetime.fromisoformat(str(dt_raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def panel_days_left(expire_iso: str | None) -> int:
    dt = _parse_iso(expire_iso)
    if not dt:
        return 0
    return (dt - datetime.now(timezone.utc)).days


def is_paid_wallet_user(user_id: int, user_profile: dict | None = None) -> bool:
    """Пополнял баланс / платил — тарификация по кошельку."""
    profile = user_profile if user_profile is not None else get_user(user_id)
    if get_balance(user_id) >= DAILY_RATE:
        return True
    if has_action(user_id, "topup"):
        return True
    if profile and float(profile.get("total_spent") or 0) > 0:
        return True
    return False


def is_bot_trial_user(user_id: int, user_keys: list[dict], user_profile: dict | None) -> bool:
    """Бесплатный trial из бота (3 мес), пока не стал платным."""
    if is_paid_wallet_user(user_id, user_profile):
        return False
    if any("-trial@" in (k.get("key_email") or "") for k in user_keys):
        return True
    profile = user_profile if user_profile is not None else get_user(user_id)
    if profile and profile.get("trial_used"):
        return True
    return False


def is_legacy_manual_panel(
    user_keys: list[dict],
    panel_expire_iso: str | None,
    panel_days: int | None = None,
) -> bool:
    """Ручной срок на панели (2100 и т.п.) — не баланс, не trial-уведомления."""
    pl = panel_days if panel_days is not None else panel_days_left(panel_expire_iso)
    if pl > LEGACY_PANEL_MIN_DAYS:
        return True
    dt = _parse_iso(panel_expire_iso)
    if dt and dt.year >= LEGACY_PANEL_MIN_YEAR:
        return True
    now = datetime.now(timezone.utc)
    for key in user_keys:
        local = _parse_iso(key.get("expiry_date"))
        if not local:
            continue
        local_days = (local - now).days
        if local_days > LEGACY_PANEL_MIN_DAYS or local.year >= LEGACY_PANEL_MIN_YEAR:
            return True
    return False


def access_profile(
    user_id: int,
    user_keys: list[dict],
    user_profile: dict | None,
    panel_expire_iso: str | None,
) -> str:
    """
    legacy — не трогать;
    wallet — ежедневный баланс + напоминания по балансу;
    trial — только напоминания по сроку trial на панели;
    silent — не платящие, не trial, не legacy (не спамим).
    """
    pl = panel_days_left(panel_expire_iso)
    if is_legacy_manual_panel(user_keys, panel_expire_iso, pl):
        return "legacy"
    if is_paid_wallet_user(user_id, user_profile):
        return "wallet"
    if is_bot_trial_user(user_id, user_keys, user_profile):
        return "trial"
    return "silent"


def days_left_for_notifications(
    user_id: int,
    user_keys: list[dict],
    user_profile: dict | None,
    panel_expire_iso: str | None,
) -> tuple[int | None, str]:
    """
    Returns (days_left, profile_kind).
    days_left None => не слать напоминания.
    """
    kind = access_profile(user_id, user_keys, user_profile, panel_expire_iso)
    if kind == "legacy" or kind == "silent":
        return None, kind
    if kind == "wallet":
        return balance_to_days(get_balance(user_id)), kind
    return panel_days_left(panel_expire_iso), kind
