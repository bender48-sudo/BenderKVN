import sqlite3

with open('/opt/remna-shop/src/shop_bot/data_manager/database.py', 'r') as f:
    db_content = f.read()

# Backup
with open('/opt/remna-shop/src/shop_bot/data_manager/database.py.bak', 'w') as f:
    f.write(db_content)

# Add new tables in initialize_db
OLD_DB = "                CREATE TABLE IF NOT EXISTS referrals ("
NEW_DB = """                CREATE TABLE IF NOT EXISTS promo_usages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, code)
                );
                CREATE TABLE IF NOT EXISTS referral_bonuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    bonus_days INTEGER NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS referrals ("""

if OLD_DB in db_content:
    db_content = db_content.replace(OLD_DB, NEW_DB, 1)
    print("Added promo_usages and referral_bonuses tables")
else:
    print("ERROR: referrals table marker not found")

# Add new functions at end of file
NEW_FUNCS = '''

# -------------------- Promo usage per user --------------------
def has_used_promo(user_id: int, code: str) -> bool:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM promo_usages WHERE user_id = ? AND code = ?", (user_id, code))
            return c.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Failed to check promo usage {user_id}/{code}: {e}")
        return False

def record_promo_usage(user_id: int, code: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO promo_usages (user_id, code) VALUES (?, ?)", (user_id, code))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to record promo usage {user_id}/{code}: {e}")

# -------------------- Referral bonus --------------------
def grant_referrer_bonus(referrer_id: int, referred_id: int, bonus_days: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM referral_bonuses WHERE referred_id = ?", (referred_id,))
            if c.fetchone():
                return False
            c.execute(
                "INSERT INTO referral_bonuses (referrer_id, referred_id, bonus_days) VALUES (?, ?, ?)",
                (referrer_id, referred_id, bonus_days)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Failed to grant referrer bonus {referrer_id}: {e}")
        return False
'''

db_content += NEW_FUNCS

with open('/opt/remna-shop/src/shop_bot/data_manager/database.py', 'w') as f:
    f.write(db_content)

print("database.py patched OK")
