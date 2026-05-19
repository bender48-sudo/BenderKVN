import hashlib
import re
import sqlite3
from datetime import datetime
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
DB_FILE = DATA_DIR / "shop_bot.db"

def initialize_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
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
                    sub_refresh_notified_generation INTEGER DEFAULT 0
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
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN sub_refresh_notified_generation INTEGER DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass
            for col, typedef in (
                ("support_topic_id", "INTEGER"),
                ("support_last_user_at", "INTEGER"),
                ("support_last_staff_at", "INTEGER"),
            ):
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
                except sqlite3.OperationalError:
                    pass
            for col, typedef in (
                ("claimed_at", "TEXT"),
                ("bind_token", "TEXT"),
                ("telegram_id", "INTEGER"),
                ("bound_at", "TEXT"),
            ):
                try:
                    cursor.execute(
                        f"ALTER TABLE web_trial_claims ADD COLUMN {col} {typedef}"
                    )
                except sqlite3.OperationalError:
                    pass
            try:
                cursor.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_web_trial_bind_token "
                    "ON web_trial_claims(bind_token) WHERE bind_token IS NOT NULL"
                )
            except sqlite3.OperationalError:
                pass
            conn.commit()
            logging.info("Database with 'created_date' column initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error on initialization: {e}")

def get_setting(key: str) -> str | None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get setting '{key}': {e}")
        return None

