"""Functional tests for atomic webhook claim (BILL-WEBHOOK-CLAIM-TOCTOU-001).

Uses a real temporary SQLite DB (no aiogram needed) by pointing SHOP_BOT_DB_PATH
at a temp file before importing the standalone ``database`` module. No live
Telegram / YooKassa / Remna calls.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_BOT_SRC = _REPO / "bot_src"
if str(_BOT_SRC) not in sys.path:
    sys.path.insert(0, str(_BOT_SRC))
if "shop_bot" not in sys.modules:
    _pkg = types.ModuleType("shop_bot")
    _pkg.__path__ = [str(_BOT_SRC)]  # type: ignore[attr-defined]
    sys.modules["shop_bot"] = _pkg

_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["SHOP_BOT_DB_PATH"] = _TMP.name

database = importlib.import_module("database")
# Force isolation regardless of import order: db_connection() reads this module
# global on every call, so other tests / the real dev DB are never touched.
database.DB_FILE = Path(_TMP.name)


def _create_table() -> None:
    with database.db_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS webhook_deliveries (
                   idempotency_key TEXT PRIMARY KEY,
                   source TEXT NOT NULL,
                   status TEXT NOT NULL,
                   payload_json TEXT,
                   error TEXT,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        conn.commit()


class TestWebhookClaim(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _create_table()

    def setUp(self) -> None:
        with database.db_connection() as conn:
            conn.execute("DELETE FROM webhook_deliveries")
            conn.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(_TMP.name)
        except OSError:
            pass

    def test_first_claim_is_new(self) -> None:
        self.assertEqual(database.claim_webhook_delivery("k1", "yk", "{}"), "new")

    def test_second_claim_is_in_progress_not_new(self) -> None:
        self.assertEqual(database.claim_webhook_delivery("k2", "yk", "{}"), "new")
        # A concurrent / retried delivery must never get a second "new".
        self.assertEqual(database.claim_webhook_delivery("k2", "yk", "{}"), "in_progress")

    def test_done_then_claim_is_duplicate(self) -> None:
        self.assertEqual(database.claim_webhook_delivery("k3", "yk", "{}"), "new")
        database.mark_webhook_done("k3")
        self.assertEqual(database.claim_webhook_delivery("k3", "yk", "{}"), "duplicate")

    def test_failed_then_claim_is_retry(self) -> None:
        self.assertEqual(database.claim_webhook_delivery("k4", "yk", "{}"), "new")
        database.mark_webhook_failed("k4", "boom")
        self.assertEqual(database.claim_webhook_delivery("k4", "yk", "{}"), "retry")

    def test_preexisting_row_blocks_new(self) -> None:
        """Simulate the TOCTOU winner: a row already exists -> claim is not 'new'."""
        with database.db_connection() as conn:
            conn.execute(
                "INSERT INTO webhook_deliveries (idempotency_key, source, status, payload_json)"
                " VALUES (?, ?, 'pending', ?)",
                ("race", "yk", "{}"),
            )
            conn.commit()
        self.assertNotEqual(database.claim_webhook_delivery("race", "yk", "{}"), "new")

    def test_only_one_new_across_many_claims(self) -> None:
        results = [database.claim_webhook_delivery("k5", "yk", "{}") for _ in range(5)]
        self.assertEqual(results.count("new"), 1, results)


if __name__ == "__main__":
    unittest.main()
