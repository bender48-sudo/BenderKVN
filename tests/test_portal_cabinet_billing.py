"""Unit tests for portal_cabinet billing_profile (P1-CAB-001)."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
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

import importlib

_dm = types.ModuleType("shop_bot.data_manager")
sys.modules["shop_bot.data_manager"] = _dm
_db = importlib.import_module("database")
sys.modules["shop_bot.data_manager.database"] = _db
_dm.database = _db

from shop_bot.portal_cabinet import build_billing_fields, cabinet_snapshot  # noqa: E402


def _future(days: int) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.isoformat()


def _past(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


class TestBuildBillingFields(unittest.TestCase):
    def test_wallet_user(self) -> None:
        user = {"balance": 200.0, "total_spent": 200.0, "trial_used": True}
        keys = [{"key_id": 1, "key_email": "u1-key1@x", "expiry_date": _future(30)}]
        with patch("shop_bot.portal_cabinet.has_action", return_value=False), patch(
            "shop_bot.portal_cabinet.BOT_PAYMENTS_LIVE", True
        ):
            doc = build_billing_fields(1001, user, keys)
        self.assertEqual(doc["billing_profile"], "wallet")
        self.assertTrue(doc["is_billable_now"])
        self.assertTrue(doc["next_charge_applicable"])
        self.assertEqual(doc["billable_config_count"], 1)
        self.assertIn("6.67", doc["billing_note"])
        self.assertEqual(doc["active_config_count"], 1)

    def test_trial_user(self) -> None:
        user = {"balance": 0.0, "trial_used": True}
        keys = [{"key_id": 2, "key_email": "u2-key1-trial@x", "expiry_date": _future(60)}]
        doc = build_billing_fields(1002, user, keys)
        self.assertEqual(doc["billing_profile"], "trial")
        self.assertFalse(doc["is_billable_now"])
        self.assertFalse(doc["next_charge_applicable"])
        self.assertEqual(doc["billable_config_count"], 0)
        self.assertIn("Пробный доступ активен", doc["billing_note"])

    def test_legacy_manual_user(self) -> None:
        user = {"balance": 186.66, "trial_used": True, "total_spent": 50.0}
        keys = [{"key_id": 3, "key_email": "owner@x", "expiry_date": "2099-12-31T00:00:00+00:00"}]
        doc = build_billing_fields(1003, user, keys)
        self.assertEqual(doc["billing_profile"], "legacy")
        self.assertFalse(doc["is_billable_now"])
        self.assertFalse(doc["next_charge_applicable"])
        self.assertTrue(doc["legacy_manual_access"])
        self.assertIn("не списывается", doc["billing_note"])
        self.assertEqual(doc["billable_config_count"], 0)

    def test_expired_user(self) -> None:
        user = {"balance": 0.0, "trial_used": True}
        keys = [{"key_id": 4, "key_email": "u4-key1-trial@x", "expiry_date": _past(3)}]
        doc = build_billing_fields(1004, user, keys)
        self.assertEqual(doc["billing_profile"], "expired")
        self.assertEqual(doc["active_config_count"], 0)
        self.assertIn("истёк", doc["billing_note"].lower())

    def test_legacy_balance_not_billable(self) -> None:
        user = {"balance": 186.66, "trial_used": True}
        keys = [{"key_id": 5, "key_email": "legacy@x", "expiry_date": "2099-06-01T00:00:00+00:00"}]
        doc = build_billing_fields(1005, user, keys)
        self.assertEqual(doc["billing_profile"], "legacy")
        self.assertAlmostEqual(float(user["balance"]), 186.66)
        self.assertFalse(doc["is_billable_now"])


class TestCabinetSnapshotBackwardCompat(unittest.TestCase):
    def test_snapshot_keeps_legacy_fields(self) -> None:
        user = {
            "agreed_to_terms": True,
            "balance": 100.0,
            "trial_used": True,
            "total_spent": 0,
        }
        keys = [{"key_id": 1, "key_email": "u-key1-trial@x", "expiry_date": _future(10)}]
        with patch("shop_bot.portal_cabinet.get_user", return_value=user), patch(
            "shop_bot.portal_cabinet.get_user_keys", return_value=keys
        ), patch("shop_bot.portal_cabinet.has_action", return_value=False), patch(
            "shop_bot.portal_cabinet.BOT_PAYMENTS_LIVE", False
        ):
            doc = cabinet_snapshot(telegram_id=4242)
        self.assertTrue(doc["ok"])
        self.assertIn("balance_rub", doc)
        self.assertIn("days_left", doc)
        self.assertIn("daily_rate", doc)
        self.assertIn("billing_profile", doc)
        self.assertIn("billing_note", doc)


if __name__ == "__main__":
    unittest.main()
