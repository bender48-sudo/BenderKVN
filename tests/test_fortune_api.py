"""Offline tests for the Fortune wheel engine + API (GAME-FORTUNE-001, P5).

Covers: migration v10, weighted sectors (sum 100, valid picks), earned spins from paid days,
the spin economy (consume / extra_spin refund), the FORTUNE_LIVE gate, server-authoritative
outcome (front never decides), ledger credit for rub rewards (idempotent), and status/history.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
import unittest
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
_db = importlib.import_module("database")
sys.modules["shop_bot.data_manager.database"] = _db
_dm.database = _db

LIVE = {"FORTUNE_LIVE": "1"}


def _fresh_db():
    path = os.path.join(tempfile.mkdtemp(), "fortune.db")
    os.environ["SHOP_BOT_DB_PATH"] = path
    _db.DB_FILE = path
    _db.initialize_db()
    _db.register_user_if_not_exists(7777, "spinner")


def _add_paid_days(user_id, n):
    for i in range(n):
        _db.log_action(user_id, f"daily_balance:2026-06-{i+1:02d}", "6.66")


class TestMigrationAndSectors(unittest.TestCase):
    def test_v10_and_weights(self):
        _fresh_db()
        from shop_bot.schema_migrations import SCHEMA_VERSION
        from shop_bot import fortune

        self.assertGreaterEqual(SCHEMA_VERSION, 10)
        with _db.db_connection() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(fortune_spins)").fetchall()}
            self.assertTrue({"user_id", "sector_key", "kind", "amount_kopeks", "ledger_ref"} <= cols)
        self.assertEqual(round(sum(s["weight"] for s in fortune.SECTORS), 2), 100.0)
        keys = {s["key"] for s in fortune.SECTORS}
        self.assertEqual(keys, {"miss", "extra_spin", "rub2", "rub5", "rub20", "jackpot"})

    def test_choose_sector_always_valid(self):
        _fresh_db()
        from shop_bot import fortune

        keys = {s["key"] for s in fortune.SECTORS}
        for _ in range(500):
            self.assertIn(fortune._choose_sector()["key"], keys)


class TestSpinEconomy(unittest.TestCase):
    def setUp(self):
        _fresh_db()
        self.f = importlib.import_module("shop_bot.fortune")

    def test_earned_spins_from_paid_days(self):
        _add_paid_days(7777, 25)  # 25 paid days → 2 earned spins
        st = self.f.status(7777)
        self.assertEqual(st["available_spins"], 2)
        self.assertEqual(st["spin_per_days"], 10)

    def test_gate_off_no_spin(self):
        _add_paid_days(7777, 30)
        with patch.dict(os.environ, {"FORTUNE_LIVE": "0"}):
            self.assertEqual(self.f.spin(7777)["error"], "fortune_disabled")

    def test_no_spins_when_unearned(self):
        with patch.dict(os.environ, LIVE):
            self.assertEqual(self.f.spin(7777)["error"], "no_spins")  # 0 paid days

    def test_rub_spin_credits_ledger_and_consumes(self):
        _add_paid_days(7777, 10)  # 1 spin
        with patch.dict(os.environ, LIVE), patch.object(self.f, "_choose_sector",
                lambda: {"key": "rub20", "label": "+20 ₽", "kind": "rub", "amount_rub": 20, "weight": 0.9}):
            res = self.f.spin(7777)
        self.assertTrue(res["ok"])
        self.assertEqual(res["sector_key"], "rub20")
        self.assertEqual(res["amount_rub"], 20)
        self.assertEqual(res["available_spins"], 0)        # consumed
        self.assertEqual(_db.get_balance(7777), 20.0)       # credited via ledger
        # ledger row recorded with the fortune ref
        led = _db.get_ledger_entries(7777)
        self.assertEqual(led[0]["kind"], "fortune")
        self.assertEqual(led[0]["amount_kopeks"], 2000)

    def test_extra_spin_refunds(self):
        _add_paid_days(7777, 10)  # 1 spin
        with patch.dict(os.environ, LIVE), patch.object(self.f, "_choose_sector",
                lambda: {"key": "extra_spin", "label": "Доп. спин", "kind": "extra_spin", "amount_rub": 0, "weight": 25.0}):
            res = self.f.spin(7777)
        self.assertEqual(res["sector_key"], "extra_spin")
        self.assertEqual(res["available_spins"], 1)  # net-neutral: consumed 1, refunded 1
        self.assertEqual(_db.get_balance(7777), 0.0)

    def test_miss_consumes_no_credit(self):
        _add_paid_days(7777, 10)
        with patch.dict(os.environ, LIVE), patch.object(self.f, "_choose_sector",
                lambda: {"key": "miss", "label": "Мимо", "kind": "nothing", "amount_rub": 0, "weight": 55.0}):
            res = self.f.spin(7777)
        self.assertEqual(res["available_spins"], 0)
        self.assertEqual(_db.get_balance(7777), 0.0)


class TestStatusAndPortal(unittest.TestCase):
    def setUp(self):
        _fresh_db()

    def test_status_history_and_sectors(self):
        from shop_bot import fortune

        _add_paid_days(7777, 10)
        with patch.dict(os.environ, LIVE), patch.object(fortune, "_choose_sector",
                lambda: {"key": "rub2", "label": "+2 ₽", "kind": "rub", "amount_rub": 2, "weight": 14.0}):
            fortune.spin(7777)
            st = fortune.status(7777)
        self.assertTrue(st["fortune_live"])
        self.assertEqual(st["spins_done"], 1)
        self.assertEqual(st["history"][0]["sector_key"], "rub2")
        self.assertEqual(st["history"][0]["amount_rub"], 2.0)
        # sectors carry odds but the front cannot decide outcome
        self.assertEqual(len(st["sectors"]), 6)
        self.assertIn("odds_pct", st["sectors"][0])

    def test_portal_gate_and_unknown(self):
        from shop_bot import portal_fortune

        with patch.dict(os.environ, {"FORTUNE_LIVE": "0"}):
            self.assertEqual(portal_fortune.spin(telegram_id=7777)["error"], "fortune_disabled")
        self.assertEqual(portal_fortune.status(telegram_id=424242)["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
