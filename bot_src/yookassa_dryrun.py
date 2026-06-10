"""QA dry-run YooKassa payment provider (QA-PAYMENT-DRYRUN-001).

Returns objects shaped like yookassa.Payment responses without API writes.
Active only when BVPN_ENV is non-production and BVPN_QA_DRY_RUN_PAYMENTS=1.
Never activates in production. Does not mutate balances.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

_SANDBOX_HOST = "sandbox.invalid"
_FORBIDDEN_FRAGMENTS = (
    "yookassa.ru",
    "yoomoney.ru",
    "checkout.yookassa",
    "live_",
    "test_shop",
)


class DryRunConfirmation:
    """Minimal confirmation object for redirect payment flows."""

    def __init__(self, confirmation_url: str, confirmation_type: str = "redirect") -> None:
        self.confirmation_url = confirmation_url
        self.type = confirmation_type


class DryRunPayment:
    """Minimal payment object consumed by bot handlers."""

    def __init__(
        self,
        payment_id: str,
        confirmation_url: str | None,
        *,
        status: str = "pending",
        amount_value: str = "0.00",
        currency: str = "RUB",
    ) -> None:
        self.id = payment_id
        self.status = status
        self.amount = {"value": amount_value, "currency": currency}
        self.confirmation = (
            DryRunConfirmation(confirmation_url) if confirmation_url else None
        )


def should_use_payments_dry_run() -> bool:
    from shop_bot.runtime_env import is_payments_dry_run, is_production

    if is_production():
        return False
    return is_payments_dry_run()


def _payment_id_from_key(idempotency_key: Any | None, payload: dict[str, Any]) -> str:
    if idempotency_key is not None:
        digest = hashlib.sha256(f"qa-yk:{idempotency_key}".encode()).hexdigest()
        return f"qa-pay-{digest[:24]}"
    meta = payload.get("metadata") or {}
    seed = str(meta.get("user_id") or meta.get("u") or uuid.uuid4())
    digest = hashlib.sha256(f"qa-yk:{seed}:{payload.get('description', '')}".encode()).hexdigest()
    return f"qa-pay-{digest[:24]}"


def _confirmation_url(payment_id: str) -> str:
    return f"https://{_SANDBOX_HOST}/pay/{payment_id}"


def dryrun_payment_create(
    payload: dict[str, Any],
    idempotency_key: Any = None,
) -> DryRunPayment:
    """Same entry point as payment_create — no YooKassa HTTP."""
    amount = payload.get("amount") or {}
    value = str(amount.get("value") or "0.00")
    currency = str(amount.get("currency") or "RUB")
    payment_id = _payment_id_from_key(idempotency_key, payload)
    confirmation = payload.get("confirmation") or {}
    conf_url = _confirmation_url(payment_id) if confirmation.get("type") == "redirect" else None
    return DryRunPayment(
        payment_id,
        conf_url,
        status="pending",
        amount_value=value,
        currency=currency,
    )


def assert_dummy_payment_safe(payment: DryRunPayment) -> None:
    """Test helper: no production YooKassa URLs or credential-like strings."""
    values = [payment.id, getattr(payment.confirmation, "confirmation_url", None) or ""]
    for raw in values:
        lower = str(raw).lower()
        if _SANDBOX_HOST not in lower and "qa-pay-" not in lower:
            raise AssertionError(f"dry-run payment id/url must be synthetic: {raw!r}")
        for frag in _FORBIDDEN_FRAGMENTS:
            if frag in lower:
                raise AssertionError(f"dry-run payment must not contain {frag!r}: {raw!r}")
