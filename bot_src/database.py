import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path

_CONTACT_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
from shop_bot.config import ABOUT_TEXT, TERMS_URL, PRIVACY_URL, SUPPORT_USER, SUPPORT_TEXT, CHANNEL_URL

logger = logging.getLogger(__name__)

# Для продакшена база должна быть в директории data
PROJECT_ROOT = Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)  # Создаем директорию если не существует
_db_override = (os.getenv("SHOP_BOT_DB_PATH") or os.getenv("BVPN_QA_DB_PATH") or "").strip()
DB_FILE = Path(_db_override).expanduser() if _db_override else DATA_DIR / "shop_bot.db"


@contextmanager
def db_connection(timeout: float = 5.0):
    """SQLite connection with busy_timeout (P2-RED-BOT-ENV-01)."""
    conn = sqlite3.connect(DB_FILE, timeout=timeout)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        yield conn
    finally:
        conn.close()


get_db_connection = db_connection


def initialize_db():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    total_spent REAL DEFAULT 0,
                    total_months INTEGER DEFAULT 0,
                    trial_used BOOLEAN DEFAULT 0,
                    agreed_to_terms BOOLEAN DEFAULT 0,
                    ref_code TEXT UNIQUE,
                    referred_by TEXT,
                    auto_renew BOOLEAN DEFAULT 0,
                    last_expiry_notified_days INTEGER DEFAULT 999,
                    sub_refresh_notified_generation INTEGER DEFAULT 0,
                    contact_email TEXT
                );
                CREATE TABLE IF NOT EXISTS vpn_keys (
                    key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    vless_uuid TEXT NOT NULL,
                    key_email TEXT NOT NULL UNIQUE,
                    expiry_date TIMESTAMP,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_notified_percent INTEGER DEFAULT 0,
                    subscription_plan TEXT,
                    traffic_extra_bytes INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS promo_codes (
                    code TEXT PRIMARY KEY,
                    discount_percent INTEGER DEFAULT 0,
                    free_days INTEGER DEFAULT 0,
                    uses_limit INTEGER DEFAULT 0,
                    uses_count INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_code TEXT,
                    referred_user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS web_trial_claims (
                    contact_email TEXT PRIMARY KEY,
                    web_user_id INTEGER NOT NULL UNIQUE,
                    panel_email TEXT,
                    contact_phone TEXT,
                    claimed_at TEXT,
                    bind_token TEXT,
                    telegram_id INTEGER,
                    bound_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS webhook_deliveries (
                    idempotency_key TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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
                );
            ''')
            default_settings = {
                "about_text": ABOUT_TEXT,
                "terms_url": TERMS_URL,
                "privacy_url": PRIVACY_URL,
                "support_user": SUPPORT_USER,
                "support_text": SUPPORT_TEXT,
                "channel_url": CHANNEL_URL,
            }
            if not cursor.execute("SELECT COUNT(*) FROM bot_settings").fetchone()[0]:
                for key, value in default_settings.items():
                    cursor.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
            from shop_bot.schema_migrations import run_schema_migrations

            run_schema_migrations(conn)
            conn.commit()
            logging.info("Database with 'created_date' column initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error on initialization: {e}")

def get_setting(key: str) -> str | None:
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get setting '{key}': {e}")
        return None

def update_setting(key: str, value: str):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE bot_settings SET value = ? WHERE key = ?", (value, key))
            conn.commit()
            logging.info(f"Setting '{key}' updated.")
    except sqlite3.Error as e:
        logging.error(f"Failed to update setting '{key}': {e}")

def upsert_setting(key: str, value: str):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to upsert setting '{key}': {e}")

def get_sub_config_generation() -> int:
    raw = get_setting("sub_config_generation")
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0

def set_sub_config_generation(generation: int, reason: str = "") -> None:
    upsert_setting("sub_config_generation", str(generation))
    if reason:
        upsert_setting("sub_config_refresh_reason", reason)

def get_sub_refresh_notified_generation(user_id: int) -> int:
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sub_refresh_notified_generation FROM users WHERE telegram_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except sqlite3.Error as e:
        logging.error(f"Failed to get sub_refresh_notified_generation for {user_id}: {e}")
        return 0

def update_sub_refresh_notified_generation(user_id: int, generation: int) -> None:
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET sub_refresh_notified_generation = ? WHERE telegram_id = ?",
                (generation, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(
            f"Failed to update sub_refresh_notified_generation for {user_id}: {e}"
        )

def mark_all_sub_refresh_notified(generation: int | None = None) -> tuple[int, int]:
    """Set sub_refresh_notified_generation for all users with VPN keys. Returns (updated, gen)."""
    gen = int(generation if generation is not None else get_sub_config_generation())
    if gen <= 0:
        return 0, gen
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET sub_refresh_notified_generation = ?
                WHERE telegram_id IN (SELECT DISTINCT user_id FROM vpn_keys)
                  AND COALESCE(sub_refresh_notified_generation, 0) < ?
                """,
                (gen, gen),
            )
            conn.commit()
            return int(cursor.rowcount), gen
    except sqlite3.Error as e:
        logging.error(f"mark_all_sub_refresh_notified failed: {e}")
        return 0, gen


def list_users_pending_sub_refresh(current_generation: int, limit: int = 15) -> list[int]:
    """Distinct vpn_keys.user_id with telegram account behind current_generation."""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT vk.user_id
                FROM vpn_keys vk
                INNER JOIN users u ON u.telegram_id = vk.user_id
                WHERE COALESCE(u.sub_refresh_notified_generation, 0) < ?
                ORDER BY vk.user_id
                LIMIT ?
                """,
                (current_generation, limit),
            )
            return [int(row[0]) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to list pending sub refresh users: {e}")
        return []

def normalize_contact_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_contact_email(email: str) -> bool:
    return bool(_CONTACT_EMAIL_RE.match(normalize_contact_email(email)))


def web_user_id_from_email(contact_email: str) -> int:
    """Stable negative telegram_id surrogate for browser-only users."""
    digest = hashlib.sha256(normalize_contact_email(contact_email).encode()).hexdigest()
    n = int(digest[:12], 16) % (2**30)
    return -(n + 100_000)


def web_trial_contact_claimed(contact_email: str) -> bool:
    try:
        em = normalize_contact_email(contact_email)
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM web_trial_claims WHERE contact_email = ?",
                (em,),
            )
            return cur.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"web_trial_contact_claimed failed: {e}")
        return True


def record_web_trial_claim(
    contact_email: str,
    web_user_id: int,
    panel_email: str,
    contact_phone: str | None = None,
) -> None:
    try:
        em = normalize_contact_email(contact_email)
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO web_trial_claims
                   (contact_email, web_user_id, panel_email, contact_phone)
                   VALUES (?, ?, ?, ?)""",
                (em, web_user_id, panel_email, (contact_phone or "").strip() or None),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"record_web_trial_claim failed: {e}")


def register_user_if_not_exists(telegram_id: int, username: str):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (telegram_id, username) VALUES (?, ?)", (telegram_id, username))
            else:
                cursor.execute("UPDATE users SET username = ? WHERE telegram_id = ?", (username, telegram_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to register user {telegram_id}: {e}")

def get_user(telegram_id: int):
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            user_data = cursor.fetchone()
            return dict(user_data) if user_data else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get user {telegram_id}: {e}")
        return None


def lookup_telegram_ids_by_hint(hint: str, *, limit: int = 5) -> list[dict]:
    """Find bot users by @username or numeric Telegram ID (browser setup lookup)."""
    raw = (hint or "").strip()
    if not raw:
        return []
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if raw.lstrip("@").isdigit():
                tid = int(raw.lstrip("@"))
                cursor.execute(
                    "SELECT telegram_id, username FROM users WHERE telegram_id = ?",
                    (tid,),
                )
            else:
                name = raw.lstrip("@").lower()
                cursor.execute(
                    """
                    SELECT telegram_id, username FROM users
                    WHERE LOWER(TRIM(username)) = ?
                       OR LOWER(TRIM(username)) LIKE ?
                    ORDER BY CASE WHEN LOWER(TRIM(username)) = ? THEN 0 ELSE 1 END
                    LIMIT ?
                    """,
                    (name, f"%{name}%", name, limit),
                )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"lookup_telegram_ids_by_hint failed: {e}")
        return []


def set_user_contact_email(telegram_id: int, email: str) -> bool:
    """Backup contact email (CLIENT-JOURNEY §5.4) — outreach when Telegram unavailable."""
    em = normalize_contact_email(email)
    if not is_valid_contact_email(em):
        return False
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET contact_email = ? WHERE telegram_id = ?",
                (em, telegram_id),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO users (telegram_id, contact_email) VALUES (?, ?)",
                    (telegram_id, em),
                )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"set_user_contact_email failed for {telegram_id}: {e}")
        return False


def set_terms_agreed(telegram_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET agreed_to_terms = 1 WHERE telegram_id = ?",
                (telegram_id,),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO users (telegram_id, username, agreed_to_terms) VALUES (?, ?, 1)",
                    (telegram_id, ""),
                )
            conn.commit()
            logging.info(f"User {telegram_id} has agreed to terms.")
    except sqlite3.Error as e:
        logging.error(f"Failed to set terms agreed for user {telegram_id}: {e}")

def update_user_stats(telegram_id: int, amount_spent: float, months_purchased: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET total_spent = total_spent + ?, total_months = total_months + ? WHERE telegram_id = ?", (amount_spent, months_purchased, telegram_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update user stats for {telegram_id}: {e}")

def set_trial_used(telegram_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET trial_used = 1 WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            logging.info(f"Trial period marked as used for user {telegram_id}.")
    except sqlite3.Error as e:
        logging.error(f"Failed to set trial used for user {telegram_id}: {e}")

def reset_trial_used(telegram_id: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET trial_used = 0 WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            logging.info(f"Trial period reset for user {telegram_id}.")
    except sqlite3.Error as e:
        logging.error(f"Failed to reset trial for user {telegram_id}: {e}")

def add_new_key(user_id: int, vless_uuid: str, key_email: str, expiry_timestamp_ms: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            # Конвертируем UTC timestamp в локальное время корректно
            from datetime import timezone
            expiry_date = datetime.fromtimestamp(expiry_timestamp_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
            created_date = datetime.now()
            cursor.execute(
                "INSERT INTO vpn_keys (user_id, vless_uuid, key_email, expiry_date, created_date) VALUES (?, ?, ?, ?, ?)",
                (user_id, vless_uuid, key_email, expiry_date, created_date)
            )
            new_key_id = cursor.lastrowid
            conn.commit()
            return new_key_id
    except sqlite3.Error as e:
        logging.error(f"Failed to add new key for user {user_id}: {e}")
        return None

def get_user_keys(user_id: int):
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vpn_keys WHERE user_id = ? ORDER BY key_id", (user_id,))
            keys = cursor.fetchall()
            return [dict(key) for key in keys]
    except sqlite3.Error as e:
        logging.error(f"Failed to get keys for user {user_id}: {e}")
        return []

def get_key_by_id(key_id: int):
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vpn_keys WHERE key_id = ?", (key_id,))
            key_data = cursor.fetchone()
            return dict(key_data) if key_data else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get key by ID {key_id}: {e}")
        return None

def update_key_info(key_id: int, new_vless_uuid: str, new_expiry_ms: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            # Конвертируем UTC timestamp в локальное время корректно
            from datetime import timezone
            expiry_date = datetime.fromtimestamp(new_expiry_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
            cursor.execute("UPDATE vpn_keys SET vless_uuid = ?, expiry_date = ? WHERE key_id = ?", (new_vless_uuid, expiry_date, key_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update key {key_id}: {e}")

def get_next_key_number(user_id: int) -> int:
    keys = get_user_keys(user_id)
    return len(keys) + 1

def get_all_vpn_users():
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT user_id FROM vpn_keys")
            users = cursor.fetchall()
            return [dict(user) for user in users]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all vpn users: {e}")
        return []

def update_key_status_from_server(key_email: str, remote_user):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            if remote_user:
                # Конвертируем UTC timestamp в локальное время корректно
                from datetime import timezone
                expiry_date = datetime.fromtimestamp(remote_user.expiry_time / 1000, tz=timezone.utc).replace(tzinfo=None)
                cursor.execute("UPDATE vpn_keys SET vless_uuid = ?, expiry_date = ? WHERE key_email = ?", (remote_user.id, expiry_date, key_email))
            else:
                cursor.execute("DELETE FROM vpn_keys WHERE key_email = ?", (key_email,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update key status for {key_email}: {e}")

def update_key_last_notified_percent(key_email: str, percent: int):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE vpn_keys SET last_notified_percent = ? WHERE key_email = ?", (percent, key_email))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update last_notified_percent for {key_email}: {e}")

def get_key_last_notified_percent(key_email: str) -> int:
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_notified_percent FROM vpn_keys WHERE key_email = ?", (key_email,))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
    except sqlite3.Error as e:
        logging.error(f"Failed to get last_notified_percent for {key_email}: {e}")
        return 0

# -------------------- Promo codes --------------------
def create_promo(code: str, discount_percent: int, free_days: int, uses_limit: int) -> bool:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO promo_codes (code, discount_percent, free_days, uses_limit, uses_count, active) VALUES (?, ?, ?, ?, COALESCE((SELECT uses_count FROM promo_codes WHERE code = ?),0), 1)", (code, discount_percent, free_days, uses_limit, code))
            conn.commit(); return True
    except sqlite3.Error as e:
        logging.error(f"Failed to create promo {code}: {e}"); return False

def get_promo(code: str):
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row; c = conn.cursor()
            c.execute("SELECT * FROM promo_codes WHERE code = ? AND active = 1", (code,))
            r = c.fetchone(); return dict(r) if r else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get promo {code}: {e}"); return None

def apply_promo_usage(code: str):
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE promo_codes SET uses_count = uses_count + 1 WHERE code = ?", (code,))
            c.execute("UPDATE promo_codes SET active = 0 WHERE code = ? AND uses_limit > 0 AND uses_count >= uses_limit", (code,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update promo usage {code}: {e}")

def get_all_promos():
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor(); c.execute("SELECT * FROM promo_codes ORDER BY code")
            rows = c.fetchall(); return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logging.error(f"Failed to list promos: {e}"); return []

def set_promo_active(code: str, active: bool) -> bool:
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("UPDATE promo_codes SET active = ? WHERE code = ?", (1 if active else 0, code)); conn.commit(); return c.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to set promo {code} active={active}: {e}"); return False

# -------------------- Referrals --------------------
def ensure_user_ref_code(telegram_id: int) -> str:
    import secrets
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("SELECT ref_code FROM users WHERE telegram_id = ?", (telegram_id,))
            row = c.fetchone()
            if row and row[0]:
                return row[0]
            new_code = secrets.token_urlsafe(6)
            c.execute("UPDATE users SET ref_code = ? WHERE telegram_id = ?", (new_code, telegram_id))
            conn.commit(); return new_code
    except sqlite3.Error as e:
        logging.error(f"Failed to ensure ref code for {telegram_id}: {e}"); return ""

def link_referral(ref_code: str, new_user_id: int):
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT telegram_id FROM users WHERE ref_code = ?", (ref_code,))
            owner = c.fetchone()
            if not owner: return False
            
            # Проверка: пользователь не может пригласить сам себя
            if owner[0] == new_user_id:
                logging.warning(f"User {new_user_id} tried to refer themselves with code {ref_code}")
                return False
                
            c.execute("UPDATE users SET referred_by = ? WHERE telegram_id = ? AND referred_by IS NULL", (ref_code, new_user_id))
            c.execute("INSERT INTO referrals (referrer_code, referred_user_id) VALUES (?, ?)", (ref_code, new_user_id))
            conn.commit(); return True
    except sqlite3.Error as e:
        logging.error(f"Failed to link referral {ref_code} -> {new_user_id}: {e}"); return False

def count_referrals(ref_code: str) -> int:
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_code = ?", (ref_code,))
            return c.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"Failed to count referrals for {ref_code}: {e}"); return 0

def get_referral_invitees(ref_code: str, limit: int = 100) -> list[dict]:
    """Referred users for a code (Mini App referral, read-only).

    Returns referred_user_id, joined_at, username, and first_topup_at (MIN created_at
    of the invitee's 'topup' actions, NULL if never paid) — newest first. No reward
    fields: referral accrual is not implemented, so the snapshot must not fabricate
    earned amounts. Paid-vs-registered is derived from first_topup_at, a real fact.
    """
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT r.referred_user_id AS referred_user_id, "
                "       r.created_at AS joined_at, "
                "       u.username AS username, "
                "       (SELECT MIN(a.created_at) FROM user_actions a "
                "          WHERE a.user_id = r.referred_user_id AND a.action = 'topup') "
                "       AS first_topup_at "
                "FROM referrals r LEFT JOIN users u ON u.telegram_id = r.referred_user_id "
                "WHERE r.referrer_code = ? ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
                (ref_code, max(1, min(int(limit or 100), 500))),
            )
            return [dict(row) for row in c.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to list invitees for {ref_code}: {e}"); return []

# -------------------- Auto renew & expiry notifications --------------------
def set_auto_renew(user_id: int, enabled: bool):
    set_yookassa_autopay_enabled(user_id, enabled)

def get_auto_renew(user_id: int) -> bool:
    """UI flag: YooKassa card autopay enabled (legacy column auto_renew kept in sync)."""
    return get_yookassa_autopay_enabled(user_id)


def get_yookassa_autopay_enabled(user_id: int) -> bool:
    try:
        with db_connection() as conn:
            row = conn.execute(
                "SELECT yookassa_autopay_enabled FROM users WHERE telegram_id = ?",
                (user_id,),
            ).fetchone()
            return bool(row and row[0])
    except sqlite3.Error as e:
        logging.error("get_yookassa_autopay_enabled %s: %s", user_id, e)
        return False


def set_yookassa_autopay_enabled(user_id: int, enabled: bool) -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET yookassa_autopay_enabled = ?, auto_renew = ? "
                "WHERE telegram_id = ?",
                (1 if enabled else 0, 1 if enabled else 0, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("set_yookassa_autopay_enabled %s: %s", user_id, e)


def get_yookassa_payment_method_id(user_id: int) -> str | None:
    try:
        with db_connection() as conn:
            row = conn.execute(
                "SELECT yookassa_payment_method_id FROM users WHERE telegram_id = ?",
                (user_id,),
            ).fetchone()
            if row and row[0]:
                return str(row[0]).strip()
    except sqlite3.Error as e:
        logging.error("get_yookassa_payment_method_id %s: %s", user_id, e)
    return None


def set_yookassa_payment_method(user_id: int, payment_method_id: str) -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET yookassa_payment_method_id = ? WHERE telegram_id = ?",
                (payment_method_id.strip(), user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("set_yookassa_payment_method %s: %s", user_id, e)


def schedule_yookassa_autopay_next(user_id: int, days: int) -> None:
    nxt = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET yookassa_autopay_next_at = ? WHERE telegram_id = ?",
                (nxt, user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("schedule_yookassa_autopay_next %s: %s", user_id, e)


def clear_yookassa_autopay_error(user_id: int) -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET yookassa_autopay_last_error = NULL WHERE telegram_id = ?",
                (user_id,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("clear_yookassa_autopay_error %s: %s", user_id, e)


def set_yookassa_autopay_error(user_id: int, message: str) -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET yookassa_autopay_last_error = ? WHERE telegram_id = ?",
                (message[:500], user_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("set_yookassa_autopay_error %s: %s", user_id, e)


def list_yookassa_autopay_due(limit: int = 20) -> list[int]:
    """Users with card autopay enabled and next charge time passed."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        with db_connection() as conn:
            rows = conn.execute(
                """
                SELECT telegram_id FROM users
                WHERE yookassa_autopay_enabled = 1
                  AND yookassa_payment_method_id IS NOT NULL
                  AND TRIM(yookassa_payment_method_id) != ''
                  AND (yookassa_autopay_next_at IS NULL OR yookassa_autopay_next_at <= ?)
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            return [int(r[0]) for r in rows]
    except sqlite3.Error as e:
        logging.error("list_yookassa_autopay_due: %s", e)
        return []


def get_yookassa_autopay(user_id: int) -> dict:
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT yookassa_autopay_enabled, yookassa_payment_method_id,
                          yookassa_autopay_next_at, yookassa_autopay_last_error
                   FROM users WHERE telegram_id = ?""",
                (user_id,),
            ).fetchone()
            if not row:
                return {}
            return dict(row)
    except sqlite3.Error as e:
        logging.error("get_yookassa_autopay %s: %s", user_id, e)
        return {}

def get_last_expiry_notified_days(user_id: int) -> int:
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("SELECT last_expiry_notified_days FROM users WHERE telegram_id = ?", (user_id,)); row = c.fetchone(); return row[0] if row else 999
    except sqlite3.Error as e:
        logging.error(f"Failed to get last_expiry_notified_days for {user_id}: {e}"); return 999

def update_last_expiry_notified_days(user_id: int, days: int):
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("UPDATE users SET last_expiry_notified_days = ? WHERE telegram_id = ?", (days, user_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update last_expiry_notified_days for {user_id}: {e}")

# -------------------- Actions log --------------------
def log_action(user_id: int, action: str, meta: str | None = None):
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("INSERT INTO user_actions (user_id, action, meta) VALUES (?, ?, ?)", (user_id, action, meta)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to log action {action} for {user_id}: {e}")


# -------------------- Support rate limits (persisted, P3-RED-SUPPORT-RATELIMIT-PERSIST-01) --------------------
def cleanup_support_rate_limits(older_than_sec: int = 7200) -> None:
    """Drop stale rate-limit rows (TTL cleanup)."""
    try:
        import time

        cutoff = time.time() - older_than_sec
        with db_connection() as conn:
            conn.execute(
                "DELETE FROM support_rate_limits WHERE window_start < ?",
                (cutoff,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("cleanup_support_rate_limits: %s", e)


def support_rate_limit_check(
    user_id: int,
    *,
    window_sec: int,
    max_hits: int,
) -> bool:
    """Return True if user exceeded limit (should block)."""
    import time

    now = time.time()
    try:
        with db_connection() as conn:
            row = conn.execute(
                "SELECT window_start, hit_count FROM support_rate_limits WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO support_rate_limits (user_id, window_start, hit_count) "
                    "VALUES (?, ?, 1)",
                    (user_id, now),
                )
                conn.commit()
                return False
            window_start, hit_count = float(row[0]), int(row[1])
            if now - window_start >= window_sec:
                conn.execute(
                    "UPDATE support_rate_limits SET window_start = ?, hit_count = 1 "
                    "WHERE user_id = ?",
                    (now, user_id),
                )
                conn.commit()
                return False
            if hit_count >= max_hits:
                return True
            conn.execute(
                "UPDATE support_rate_limits SET hit_count = hit_count + 1 "
                "WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
            return False
    except sqlite3.Error as e:
        logging.error("support_rate_limit_check user=%s: %s", user_id, e)
        return False

def add_traffic_extra(key_id: int, gb: int):
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("UPDATE vpn_keys SET traffic_extra_bytes = traffic_extra_bytes + ? WHERE key_id = ?", (gb * 1024 * 1024 * 1024, key_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to add extra traffic for key {key_id}: {e}")

def set_key_plan(key_id: int, plan_id: str):
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("UPDATE vpn_keys SET subscription_plan = ? WHERE key_id = ?", (plan_id, key_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set plan {plan_id} for key {key_id}: {e}")

def has_action(user_id: int, action: str) -> bool:
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("SELECT 1 FROM user_actions WHERE user_id = ? AND action = ? LIMIT 1", (user_id, action)); return c.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Failed to check action {action} for {user_id}: {e}"); return False


def get_latest_action_meta(user_id: int, action: str) -> str | None:
    """Most recent meta value for an action (e.g. language, consent version). §7.4/D15."""
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT meta FROM user_actions WHERE user_id = ? AND action = ? "
                "ORDER BY id DESC LIMIT 1",
                (user_id, action),
            )
            row = c.fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to read action meta {action} for {user_id}: {e}")
        return None


def get_balance_ledger(user_id: int, limit: int = 50) -> list[dict]:
    """Read-only balance history from user_actions (MINI-APP balance, Phase A).

    Returns top-ups (action='topup') and daily charges (action LIKE 'daily_balance:%'),
    newest first. No schema change; no mutation. Idempotency rows ('yk:'/'crypto:') are
    excluded by the action filter so each top-up appears once.
    """
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT action, meta, created_at FROM user_actions "
                "WHERE user_id = ? AND (action = 'topup' OR action LIKE 'daily_balance:%') "
                "ORDER BY id DESC LIMIT ?",
                (user_id, int(limit)),
            )
            return [dict(r) for r in c.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to read balance ledger for {user_id}: {e}")
        return []


# -------------------- balance_ledger (Phase B journal, REF-LEDGER-001) --------------------
def credit_ledger(
    user_id: int, kind: str, amount_kopeks: int, ref: str, meta: str | None = None
) -> bool:
    """Atomically append a balance_ledger row AND apply it to users.balance, once per (user, ref).

    Returns True if newly credited; False if this event was already recorded (idempotent), the
    user is missing, or on error. ``amount_kopeks`` is signed (+credit / -debit). This is the
    single place that both journals and mutates balance — used by referral/partner rewards.
    Top-ups and daily charges keep their existing balance path; they are not journaled here.
    """
    amt = int(amount_kopeks)
    if not ref:
        logging.error("credit_ledger requires a ref (user=%s kind=%s)", user_id, kind)
        return False
    try:
        with db_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM balance_ledger WHERE user_id = ? AND ref = ? LIMIT 1",
                (user_id, ref),
            )
            if cur.fetchone():
                conn.rollback()
                return False
            cur.execute(
                "SELECT COALESCE(balance, 0) FROM users WHERE telegram_id = ?", (user_id,)
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                return False
            new_balance = float(row[0]) + amt / 100.0
            cur.execute(
                "INSERT INTO balance_ledger "
                "(user_id, kind, amount_kopeks, balance_after_kopeks, ref, meta) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, kind, amt, round(new_balance * 100), ref, meta),
            )
            cur.execute(
                "UPDATE users SET balance = ? WHERE telegram_id = ?",
                (new_balance, user_id),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error("credit_ledger failed user=%s ref=%s: %s", user_id, ref, e)
        return False


def get_ledger_entries(user_id: int, limit: int = 50) -> list[dict]:
    """Newest-first balance_ledger rows for a user (Phase B history source)."""
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT id, kind, amount_kopeks, balance_after_kopeks, ref, meta, created_at_utc "
                "FROM balance_ledger WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, max(1, min(int(limit or 50), 500))),
            )
            return [dict(r) for r in c.fetchall()]
    except sqlite3.Error as e:
        logging.error("get_ledger_entries %s: %s", user_id, e)
        return []


def sum_ledger_kinds(user_id: int, kinds: tuple[str, ...]) -> int:
    """Sum of signed amount_kopeks for the given kinds (e.g. referral earnings)."""
    klist = list(kinds)
    if not klist:
        return 0
    placeholders = ",".join("?" * len(klist))
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                f"SELECT COALESCE(SUM(amount_kopeks), 0) FROM balance_ledger "
                f"WHERE user_id = ? AND kind IN ({placeholders})",
                (user_id, *klist),
            )
            return int(c.fetchone()[0])
    except sqlite3.Error as e:
        logging.error("sum_ledger_kinds %s: %s", user_id, e)
        return 0


def get_referral_rewards_by_invitee(referrer_id: int) -> dict[int, int]:
    """Map invitee_id → credited kopeks from this referrer's reward rows.

    Refs are 'ref_first:<invitee>' / 'pt_first:<invitee>' / 'pt_recur:<payment_id>'. Only the
    per-invitee refs (numeric tail) are attributed; recurring-by-payment rows are skipped here.
    """
    out: dict[int, int] = {}
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT ref, amount_kopeks FROM balance_ledger "
                "WHERE user_id = ? AND kind IN ('referral_reward', 'partner_reward') "
                "AND ref IS NOT NULL AND ref != 'ref_welcome'",
                (referrer_id,),
            )
            for ref, amt in c.fetchall():
                tail = str(ref).split(":", 1)
                if len(tail) == 2 and tail[1].isdigit():
                    inv = int(tail[1])
                    out[inv] = out.get(inv, 0) + int(amt)
    except sqlite3.Error as e:
        logging.error("get_referral_rewards_by_invitee %s: %s", referrer_id, e)
    return out


def count_actions(user_id: int, action: str) -> int:
    """Count user_actions rows for (user, action) — e.g. to detect a first top-up."""
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM user_actions WHERE user_id = ? AND action = ?",
                (user_id, action),
            )
            return int(c.fetchone()[0])
    except sqlite3.Error as e:
        logging.error("count_actions %s/%s: %s", user_id, action, e)
        return 0


def try_acquire_topup_idempotency(user_id: int, idempotency_key: str) -> bool:
    """Atomically claim topup idempotency before balance change (P2-RED-BOT-INTEGRITY-01)."""
    key = (idempotency_key or "").strip()
    if not key:
        return True
    try:
        with db_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM user_actions WHERE user_id = ? AND action = ? LIMIT 1",
                (user_id, key),
            )
            if cur.fetchone():
                conn.rollback()
                return False
            cur.execute(
                "INSERT INTO user_actions (user_id, action, meta) VALUES (?, ?, ?)",
                (user_id, key, "topup"),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error("try_acquire_topup_idempotency %s user=%s: %s", key, user_id, e)
        return False


# -------------------- Webhook idempotency / DLQ (P6-RED-PAY-01) --------------------
def claim_webhook_delivery(idempotency_key: str, source: str, payload_json: str) -> str:
    """new | duplicate | in_progress | retry

    BILL-WEBHOOK-CLAIM-TOCTOU-001: claim atomically. The previous SELECT-then-INSERT
    let two concurrent workers both see "no row" and both return "new", causing a
    double credit. `idempotency_key` is the PRIMARY KEY, so `INSERT OR IGNORE` makes
    exactly one caller win the race (rowcount == 1 -> "new"); everyone else inspects
    the existing row. On any DB error we fail safe to "in_progress" (the caller skips
    processing and the payment provider retries) rather than "new" (double credit).
    """
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                """INSERT OR IGNORE INTO webhook_deliveries
                   (idempotency_key, source, status, payload_json)
                   VALUES (?, ?, 'pending', ?)""",
                (idempotency_key, source, payload_json),
            )
            if c.rowcount == 1:
                conn.commit()
                return "new"
            # Row already existed — only one worker reaches here per key.
            c.execute(
                "SELECT status FROM webhook_deliveries WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = c.fetchone()
            if not row:
                conn.commit()
                return "in_progress"
            status = row[0]
            if status == "done":
                conn.commit()
                return "duplicate"
            if status in ("pending", "processing"):
                conn.commit()
                return "in_progress"
            # failed -> reclaim for retry
            c.execute(
                """UPDATE webhook_deliveries
                   SET status = 'pending', source = ?, payload_json = ?, error = NULL,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE idempotency_key = ?""",
                (source, payload_json, idempotency_key),
            )
            conn.commit()
            return "retry"
    except sqlite3.Error as e:
        logging.error("claim_webhook_delivery %s: %s", idempotency_key, e)
        return "in_progress"

def mark_webhook_processing(idempotency_key: str) -> None:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                """UPDATE webhook_deliveries
                   SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                   WHERE idempotency_key = ?""",
                (idempotency_key,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("mark_webhook_processing %s: %s", idempotency_key, e)

def mark_webhook_done(idempotency_key: str) -> None:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                """UPDATE webhook_deliveries
                   SET status = 'done', error = NULL, updated_at = CURRENT_TIMESTAMP
                   WHERE idempotency_key = ?""",
                (idempotency_key,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("mark_webhook_done %s: %s", idempotency_key, e)

def mark_webhook_failed(idempotency_key: str, error: str) -> None:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                """UPDATE webhook_deliveries
                   SET status = 'failed', error = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE idempotency_key = ?""",
                (error[:2000], idempotency_key),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("mark_webhook_failed %s: %s", idempotency_key, e)

def count_webhook_dlq() -> int:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM webhook_deliveries WHERE status = 'failed'")
            return int(c.fetchone()[0])
    except sqlite3.Error as e:
        logging.error("count_webhook_dlq: %s", e)
        return 0

def get_user_by_ref_code(ref_code: str):
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor(); c.execute("SELECT * FROM users WHERE ref_code = ?", (ref_code,)); row = c.fetchone(); return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get user by ref_code {ref_code}: {e}"); return None

# -------------------- Admin stats --------------------
def get_admin_stats():
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*), COALESCE(SUM(total_spent),0), COALESCE(SUM(total_months),0) FROM users")
            users_count, total_spent, total_months = c.fetchone()
            c.execute("SELECT COUNT(*) FROM vpn_keys")
            total_keys = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM vpn_keys WHERE expiry_date > CURRENT_TIMESTAMP")
            active_keys = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM promo_codes WHERE active = 1")
            active_promos = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM referrals")
            total_referrals = c.fetchone()[0]
            return {
                'users_count': users_count,
                'total_spent': total_spent,
                'total_months': total_months,
                'total_keys': total_keys,
                'active_keys': active_keys,
                'active_promos': active_promos,
                'total_referrals': total_referrals,
            }
    except sqlite3.Error as e:
        logging.error(f"Failed to get admin stats: {e}")
        return {}

def set_last_backup_timestamp(ts_iso: str):
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('last_backup_iso', ?)", (ts_iso,)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set last backup timestamp: {e}")

def get_last_backup_timestamp() -> str | None:
    try:
        with db_connection() as conn:
            c = conn.cursor(); c.execute("SELECT value FROM bot_settings WHERE key = 'last_backup_iso'")
            row = c.fetchone(); return row[0] if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get last backup timestamp: {e}"); return None


def _expiry_hour_setting_key(telegram_id: int) -> str:
    return f"expiry_6h_notified:{int(telegram_id)}"


def was_expiry_hour_notified(telegram_id: int) -> bool:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT value FROM bot_settings WHERE key = ?",
                (_expiry_hour_setting_key(telegram_id),),
            )
            row = c.fetchone()
            return bool(row and row[0] == "1")
    except sqlite3.Error as e:
        logging.error(f"Failed expiry hour flag for {telegram_id}: {e}")
        return False


def mark_expiry_hour_notified(telegram_id: int) -> None:
    try:
        ts = datetime.now(timezone.utc).isoformat()
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
                (_expiry_hour_setting_key(telegram_id), ts),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed set expiry hour flag for {telegram_id}: {e}")


def prune_stale_expiry_notification_flags(older_than_days: int = 30) -> int:
    """Remove expiry_*_notified:* bot_settings older than N days (P3-UX-BOT-POLISH-02)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
    try:
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM bot_settings
                WHERE key LIKE 'expiry_%_notified:%'
                  AND value IS NOT NULL
                  AND value != '1'
                  AND value < ?
                """,
                (cutoff,),
            )
            deleted = cur.rowcount
            cur.execute(
                """
                DELETE FROM bot_settings
                WHERE key LIKE 'expiry_%_notified:%' AND value = '1'
                """
            )
            deleted += cur.rowcount
            conn.commit()
            return deleted
    except sqlite3.Error as e:
        logging.error("prune_stale_expiry_notification_flags: %s", e)
        return 0


def clear_expiry_hour_notified(telegram_id: int) -> None:
    try:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM bot_settings WHERE key = ?",
                (_expiry_hour_setting_key(telegram_id),),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed clear expiry hour flag for {telegram_id}: {e}")


def get_balance(telegram_id: int) -> float:
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            return float(row["balance"]) if row and row["balance"] is not None else 0.0
    except sqlite3.Error as e:
        logging.error(f"Failed to get balance for {telegram_id}: {e}")
        return 0.0


def set_balance(telegram_id: int, amount: float) -> None:
    """Set wallet balance (admin / support correction)."""
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET balance = ? WHERE telegram_id = ?",
                (float(amount), telegram_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set balance for {telegram_id}: {e}")


def add_balance(telegram_id: int, amount: float):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE telegram_id = ?",
                (amount, telegram_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to add balance {amount} for {telegram_id}: {e}")


def try_deduct_balance(telegram_id: int, amount: float) -> bool:
    """Atomically deduct if balance sufficient (P6-RED-PAY-03)."""
    if amount <= 0:
        return True
    try:
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET balance = COALESCE(balance, 0) - ? "
                "WHERE telegram_id = ? AND COALESCE(balance, 0) >= ?",
                (amount, telegram_id, amount),
            )
            conn.commit()
            return cur.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to deduct balance {amount} for {telegram_id}: {e}")
        return False


RENEWAL_STATUS_PENDING = "pending"
RENEWAL_STATUS_SUCCESS = "success"
RENEWAL_STATUS_REFUNDED = "refunded"
RENEWAL_STATUS_FAILED = "failed"


def has_pending_renewal_attempt(user_id: int, key_id: int) -> bool:
    """True if an incomplete renewal attempt exists for this user/key."""
    try:
        with db_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM renewal_attempts "
                "WHERE user_id = ? AND key_id = ? AND status = ? LIMIT 1",
                (user_id, key_id, RENEWAL_STATUS_PENDING),
            ).fetchone()
            return row is not None
    except sqlite3.Error as e:
        logging.error(
            "has_pending_renewal_attempt user=%s key=%s: %s", user_id, key_id, e
        )
        return True


def create_renewal_attempt(
    attempt_id: str,
    user_id: int,
    key_id: int,
    cost_rub: float,
    plan: str,
) -> bool:
    """Insert pending attempt before balance deduct (P2-RED-BOT-RENEW-IDEM-01)."""
    if has_pending_renewal_attempt(user_id, key_id):
        return False
    try:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO renewal_attempts "
                "(attempt_id, user_id, key_id, status, cost_rub, plan, balance_deducted) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (attempt_id, user_id, key_id, RENEWAL_STATUS_PENDING, cost_rub, plan),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error("create_renewal_attempt %s: %s", attempt_id, e)
        return False


def mark_renewal_balance_deducted(attempt_id: str) -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE renewal_attempts SET balance_deducted = 1 WHERE attempt_id = ?",
                (attempt_id,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("mark_renewal_balance_deducted %s: %s", attempt_id, e)


def complete_renewal_attempt(attempt_id: str, status: str) -> None:
    """Terminal status: success, refunded, or failed."""
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE renewal_attempts SET status = ?, completed_at = CURRENT_TIMESTAMP "
                "WHERE attempt_id = ?",
                (status, attempt_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error("complete_renewal_attempt %s -> %s: %s", attempt_id, status, e)


def list_stale_pending_renewals(older_than_minutes: int = 5) -> list[dict]:
    try:
        with db_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT attempt_id, user_id, key_id, cost_rub, plan, balance_deducted "
                "FROM renewal_attempts "
                "WHERE status = ? AND created_at <= datetime('now', ?)",
                (RENEWAL_STATUS_PENDING, f"-{int(older_than_minutes)} minutes"),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logging.error("list_stale_pending_renewals: %s", e)
        return []


def recover_stale_renewals(older_than_minutes: int = 5) -> int:
    """On startup: refund deducted stale pending; close others as failed."""
    recovered = 0
    for row in list_stale_pending_renewals(older_than_minutes):
        attempt_id = row["attempt_id"]
        user_id = int(row["user_id"])
        cost_rub = float(row["cost_rub"])
        if row["balance_deducted"]:
            add_balance(user_id, cost_rub)
            complete_renewal_attempt(attempt_id, RENEWAL_STATUS_REFUNDED)
            log_action(
                user_id,
                "auto_renew_recovery",
                f"refunded:{attempt_id}:{cost_rub:.2f}",
            )
            logging.warning(
                "renewal recovery: refunded user=%s attempt=%s %.2f rub",
                user_id,
                attempt_id,
                cost_rub,
            )
        else:
            complete_renewal_attempt(attempt_id, RENEWAL_STATUS_FAILED)
            log_action(user_id, "auto_renew_recovery", f"failed:{attempt_id}")
            logging.warning(
                "renewal recovery: closed pending attempt=%s user=%s (no deduct)",
                attempt_id,
                user_id,
            )
        recovered += 1
    return recovered