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

from shop_bot.portal_cabinet import (  # noqa: E402
    build_billing_fields,
    build_configuration_fields,
    cabinet_snapshot,
)


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
        self.assertIn("6.66", doc["billing_note"])
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


class TestBuildConfigurationFields(unittest.TestCase):
    def test_no_keys(self) -> None:
        doc = build_configuration_fields([], "expired")
        self.assertEqual(doc["active_config_count"], 0)
        self.assertEqual(doc["configurations"], [])
        self.assertFalse(doc["multiple_configs_anomaly"])

    def test_one_active_key(self) -> None:
        keys = [{"key_id": 10, "key_email": "u-key1-trial@x", "expiry_date": _future(30), "created_date": _past(1)}]
        doc = build_configuration_fields(keys, "trial")
        self.assertEqual(doc["active_config_count"], 1)
        self.assertEqual(len(doc["configurations"]), 1)
        cfg = doc["configurations"][0]
        self.assertTrue(cfg["active"])
        self.assertEqual(cfg["status"], "active")
        self.assertTrue(cfg["is_primary"])
        self.assertTrue(cfg["has_subscription_url"])
        self.assertIsNone(cfg["subscription_url_masked"])
        self.assertFalse(cfg["billable"])

    def test_expired_key_listed(self) -> None:
        keys = [{"key_id": 11, "key_email": "u@x", "expiry_date": _past(5)}]
        doc = build_configuration_fields(keys, "expired")
        self.assertEqual(doc["active_config_count"], 0)
        self.assertEqual(doc["configurations"][0]["status"], "expired")
        self.assertFalse(doc["configurations"][0]["active"])

    def test_multiple_active_anomaly(self) -> None:
        keys = [
            {"key_id": 1, "key_email": "a@x", "expiry_date": _future(10)},
            {"key_id": 2, "key_email": "b@x", "expiry_date": _future(20)},
        ]
        doc = build_configuration_fields(keys, "trial")
        self.assertEqual(doc["active_config_count"], 2)
        self.assertTrue(doc["multiple_configs_anomaly"])
        primaries = [c for c in doc["configurations"] if c["is_primary"]]
        self.assertEqual(len(primaries), 1)
        self.assertEqual(primaries[0]["key_id"], 2)

    def test_wallet_one_active_billable(self) -> None:
        keys = [{"key_id": 7, "key_email": "w@x", "expiry_date": _future(15)}]
        doc = build_configuration_fields(keys, "wallet")
        self.assertTrue(doc["configurations"][0]["billable"])

    def test_legacy_one_active(self) -> None:
        keys = [{"key_id": 3, "key_email": "legacy@x", "expiry_date": "2099-12-31T00:00:00+00:00"}]
        doc = build_configuration_fields(keys, "legacy")
        self.assertEqual(doc["active_config_count"], 1)
        self.assertFalse(doc["configurations"][0]["billable"])


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
        self.assertIn("configurations", doc)
        self.assertIsInstance(doc["configurations"], list)


if __name__ == "__main__":
    unittest.main()
