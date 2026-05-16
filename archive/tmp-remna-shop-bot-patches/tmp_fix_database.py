DBFILE = "/opt/remna-shop/src/shop_bot/data_manager/database.py"

with open(DBFILE) as f:
    content = f.read()

# 1. Add ALTER TABLE for balance in initialize_db, before conn.commit()
# Find the line: conn.commit() followed by logging.info("Database with 'created_date'")
OLD_COMMIT = '            conn.commit()\n            logging.info("Database with \'created_date\' column initialized successfully.")'
NEW_COMMIT = '''            # Migrate: add balance column if not exists
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # column already exists
            conn.commit()
            logging.info("Database with 'created_date' column initialized successfully.")'''

count1 = content.count(OLD_COMMIT)
print(f"Step 1 - commit block found: {count1}")
if count1 == 1:
    content = content.replace(OLD_COMMIT, NEW_COMMIT)
    print("  ALTER TABLE migration added to initialize_db")
else:
    print("  WARNING: could not find exact commit block")

# 2. Append new balance functions at end of file
BALANCE_FUNCS = '''

# ==================== Balance functions ====================

def get_balance(telegram_id: int) -> float:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            return float(row["balance"]) if row else 0.0
    except sqlite3.Error as e:
        logging.error(f"Failed to get balance for {telegram_id}: {e}")
        return 0.0


def add_balance(telegram_id: int, amount: float):
    """Add amount to user balance. Amount can be negative (for daily charge)."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to add balance {amount} for {telegram_id}: {e}")


def set_balance(telegram_id: int, amount: float):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (amount, telegram_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to set balance for {telegram_id}: {e}")


def get_all_users_with_balance():
    """For daily charge cron — get all users with balance > 0 and active keys."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT u.telegram_id, u.balance, u.username
                FROM users u
                JOIN vpn_keys vk ON u.telegram_id = vk.user_id
                WHERE u.balance > 0
                GROUP BY u.telegram_id
            """)
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get users with balance: {e}")
        return []
'''

content += BALANCE_FUNCS

with open(DBFILE, 'w') as f:
    f.write(content)

# Verify
import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"get_balance defined: {'def get_balance' in content}")
print(f"add_balance defined: {'def add_balance' in content}")
print(f"set_balance defined: {'def set_balance' in content}")
print(f"get_all_users_with_balance defined: {'def get_all_users_with_balance' in content}")
print(f"ALTER TABLE balance in init: {'ALTER TABLE users ADD COLUMN balance' in content}")
