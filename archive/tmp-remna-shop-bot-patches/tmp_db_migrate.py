import sqlite3
conn = sqlite3.connect("/app/data/shop_bot.db")
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    conn.commit()
    print("Column 'balance' added")
except Exception as e:
    print(f"Already exists: {e}")

cur.execute("SELECT telegram_id, balance FROM users LIMIT 3")
for r in cur.fetchall():
    print(f"  user {r[0]}: balance={r[1]}")
conn.close()
