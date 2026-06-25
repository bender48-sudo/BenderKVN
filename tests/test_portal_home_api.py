"""Offline tests for the in-app Mini App home summary API (MINI-APP-BUILD-001, P-HOME).

No live Telegram / Remna / payments. Covers: aggregation of access + balance + referral into
one payload, honest capacity (no fabricated counter), unread=0, the Fortune banner flag, and
error propagation from the cabinet (not_found / terms_required).
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import time
import types
import unittest

sys_path_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOT_SRC = os.path.join(sys_path_repo, "bot_src")
if _BOT_SRC not in sys.path:
    sys.path.insert(0, _BOT_SRC)
if "shop_bot" not in sys.modules:
    _pkg = types.ModuleType("shop_bot")
    _pkg.__path__ = [_BOT_SRC]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = _pkg

_dm = types.ModuleType("shop_bot.data_manager")
sys.modules["shop_bot.data_manager"] = _dm
_db = importlib.import_module("database")
sys.modules["shop_bot.data_manager.database"] = _db
_dm.database = _db


def _fresh_db() -> None:
    path = os.path.join(tempfile.mkdtemp(), "home.db")
    os.environ["SHOP_BOT_DB_PATH"] = path
    _db.DB_FILE = path
    _db.initialize_db()


class TestHomeAggregate(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(3001, "valera_lera")
        _db.set_terms_agreed(3001)
        _db.set_balance(3001, 320.0)
        # active config (device) with future expiry
        future_ms = int((time.time() + 80 * 86400) * 1000)
        _db.add_new_key(3001, "uuid-1", "k1@bvpn", future_ms)
        # 2 referrals, one paid
        code = _db.ensure_user_ref_code(3001)
        _db.register_user_if_not_exists(3101, "friend_a")
        _db.register_user_if_not_exists(3102, "friend_b")
        _db.link_referral(code, 3101)
        _db.link_referral(code, 3102)
        _db.log_action(3101, "topup", "600.0")

    def test_aggregates_access_balance_referral(self) -> None:
        from shop_bot.portal_home import home_snapshot

        doc = home_snapshot(telegram_id=3001)
        self.assertTrue(doc["ok"])
        # access
        self.assertEqual(doc["access"]["device_count"], 1)
        self.assertIn(doc["access"]["status"], ("trial", "active"))
        self.assertTrue(doc["access"]["has_access"])
        self.assertGreater(doc["access"]["days_left"], 0)
        self.assertTrue(doc["access"]["traffic_unlimited"])
        # balance
        self.assertEqual(doc["balance"]["balance_rub"], 320.0)
        self.assertGreater(doc["balance"]["days_left"], 0)
        # referral (counts real; earned 0 while accrual gated OFF)
        self.assertEqual(doc["referral"]["friends_count"], 2)
        self.assertEqual(doc["referral"]["earned_rub"], 0.0)
        self.assertTrue(doc["referral"]["available"])
        # profile
        self.assertEqual(doc["profile"]["username"], "valera_lera")
        self.assertEqual(doc["profile"]["language"], "ru")

    def test_capacity_honest_no_fake_counter(self) -> None:
        from shop_bot.portal_home import home_snapshot

        cap = home_snapshot(telegram_id=3001)["capacity"]
        self.assertFalse(cap["counter_available"])
        self.assertEqual(cap["cap_limit"], 30000)
        self.assertNotIn("fill", cap)
        self.assertNotIn("active_count", cap)

    def test_unread_zero_and_banners(self) -> None:
        from shop_bot.portal_home import home_snapshot

        doc = home_snapshot(telegram_id=3001)
        self.assertEqual(doc["unread"], 0)
        self.assertTrue(doc["banners"]["referral"])
        self.assertTrue(doc["banners"]["access_card"])
        self.assertTrue(doc["banners"]["fortune"]["show"])
        self.assertEqual(doc["banners"]["fortune"]["state"], "in_development")


class TestHomeErrors(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()

    def test_unknown_user_not_found(self) -> None:
        from shop_bot.portal_home import home_snapshot

        self.assertEqual(home_snapshot(telegram_id=999999)["error"], "not_found")

    def test_terms_required_propagates(self) -> None:
        from shop_bot.portal_home import home_snapshot

        _db.register_user_if_not_exists(4001, "no_terms")  # not agreed
        doc = home_snapshot(telegram_id=4001)
        self.assertFalse(doc["ok"])
        self.assertEqual(doc["error"], "terms_required")


if __name__ == "__main__":
    unittest.main()
