"""BILL-UT-004: offline tests for webhook amount verification."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_BOT_SRC = _REPO / "bot_src"
_WS = _BOT_SRC / "webhook_server"
if str(_BOT_SRC) not in sys.path:
    sys.path.insert(0, str(_BOT_SRC))
if "shop_bot" not in sys.modules:
    _pkg = types.ModuleType("shop_bot")
    _pkg.__path__ = [str(_BOT_SRC)]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = _pkg
_ws_pkg = types.ModuleType("shop_bot.webhook_server")
_ws_pkg.__path__ = [str(_WS)]  # type: ignore[attr-defined]
sys.modules["shop_bot.webhook_server"] = _ws_pkg

from shop_bot.webhook_server.payment_amount_verify import (  # noqa: E402
    verify_crypto_amount,
    verify_yookassa_amount,
)


def _yookassa_event(*, paid: str, meta_amount: str | None, event: str = "payment.succeeded") -> dict:
    meta = {"amount": meta_amount} if meta_amount is not None else {}
    return {
        "event": event,
        "object": {
            "id": "pay-test-1",
            "amount": {"value": paid, "currency": "RUB"},
            "metadata": meta,
        },
    }


class TestVerifyYookassaAmount(unittest.TestCase):
    def test_non_success_event_skips_check(self) -> None:
        ev = _yookassa_event(paid="200.00", meta_amount="200.00", event="payment.waiting_for_capture")
        self.assertTrue(verify_yookassa_amount(ev))

    def test_matching_amount_passes(self) -> None:
        ev = _yookassa_event(paid="200.00", meta_amount="200")
        self.assertTrue(verify_yookassa_amount(ev))

    def test_missing_metadata_amount_fails(self) -> None:
        ev = _yookassa_event(paid="200.00", meta_amount=None)
        self.assertFalse(verify_yookassa_amount(ev))

    def test_amount_mismatch_fails(self) -> None:
        ev = _yookassa_event(paid="199.00", meta_amount="200.00")
        self.assertFalse(verify_yookassa_amount(ev))

    def test_small_rounding_within_epsilon_passes(self) -> None:
        ev = _yookassa_event(paid="200.01", meta_amount="200.00")
        self.assertTrue(verify_yookassa_amount(ev))


class TestVerifyCryptoAmount(unittest.TestCase):
    def test_matching_crypto_amount_passes(self) -> None:
        self.assertTrue(
            verify_crypto_amount({"amount": 200.0, "metadata": {"amount": 200.0}, "order_id": "o1"})
        )

    def test_crypto_mismatch_fails(self) -> None:
        self.assertFalse(
            verify_crypto_amount({"amount": 50.0, "metadata": {"price": 200.0}, "order_id": "o2"})
        )

    def test_missing_expected_metadata_fails(self) -> None:
        self.assertFalse(
            verify_crypto_amount(
                {"amount": 200.0, "metadata": {"plan": "topup_200"}, "order_id": "o3"}
            )
        )


if __name__ == "__main__":
    unittest.main()
