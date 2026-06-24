"""Offline unit tests for balance/day-rate billing math (BILL-UT-001 scope).

``config`` imports only ``shop_bot.public_urls`` (stdlib), so it loads without
aiogram. Math/label tests lock honest kopeks day-rate (200 RUB = 30 days).
Integration tests exercise ``charge_daily_balance_if_due`` against a temp SQLite DB.
No live Telegram / YooKassa / Remna calls.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
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

from shop_bot.config import (  # noqa: E402
    DAILY_RATE,
    DAILY_RATE_KOPEKS,
    TOPUP_PRESETS,
    balance_to_days,
    daily_charge_rub,
    rub_to_kopeks,
    topup_button_label,
)


def _wire_database_module(database) -> None:
    _dm = types.ModuleType("shop_bot.data_manager")
    sys.modules["shop_bot.data_manager"] = _dm
    sys.modules["shop_bot.data_manager.database"] = database
    _dm.database = database


def _wire_remnawave_stub() -> None:
    _mod = types.ModuleType("shop_bot.modules")
    sys.modules["shop_bot.modules"] = _mod
    remnawave_api = importlib.import_module("remnawave_api")
    sys.modules["shop_bot.modules.remnawave_api"] = remnawave_api
    _mod.remnawave_api = remnawave_api


def _utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _daily_action_for_today() -> str:
    return f"daily_balance:{_utc_date_str()}"


class TestDailyRate(unittest.TestCase):
    def test_daily_rate_kopeks_and_display(self) -> None:
        self.assertEqual(DAILY_RATE_KOPEKS, 666)
        self.assertEqual(DAILY_RATE, 6.66)
        self.assertEqual(daily_charge_rub(), 6.66)


class TestBalanceToDays(unittest.TestCase):
    def test_below_one_day_is_zero(self) -> None:
        self.assertEqual(balance_to_days(0), 0)
        self.assertEqual(balance_to_days(6.65), 0)

    def test_exactly_one_day(self) -> None:
        self.assertEqual(balance_to_days(6.66), 1)

    def test_floor_behavior(self) -> None:
        # 50 ₽ = 5000 kopeks // 666 = 7 whole days
        self.assertEqual(balance_to_days(50), 7)

    def test_200_is_exactly_30_days(self) -> None:
        self.assertEqual(balance_to_days(200), 30)
        self.assertEqual(rub_to_kopeks(200) // DAILY_RATE_KOPEKS, 30)

    def test_2000_is_about_ten_months(self) -> None:
        self.assertEqual(balance_to_days(2000), 300)

    def test_monotonic_non_decreasing(self) -> None:
        prev = -1
        for rub in range(0, 2001, 50):
            d = balance_to_days(rub)
            self.assertGreaterEqual(d, prev)
            prev = d


class TestTopupLabels(unittest.TestCase):
    def test_label_matches_balance_to_days(self) -> None:
        for _key, (_name, _price, amount) in TOPUP_PRESETS.items():
            label = topup_button_label(amount)
            self.assertIn(str(balance_to_days(amount)), label)

    def test_200_preset_label_says_30(self) -> None:
        self.assertIn("30", topup_button_label(200))


class TestChargeDailyBalanceIfDue(unittest.TestCase):
    """BILL-UT-001: charge_daily_balance_if_due integration (temp SQLite)."""

    _tmp_path: str
    database: types.ModuleType
    balance_billing: types.ModuleType

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        cls._tmp_path = cls._tmp.name
        os.environ["SHOP_BOT_DB_PATH"] = cls._tmp_path
        cls.database = importlib.import_module("database")
        cls.database.DB_FILE = Path(cls._tmp_path)
        _wire_database_module(cls.database)
        _wire_remnawave_stub()
        cls.database.initialize_db()
        cls.balance_billing = importlib.import_module("balance_billing")

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._tmp_path)
        except OSError:
            pass

    def setUp(self) -> None:
        uid = self._uid()
        with self.database.db_connection() as conn:
            conn.execute("DELETE FROM user_actions")
            conn.execute("DELETE FROM users")
            conn.commit()
        self.database.register_user_if_not_exists(uid, "bill_ut_user")
        self.database.add_balance(uid, 0.0)

    def _uid(self) -> int:
        return 900_001

    def _balance(self) -> float:
        return self.database.get_balance(self._uid())

    def _action_meta(self, action: str) -> str | None:
        return self.database.get_latest_action_meta(self._uid(), action)

    @patch("balance_billing.BOT_PAYMENTS_LIVE", False)
    def test_skipped_when_payments_not_live(self) -> None:
        self.database.add_balance(self._uid(), 100.0)
        status = self.balance_billing.charge_daily_balance_if_due(self._uid())
        self.assertEqual(status, "skipped")
        self.assertAlmostEqual(self._balance(), 100.0, places=2)
        self.assertFalse(self.database.has_action(self._uid(), _daily_action_for_today()))

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    def test_charged_deducts_daily_rate(self) -> None:
        charge = daily_charge_rub()
        self.database.add_balance(self._uid(), 100.0)
        status = self.balance_billing.charge_daily_balance_if_due(self._uid())
        self.assertEqual(status, "charged")
        self.assertAlmostEqual(self._balance(), 100.0 - charge, places=2)
        self.assertEqual(self._action_meta(_daily_action_for_today()), f"{charge:.2f}")

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    def test_second_call_same_day_is_already(self) -> None:
        charge = daily_charge_rub()
        self.database.add_balance(self._uid(), 100.0)
        self.assertEqual(self.balance_billing.charge_daily_balance_if_due(self._uid()), "charged")
        status = self.balance_billing.charge_daily_balance_if_due(self._uid())
        self.assertEqual(status, "already")
        self.assertAlmostEqual(self._balance(), 100.0 - charge, places=2)

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    def test_insufficient_balance_logs_pause(self) -> None:
        self.database.add_balance(self._uid(), 6.65)
        status = self.balance_billing.charge_daily_balance_if_due(self._uid())
        self.assertEqual(status, "insufficient")
        self.assertAlmostEqual(self._balance(), 6.65, places=2)
        self.assertEqual(self._action_meta(_daily_action_for_today()), "insufficient")

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    def test_after_insufficient_retry_same_day_is_already(self) -> None:
        self.database.add_balance(self._uid(), 6.65)
        self.assertEqual(self.balance_billing.charge_daily_balance_if_due(self._uid()), "insufficient")
        self.assertEqual(self.balance_billing.charge_daily_balance_if_due(self._uid()), "already")
        self.assertAlmostEqual(self._balance(), 6.65, places=2)

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    def test_exactly_one_day_rate_charges_to_near_zero(self) -> None:
        charge = daily_charge_rub()
        self.database.add_balance(self._uid(), charge)
        status = self.balance_billing.charge_daily_balance_if_due(self._uid())
        self.assertEqual(status, "charged")
        self.assertAlmostEqual(self._balance(), 0.0, places=2)

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    def test_waive_blocks_charge_same_day(self) -> None:
        self.database.add_balance(self._uid(), 100.0)
        self.balance_billing.waive_daily_charge_today(self._uid())
        status = self.balance_billing.charge_daily_balance_if_due(self._uid())
        self.assertEqual(status, "already")
        self.assertAlmostEqual(self._balance(), 100.0, places=2)
        self.assertEqual(self._action_meta(_daily_action_for_today()), "waived_topup")

    @patch("balance_billing.BOT_PAYMENTS_LIVE", True)
    @patch("balance_billing._utc_today")
    def test_waive_does_not_block_next_utc_day(self, mock_today) -> None:
        charge = daily_charge_rub()
        mock_today.side_effect = ["2026-06-24", "2026-06-25"]
        self.database.add_balance(self._uid(), 100.0)
        self.balance_billing.waive_daily_charge_today(self._uid())
        self.assertEqual(self.balance_billing.charge_daily_balance_if_due(self._uid()), "charged")
        self.assertAlmostEqual(self._balance(), 100.0 - charge, places=2)
        self.assertEqual(self._action_meta("daily_balance:2026-06-25"), f"{charge:.2f}")


if __name__ == "__main__":
    unittest.main()
