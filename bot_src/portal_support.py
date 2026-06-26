"""In-app Mini App support tickets API (SUPPORT-TICKET-BRIDGE-001, P4).

Thin request layer over ``support_tickets`` (model/status engine) + ``support_ticket_bridge``
(app→TG). Gated by ``SUPPORT_TICKETS_LIVE`` (default OFF): while off, reads return empty/zero
honestly and writes return ``support_disabled`` — nothing is created and no TG topic is made.

Identity is Telegram-keyed (tickets belong to a telegram user). NOTE for prod hardening: the
server should derive the user from **validated initData**, not a client-supplied telegram_id —
same caveat as the other /portal-* endpoints; tighten before enabling live.
"""
from __future__ import annotations

import logging

from shop_bot.config import SUPPORT_TICKET_SUBJECTS, support_tickets_live
from shop_bot.data_manager.database import get_user
from shop_bot.web_trial_db import (
    get_claim_by_customer_id,
    get_web_trial_claim,
    normalize_contact_email,
)

logger = logging.getLogger(__name__)


def _resolve(telegram_id, customer_id, email) -> tuple[int | None, str | None]:
    """Resolve to the telegram user_id that owns tickets. (user_id, error)."""
    if telegram_id and int(telegram_id) > 0:
        if not get_user(int(telegram_id)):
            return None, "not_found"
        return int(telegram_id), None
    claim = None
    em = normalize_contact_email(email)
    if em:
        claim = get_web_trial_claim(em)
    if not claim and customer_id:
        claim = get_claim_by_customer_id(customer_id)
    if not claim:
        return None, "not_found"
    tid = claim.get("telegram_id")
    if not tid:
        return None, "needs_telegram_bind"  # tickets are telegram-keyed
    if not get_user(int(tid)):
        return None, "not_found"
    return int(tid), None


def subjects() -> list[str]:
    return list(SUPPORT_TICKET_SUBJECTS)


# -------------------- reads (safe to serve; empty when gated off) --------------------
def list_tickets(*, telegram_id=None, customer_id="", email="") -> dict:
    if not support_tickets_live():
        return {"ok": True, "support_live": False, "tickets": []}
    uid, err = _resolve(telegram_id, customer_id, email)
    if err == "needs_telegram_bind":
        return {"ok": True, "support_live": True, "needs_telegram_bind": True, "tickets": []}
    if err:
        return {"ok": True, "support_live": True, "tickets": []}
    from shop_bot import support_tickets

    return {"ok": True, "support_live": True, "tickets": support_tickets.list_tickets(uid)}


def unread(*, telegram_id=None, customer_id="", email="") -> dict:
    if not support_tickets_live():
        return {"ok": True, "count": 0}
    uid, err = _resolve(telegram_id, customer_id, email)
    if err or uid is None:
        return {"ok": True, "count": 0}
    from shop_bot import support_tickets

    return {"ok": True, "count": support_tickets.unread_count(uid)}


def ticket_get(ticket_id, *, telegram_id=None, customer_id="", email="") -> dict:
    if not support_tickets_live():
        return {"ok": False, "error": "support_disabled"}
    uid, err = _resolve(telegram_id, customer_id, email)
    if err:
        return {"ok": False, "error": err}
    from shop_bot import support_tickets

    doc = support_tickets.get_ticket(uid, int(ticket_id), mark_read=True)
    if not doc:
        return {"ok": False, "error": "not_found"}
    doc["ok"] = True
    return doc


# -------------------- writes (gated) --------------------
def create_ticket(*, telegram_id=None, customer_id="", email="", subject="other", text="") -> dict:
    if not support_tickets_live():
        return {"ok": False, "error": "support_disabled"}
    uid, err = _resolve(telegram_id, customer_id, email)
    if err:
        return {"ok": False, "error": err}
    if not (text or "").strip():
        return {"ok": False, "error": "empty_text"}
    from shop_bot import support_tickets

    ticket = support_tickets.create_ticket(uid, subject, text, email)
    try:
        from shop_bot.support_ticket_bridge import bridge_new_ticket

        bridge_new_ticket(ticket, text)
    except Exception as e:  # bridge is best-effort; ticket already persisted
        logger.error("ticket bridge (create) failed id=%s: %s", ticket.get("id"), e)
    return {
        "ok": True,
        "ticket_id": ticket["id"],
        "number": support_tickets.format_number(ticket["id"]),
        "status": ticket["status"],
    }


def ticket_message(ticket_id, text, *, telegram_id=None, customer_id="", email="") -> dict:
    if not support_tickets_live():
        return {"ok": False, "error": "support_disabled"}
    uid, err = _resolve(telegram_id, customer_id, email)
    if err:
        return {"ok": False, "error": err}
    if not (text or "").strip():
        return {"ok": False, "error": "empty_text"}
    from shop_bot import support_tickets

    owned = support_tickets.get_ticket(uid, int(ticket_id), mark_read=False)
    if not owned:
        return {"ok": False, "error": "not_found"}
    ticket = support_tickets.add_user_message(int(ticket_id), text)
    try:
        from shop_bot.support_ticket_bridge import bridge_user_message

        bridge_user_message(ticket, text)
    except Exception as e:
        logger.error("ticket bridge (message) failed id=%s: %s", ticket_id, e)
    return {"ok": True, "status": ticket["status"]}
