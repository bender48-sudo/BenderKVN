#!/usr/bin/env python3
"""P6-RED-PAY-06: payment amount cross-check."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "bot_src" / "webhook_server" / "payment_amount_verify.py"


def _load():
    spec = importlib.util.spec_from_file_location("payment_amount_verify", MOD)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    pav = _load()
    verify_yookassa_amount = pav.verify_yookassa_amount
    verify_crypto_amount = pav.verify_crypto_amount

    ok_event = {
        "event": "payment.succeeded",
        "object": {
            "id": "test",
            "amount": {"value": "100.00", "currency": "RUB"},
            "metadata": {"user_id": 1, "price": 100, "t": "topup"},
        },
    }
    if not verify_yookassa_amount(ok_event):
        print("PAYMENT_AMOUNT_VERIFY_FAIL: valid yookassa rejected", file=sys.stderr)
        return 1
    bad_event = {
        "event": "payment.succeeded",
        "object": {
            "id": "test2",
            "amount": {"value": "50.00", "currency": "RUB"},
            "metadata": {"user_id": 1, "price": 100},
        },
    }
    if verify_yookassa_amount(bad_event):
        print("PAYMENT_AMOUNT_VERIFY_FAIL: mismatch yookassa accepted", file=sys.stderr)
        return 1
    ok_crypto = {
        "status": "paid",
        "amount": 200,
        "metadata": {"user_id": 1, "price": 200},
    }
    if not verify_crypto_amount(ok_crypto):
        print("PAYMENT_AMOUNT_VERIFY_FAIL: valid crypto rejected", file=sys.stderr)
        return 1
    pq = (ROOT / "bot_src" / "webhook_server" / "payment_queue.py").read_text(encoding="utf-8")
    if "verify_yookassa_amount" not in pq or "verify_crypto_amount" not in pq:
        print("PAYMENT_AMOUNT_VERIFY_FAIL: payment_queue not wired", file=sys.stderr)
        return 1
    print("PAYMENT_AMOUNT_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
