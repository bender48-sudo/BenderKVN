"""Versioned SQLite schema migrations (P2-OPS-DB-MIGRATE-01)."""
from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 10


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def _current_version(conn: sqlite3.Connection) -> int:
    if _table_has_column(conn, "schema_version", "id"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            )
            """
        )
        row = conn.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_version (id, version) VALUES (1, 0)"
            )
            return 0
        return int(row[0])

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
        return 0
    return int(row[0])


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    if _table_has_column(conn, "schema_version", "id"):
        conn.execute(
            "UPDATE schema_version SET version = ? WHERE id = 1", (version,)
        )
        if conn.total_changes == 0:
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, ?)",
                (version,),
            )
    else:
        conn.execute("UPDATE schema_version SET version = ?", (version,))


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
    """Support rate limits + user/support columns; renewal_attempts guard (P2-OPS-SCHEMA-02)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS renewal_attempts (
            attempt_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            key_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            cost_rub REAL NOT NULL,
            plan TEXT,
            balance_deducted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """
    )
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


def _migrate_v4(conn: sqlite3.Connection) -> None:
    """schema_version single-row PK (P2-OPS-SCHEMA-02)."""
    if _table_has_column(conn, "schema_version", "id"):
        return
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    ver = int(row[0]) if row else 0
    conn.execute("DROP TABLE schema_version")
    conn.execute(
        """
        CREATE TABLE schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO schema_version (id, version) VALUES (1, ?)", (ver,)
    )


def _migrate_v5(conn: sqlite3.Connection) -> None:
    """Bind token TTL column (P2-RED-BOT-SEC-02)."""
    try:
        conn.execute(
            "ALTER TABLE web_trial_claims ADD COLUMN bind_token_expires_at TEXT"
        )
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise


def _migrate_v6(conn: sqlite3.Connection) -> None:
    """YooKassa card autopay columns (P2-COM-YK-AUTOPAY-01)."""
    for col, typedef in (
        ("yookassa_payment_method_id", "TEXT"),
        ("yookassa_autopay_enabled", "INTEGER DEFAULT 0"),
        ("yookassa_autopay_next_at", "TEXT"),
        ("yookassa_autopay_last_error", "TEXT"),
    ):
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise


def _migrate_v7(conn: sqlite3.Connection) -> None:
    """User contact email for backup outreach (CLIENT-JOURNEY §5.4)."""
    try:
        conn.execute("ALTER TABLE users ADD COLUMN contact_email TEXT")
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_contact_email "
        "ON users(contact_email) WHERE contact_email IS NOT NULL"
    )


def _migrate_v8(conn: sqlite3.Connection) -> None:
    """Append-only balance ledger (REF-LEDGER-001).

    Journal alongside users.balance (which stays authoritative). Additive only — CREATE,
    no ALTER, no data move. Amounts are signed kopeks. Idempotency: one row per (user, ref)
    where ref is set; ref=NULL rows are manual adjustments and not deduplicated.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS balance_ledger (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id               INTEGER NOT NULL,
            kind                  TEXT    NOT NULL,
            amount_kopeks         INTEGER NOT NULL,
            balance_after_kopeks  INTEGER,
            ref                   TEXT,
            meta                  TEXT,
            created_at_utc        TEXT    NOT NULL
                                  DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_user_ref "
        "ON balance_ledger(user_id, ref) WHERE ref IS NOT NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ledger_user_id "
        "ON balance_ledger(user_id, id DESC)"
    )


def _migrate_v9(conn: sqlite3.Connection) -> None:
    """In-app support tickets + bridge (SUPPORT-TICKET-BRIDGE-001, P4).

    Additive only — CREATE, no ALTER, no data move. One forum topic per ticket bridges to TG;
    status is who-wrote-last (waiting/answered) + manual/3-day close. Reversible (drop tables).
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id              INTEGER NOT NULL,
            subject              TEXT    NOT NULL,
            status               TEXT    NOT NULL DEFAULT 'waiting',
            tg_topic_id          INTEGER,
            contact_email        TEXT,
            last_message_at      TEXT,
            last_sender          TEXT,
            first_staff_reply_at TEXT,
            unread_user          INTEGER NOT NULL DEFAULT 0,
            created_at_utc       TEXT    NOT NULL,
            closed_at_utc        TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id      INTEGER NOT NULL,
            sender         TEXT    NOT NULL,
            body           TEXT,
            channel        TEXT,
            tg_message_id  INTEGER,
            created_at_utc TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_user "
        "ON tickets(user_id, last_message_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_topic "
        "ON tickets(tg_topic_id) WHERE tg_topic_id IS NOT NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_openset "
        "ON tickets(status, last_message_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ticket_msgs ON ticket_messages(ticket_id, id)"
    )


def _migrate_v10(conn: sqlite3.Connection) -> None:
    """Fortune wheel spins (GAME-FORTUNE-001, P5).

    Additive only. One row per server-authoritative spin; rub rewards are credited via
    balance_ledger (kind='fortune', ref='fortune:<spin_id>'). Earned spins derive from paid
    active days; this table is the spend/extra-spin record. Reversible (drop table).
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fortune_spins (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            sector_key     TEXT    NOT NULL,
            kind           TEXT    NOT NULL,        -- nothing | extra_spin | rub
            amount_kopeks  INTEGER NOT NULL DEFAULT 0,
            ledger_ref     TEXT,
            created_at_utc TEXT    NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fortune_user ON fortune_spins(user_id, id DESC)")


_MIGRATORS = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
    4: _migrate_v4,
    5: _migrate_v5,
    6: _migrate_v6,
    7: _migrate_v7,
    8: _migrate_v8,
    9: _migrate_v9,
    10: _migrate_v10,
}


def run_schema_migrations(conn: sqlite3.Connection | None = None) -> int:
    """Apply pending migrations; returns new schema version."""
    own_conn = conn is None
    if own_conn:
        from shop_bot.data_manager.database import db_connection

        with db_connection() as conn:
            return run_schema_migrations(conn)
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
        if own_conn:
            pass
