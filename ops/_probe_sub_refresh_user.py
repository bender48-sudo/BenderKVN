#!/usr/bin/env python3
"""Probe sub_refresh notify state for one telegram_id (run on AMS in docker)."""
import sqlite3
import sys

tid = int(sys.argv[1])
db = sys.argv[2] if len(sys.argv) > 2 else "/app/data/shop_bot.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

u = conn.execute(
    "SELECT telegram_id, username, agreed_to_terms, sub_refresh_notified_generation "
    "FROM users WHERE telegram_id=?",
    (tid,),
).fetchone()
print("user", dict(u) if u else "NO_ROW")

gen = conn.execute(
    "SELECT value FROM bot_settings WHERE key='sub_config_generation'"
).fetchone()
current = int(gen["value"]) if gen else 0
print("current_gen", current)
if u:
    notified = int(u["sub_refresh_notified_generation"] or 0)
    print("notified_gen", notified)
    print("pending_notify", notified < current)

keys = conn.execute(
    "SELECT key_id, key_email, expiry_date FROM vpn_keys WHERE user_id=? ORDER BY key_id DESC LIMIT 5",
    (tid,),
).fetchall()
print("vpn_keys", [dict(k) for k in keys])

pending_n = conn.execute(
    """
    SELECT COUNT(DISTINCT vk.user_id)
    FROM vpn_keys vk
    JOIN users u ON u.telegram_id = vk.user_id
    WHERE COALESCE(u.sub_refresh_notified_generation, 0) < ?
    """,
    (current,),
).fetchone()[0]
print("pending_users_total", pending_n)

acts = conn.execute(
    "SELECT id, action, meta, created_at FROM user_actions WHERE user_id=? "
    "ORDER BY id DESC LIMIT 20",
    (tid,),
).fetchall()
for a in acts:
    print("action", dict(a))
