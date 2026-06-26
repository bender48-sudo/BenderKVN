"""SUBSCRIPTION-RESOLVE-TZ-001: UTC-aware expiry in subscription_unavailable."""
from __future__ import annotations

import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOT_SRC = os.path.join(_REPO, "bot_src")
if _BOT_SRC not in sys.path:
    sys.path.insert(0, _BOT_SRC)
if "shop_bot" not in sys.modules:
    _pkg = types.ModuleType("shop_bot")
    _pkg.__path__ = [_BOT_SRC]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = _pkg

_dm = types.ModuleType("shop_bot.data_manager")
sys.modules["shop_bot.data_manager"] = _dm
import importlib

_db = importlib.import_module("database")
sys.modules["shop_bot.data_manager.database"] = _db
_dm.database = _db

_mod = types.ModuleType("shop_bot.modules")
sys.modules["shop_bot.modules"] = _mod
_remnawave = importlib.import_module("remnawave_api")
sys.modules["shop_bot.modules.remnawave_api"] = _remnawave
_mod.remnawave_api = _remnawave

from shop_bot.subscription_resolve import _parse_expiry_utc, subscription_unavailable  # noqa: E402


class SubscriptionResolveTzTests(unittest.TestCase):
    def test_parse_expiry_naive_as_utc(self) -> None:
        dt = _parse_expiry_utc("2026-06-26T12:00:00")
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.hour, 12)

    def test_parse_expiry_z_suffix(self) -> None:
        dt = _parse_expiry_utc("2026-06-26T12:00:00Z")
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_active_key_not_treated_expired_when_local_ahead_of_utc(self) -> None:
        """UTC-aware compare: expiry still in the future vs fixed now."""
        expiry_naive = "2026-06-26 14:00:00"
        fixed_now = datetime(2026, 6, 26, 10, 0, 0, tzinfo=timezone.utc)

        with patch("shop_bot.subscription_resolve.get_user", return_value={"agreed_to_terms": 1, "trial_used": 1}), patch(
            "shop_bot.subscription_resolve.get_user_keys",
            return_value=[{"expiry_date": expiry_naive}],
        ), patch("shop_bot.subscription_resolve.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
            doc = subscription_unavailable(4242)

        self.assertEqual(doc["error"], "panel_unreachable")

    def test_expired_key_when_past_utc(self) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with patch("shop_bot.subscription_resolve.get_user", return_value={"agreed_to_terms": 1, "trial_used": 1}), patch(
            "shop_bot.subscription_resolve.get_user_keys",
            return_value=[{"expiry_date": past}],
        ):
            doc = subscription_unavailable(4242)
        self.assertEqual(doc["error"], "subscription_expired")


if __name__ == "__main__":
    unittest.main()
