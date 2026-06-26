"""In-app support tickets: model + status engine (SUPPORT-TICKET-BRIDGE-001, P4).

Pure DB layer over ``tickets`` / ``ticket_messages`` (migration v9). The TG bridge
(``support_ticket_bridge`` + the aiogram reply handler) calls into this; the Mini App API
will too. Status is **who-wrote-last**: user → ``waiting`` (Ждёт ответа), staff → ``answered``
(Ответ есть); a ``system`` auto-ack does NOT flip to answered. Close is manual (TG ``/close``)
or 3 days of silence; a new user message reopens a closed ticket.

This module does no Telegram I/O and is independent of the ``SUPPORT_TICKETS_LIVE`` gate (the
gate is enforced at the API/bridge layer) so the engine is fully unit-testable offline.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from shop_bot.config import SUPPORT_TICKET_AUTOCLOSE_DAYS, SUPPORT_TICKET_SUBJECTS
from shop_bot.data_manager.database import db_connection, get_setting

STATUS_WAITING = "waiting"
STATUS_ANSWERED = "answered"
STATUS_CLOSED = "closed"

_DEFAULT_AUTO_ACK = (
    "Получили обращение — ответим в ближайшее время. "
    "Ответ придёт сюда; на первое сообщение продублируем в Telegram."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def format_number(ticket_id: int) -> str:
    """Display number — raw id, zero-padded to 4 (#1042)."""
    return f"#{int(ticket_id):04d}"


def normalize_subject(subject: str | None) -> str:
    s = (subject or "").strip().lower()
    return s if s in SUPPORT_TICKET_SUBJECTS else "other"


def auto_ack_text() -> str:
    """Admin-editable auto-acknowledgement (bot_settings key support_auto_ack_text)."""
    return (get_setting("support_auto_ack_text") or "").strip() or _DEFAULT_AUTO_ACK


# -------------------- internal --------------------
def _row(conn, ticket_id: int) -> dict | None:
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(r) if r else None


def _insert_message(conn, ticket_id, sender, body, channel, tg_message_id=None) -> None:
    conn.execute(
        "INSERT INTO ticket_messages (ticket_id, sender, body, channel, tg_message_id, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ticket_id, sender, body, channel, tg_message_id, _iso()),
    )


# -------------------- create --------------------
def create_ticket(user_id: int, subject: str, text: str, email: str | None = None) -> dict:
    """New ticket (status waiting) + first user message + system auto-ack. Returns the ticket."""
    subj = normalize_subject(subject)
    now = _iso()
    with db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO tickets (user_id, subject, status, contact_email, last_message_at, "
            "last_sender, unread_user, created_at_utc) VALUES (?, ?, ?, ?, ?, 'user', 0, ?)",
            (int(user_id), subj, STATUS_WAITING, (email or "").strip() or None, now, now),
        )
        ticket_id = cur.lastrowid
        _insert_message(conn, ticket_id, "user", (text or "").strip(), "app")
        _insert_message(conn, ticket_id, "system", auto_ack_text(), "app")
        conn.execute(
            "UPDATE tickets SET last_message_at = ?, last_sender = 'system' WHERE id = ?",
            (_iso(), ticket_id),
        )
        conn.commit()
        return _row(conn, ticket_id)


def set_topic(ticket_id: int, tg_topic_id: int) -> None:
    with db_connection() as conn:
        conn.execute("UPDATE tickets SET tg_topic_id = ? WHERE id = ?", (int(tg_topic_id), int(ticket_id)))
        conn.commit()


# -------------------- messages + status transitions --------------------
def add_user_message(ticket_id: int, text: str, channel: str = "app") -> dict | None:
    """User reply → status waiting (reopen if closed)."""
    with db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        t = _row(conn, ticket_id)
        if not t:
            conn.rollback()
            return None
        _insert_message(conn, ticket_id, "user", (text or "").strip(), channel)
        conn.execute(
            "UPDATE tickets SET status = ?, last_sender = 'user', last_message_at = ?, "
            "closed_at_utc = NULL WHERE id = ?",
            (STATUS_WAITING, _iso(), ticket_id),
        )
        conn.commit()
        return _row(conn, ticket_id)


def add_staff_message(
    ticket_id: int, text: str, tg_message_id: int | None = None, channel: str = "tg"
) -> tuple[dict | None, bool]:
    """Staff reply → status answered, unread++. Returns (ticket, is_first_reply)."""
    with db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        t = _row(conn, ticket_id)
        if not t:
            conn.rollback()
            return None, False
        is_first = not t.get("first_staff_reply_at")
        _insert_message(conn, ticket_id, "staff", (text or "").strip(), channel, tg_message_id)
        conn.execute(
            "UPDATE tickets SET status = ?, last_sender = 'staff', last_message_at = ?, "
            "unread_user = unread_user + 1, "
            "first_staff_reply_at = COALESCE(first_staff_reply_at, ?) WHERE id = ?",
            (STATUS_ANSWERED, _iso(), _iso() if is_first else None, ticket_id),
        )
        conn.commit()
        return _row(conn, ticket_id), is_first


def add_system_message(ticket_id: int, text: str) -> None:
    """System note (does not change status)."""
    with db_connection() as conn:
        _insert_message(conn, ticket_id, "system", text, "app")
        conn.execute(
            "UPDATE tickets SET last_message_at = ?, last_sender = 'system' WHERE id = ?",
            (_iso(), ticket_id),
        )
        conn.commit()


def close_ticket(ticket_id: int) -> dict | None:
    with db_connection() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, closed_at_utc = ? WHERE id = ?",
            (STATUS_CLOSED, _iso(), int(ticket_id)),
        )
        conn.commit()
        return _row(conn, ticket_id)


