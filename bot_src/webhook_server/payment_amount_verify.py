"""Cross-check webhook payment amount vs metadata (P6-RED-PAY-06)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_AMOUNT_EPS = 0.02


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _metadata_amount(meta: dict[str, Any]) -> float | None:
    for key in ("amount", "price", "a"):
        v = _to_float(meta.get(key))
        if v is not None:
            return v
    return None


def verify_yookassa_amount(event_json: dict[str, Any]) -> bool:
    if event_json.get("event") != "payment.succeeded":
        return True
    obj = event_json.get("object") or {}
    meta = obj.get("metadata") or {}
    expected = _metadata_amount(meta)
    if expected is None:
        return True
    paid = _to_float((obj.get("amount") or {}).get("value"))
    if paid is None:
        logger.warning("YooKassa webhook missing amount.value")
        return False
    if abs(paid - expected) > _AMOUNT_EPS:
        logger.error(
            "YooKassa amount mismatch: paid=%s metadata=%s payment_id=%s",
            paid,
            expected,
            obj.get("id"),
        )
        return False
    return True


def verify_crypto_amount(data: dict[str, Any]) -> bool:
    meta = data.get("metadata") or data
    if not isinstance(meta, dict):
        return True
    expected = _metadata_amount(meta)
    if expected is None:
        return True
    paid = _to_float(data.get("amount") or data.get("fiat_amount") or data.get("sum"))
    if paid is None:
        return True
    if abs(paid - expected) > _AMOUNT_EPS:
        logger.error(
            "Crypto amount mismatch: paid=%s metadata=%s order=%s",
            paid,
            expected,
            data.get("order_id") or data.get("invoice_id"),
        )
        return False
    return True
