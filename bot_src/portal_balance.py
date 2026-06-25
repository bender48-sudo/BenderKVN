"""In-app Mini App balance: tariff, transactions (Phase A), payment creation.

MINI-APP-BUILD-001 (balance screen, Variant 1 migration). Design notes:

* **Transactions** are read-only over ``user_actions`` (Phase A) — no schema migration.
  Same response contract as the future dedicated ledger (Phase B), so the front does
  not change when B lands.
* **create-payment** reuses the exact YooKassa ``metadata`` contract the webhook already
  consumes (``t=topup`` / ``user_id`` / ``amount``) — the webhook is NOT changed. It goes
  through ``yookassa_payment.payment_create`` so the dry-run / write-guard apply.
* **Live in-app collection is gated** behind ``MINIAPP_PAYMENTS_LIVE`` (default off). Merging
  this code does not enable real money collection; flipping the env is a separate owner OK
  (HONEST-GATE-PAID-001).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from shop_bot.config import (
    DAILY_RATE,
    DAILY_RATE_KOPEKS,
    PORTAL_TOPUP_MAX_RUB,
    PORTAL_TOPUP_MIN_RUB,
    PORTAL_TOPUP_PRESETS_RUB,
    balance_to_days,
    rub_to_kopeks,
)
from shop_bot.data_manager.database import get_balance_ledger, get_user
from shop_bot.web_trial_db import (
    get_claim_by_customer_id,
    get_web_trial_claim,
    normalize_contact_email,
)

logger = logging.getLogger(__name__)


def miniapp_payments_live() -> bool:
    """Dedicated gate for in-app payment creation (separate from bot BOT_PAYMENTS_LIVE)."""
    return os.getenv("MINIAPP_PAYMENTS_LIVE", "").strip().lower() in ("1", "true", "yes")


def _default_return_url() -> str:
    """Where YooKassa redirects the user back after the bank page (D6)."""
    explicit = (os.getenv("PORTAL_PAYMENT_RETURN_URL") or "").strip()
    if explicit:
        return explicit
    base = (os.getenv("PORTAL_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if base:
        return f"{base}/portal/cabinet.html"
    return "https://t.me/"


# -------------------- Tariff --------------------
def build_tariff() -> dict:
    """Presets (round ₽; days computed server-side) + rate + custom min/max."""
    presets = [
        {"amount_rub": int(rub), "days": balance_to_days(rub)}
        for rub in PORTAL_TOPUP_PRESETS_RUB
    ]
    return {
        "ok": True,
        "currency": "RUB",
        "daily_rate": DAILY_RATE,
        "daily_rate_kopeks": DAILY_RATE_KOPEKS,
        "min_rub": PORTAL_TOPUP_MIN_RUB,
        "max_rub": PORTAL_TOPUP_MAX_RUB,
        "presets": presets,
        "payments_live": miniapp_payments_live(),
    }


# -------------------- Transactions (Phase A over user_actions) --------------------
def _parse_amount(meta) -> float | None:
    try:
        val = float(meta)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _iso_utc(raw) -> str | None:
    """user_actions.created_at is 'YYYY-MM-DD HH:MM:SS' (SQLite CURRENT_TIMESTAMP, UTC)."""
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


def build_transactions(user_id: int, limit: int = 50) -> dict:
    """Map ledger rows → {type, sign, amount_rub, at_utc}. Newest first."""
    rows = get_balance_ledger(user_id, limit)
    items: list[dict] = []
    for row in rows:
        action = (row.get("action") or "").strip()
        amount = _parse_amount(row.get("meta"))
        if amount is None:
            # daily_balance rows with 'waived_topup' / 'insufficient' meta are not money moves.
            continue
        at_iso = _iso_utc(row.get("created_at"))
        if action == "topup":
            items.append(
                {"type": "topup", "sign": "+", "amount_rub": round(amount, 2), "at_utc": at_iso}
            )
        elif action.startswith("daily_balance:"):
            items.append(
                {
                    "type": "daily_charge",
                    "sign": "-",
                    "amount_rub": round(amount, 2),
                    "at_utc": at_iso,
                }
            )
    return {"ok": True, "transactions": items, "count": len(items)}


# -------------------- User resolution (billing identity) --------------------
def _resolve_billing_user_id(
    telegram_id: int | None, customer_id: str, email: str
) -> tuple[int | None, str | None]:
    """Resolve to the user_id the webhook credits. (user_id, error)."""
    if telegram_id and int(telegram_id) > 0:
        user = get_user(int(telegram_id))
        if not user:
            return None, "not_found"
        if not user.get("agreed_to_terms"):
            return None, "terms_required"
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
        # Web-only users have no Telegram-keyed billing row to credit yet.
        return None, "needs_telegram_bind"
    user = get_user(int(tid))
    if not user:
        return None, "not_found"
    if not user.get("agreed_to_terms"):
        return None, "terms_required"
    return int(tid), None


def transactions_snapshot(
    *, telegram_id: int | None = None, customer_id: str = "", email: str = "", limit: int = 50
) -> dict:
    user_id, err = _resolve_billing_user_id(telegram_id, customer_id, email)
    if err == "not_found":
        return {"ok": False, "error": "not_found"}
    if user_id is None:
        # needs_telegram_bind / terms_required → no history to show yet, not an error screen.
        return {"ok": True, "transactions": [], "count": 0}
    safe_limit = max(1, min(int(limit or 50), 200))
    return build_transactions(user_id, safe_limit)


# -------------------- Payment creation --------------------
def _resolve_amount_kopeks(amount_rub) -> tuple[int | None, str | None]:
    if amount_rub is None:
        return None, "invalid_amount"
    try:
        rub = float(amount_rub)
    except (TypeError, ValueError):
        return None, "invalid_amount"
    if rub < PORTAL_TOPUP_MIN_RUB or rub > PORTAL_TOPUP_MAX_RUB:
        return None, "amount_out_of_range"
    kopeks = rub_to_kopeks(rub)
    if kopeks <= 0:
        return None, "invalid_amount"
    return kopeks, None


def create_topup_payment(
    *,
    telegram_id: int | None = None,
    customer_id: str = "",
    email: str = "",
    amount_rub=None,
) -> dict:
    """Create a YooKassa top-up and return the redirect URL. No balance mutation here."""
    if not miniapp_payments_live():
        return {"ok": False, "error": "payments_disabled"}

    user_id, err = _resolve_billing_user_id(telegram_id, customer_id, email)
    if err:
        return {"ok": False, "error": err}

    kopeks, perr = _resolve_amount_kopeks(amount_rub)
    if perr:
        return {"ok": False, "error": perr}

    amount_value = f"{kopeks / 100:.2f}"
    amount_rub_num = kopeks / 100.0
    description = f"Пополнение баланса BenderVPN {amount_rub_num:.0f} ₽"

    from shop_bot.yookassa_payment import payment_create, yookassa_receipt

    payload = {
        "amount": {"value": amount_value, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": _default_return_url()},
        "capture": True,
        "description": description,
        "receipt": yookassa_receipt(description, amount_value, user_id),
        # Same keys the webhook reads (webhook_server/payment_queue._handle_yookassa).
        "metadata": {
            "t": "topup",
            "u": user_id,
            "user_id": user_id,
            "a": amount_value,
            "amount": amount_value,
            "src": "miniapp",
        },
    }
    try:
        payment = payment_create(payload, uuid.uuid4())
    except Exception as exc:  # QaGuardError or YooKassa errors
        logger.error("portal create_topup_payment failed user=%s: %s", user_id, exc, exc_info=True)
        return {"ok": False, "error": "payment_link_failed"}

    confirmation = getattr(payment, "confirmation", None)
    conf_url = getattr(confirmation, "confirmation_url", None) if confirmation else None
    if not conf_url:
        return {"ok": False, "error": "payment_link_failed"}

    return {
        "ok": True,
        "payment_id": getattr(payment, "id", None),
        "confirmation_url": conf_url,
        "amount_rub": round(amount_rub_num, 2),
        "days": balance_to_days(amount_rub_num),
    }
