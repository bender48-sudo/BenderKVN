"""Read-only web cabinet snapshot (P3-FLOW-15, P1-CAB-001 billing_profile)."""
from __future__ import annotations

from datetime import datetime, timezone

from shop_bot.config import BOT_PAYMENTS_LIVE, DAILY_RATE, balance_covers_one_day, balance_to_days
from shop_bot.data_manager.database import (
    get_latest_action_meta,
    get_user,
    get_user_keys,
    has_action,
)
from shop_bot.subscription_profile import access_profile, is_legacy_manual_panel
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


def _parse_key_expiry(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _active_keys(keys: list[dict], now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    out: list[dict] = []
    for key in keys:
        exp = _parse_key_expiry(key.get("expiry_date"))
        if exp and exp > now:
            out.append(key)
    return out


def _latest_key_expiry(keys: list[dict]) -> datetime | None:
    best: datetime | None = None
    for key in keys:
        exp = _parse_key_expiry(key.get("expiry_date"))
        if exp and (best is None or exp > best):
            best = exp
    return best


def _format_expiry_display(dt: datetime | None) -> tuple[str | None, str | None]:
    if not dt:
        return None, None
    return dt.strftime("%d.%m.%Y"), dt.astimezone(timezone.utc).isoformat()


def _format_created_display(raw: str | None) -> tuple[str | None, str | None]:
    if raw is None:
        return None, None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = _parse_key_expiry(str(raw))
    if not dt:
        return None, None
    return dt.strftime("%d.%m.%Y"), dt.astimezone(timezone.utc).isoformat()


def _primary_key_id(keys: list[dict], now: datetime | None = None) -> int | None:
    """Key shown in setup: newest expiry among active, else newest overall."""
    now = now or datetime.now(timezone.utc)
    active = _active_keys(keys, now)
    pool = active if active else keys
    if not pool:
        return None
    primary = max(pool, key=lambda k: k.get("expiry_date") or "")
    kid = primary.get("key_id")
    return int(kid) if kid is not None else None


def build_configuration_fields(
    keys: list[dict],
    billing_profile: str,
    *,
    now: datetime | None = None,
) -> dict:
    """
    Read-only vpn_keys summary for cabinet UI (P1-DEV-001).
    No Remna calls; no subscription URLs.
    """
    now = now or datetime.now(timezone.utc)
    active = _active_keys(keys, now)
    primary_id = _primary_key_id(keys, now)
    active_count = len(active)
    configurations: list[dict] = []

    for key in sorted(keys, key=lambda k: int(k.get("key_id") or 0)):
        kid = key.get("key_id")
        exp = _parse_key_expiry(key.get("expiry_date"))
        is_active = bool(exp and exp > now)
        exp_disp, exp_iso = _format_expiry_display(exp)
        created_disp, created_iso = _format_created_display(key.get("created_date"))
        is_primary = primary_id is not None and int(kid or 0) == primary_id
        billable = billing_profile == "wallet" and is_active and is_primary and active_count <= 1

        configurations.append(
            {
                "key_id": kid,
                "id": f"CFG-{kid}" if kid is not None else None,
                "label": f"Настройка #{kid}" if kid is not None else "Настройка",
                "active": is_active,
                "status": "active" if is_active else "expired",
                "created_at": created_disp,
                "created_at_iso": created_iso,
                "expires": exp_disp,
                "expires_at": exp_disp,
                "expires_at_iso": exp_iso,
                "has_subscription_url": is_active,
                "subscription_url_masked": None,
                "is_primary": is_primary,
                "is_current": is_primary,
                "billable": billable,
            }
        )

    return {
        "active_config_count": active_count,
        "configurations": configurations,
        "multiple_configs_anomaly": active_count > 1,
        "support_required_for_extra_configs": active_count > 1,
    }


def _daily_charge_action_for(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"daily_balance:{now.strftime('%Y-%m-%d')}"


def build_billing_fields(
    user_id: int,
    user: dict,
    keys: list[dict] | None = None,
    *,
    now: datetime | None = None,
) -> dict:
    """
    Read-only billing/access classification for cabinet UI.
    Does not mutate balance, keys, or Remna panel.
    """
    now = now or datetime.now(timezone.utc)
    keys = keys if keys is not None else get_user_keys(user_id)
    balance = float(user.get("balance") or 0)
    active = _active_keys(keys, now)
    latest_expiry = _latest_key_expiry(active or keys)
    panel_expire_iso = latest_expiry.isoformat() if latest_expiry else None
    expiry_display, expiry_iso = _format_expiry_display(latest_expiry)

    profile_kind = access_profile(user_id, keys, user, panel_expire_iso)

    if profile_kind == "legacy":
        billing_profile = "legacy"
    elif profile_kind == "wallet":
        billing_profile = "wallet" if active else "expired"
    elif profile_kind == "trial":
        billing_profile = "trial" if active else "expired"
    elif not active:
        billing_profile = "expired"
    else:
        billing_profile = "unknown"

    config_fields = build_configuration_fields(keys, billing_profile, now=now)
    active_config_count = config_fields["active_config_count"]
    billable_config_count = (
        1 if billing_profile == "wallet" and active_config_count == 1 else 0
    )

    is_billable_now = (
        billing_profile == "wallet"
        and active_config_count > 0
        and balance_covers_one_day(balance)
    )

    daily_action = _daily_charge_action_for(now)
    already_charged_today = has_action(user_id, daily_action)
    next_charge_applicable = (
        is_billable_now
        and BOT_PAYMENTS_LIVE
        and not already_charged_today
    )

    billing_note_code = billing_profile
    billing_note = ""

    if billing_profile == "legacy":
        billing_note_code = "legacy_manual"
        when = expiry_display or "—"
        billing_note = (
            f"Доступ активен вручную до {when}. "
            "Баланс сохранён и сейчас не списывается."
        )
    elif billing_profile == "wallet":
        billing_note_code = "wallet_daily"
        billing_note = (
            f"Баланс: {balance:.0f} ₽. Списание: {DAILY_RATE:.2f} ₽/день за активный конфиг."
        )
        if not is_billable_now and balance > 0:
            billing_note += " Сейчас баланса не хватает на следующий день."
        elif not BOT_PAYMENTS_LIVE:
            billing_note += " Автосписание временно отключено."
        elif already_charged_today:
            billing_note += " Сегодня списание уже учтено."
        elif next_charge_applicable:
            billing_note += " Следующее списание — по расписанию сервиса."
    elif billing_profile == "trial":
        billing_note_code = "trial_active"
        when = expiry_display or "—"
        billing_note = f"Пробный доступ активен до {when}. Списания с баланса нет."
    elif billing_profile == "expired":
        billing_note_code = "access_expired"
        billing_note = (
            "Доступ истёк. Пополните баланс в боте или обратитесь в поддержку."
        )
    else:
        billing_note_code = "unknown"
        billing_note = "Статус доступа уточняется. Если что-то не так — напишите в поддержку."

    return {
        "billing_profile": billing_profile,
        "access_profile": billing_profile,
        "is_billable_now": is_billable_now,
        "next_charge_applicable": next_charge_applicable,
        "access_expires_at": expiry_display,
        "access_expires_at_iso": expiry_iso,
        # Runway «хватит до {дата}» for Mini App balance — alias of server-synced
        # access expiry (sync_panel_from_balance sets expireAt = now + balance/rate days).
        # Server-side UTC; UI must not recompute from balance/rate.
        "runway_until": expiry_display,
        "runway_until_iso": expiry_iso,
        "billing_note_code": billing_note_code,
        "billing_note": billing_note,
        "billing_note_text": billing_note,
        "active_config_count": active_config_count,
        "billable_config_count": billable_config_count,
        "legacy_manual_access": profile_kind == "legacy"
        or is_legacy_manual_panel(keys, panel_expire_iso),
        **config_fields,
    }


def build_profile_fields(user_id: int, user: dict, base: dict) -> dict:
    """§7.4 / D15 profile: email, phone, language, consents (read-only snapshot)."""
    lang = (get_latest_action_meta(user_id, "onboarding_language") or "ru").strip().lower()
    if lang not in ("ru", "en"):
        lang = "ru"
    rules_v = get_latest_action_meta(user_id, "rules_accepted")
    privacy_v = get_latest_action_meta(user_id, "privacy_accepted")
    agreed = bool(user.get("agreed_to_terms")) or bool(rules_v) or bool(privacy_v)
    consents = []
    if agreed:
        consents.append({"doc": "rules", "version": rules_v or "1", "accepted": True})
        consents.append({"doc": "privacy", "version": privacy_v or "1", "accepted": True})
    return {
        "profile": {
            "email": (user.get("contact_email") or "").strip() or None,
            "phone": (base.get("phone") or "").strip() or None if base.get("phone") else None,
            "language": lang,
            "username": (user.get("username") or "").strip() or None,
            "consents": consents,
            "notifications": {
                "telegram": bool(base.get("telegram_bound")),
                "email": bool((user.get("contact_email") or "").strip()),
            },
        }
    }


def _enrich_cabinet_response(user_id: int, user: dict, base: dict) -> dict:
    keys = get_user_keys(user_id)
    billing = build_billing_fields(user_id, user, keys)
    out = dict(base)
    out.update(billing)
    out.update(build_profile_fields(user_id, user, out))
    return out


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
                "затем «Получить настройку» или «Пополнить баланс»."
            ),
            "bot_url": _bot_open_url(),
        }
    balance = float(user.get("balance") or 0)
    days = balance_to_days(balance)
    base = {
        "ok": True,
        "customer_id": f"TG-{telegram_id}",
        "balance_rub": round(balance, 2),
        "days_left": days,
        "daily_rate": DAILY_RATE,
        "telegram_bound": True,
        "web_only": False,
        "source": "telegram",
    }
    return _enrich_cabinet_response(telegram_id, user, base)


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
        claim = get_web_trial_claim(em)
    if not claim and customer_id:
        claim = get_claim_by_customer_id(customer_id)
    if not claim:
        return {"ok": False, "error": "not_found"}

    web_uid = int(claim["web_user_id"])
    user = get_user(web_uid)
    billing_uid = web_uid
    if not user and claim.get("telegram_id"):
        billing_uid = int(claim["telegram_id"])
        user = get_user(billing_uid)
    balance = float(user["balance"]) if user and user.get("balance") is not None else 0.0
    days = balance_to_days(balance)
    tg_bound = bool(claim.get("telegram_id"))
    base = {
        "ok": True,
        "customer_id": format_customer_id(web_uid),
        "balance_rub": round(balance, 2),
        "days_left": days,
        "daily_rate": DAILY_RATE,
        "telegram_bound": tg_bound,
        "web_only": is_web_surrogate_id(web_uid) and not tg_bound,
        "phone": (claim.get("contact_phone") or "").strip() or None,
    }
    if not tg_bound and is_web_surrogate_id(web_uid):
        base["needs_telegram_bind"] = True
    if user:
        return _enrich_cabinet_response(billing_uid, user, base)
    return base
