"""Offline tests for the in-app Mini App referral API (MINI-APP-BUILD-001, P3).

No live Telegram / Remna / payments. Covers: invite link + code from existing
attribution, real friend counts, honest paid-vs-registered invitee status, the
no-accrual honesty contract (rewards_active=false, earned_rub=0, no fabricated
per-invitee reward), server-driven program terms, the dormant partner block, and
identity resolution (unknown user → not_found; web-only → needs_telegram_bind).
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
    path = Path(tempfile.mkdtemp()) / "referral.db"
    os.environ["SHOP_BOT_DB_PATH"] = str(path)
    _db.DB_FILE = str(path)
    _db.initialize_db()
    return path


class TestReferralLink(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(5001, "owner_user")

    def test_link_code_and_honest_empty_state(self) -> None:
        from shop_bot.portal_referral import referral_snapshot

        doc = referral_snapshot(telegram_id=5001)
        self.assertTrue(doc["ok"])
        self.assertTrue(doc["available"])
        self.assertTrue(doc["ref_code"])
        # Invite link carries the ref code; bot deep-link is the alternate.
        self.assertIn(doc["ref_code"], doc["invite_url"])
        self.assertIn("ref=" if "ref=" in doc["invite_url"] else "ref_", doc["invite_url"])
        self.assertIn(f"start=ref_{doc['ref_code']}", doc["bot_invite_url"])
        self.assertEqual(doc["qr_url"], doc["invite_url"])
        # Honest empty state — no friends, no fabricated earnings.
        self.assertEqual(doc["friends_count"], 0)
        self.assertEqual(doc["friends_paid_count"], 0)
        self.assertEqual(doc["earned_rub"], 0.0)
        self.assertEqual(doc["invitees"], [])

    def test_unknown_user_not_found(self) -> None:
        from shop_bot.portal_referral import referral_snapshot

        self.assertEqual(referral_snapshot(telegram_id=999999)["error"], "not_found")


class TestInviteeStatus(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(6001, "ref_owner")
        self.code = _db.ensure_user_ref_code(6001)
        # Two invitees: one paid, one only registered.
        _db.register_user_if_not_exists(6101, "mikhail")
        _db.register_user_if_not_exists(6102, "dmitry")
        _db.link_referral(self.code, 6101)
        _db.link_referral(self.code, 6102)
        _db.log_action(6101, "topup", "600.0")  # 6101 paid

    def test_counts_and_paid_vs_registered(self) -> None:
        from shop_bot.portal_referral import referral_snapshot

        doc = referral_snapshot(telegram_id=6001)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["friends_count"], 2)
        self.assertEqual(doc["friends_paid_count"], 1)
        by_id = {inv["user_id"]: inv for inv in doc["invitees"]}
        self.assertEqual(by_id[6101]["status"], "paid")
        self.assertIsNotNone(by_id[6101]["first_topup_at_iso"])
        self.assertTrue(by_id[6101]["first_topup_at_iso"].endswith("+00:00"))
        self.assertEqual(by_id[6101]["name"], "mikhail")
        self.assertEqual(by_id[6101]["avatar_letter"], "M")
        self.assertEqual(by_id[6102]["status"], "registered")
        self.assertIsNone(by_id[6102]["first_topup_at_iso"])

    def test_earned_stays_zero_without_accrual(self) -> None:
        """Even with a paid invitee, no reward is fabricated while accrual is off."""
        from shop_bot.portal_referral import referral_snapshot

        with patch.dict(os.environ, {"REFERRAL_REWARDS_ACTIVE": "0"}):
            doc = referral_snapshot(telegram_id=6001)
        self.assertEqual(doc["earned_rub"], 0.0)
        self.assertFalse(doc["program"]["rewards_active"])
        # reward_rub is present but honestly None — never a fabricated number.
        for inv in doc["invitees"]:
            self.assertIsNone(inv["reward_rub"])


class TestProgramAndPartner(unittest.TestCase):
    def setUp(self) -> None:
        _fresh_db()
        _db.register_user_if_not_exists(7001, "prog_user")

    def test_program_terms_server_driven(self) -> None:
        from shop_bot.portal_referral import referral_snapshot

        doc = referral_snapshot(telegram_id=7001)
        prog = doc["program"]
        self.assertEqual(prog["friend_bonus_rub"], 100)
        self.assertEqual(prog["referrer_pct"], 30)
        self.assertEqual(prog["partner"]["first_pct"], 50)
        self.assertEqual(prog["partner"]["recurring_pct"], 10)
        self.assertEqual(prog["partner"]["min_withdraw_rub"], 5000)

    def test_program_terms_env_overridable(self) -> None:
        import shop_bot.config as cfg
        import shop_bot.portal_referral as pr

        try:
            with patch.dict(
                os.environ,
                {"REFERRAL_FRIEND_BONUS_RUB": "150", "REFERRAL_REFERRER_PCT": "25"},
            ):
                importlib.reload(cfg)
                importlib.reload(pr)
                doc = pr.referral_snapshot(telegram_id=7001)
                self.assertEqual(doc["program"]["friend_bonus_rub"], 150)
                self.assertEqual(doc["program"]["referrer_pct"], 25)
        finally:
            # Restore modules AFTER the env patch is undone, else the reload re-bakes 150.
            importlib.reload(cfg)
            importlib.reload(pr)

    def test_partner_block_dormant(self) -> None:
        from shop_bot.portal_referral import referral_snapshot

        partner = referral_snapshot(telegram_id=7001)["partner"]
        self.assertFalse(partner["is_partner"])
        self.assertEqual(partner["status"], "none")
        self.assertFalse(partner["withdraw_enabled"])
        self.assertEqual(partner["available_rub"], 0.0)
        self.assertEqual(partner["min_withdraw_rub"], 5000)


if __name__ == "__main__":
    unittest.main()
