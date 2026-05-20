#!/usr/bin/env python3
"""List bot users who started but never accepted terms (AMS shop_bot.db).

Usage on AMS:
  python3 /tmp/probe_terms_stuck_users.py /opt/remna-shop/data/shop_bot.db

From workstation (SSH):
  scp ops/probe_terms_stuck_users.py bvpn-ams:/tmp/
  ssh bvpn-ams python3 /tmp/probe_terms_stuck_users.py /opt/remna-shop/data/shop_bot.db
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def main() -> int:
    db = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/remna-shop/data/shop_bot.db")
    if not db.is_file():
        print(f"DB not found: {db}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    stuck = conn.execute(
        """
        SELECT u.telegram_id, u.username,
               (SELECT MAX(ua.created_at) FROM user_actions ua
                WHERE ua.user_id = u.telegram_id AND ua.action = 'funnel_bot_start') AS last_start
        FROM users u
        WHERE COALESCE(u.agreed_to_terms, 0) = 0
          AND u.telegram_id > 0
        """
    ).fetchall()

    # SQLite NULLS LAST — emulate
    rows = [dict(r) for r in stuck]
    rows.sort(key=lambda r: (r.get("last_start") or "", r["telegram_id"]), reverse=True)

    print(f"TERMS_NOT_ACCEPTED count={len(rows)}")
    for r in rows[:50]:
        print(
            f"  tid={r['telegram_id']} user=@{r.get('username') or '-'} "
            f"last_start={r.get('last_start') or 'never'}"
        )
    if len(rows) > 50:
        print(f"  ... and {len(rows) - 50} more")

    # Users who clicked start recently (7d) but no terms — best broadcast candidates
    recent = conn.execute(
        """
        SELECT COUNT(DISTINCT u.telegram_id)
        FROM users u
        JOIN user_actions ua ON ua.user_id = u.telegram_id
        WHERE COALESCE(u.agreed_to_terms, 0) = 0
          AND ua.action = 'funnel_bot_start'
          AND ua.created_at >= datetime('now', '-7 days')
        """
    ).fetchone()[0]
    print(f"TERMS_STUCK_WITH_START_7D={recent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
