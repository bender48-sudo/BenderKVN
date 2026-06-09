"""Payment idempotency key builders (BILL-FIX-001). No DB imports."""

from __future__ import annotations

# Canonical user_actions key for YooKassa top-up (webhook + reconcile).
YOOKASSA_TOPUP_ACTION_PREFIX = "yk:"

# Legacy reconcile prefix — skip if present when reconciling.
LEGACY_YOOKASSA_RECONCILE_PREFIX = "yookassa:"


def yookassa_topup_action_key(payment_id: str) -> str:
    """Build idempotency key recorded in user_actions by process_topup_payment."""
    pid = (payment_id or "").strip()
    if not pid:
        raise ValueError("payment_id required")
    return f"{YOOKASSA_TOPUP_ACTION_PREFIX}{pid}"
