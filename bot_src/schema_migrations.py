"""Versioned SQLite schema migrations (P2-OPS-DB-MIGRATE-01)."""
from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 3


def _current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
        """
    )
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (0)")
        conn.commit()
        return 0
    return int(row[0])


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute("UPDATE schema_version SET version = ?", (version,))
    conn.commit()


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Hot-path indexes (P2-OPS-DB-INDEX-01)."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vpn_keys_user_id ON vpn_keys(user_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vpn_keys_expiry ON vpn_keys(expiry_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_referrals_referrer "
        "ON referrals(referrer_code)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_actions_user ON user_actions(user_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_web_trial_bind_token "
        "ON web_trial_claims(bind_token) WHERE bind_token IS NOT NULL"
    )


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Support rate limits + user/support columns formerly via silent ALTER."""
    for col, typedef in (
        ("balance", "REAL DEFAULT 0"),
        ("sub_refresh_notified_generation", "INTEGER DEFAULT 0"),
        ("support_topic_id", "INTEGER"),
        ("support_last_user_at", "INTEGER"),
        ("support_last_staff_at", "INTEGER"),
    ):
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
    for col, typedef in (
        ("claimed_at", "TEXT"),
        ("bind_token", "TEXT"),
        ("telegram_id", "INTEGER"),
        ("bound_at", "TEXT"),
    ):
        try:
            conn.execute(
                f"ALTER TABLE web_trial_claims ADD COLUMN {col} {typedef}"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS support_rate_limits (
            user_id INTEGER PRIMARY KEY,
            window_start REAL NOT NULL,
            hit_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_renewal_attempts_user "
        "ON renewal_attempts(user_id, status)"
    )


def _migrate_v3(conn: sqlite3.Connection) -> None:
    """Web trial customer_seq for indexed BVPN-ID lookup."""
    try:
        conn.execute(
            "ALTER TABLE web_trial_claims ADD COLUMN customer_seq INTEGER"
        )
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise
    conn.execute(
        """
        UPDATE web_trial_claims
        SET customer_seq = ABS(web_user_id) % 100000000
        WHERE customer_seq IS NULL
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_web_trial_customer_seq "
        "ON web_trial_claims(customer_seq)"
    )


_MIGRATORS = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
}


def run_schema_migrations(conn: sqlite3.Connection | None = None) -> int:
    """Apply pending migrations; returns new schema version."""
    own_conn = conn is None
    if own_conn:
        from shop_bot.data_manager.database import DB_FILE

        conn = sqlite3.connect(DB_FILE)
    try:
        current = _current_version(conn)
        while current < SCHEMA_VERSION:
            next_v = current + 1
            migrator = _MIGRATORS[next_v]
            logger.info("Applying schema migration v%s", next_v)
            with conn:
                migrator(conn)
                _set_version(conn, next_v)
            current = next_v
        return current
    finally:
        if own_conn and conn is not None:
            conn.close()
