import sqlite3
conn = sqlite3.connect('/app/data/shop_bot.db')
c = conn.cursor()

print('=== last_expiry_notified_days distribution ===')
c.execute('SELECT last_expiry_notified_days, COUNT(*) FROM users GROUP BY last_expiry_notified_days')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} users')

print()
print('=== trial keys status ===')
c.execute("SELECT COUNT(*) as total, SUM(CASE WHEN expiry_date > datetime('now') THEN 1 ELSE 0 END) as active, SUM(CASE WHEN expiry_date <= datetime('now') THEN 1 ELSE 0 END) as expired FROM vpn_keys WHERE key_email LIKE '%-trial@kitsura.fun'")
r = c.fetchone()
print(f'  total_trial={r[0]} still_active={r[1]} expired={r[2]}')

print()
print('=== expiry distribution (active keys) ===')
c.execute("SELECT DATE(expiry_date) as expires_on, COUNT(*) as keys FROM vpn_keys WHERE expiry_date > datetime('now') GROUP BY DATE(expiry_date) ORDER BY expires_on")
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} keys')

print()
print('=== all vpn_keys overview ===')
c.execute('SELECT key_email, expiry_date, subscription_plan FROM vpn_keys ORDER BY expiry_date')
for r in c.fetchall():
    print(f'  {r[0]} | expires: {r[1]} | plan: {r[2]}')
