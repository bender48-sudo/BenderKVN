"""YooKassa Payment.create helpers (fiscal receipt 54-FZ)."""
from __future__ import annotations

import os
from typing import Any


def payment_create(payload: dict[str, Any], idempotency_key: Any = None):
    """Payment.create with non-prod write guard (QA-GUARD-001) and dry-run (QA-PAYMENT-DRYRUN-001)."""
    from shop_bot.runtime_env import assert_yookassa_write_allowed
    from shop_bot.yookassa_dryrun import dryrun_payment_create, should_use_payments_dry_run

    assert_yookassa_write_allowed("Payment.create")
    if should_use_payments_dry_run():
        return dryrun_payment_create(payload, idempotency_key)
    from yookassa import Payment

    if idempotency_key is not None:
        return Payment.create(payload, idempotency_key)
    return Payment.create(payload)


def yookassa_receipt(description: str, amount_value: str, user_id: int) -> dict:
    """Fiscal receipt block required when online cash register is enabled in YooKassa."""
    email = (os.getenv("YOOKASSA_RECEIPT_EMAIL") or "").strip()
    if not email:
        email = f"tg{int(user_id)}@bender.vpn"
    vat_code = int(os.getenv("YOOKASSA_RECEIPT_VAT_CODE", "6"))
    return {
        "customer": {"email": email},
        "items": [
            {
                "description": (description or "BenderVPN")[:128],
                "quantity": "1.00",
                "amount": {"value": str(amount_value), "currency": "RUB"},
                "vat_code": vat_code,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }
        ],
    }
