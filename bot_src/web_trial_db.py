"""Web-only trial DB helpers (patch AMS without replacing database.py)."""
from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from datetime import datetime, timezone

from shop_bot.data_manager.database import DB_FILE

logger = logging.getLogger(__name__)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCHEMA_READY = False


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
        _SCHEMA_READY = True
    except Exception as exc:
        logger.error("ensure_web_trial_schema failed: %s", exc)
        raise


def normalize_contact_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_contact_email(email: str) -> bool:
    em = normalize_contact_email(email)
    return bool(em) and len(em) <= 254 and bool(_EMAIL_RE.match(em))


def web_user_id_from_email(contact_email: str) -> int:
    digest = hashlib.sha256(normalize_contact_email(contact_email).encode()).digest()
    n = int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF
    return -int(n or 1)


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
    except Exception as exc:
        logger.error("record_web_trial_claim failed: %s", exc)