def update_setting(key: str, value: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE bot_settings SET value = ? WHERE key = ?", (value, key))
            conn.commit()
            logging.info(f"Setting '{key}' updated.")
    except sqlite3.Error as e:
        logging.error(f"Failed to update setting '{key}': {e}")

def upsert_setting(key: str, value: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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

def list_users_pending_sub_refresh(current_generation: int, limit: int = 15) -> list[int]:
    """Distinct vpn_keys.user_id with telegram account behind current_generation."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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

def set_terms_agreed(telegram_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET agreed_to_terms = 1 WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            logging.info(f"User {telegram_id} has agreed to terms.")
    except sqlite3.Error as e:
        logging.error(f"Failed to set terms agreed for user {telegram_id}: {e}")

def update_user_stats(telegram_id: int, amount_spent: float, months_purchased: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET total_spent = total_spent + ?, total_months = total_months + ? WHERE telegram_id = ?", (amount_spent, months_purchased, telegram_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update user stats for {telegram_id}: {e}")

def set_trial_used(telegram_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET trial_used = 1 WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            logging.info(f"Trial period marked as used for user {telegram_id}.")
    except sqlite3.Error as e:
        logging.error(f"Failed to set trial used for user {telegram_id}: {e}")

def reset_trial_used(telegram_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET trial_used = 0 WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            logging.info(f"Trial period reset for user {telegram_id}.")
    except sqlite3.Error as e:
        logging.error(f"Failed to reset trial for user {telegram_id}: {e}")

def add_new_key(user_id: int, vless_uuid: str, key_email: str, expiry_timestamp_ms: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE vpn_keys SET last_notified_percent = ? WHERE key_email = ?", (percent, key_email))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update last_notified_percent for {key_email}: {e}")

def get_key_last_notified_percent(key_email: str) -> int:
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO promo_codes (code, discount_percent, free_days, uses_limit, uses_count, active) VALUES (?, ?, ?, ?, COALESCE((SELECT uses_count FROM promo_codes WHERE code = ?),0), 1)", (code, discount_percent, free_days, uses_limit, code))
            conn.commit(); return True
    except sqlite3.Error as e:
        logging.error(f"Failed to create promo {code}: {e}"); return False

def get_promo(code: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row; c = conn.cursor()
            c.execute("SELECT * FROM promo_codes WHERE code = ? AND active = 1", (code,))
            r = c.fetchone(); return dict(r) if r else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get promo {code}: {e}"); return None

def apply_promo_usage(code: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("UPDATE promo_codes SET uses_count = uses_count + 1 WHERE code = ?", (code,))
            c.execute("UPDATE promo_codes SET active = 0 WHERE code = ? AND uses_limit > 0 AND uses_count >= uses_limit", (code,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update promo usage {code}: {e}")

def get_all_promos():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor(); c.execute("SELECT * FROM promo_codes ORDER BY code")
            rows = c.fetchall(); return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logging.error(f"Failed to list promos: {e}"); return []

def set_promo_active(code: str, active: bool) -> bool:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("UPDATE promo_codes SET active = ? WHERE code = ?", (1 if active else 0, code)); conn.commit(); return c.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to set promo {code} active={active}: {e}"); return False

# -------------------- Referrals --------------------
def ensure_user_ref_code(telegram_id: int) -> str:
    import secrets
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_code = ?", (ref_code,))
            return c.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"Failed to count referrals for {ref_code}: {e}"); return 0

# -------------------- Auto renew & expiry notifications --------------------
def set_auto_renew(user_id: int, enabled: bool):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("UPDATE users SET auto_renew = ? WHERE telegram_id = ?", (1 if enabled else 0, user_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set auto_renew for {user_id}: {e}")

def get_auto_renew(user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("SELECT auto_renew FROM users WHERE telegram_id = ?", (user_id,)); row = c.fetchone(); return bool(row and row[0])
    except sqlite3.Error as e:
        logging.error(f"Failed to get auto_renew for {user_id}: {e}"); return False

def get_last_expiry_notified_days(user_id: int) -> int:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("SELECT last_expiry_notified_days FROM users WHERE telegram_id = ?", (user_id,)); row = c.fetchone(); return row[0] if row else 999
    except sqlite3.Error as e:
        logging.error(f"Failed to get last_expiry_notified_days for {user_id}: {e}"); return 999

def update_last_expiry_notified_days(user_id: int, days: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("UPDATE users SET last_expiry_notified_days = ? WHERE telegram_id = ?", (days, user_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to update last_expiry_notified_days for {user_id}: {e}")

# -------------------- Actions log --------------------
def log_action(user_id: int, action: str, meta: str | None = None):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("INSERT INTO user_actions (user_id, action, meta) VALUES (?, ?, ?)", (user_id, action, meta)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to log action {action} for {user_id}: {e}")

def add_traffic_extra(key_id: int, gb: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("UPDATE vpn_keys SET traffic_extra_bytes = traffic_extra_bytes + ? WHERE key_id = ?", (gb * 1024 * 1024 * 1024, key_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to add extra traffic for key {key_id}: {e}")

def set_key_plan(key_id: int, plan_id: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("UPDATE vpn_keys SET subscription_plan = ? WHERE key_id = ?", (plan_id, key_id)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set plan {plan_id} for key {key_id}: {e}")

def has_action(user_id: int, action: str) -> bool:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("SELECT 1 FROM user_actions WHERE user_id = ? AND action = ? LIMIT 1", (user_id, action)); return c.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Failed to check action {action} for {user_id}: {e}"); return False

# -------------------- Webhook idempotency / DLQ (P6-RED-PAY-01) --------------------
def claim_webhook_delivery(idempotency_key: str, source: str, payload_json: str) -> str:
    """new | duplicate | in_progress | retry"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT status FROM webhook_deliveries WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = c.fetchone()
            if row:
                status = row[0]
                if status == "done":
                    return "duplicate"
                if status in ("pending", "processing"):
                    return "in_progress"
                c.execute(
                    """UPDATE webhook_deliveries
                       SET status = 'pending', source = ?, payload_json = ?, error = NULL,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE idempotency_key = ?""",
                    (source, payload_json, idempotency_key),
                )
                conn.commit()
                return "retry"
            c.execute(
                """INSERT INTO webhook_deliveries
                   (idempotency_key, source, status, payload_json)
                   VALUES (?, ?, 'pending', ?)""",
                (idempotency_key, source, payload_json),
            )
            conn.commit()
            return "new"
    except sqlite3.Error as e:
        logging.error("claim_webhook_delivery %s: %s", idempotency_key, e)
        return "new"

def mark_webhook_processing(idempotency_key: str) -> None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM webhook_deliveries WHERE status = 'failed'")
            return int(c.fetchone()[0])
    except sqlite3.Error as e:
        logging.error("count_webhook_dlq: %s", e)
        return 0

def get_user_by_ref_code(ref_code: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor(); c.execute("SELECT * FROM users WHERE ref_code = ?", (ref_code,)); row = c.fetchone(); return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get user by ref_code {ref_code}: {e}"); return None

# -------------------- Admin stats --------------------
def get_admin_stats():
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('last_backup_iso', ?)", (ts_iso,)); conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set last backup timestamp: {e}")

def get_last_backup_timestamp() -> str | None:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor(); c.execute("SELECT value FROM bot_settings WHERE key = 'last_backup_iso'")
            row = c.fetchone(); return row[0] if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get last backup timestamp: {e}"); return None


def get_balance(telegram_id: int) -> float:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            return float(row["balance"]) if row and row["balance"] is not None else 0.0
    except sqlite3.Error as e:
        logging.error(f"Failed to get balance for {telegram_id}: {e}")
        return 0.0


def add_balance(telegram_id: int, amount: float):
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
        with sqlite3.connect(DB_FILE) as conn:
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