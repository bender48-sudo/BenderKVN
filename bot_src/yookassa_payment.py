"""YooKassa Payment.create helpers (fiscal receipt 54-FZ)."""
from __future__ import annotations

import os


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
