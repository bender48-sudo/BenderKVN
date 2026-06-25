"""Offline tests for balance_ledger (v8) + idempotent referral accrual (REF-LEDGER-001).

No live Telegram / payments. Covers: the v8 migration shape, credit_ledger atomic idempotency
(one row + one balance bump per (user, ref)), the rewards gate (no-op while OFF), the 30%
first-top-up referrer reward + 100₽ welcome bonus when ON, double-pay protection, and that
/portal-referral surfaces the real earned_rub / per-invitee reward_rub from the ledger.
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
    path = Path(tempfile.mkdtemp()) / "ledger.db"
    os.environ["SHOP_BOT_DB_PATH"] = str(path)
    _db.DB_FILE = str(path)
    _db.initialize_db()
    return path


class TestMigrationV8(unittest.TestCase):
    def test_table_and_indexes_exist(self) -> None:
        _fresh_db()
        from shop_bot.schema_migrations import SCHEMA_VERSION

        self.assertGreaterEqual(SCHEMA_VERSION, 8)
        with _db.db_connection() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(balance_ledger)").fetchall()}
            self.assertEqual(
                cols,
                {
                    "id",
                    "user_id",
                    "kind",
                    "amount_kopeks",
                    "balance_after_kopeks",
                    "ref",
                    "meta",
                    "created_at_utc",
                },
            )
            idx = {r[1] for r in conn.execute("PRAGMA index_list(balance_ledger)").fetchall()}
            self.assertIn("idx_ledger_user_ref", idx)


class TestCreditLedger(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(9001, "ledger_user")

    def test_credit_applies_balance_and_records_after(self) -> None:
        ok = _db.credit_ledger(9001, "referral_reward", 10000, "ref_first:42")  # +100.00 ₽
        self.assertTrue(ok)
        self.assertEqual(_db.get_balance(9001), 100.0)
        rows = _db.get_ledger_entries(9001)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount_kopeks"], 10000)
        self.assertEqual(rows[0]["balance_after_kopeks"], 10000)

    def test_idempotent_same_ref_no_double_credit(self) -> None:
        self.assertTrue(_db.credit_ledger(9001, "referral_reward", 10000, "ref_first:42"))
        self.assertFalse(_db.credit_ledger(9001, "referral_reward", 10000, "ref_first:42"))
        self.assertEqual(_db.get_balance(9001), 100.0)  # credited once
        self.assertEqual(len(_db.get_ledger_entries(9001)), 1)

    def test_missing_user_no_row(self) -> None:
        self.assertFalse(_db.credit_ledger(424242, "referral_reward", 10000, "ref_first:1"))


class TestAccrualGate(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(1001, "referrer")
        self.code = _db.ensure_user_ref_code(1001)
        _db.register_user_if_not_exists(1002, "invitee")
        _db.set_terms_agreed(1002)
        _db.link_referral(self.code, 1002)

    def test_first_topup_reward_noop_when_gate_off(self) -> None:
        from shop_bot.referral_rewards import credit_referrer_first_topup

        with patch.dict(os.environ, {"REFERRAL_REWARDS_ACTIVE": "0"}):
            self.assertFalse(credit_referrer_first_topup(1002, 600))
        self.assertEqual(_db.get_balance(1001), 0.0)

    def test_first_topup_reward_credits_referrer_when_on(self) -> None:
        from shop_bot.referral_rewards import credit_referrer_first_topup

        with patch.dict(os.environ, {"REFERRAL_REWARDS_ACTIVE": "1"}):
            self.assertTrue(credit_referrer_first_topup(1002, 600))  # 30% of 600 = 180
            self.assertEqual(_db.get_balance(1001), 180.0)
            # Idempotent: a duplicate first-topup call does not double-pay.
            self.assertFalse(credit_referrer_first_topup(1002, 600))
            self.assertEqual(_db.get_balance(1001), 180.0)

    def test_welcome_bonus_credits_invitee_when_on(self) -> None:
        from shop_bot.referral_rewards import credit_referral_welcome

        with patch.dict(os.environ, {"REFERRAL_REWARDS_ACTIVE": "1"}):
            self.assertTrue(credit_referral_welcome(1002))  # +100 ₽
            self.assertEqual(_db.get_balance(1002), 100.0)
            self.assertFalse(credit_referral_welcome(1002))  # once per user
            self.assertEqual(_db.get_balance(1002), 100.0)

    def test_welcome_skipped_without_terms(self) -> None:
        from shop_bot.referral_rewards import credit_referral_welcome

        _db.register_user_if_not_exists(1003, "noterms")
        _db.link_referral(self.code, 1003)  # referred but not agreed terms
        with patch.dict(os.environ, {"REFERRAL_REWARDS_ACTIVE": "1"}):
            self.assertFalse(credit_referral_welcome(1003))
        self.assertEqual(_db.get_balance(1003), 0.0)


class TestPortalReferralEarned(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(2001, "ref_owner")
        self.code = _db.ensure_user_ref_code(2001)
        _db.register_user_if_not_exists(2002, "paid_friend")
        _db.set_terms_agreed(2002)
        _db.link_referral(self.code, 2002)
        _db.log_action(2002, "topup", "600.0")  # friend paid (status fact)

    def test_earned_reflects_ledger_rewards(self) -> None:
        from shop_bot.portal_referral import referral_snapshot
        from shop_bot.referral_rewards import credit_referrer_first_topup

        with patch.dict(os.environ, {"REFERRAL_REWARDS_ACTIVE": "1"}):
            credit_referrer_first_topup(2002, 600)  # +180 ₽ to 2001
            doc = referral_snapshot(telegram_id=2001)
        self.assertEqual(doc["earned_rub"], 180.0)
        inv = {i["user_id"]: i for i in doc["invitees"]}[2002]
        self.assertEqual(inv["status"], "paid")
        self.assertEqual(inv["reward_rub"], 180.0)


if __name__ == "__main__":
    unittest.main()