def auto_close_stale(now: datetime | None = None, days: int | None = None) -> list[int]:
    """Close tickets with no activity for ``days`` (default 3). Returns closed ids. Idempotent."""
    cutoff = (now or _now()) - timedelta(days=days if days is not None else SUPPORT_TICKET_AUTOCLOSE_DAYS)
    closed: list[int] = []
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, last_message_at FROM tickets WHERE status != ?", (STATUS_CLOSED,)
        ).fetchall()
        for r in rows:
            last = _parse(r["last_message_at"])
            if last and last < cutoff:
                conn.execute(
                    "UPDATE tickets SET status = ?, closed_at_utc = ? WHERE id = ?",
                    (STATUS_CLOSED, _iso(), r["id"]),
                )
                closed.append(int(r["id"]))
        conn.commit()
    return closed


# -------------------- reads --------------------
def _latest_body(conn, ticket_id: int) -> str | None:
    conn.row_factory = sqlite3.Row
    r = conn.execute(
        "SELECT body FROM ticket_messages WHERE ticket_id = ? ORDER BY id DESC LIMIT 1",
        (ticket_id,),
    ).fetchone()
    return (r["body"] if r else None)


def list_tickets(user_id: int) -> list[dict]:
    out: list[dict] = []
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY last_message_at DESC, id DESC",
            (int(user_id),),
        ).fetchall()
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "number": format_number(r["id"]),
                    "subject": r["subject"],
                    "status": r["status"],
                    "last_message": _latest_body(conn, r["id"]),
                    "last_message_at_iso": r["last_message_at"],
                    "unread": int(r["unread_user"] or 0),
                }
            )
    return out


def get_ticket(user_id: int, ticket_id: int, mark_read: bool = True) -> dict | None:
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        t = conn.execute(
            "SELECT * FROM tickets WHERE id = ? AND user_id = ?", (int(ticket_id), int(user_id))
        ).fetchone()
        if not t:
            return None
        msgs = conn.execute(
            "SELECT sender, body, channel, created_at_utc FROM ticket_messages "
            "WHERE ticket_id = ? ORDER BY id ASC",
            (int(ticket_id),),
        ).fetchall()
        if mark_read:
            conn.execute("UPDATE tickets SET unread_user = 0 WHERE id = ?", (int(ticket_id),))
            conn.commit()
        return {
            "ticket": {
                "id": t["id"], "number": format_number(t["id"]), "subject": t["subject"],
                "status": STATUS_CLOSED if t["status"] == STATUS_CLOSED else t["status"],
                "created_at_iso": t["created_at_utc"], "email": t["contact_email"],
            },
            "messages": [
                {"sender": m["sender"], "body": m["body"], "at_iso": m["created_at_utc"]}
                for m in msgs
            ],
        }


def mark_read(ticket_id: int) -> None:
    with db_connection() as conn:
        conn.execute("UPDATE tickets SET unread_user = 0 WHERE id = ?", (int(ticket_id),))
        conn.commit()


def unread_count(user_id: int) -> int:
    with db_connection() as conn:
        r = conn.execute(
            "SELECT COALESCE(SUM(unread_user), 0) FROM tickets WHERE user_id = ?", (int(user_id),)
        ).fetchone()
        return int(r[0] or 0)


def get_ticket_by_topic(tg_topic_id: int) -> dict | None:
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        r = conn.execute("SELECT * FROM tickets WHERE tg_topic_id = ?", (int(tg_topic_id),)).fetchone()
        return dict(r) if r else None
