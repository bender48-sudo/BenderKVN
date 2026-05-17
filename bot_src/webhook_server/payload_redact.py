"""Redact PSP webhook bodies before SQLite persistence (P3-RED-MIN-01)."""
from __future__ import annotations

from typing import Any

_ALLOWED_YK_META = frozenset(
    {"user_id", "u", "amount", "a", "t", "plan_id", "months", "key_id", "price"}
)


def redact_webhook_payload(source: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Minimal fields for idempotency/DLQ; full payload stays in memory only for worker."""
    if source == "yookassa":
        obj = payload.get("object") if isinstance(payload.get("object"), dict) else {}
        meta = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        return {
            "event": payload.get("event"),
            "object": {
                "id": obj.get("id"),
                "status": obj.get("status"),
                "metadata": {k: meta[k] for k in _ALLOWED_YK_META if k in meta},
            },
        }
    if source in ("crypto", "cryptobot"):
        meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        slim_meta = {k: meta[k] for k in ("user_id", "u", "amount", "a", "plan_id") if k in meta}
        out: dict[str, Any] = {"status": payload.get("status")}
        for k in ("order_id", "invoice_id", "payment_id", "id"):
            if payload.get(k):
                out[k] = payload[k]
                break
        if slim_meta:
            out["metadata"] = slim_meta
        return out
    return {"source": source, "keys": sorted(payload.keys())[:16]}
