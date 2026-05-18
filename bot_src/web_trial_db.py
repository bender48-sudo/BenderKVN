"""Web-only trial DB helpers (patch AMS without replacing database.py)."""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
import sqlite3
from datetime import datetime, timezone

from shop_bot.data_manager.database import DB_FILE

logger = logging.getLogger(__name__)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCHEMA_READY = False
_BIND_COLS_READY = False


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_FILE)


def ensure_web_trial_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    try:
        with _conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_trial_claims (
                    contact_email TEXT PRIMARY KEY,
                    web_user_id INTEGER NOT NULL,
                    panel_email TEXT,
                    contact_phone TEXT,
                    claimed_at TEXT NOT NULL
                )
                """
            )
        _ensure_bind_columns(conn)
        _SCHEMA_READY = True
    except Exception as exc:
        logger.error("ensure_web_trial_schema failed: %s", exc)
        raise


def _ensure_bind_columns(conn: sqlite3.Connection) -> None:
    global _BIND_COLS_READY
    if _BIND_COLS_READY:
        return
    for ddl in (
        "ALTER TABLE web_trial_claims ADD COLUMN bind_token TEXT",
        "ALTER TABLE web_trial_claims ADD COLUMN telegram_id INTEGER",
        "ALTER TABLE web_trial_claims ADD COLUMN bound_at TEXT",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_web_trial_bind_token "
            "ON web_trial_claims(bind_token) WHERE bind_token IS NOT NULL"
        )
    except sqlite3.OperationalError:
        pass
    _BIND_COLS_READY = True


def is_web_surrogate_id(user_id: int) -> bool:
    return int(user_id) < 0


def normalize_contact_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_contact_email(email: str) -> bool:
    em = normalize_contact_email(email)
    return bool(em) and len(em) <= 254 and bool(_EMAIL_RE.match(em))


def web_user_id_from_email(contact_email: str) -> int:
    digest = hashlib.sha256(normalize_contact_email(contact_email).encode()).digest()
    n = int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF
    return -int(n or 1)


def format_customer_id(web_user_id: int) -> str:
    """Public ID for support / self-service (no email in UI)."""
    return f"BVPN-{abs(int(web_user_id)) % 100_000_000:08d}"


def _claim_row_to_dict(row) -> dict:
    return {
        "contact_email": row[0],
        "web_user_id": int(row[1]),
        "panel_email": row[2] or "",
        "contact_phone": row[3] or "",
        "claimed_at": row[4] or "",
        "bind_token": row[5] if len(row) > 5 else "",
        "telegram_id": int(row[6]) if len(row) > 6 and row[6] is not None else None,
        "bound_at": row[7] if len(row) > 7 else "",
    }


_CLAIM_SELECT = """SELECT contact_email, web_user_id, panel_email, contact_phone, claimed_at,
                          bind_token, telegram_id, bound_at
                   FROM web_trial_claims"""


def get_web_trial_claim(contact_email: str) -> dict | None:
    ensure_web_trial_schema()
    em = normalize_contact_email(contact_email)
    try:
        with _conn() as conn:
            row = conn.execute(f"{_CLAIM_SELECT} WHERE contact_email = ?", (em,)).fetchone()
        if not row:
            return None
        return _claim_row_to_dict(row)
    except Exception as exc:
        logger.error("get_web_trial_claim failed: %s", exc)
        return None


def get_web_trial_claim_by_web_user_id(web_user_id: int) -> dict | None:
    ensure_web_trial_schema()
    try:
        with _conn() as conn:
            row = conn.execute(
                f"{_CLAIM_SELECT} WHERE web_user_id = ?",
                (int(web_user_id),),
            ).fetchone()
        if not row:
            return None
        return _claim_row_to_dict(row)
    except Exception as exc:
        logger.error("get_web_trial_claim_by_web_user_id failed: %s", exc)
        return None


def get_claim_by_bind_token(bind_token: str) -> dict | None:
    token = (bind_token or "").strip().lower()
    if not token or len(token) < 16:
        return None
    ensure_web_trial_schema()
    try:
        with _conn() as conn:
            row = conn.execute(f"{_CLAIM_SELECT} WHERE bind_token = ?", (token,)).fetchone()
        if not row:
            return None
        return _claim_row_to_dict(row)
    except Exception as exc:
        logger.error("get_claim_by_bind_token failed: %s", exc)
        return None


def ensure_bind_token(web_user_id: int) -> str:
    """Create or return deep-link bind token for a web trial user."""
    ensure_web_trial_schema()
    claim = get_web_trial_claim_by_web_user_id(web_user_id)
    if not claim:
        return ""
    if claim.get("bind_token"):
        return str(claim["bind_token"])
    token = secrets.token_hex(16)
    try:
        with _conn() as conn:
            conn.execute(
                "UPDATE web_trial_claims SET bind_token = ? WHERE web_user_id = ?",
                (token, int(web_user_id)),
            )
        return token
    except Exception as exc:
        logger.error("ensure_bind_token failed: %s", exc)
        return ""


def mark_web_claim_bound(web_user_id: int, telegram_id: int) -> None:
    ensure_web_trial_schema()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _conn() as conn:
            conn.execute(
                """UPDATE web_trial_claims
                   SET telegram_id = ?, bound_at = ?
                   WHERE web_user_id = ?""",
                (int(telegram_id), now, int(web_user_id)),
            )
    except Exception as exc:
        logger.error("mark_web_claim_bound failed: %s", exc)


def web_trial_contact_claimed(contact_email: str) -> bool:
    ensure_web_trial_schema()
    em = normalize_contact_email(contact_email)
    try:
        with _conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM web_trial_claims WHERE contact_email = ?",
                (em,),
            ).fetchone()
        return row is not None
    except Exception as exc:
        logger.error("web_trial_contact_claimed failed: %s", exc)
        return True


def record_web_trial_claim(
    contact_email: str,
    web_user_id: int,
    panel_email: str,
    contact_phone: str | None = None,
) -> None:
    ensure_web_trial_schema()
    em = normalize_contact_email(contact_email)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO web_trial_claims
                   (contact_email, web_user_id, panel_email, contact_phone, claimed_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (em, web_user_id, panel_email, contact_phone or "", now),
            )
        ensure_bind_token(web_user_id)
    except Exception as exc:
        logger.error("record_web_trial_claim failed: %s", exc)
