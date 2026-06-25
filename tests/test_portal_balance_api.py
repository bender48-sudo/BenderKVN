"""Offline tests for in-app Mini App balance API (MINI-APP-BUILD-001).

No live YooKassa / Telegram / Remna. Payments use the dry-run provider. Covers:
tariff presets (server-computed days), transactions mapping over user_actions
(Phase A), amount validation, the MINIAPP_PAYMENTS_LIVE gate, and that the payment
metadata matches the contract the webhook (payment_queue._handle_yookassa) consumes.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
_BOT_SRC = _REPO / "bot_src"
if str(_BOT_SRC) not in sys.path:
    sys.path.insert(0, str(_BOT_SRC))
if "shop_bot" not in sys.modules:
    _pkg = types.ModuleType("shop_bot")
    _pkg.__path__ = [str(_BOT_SRC)]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = _pkg

_dm = types.ModuleType("shop_bot.data_manager")
sys.modules["shop_bot.data_manager"] = _dm
_db = importlib.import_module("database")
sys.modules["shop_bot.data_manager.database"] = _db
_dm.database = _db


def _fresh_db() -> Path:
    path = Path(tempfile.mkdtemp()) / "balance.db"
    os.environ["SHOP_BOT_DB_PATH"] = str(path)
    _db.DB_FILE = str(path)
    _db.initialize_db()
    return path


class TestTariff(unittest.TestCase):
    def test_presets_round_amounts_server_days(self) -> None:
        from shop_bot.portal_balance import build_tariff

        with patch.dict(os.environ, {"MINIAPP_PAYMENTS_LIVE": "1"}):
            doc = build_tariff()
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["daily_rate_kopeks"], 666)
        self.assertEqual(doc["min_rub"], 200)
        self.assertEqual(doc["max_rub"], 10_000)
        self.assertTrue(doc["payments_live"])
        amounts = [(p["amount_rub"], p["days"]) for p in doc["presets"]]
        self.assertEqual(amounts, [(200, 30), (600, 90), (1200, 180), (2400, 360)])

    def test_payments_live_reflects_gate_off(self) -> None:
        from shop_bot.portal_balance import build_tariff

        with patch.dict(os.environ, {"MINIAPP_PAYMENTS_LIVE": "0"}):
            self.assertFalse(build_tariff()["payments_live"])


class TestTransactions(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(7001, "txn_user")
        _db.set_terms_agreed(7001)

    def test_maps_topup_and_daily_skips_non_money(self) -> None:
        from shop_bot.portal_balance import transactions_snapshot

        _db.log_action(7001, "topup", "600.0")
        _db.log_action(7001, "daily_balance:2026-06-24", "6.66")
        _db.log_action(7001, "daily_balance:2026-06-25", "insufficient")  # skip
        _db.log_action(7001, "daily_balance:2026-06-23", "waived_topup")  # skip
        _db.log_action(7001, "yk:pay-123", "600.0")  # idempotency row, skip

        doc = transactions_snapshot(telegram_id=7001)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["count"], 2)
        kinds = [(t["type"], t["sign"], t["amount_rub"]) for t in doc["transactions"]]
        self.assertIn(("topup", "+", 600.0), kinds)
        self.assertIn(("daily_charge", "-", 6.66), kinds)
        for t in doc["transactions"]:
            self.assertIsNotNone(t["at_utc"])
            self.assertTrue(t["at_utc"].endswith("+00:00"))

    def test_unknown_user_not_found(self) -> None:
        from shop_bot.portal_balance import transactions_snapshot

        self.assertEqual(transactions_snapshot(telegram_id=999999)["error"], "not_found")


class TestCreatePayment(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(8001, "pay_user")
        _db.set_terms_agreed(8001)
        self._env = patch.dict(
            os.environ,
            {
                "BVPN_ENV": "test",
                "BVPN_QA_DRY_RUN_PAYMENTS": "1",
                "MINIAPP_PAYMENTS_LIVE": "1",
                "PORTAL_PUBLIC_BASE_URL": "https://app.bendervpn.io",
            },
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_gate_off_disables(self) -> None:
        from shop_bot.portal_balance import create_topup_payment

        with patch.dict(os.environ, {"MINIAPP_PAYMENTS_LIVE": "0"}):
            doc = create_topup_payment(telegram_id=8001, amount_rub=600)
        self.assertEqual(doc["error"], "payments_disabled")

    def test_amount_bounds(self) -> None:
        from shop_bot.portal_balance import create_topup_payment

        self.assertEqual(create_topup_payment(telegram_id=8001, amount_rub=50)["error"], "amount_out_of_range")
        self.assertEqual(
            create_topup_payment(telegram_id=8001, amount_rub=20000)["error"], "amount_out_of_range"
        )
        self.assertEqual(create_topup_payment(telegram_id=8001, amount_rub=None)["error"], "invalid_amount")

    def test_terms_required(self) -> None:
        from shop_bot.portal_balance import create_topup_payment

        _db.register_user_if_not_exists(8002, "no_terms")  # not agreed
        self.assertEqual(create_topup_payment(telegram_id=8002, amount_rub=600)["error"], "terms_required")

    def test_dry_run_returns_confirmation_url(self) -> None:
        from shop_bot.portal_balance import create_topup_payment

        doc = create_topup_payment(telegram_id=8001, amount_rub=600)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["amount_rub"], 600.0)
        self.assertEqual(doc["days"], 90)
        self.assertIn("sandbox.invalid", doc["confirmation_url"])

    def test_metadata_matches_webhook_contract(self) -> None:
        """create-payment metadata must be what payment_queue._handle_yookassa reads."""
        from shop_bot import portal_balance

        captured: dict = {}

        def _fake_create(payload, idempotency_key=None):
            captured["payload"] = payload

            class _Conf:
                confirmation_url = "https://sandbox.invalid/pay/x"

            class _Pay:
                id = "qa-pay-x"
                confirmation = _Conf()

            return _Pay()

        with patch("shop_bot.yookassa_payment.payment_create", _fake_create):
            doc = portal_balance.create_topup_payment(telegram_id=8001, amount_rub=600)
        self.assertTrue(doc["ok"])
        meta = captured["payload"]["metadata"]
        # Exact keys consumed by webhook_server/payment_queue._handle_yookassa
        self.assertEqual(meta["t"], "topup")
        self.assertEqual(int(meta["user_id"]), 8001)
        self.assertEqual(float(meta["amount"]), 600.0)
        self.assertEqual(captured["payload"]["confirmation"]["type"], "redirect")
        self.assertEqual(
            captured["payload"]["confirmation"]["return_url"],
            "https://app.bendervpn.io/portal/cabinet.html",
        )


if __name__ == "__main__":
    unittest.main()
