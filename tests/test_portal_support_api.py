"""Offline tests for the support tickets API (SUPPORT-TICKET-BRIDGE-001, P4).

No Telegram I/O (the bridge no-ops without token/group). Covers the SUPPORT_TICKETS_LIVE gate
(reads empty / writes support_disabled when off), and — when on — create, list, get (marks
read), message (status→waiting), unread, ownership scoping, and that /portal-home surfaces the
real unread count on the bell.
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

LIVE = {"SUPPORT_TICKETS_LIVE": "1"}


def _fresh_db():
    path = os.path.join(tempfile.mkdtemp(), "support_api.db")
    os.environ["SHOP_BOT_DB_PATH"] = path
    _db.DB_FILE = path
    _db.initialize_db()
    _db.register_user_if_not_exists(4242, "ticket_user")
    _db.set_terms_agreed(4242)


class TestGateOff(unittest.TestCase):
    def setUp(self):
        _fresh_db()

    def test_reads_empty_writes_disabled_when_off(self):
        from shop_bot import portal_support as ps

        with patch.dict(os.environ, {"SUPPORT_TICKETS_LIVE": "0"}):
            self.assertEqual(ps.list_tickets(telegram_id=4242), {"ok": True, "support_live": False, "tickets": []})
            self.assertEqual(ps.unread(telegram_id=4242), {"ok": True, "count": 0})
            self.assertEqual(ps.create_ticket(telegram_id=4242, subject="connection", text="x")["error"], "support_disabled")
            self.assertEqual(ps.ticket_message(1, "x", telegram_id=4242)["error"], "support_disabled")


class TestGateOn(unittest.TestCase):
    def setUp(self):
        _fresh_db()
        self._p = patch.dict(os.environ, LIVE)
        self._p.start()
        self.addCleanup(self._p.stop)

    def test_create_list_get_message_flow(self):
        from shop_bot import portal_support as ps

        created = ps.create_ticket(telegram_id=4242, subject="payment", text="не прошла оплата", email="a@b.io")
        self.assertTrue(created["ok"])
        self.assertEqual(created["status"], "waiting")
        self.assertTrue(created["number"].startswith("#"))
        tid = created["ticket_id"]

        lst = ps.list_tickets(telegram_id=4242)
        self.assertTrue(lst["support_live"])
        self.assertEqual(len(lst["tickets"]), 1)
        self.assertEqual(lst["tickets"][0]["status"], "waiting")

        got = ps.ticket_get(tid, telegram_id=4242)
        self.assertTrue(got["ok"])
        self.assertEqual([m["sender"] for m in got["messages"]], ["user", "system"])

        msg = ps.ticket_message(tid, "ещё деталь", telegram_id=4242)
        self.assertEqual(msg["status"], "waiting")

    def test_empty_text_rejected(self):
        from shop_bot import portal_support as ps

        self.assertEqual(ps.create_ticket(telegram_id=4242, subject="other", text="   ")["error"], "empty_text")

    def test_ownership_scoped(self):
        from shop_bot import portal_support as ps

        _db.register_user_if_not_exists(9999, "other_user")
        tid = ps.create_ticket(telegram_id=4242, subject="other", text="мой тикет")["ticket_id"]
        self.assertEqual(ps.ticket_get(tid, telegram_id=9999)["error"], "not_found")
        self.assertEqual(ps.ticket_message(tid, "чужое", telegram_id=9999)["error"], "not_found")

    def test_unread_and_home_bell(self):
        from shop_bot import portal_support as ps
        from shop_bot import support_tickets
        from shop_bot.portal_home import home_snapshot

        tid = ps.create_ticket(telegram_id=4242, subject="other", text="вопрос")["ticket_id"]
        support_tickets.add_staff_message(tid, "ответ стаффа")  # creates 1 unread
        self.assertEqual(ps.unread(telegram_id=4242)["count"], 1)
        # home bell reflects it
        self.assertEqual(home_snapshot(telegram_id=4242)["unread"], 1)
        # opening the ticket clears unread
        ps.ticket_get(tid, telegram_id=4242)
        self.assertEqual(ps.unread(telegram_id=4242)["count"], 0)
        self.assertEqual(home_snapshot(telegram_id=4242)["unread"], 0)


if __name__ == "__main__":
    unittest.main()
