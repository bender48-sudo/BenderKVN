import sqlite3
conn = sqlite3.connect("/app/data/shop_bot.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== users sample ===")
c.execute("SELECT telegram_id, username, total_spent, total_months, trial_used, auto_renew FROM users LIMIT 5")
for r in c.fetchall():
    print(dict(r))

print()
print("=== vpn_keys sample ===")
c.execute("SELECT key_id, user_id, key_email, expiry_date, subscription_plan, traffic_extra_bytes FROM vpn_keys LIMIT 5")
for r in c.fetchall():
    print(dict(r))

print()
print("=== user_actions types ===")
c.execute("SELECT action, COUNT(*) as cnt FROM user_actions GROUP BY action ORDER BY cnt DESC")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
