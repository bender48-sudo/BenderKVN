"""Support ticket ⇄ Telegram bridge (SUPPORT-TICKET-BRIDGE-001, P4).

Sync side (app → TG), called from the Mini App API: creates one **forum topic per ticket**
(``#тикет_NNNN``) and posts messages, via direct Telegram Bot API HTTP (stdlib urllib — no new
dependency, works inside the sync Flask webhook). The TG → app side (staff replies) lives in the
aiogram handler ``support_handler.admin_reply_in_topic``.

Everything is gated by ``SUPPORT_TICKETS_LIVE`` and the presence of ``TELEGRAM_BOT_TOKEN`` /
``SUPPORT_GROUP_ID`` — a no-op (returns None/False) otherwise, so nothing happens until an owner
flips it on. The first-staff-reply **email** duplicate is a stub hook (Q2: SMTP not wired yet);
TG-DM + in-app land now, email later — without blocking.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

from shop_bot.config import support_tickets_live
from shop_bot.support_tickets import format_number, set_topic

logger = logging.getLogger(__name__)

SUBJECT_RU = {
    "connection": "Подключение",
    "payment": "Оплата",
    "devices": "Устройства",
    "other": "Другое",
    "partner_apply": "Партнёрство",
    "partner_withdraw": "Вывод средств (партнёр)",
}


def _token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()


def _group_id() -> int:
    try:
        return int(os.getenv("SUPPORT_GROUP_ID", "0"))
    except ValueError:
        return 0


def _ready() -> bool:
    return support_tickets_live() and bool(_token()) and bool(_group_id())


def _api(method: str, payload: dict):
    """POST to the Telegram Bot API; returns ``result`` or None on failure."""
    token = _token()
    if not token:
        return None
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("ok"):
            return body.get("result")
        logger.error("tg api %s failed: %s", method, body.get("description"))
        return None
    except Exception as e:  # network / timeout / token
        logger.error("tg api %s error: %s", method, e)
        return None


def create_ticket_topic(ticket: dict):
    """Create the forum topic for a ticket; returns topic id (message_thread_id) or None."""
    subj = SUBJECT_RU.get(ticket.get("subject"), "Обращение")
    name = f"{format_number(ticket['id'])} · {subj} · {ticket.get('user_id')}"
    res = _api("createForumTopic", {"chat_id": _group_id(), "name": name[:128]})
    return res.get("message_thread_id") if res else None


def post_to_topic(topic_id: int, text: str):
    """Send a message into a ticket's forum topic; returns the message id or None."""
    res = _api(
        "sendMessage",
        {"chat_id": _group_id(), "message_thread_id": int(topic_id), "text": text},
    )
    return res.get("message_id") if res else None


def send_dm(user_id: int, text: str) -> bool:
    """DM the user (used for the first-staff-reply duplicate so they notice without the app)."""
    return _api("sendMessage", {"chat_id": int(user_id), "text": text}) is not None


def deliver_email(email: str | None, subject: str, body: str) -> bool:
    """Email duplicate — STUB (Q2: SMTP not wired). Logs intent and returns False.

    Wire a real transport here later; callers already treat email as best-effort, so the
    first-reply duplicate degrades gracefully to TG-DM + in-app today.
    """
    if not email:
        return False
    logger.info("support email hook (not wired): to=%s subject=%s", email, subject)
    return False


def bridge_new_ticket(ticket: dict, first_text: str):
    """Create the topic and post the header + first user message. Returns topic id or None.

    No-op (returns None) unless SUPPORT_TICKETS_LIVE + token + group are all present.
    """
    if not _ready():
        return None
    topic_id = create_ticket_topic(ticket)
    if not topic_id:
        return None
    set_topic(ticket["id"], topic_id)
    subj = SUBJECT_RU.get(ticket.get("subject"), "Обращение")
    header = (
        f"{format_number(ticket['id'])} · {subj}\n"
        f"user_id: {ticket.get('user_id')}"
        + (f"\nemail: {ticket['contact_email']}" if ticket.get("contact_email") else "")
    )
    post_to_topic(topic_id, header)
    if (first_text or "").strip():
        post_to_topic(topic_id, (first_text or "").strip())
    return topic_id


def bridge_user_message(ticket: dict, text: str):
    """Relay a follow-up user message into the ticket topic. No-op unless ready + topic exists."""
    if not _ready() or not ticket.get("tg_topic_id"):
        return None
    return post_to_topic(ticket["tg_topic_id"], (text or "").strip())
