"""Balance wallet: daily kopeks charge + panel expireAt sync (P2-COM-BALANCE-DAILY-01)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from shop_bot.config import BOT_PAYMENTS_LIVE, balance_to_days, daily_charge_rub
from shop_bot.data_manager.database import (
    get_balance,
    get_user_keys,
    has_action,
    log_action,
    try_deduct_balance,
    update_key_info,
)
from shop_bot.modules import remnawave_api

logger = logging.getLogger(__name__)


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _daily_charge_action() -> str:
    return f"daily_balance:{_utc_today()}"


def waive_daily_charge_today(user_id: int) -> None:
    """After topup: do not deduct daily rate again on the same UTC day."""
    action = _daily_charge_action()
    if not has_action(user_id, action):
        log_action(user_id, action, "waived_topup")


def charge_daily_balance_if_due(user_id: int) -> str:
    """Idempotent daily tariff. Returns charged | already | insufficient | skipped."""
    if not BOT_PAYMENTS_LIVE:
        return "skipped"
    action = _daily_charge_action()
    if has_action(user_id, action):
        return "already"
    # waived_topup logged without deduct — treat as already handled for the day
    charge = daily_charge_rub()
    if not try_deduct_balance(user_id, charge):
        log_action(user_id, action, "insufficient")
        return "insufficient"
    log_action(user_id, action, f"{charge:.2f}")
    return "charged"


async def sync_panel_from_balance(user_id: int) -> bool:
    """Set Remna expireAt = now + floor(balance / daily rate) days (absolute, not additive)."""
    balance = get_balance(user_id)
    days = balance_to_days(balance)
    keys = get_user_keys(user_id)
    email = keys[0]["key_email"] if keys else None
    expire_iso = await remnawave_api.set_user_access_days(
        str(user_id), days, email=email
    )
    if not expire_iso:
        return False
    try:
        expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
        expiry_ms = int(expiry_dt.timestamp() * 1000)
        if keys:
            kid = keys[0]["key_id"]
            uuid = keys[0].get("vless_uuid") or ""
            update_key_info(kid, uuid, expiry_ms)
    except (ValueError, TypeError) as exc:
        logger.warning("sync_panel_from_balance local key update user=%s: %s", user_id, exc)
    from shop_bot.subscription_cache import invalidate_subscription_url_cache

    invalidate_subscription_url_cache(user_id)
    return True


async def process_daily_balance_user(
    user_id: int,
    *,
    panel_expire_iso: str | None = None,
) -> None:
    """One scheduler tick: daily charge + panel sync только для платящих (wallet)."""
    keys = get_user_keys(user_id)
    if not keys:
        return
    from shop_bot.subscription_profile import access_profile
    from shop_bot.data_manager.database import get_user

    profile = get_user(user_id)
    kind = access_profile(user_id, keys, profile, panel_expire_iso)
    if kind != "wallet":
        return
    status = charge_daily_balance_if_due(user_id)
    if status in ("charged", "already", "insufficient", "skipped"):
        await sync_panel_from_balance(user_id)
    if status == "insufficient":
        logger.info("daily balance insufficient user=%s", user_id)
