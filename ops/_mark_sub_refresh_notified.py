#!/usr/bin/env python3
import sqlite3
import sys

tid = int(sys.argv[1])
gen = int(sys.argv[2])
db = sys.argv[3] if len(sys.argv) > 3 else "/app/data/shop_bot.db"
conn = sqlite3.connect(db)
conn.execute(
    "UPDATE users SET sub_refresh_notified_generation = ? WHERE telegram_id = ?",
    (gen, tid),
)
conn.commit()
print("OK", tid, "->", gen)
