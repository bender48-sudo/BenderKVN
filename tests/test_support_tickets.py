"""Offline tests for the support ticket model + status engine (SUPPORT-TICKET-BRIDGE-001, P4).

No Telegram I/O. Covers: create (waiting + first user msg + system auto-ack), who-wrote-last
status (user→waiting, staff→answered, system stays waiting), first-reply detection, unread +
mark-read, reopen of a closed ticket, manual close, 3-day auto-close, list/get, topic lookup,
number formatting, subject normalization.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone

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


def _fresh_db():
    path = os.path.join(tempfile.mkdtemp(), "tickets.db")
    os.environ["SHOP_BOT_DB_PATH"] = path
    _db.DB_FILE = path
    _db.initialize_db()


def _backdate(ticket_id, days):
    iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _db.db_connection() as conn:
        conn.execute("UPDATE tickets SET last_message_at = ? WHERE id = ?", (iso, ticket_id))
        conn.commit()


class TestMigrationV9(unittest.TestCase):
    def test_tables_exist(self):
        _fresh_db()
        from shop_bot.schema_migrations import SCHEMA_VERSION
        self.assertGreaterEqual(SCHEMA_VERSION, 9)
        with _db.db_connection() as conn:
            tcols = {r[1] for r in conn.execute("PRAGMA table_info(tickets)").fetchall()}
            self.assertTrue({"id", "user_id", "subject", "status", "tg_topic_id",
                             "unread_user", "first_staff_reply_at"} <= tcols)
            mcols = {r[1] for r in conn.execute("PRAGMA table_info(ticket_messages)").fetchall()}
            self.assertTrue({"ticket_id", "sender", "body", "channel"} <= mcols)


class TestCreateAndStatus(unittest.TestCase):
    def setUp(self):
        _fresh_db()
        self.st = importlib.import_module("shop_bot.support_tickets")

    def test_create_waiting_with_user_and_system_msgs(self):
        t = self.st.create_ticket(555, "connection", "не подключается")
        self.assertEqual(t["status"], "waiting")
        doc = self.st.get_ticket(555, t["id"])
        senders = [m["sender"] for m in doc["messages"]]
        self.assertEqual(senders, ["user", "system"])  # first msg + auto-ack
        self.assertIn("не подключается", doc["messages"][0]["body"])
        # system auto-ack must NOT flip status to answered
        self.assertEqual(doc["ticket"]["status"], "waiting")

    def test_staff_reply_answered_and_first_flag(self):
        t = self.st.create_ticket(555, "payment", "вопрос по оплате")
        tk, first = self.st.add_staff_message(t["id"], "сейчас гляну")
        self.assertEqual(tk["status"], "answered")
        self.assertTrue(first)
        self.assertEqual(tk["unread_user"], 1)
        tk2, first2 = self.st.add_staff_message(t["id"], "готово")
        self.assertFalse(first2)  # only the first reply duplicates email+TG
        self.assertEqual(tk2["unread_user"], 2)

    def test_user_reply_back_to_waiting(self):
        t = self.st.create_ticket(555, "other", "привет")
        self.st.add_staff_message(t["id"], "слушаю")
        tk = self.st.add_user_message(t["id"], "ещё вопрос")
        self.assertEqual(tk["status"], "waiting")

    def test_subject_normalized(self):
        t = self.st.create_ticket(555, "НЕИЗВЕСТНО", "x")
        self.assertEqual(t["subject"], "other")
        p = self.st.create_ticket(555, "partner_withdraw", "вывод")
        self.assertEqual(p["subject"], "partner_withdraw")

    def test_number_format(self):
        self.assertEqual(self.st.format_number(42), "#0042")
        self.assertEqual(self.st.format_number(1042), "#1042")


class TestUnreadAndReopen(unittest.TestCase):
    def setUp(self):
        _fresh_db()
        self.st = importlib.import_module("shop_bot.support_tickets")

    def test_unread_and_mark_read(self):
        t = self.st.create_ticket(700, "devices", "слетела настройка")
        self.st.add_staff_message(t["id"], "ответ 1")
        self.st.add_staff_message(t["id"], "ответ 2")
        self.assertEqual(self.st.unread_count(700), 2)
        self.st.get_ticket(700, t["id"], mark_read=True)  # opening clears unread
        self.assertEqual(self.st.unread_count(700), 0)

    def test_close_and_reopen(self):
        t = self.st.create_ticket(700, "other", "тест")
        self.st.close_ticket(t["id"])
        self.assertEqual(self.st.get_ticket(700, t["id"])["ticket"]["status"], "closed")
        self.st.add_user_message(t["id"], "снова не работает")  # reopen
        self.assertEqual(self.st.get_ticket(700, t["id"])["ticket"]["status"], "waiting")

    def test_get_ticket_owner_scoped(self):
        t = self.st.create_ticket(700, "other", "тест")
        self.assertIsNone(self.st.get_ticket(701, t["id"]))  # not the owner


class TestAutoClose(unittest.TestCase):
    def setUp(self):
        _fresh_db()
        self.st = importlib.import_module("shop_bot.support_tickets")

    def test_auto_close_after_3_days_silence(self):
        old = self.st.create_ticket(800, "other", "старый")
        fresh = self.st.create_ticket(800, "other", "свежий")
        _backdate(old["id"], 4)   # 4 days idle
        _backdate(fresh["id"], 1)  # 1 day idle
        closed = self.st.auto_close_stale()
        self.assertEqual(closed, [old["id"]])
        self.assertEqual(self.st.get_ticket(800, old["id"])["ticket"]["status"], "closed")
        self.assertEqual(self.st.get_ticket(800, fresh["id"])["ticket"]["status"], "waiting")
        self.assertEqual(self.st.auto_close_stale(), [])  # idempotent

    def test_topic_lookup(self):
        t = self.st.create_ticket(800, "other", "x")
        self.st.set_topic(t["id"], 9090)
        self.assertEqual(self.st.get_ticket_by_topic(9090)["id"], t["id"])
        self.assertIsNone(self.st.get_ticket_by_topic(123456))


if __name__ == "__main__":
    unittest.main()
