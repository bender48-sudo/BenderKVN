"""YooKassa card autopay: bind payment_method + monthly charge (P2-COM-YK-AUTOPAY-01)."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from yookassa import Payment

from shop_bot.yookassa_payment import yookassa_receipt

logger = logging.getLogger(__name__)


def autopay_amount_rub() -> float:
    return float(os.getenv("YOOKASSA_AUTOPAY_AMOUNT_RUB", "200"))


def autopay_interval_days() -> int:
    return int(os.getenv("YOOKASSA_AUTOPAY_INTERVAL_DAYS", "30"))


def return_url() -> str:
    username = (os.getenv("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
    return f"https://t.me/{username}" if username else "https://t.me/"


def create_bind_payment(user_id: int) -> tuple[str | None, str | None]:
    """First payment: charge monthly amount + save_payment_method for future autopay."""
    amount_rub = autopay_amount_rub()
    amount_value = f"{amount_rub:.2f}"
    description = f"BenderVPN — автоплатёж, первый месяц {amount_rub:.0f} ₽"
    try:
        payment = Payment.create(
            {
                "amount": {"value": amount_value, "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": return_url()},
                "capture": True,
                "save_payment_method": True,
                "description": description,
                "receipt": yookassa_receipt(description, amount_value, user_id),
                "metadata": {
                    "t": "topup",
                    "u": user_id,
                    "user_id": user_id,
                    "a": amount_value,
                    "amount": amount_value,
                    "autopay_bind": "1",
                },
            },
            str(uuid.uuid4()),
        )
        url = payment.confirmation.confirmation_url
        return url, None
    except Exception as exc:
        logger.error("create_bind_payment user=%s: %s", user_id, exc, exc_info=True)
        return None, str(exc)


def create_recurring_charge(user_id: int, payment_method_id: str) -> tuple[str | None, str | None]:
    """Charge saved card (no redirect). Result via webhook."""
    amount_rub = autopay_amount_rub()
    amount_value = f"{amount_rub:.2f}"
    description = f"BenderVPN — автопродление {amount_rub:.0f} ₽"
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    idem = f"yk-autopay-{user_id}-{period}"
    try:
        payment = Payment.create(
            {
                "amount": {"value": amount_value, "currency": "RUB"},
                "capture": True,
                "payment_method_id": payment_method_id,
                "description": description,
                "receipt": yookassa_receipt(description, amount_value, user_id),
                "metadata": {
                    "t": "topup",
                    "u": user_id,
                    "user_id": user_id,
                    "a": amount_value,
                    "amount": amount_value,
                    "autopay_renew": "1",
                },
            },
            idem,
        )
        return payment.id, None
    except Exception as exc:
        logger.error(
            "create_recurring_charge user=%s: %s", user_id, exc, exc_info=True
        )
        return None, str(exc)


def _payment_method_id_from_event(event_json: dict[str, Any]) -> str | None:
    obj = event_json.get("object") or {}
    pm = obj.get("payment_method") or {}
    if pm.get("saved") and pm.get("id"):
        return str(pm["id"])
    return None


def on_payment_succeeded(event_json: dict[str, Any]) -> None:
    """Persist saved card + schedule next charge after successful payment."""
    from shop_bot.data_manager.database import (
        clear_yookassa_autopay_error,
        get_yookassa_autopay,
        schedule_yookassa_autopay_next,
        set_yookassa_autopay_enabled,
        set_yookassa_payment_method,
    )

    metadata = (event_json.get("object") or {}).get("metadata") or {}
    user_id = int(metadata.get("user_id") or metadata.get("u") or 0)
    if user_id <= 0:
        return

    bind = str(metadata.get("autopay_bind") or "") == "1"
    renew = str(metadata.get("autopay_renew") or "") == "1"
    if not bind and not renew:
        # Optional: save method if user paid with save_payment_method on ordinary topup
        return

    pm_id = _payment_method_id_from_event(event_json)
    if pm_id:
        set_yookassa_payment_method(user_id, pm_id)

    if bind or renew:
        set_yookassa_autopay_enabled(user_id, True)
        schedule_yookassa_autopay_next(
            user_id, days=autopay_interval_days()
        )
        clear_yookassa_autopay_error(user_id)
        logger.info(
            "yookassa autopay armed user=%s bind=%s renew=%s pm=%s",
            user_id,
            bind,
            renew,
            pm_id,
        )
