#!/usr/bin/env python3
"""One-off: message users who never accepted terms (stuck on «Принимаю»).

Reads AMS SQLite + .secrets/bot-token.txt. Default --dry-run.

  python ops/notify_terms_retry.py --dry-run
  python ops/notify_terms_retry.py --apply
  python ops/notify_terms_retry.py --apply --only-recent-days 7

On AMS:
  scp ops/notify_terms_retry.py bvpn-ams:/tmp/
  ssh bvpn-ams 'python3 /tmp/notify_terms_retry.py --db /opt/remna-shop/data/shop_bot.db --dry-run'
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT_TOKEN_PATH = ROOT / ".secrets" / "bot-token.txt"

MESSAGE_HTML = (
    "🛠 <b>Мы исправили кнопку «Принимаю»</b> в боте.\n\n"
    "Если у вас зависала «Загрузка…» — откройте бота и:\n"
    "• нажмите <b>Принимаю</b> ещё раз на старом сообщении, <b>или</b>\n"
    "• отправьте команду <b>/start</b>\n\n"
    "После этого откроется главное меню. Если не помогло — напишите в поддержку."
)

RATE_PER_SEC = 20


def _tg_send(chat_id: int, text: str, token: str) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        if data.get("ok"):
            return True, "ok"
        return False, str(data.get("description", data))[:200]
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
            desc = err.get("description", str(e))
        except Exception:
            desc = str(e)
        return False, desc[:200]
    except Exception as e:
        return False, str(e)[:200]


def _stuck_user_ids(conn: sqlite3.Connection, recent_days: int | None) -> list[int]:
    if recent_days and recent_days > 0:
        rows = conn.execute(
            """
            SELECT DISTINCT u.telegram_id
            FROM users u
            JOIN user_actions ua ON ua.user_id = u.telegram_id
            WHERE COALESCE(u.agreed_to_terms, 0) = 0
              AND u.telegram_id > 0
              AND ua.action = 'funnel_bot_start'
              AND ua.created_at >= datetime('now', printf('-%d days', ?))
            ORDER BY u.telegram_id
            """,
            (recent_days,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT u.telegram_id
            FROM users u
            WHERE COALESCE(u.agreed_to_terms, 0) = 0
              AND u.telegram_id > 0
              AND EXISTS (
                SELECT 1 FROM user_actions ua
                WHERE ua.user_id = u.telegram_id AND ua.action = 'funnel_bot_start'
              )
            ORDER BY u.telegram_id
            """
        ).fetchall()
    return [int(r[0]) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/opt/remna-shop/data/shop_bot.db")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test-admin", type=int, default=0, help="Send only to this telegram id")
    ap.add_argument("--only-recent-days", type=int, default=14)
    ap.add_argument("--token-file", default=str(BOT_TOKEN_PATH))
    args = ap.parse_args()

    db = Path(args.db)
    if not db.is_file():
        print(f"DB not found: {db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db)
    ids = _stuck_user_ids(conn, args.only_recent_days)
    print(f"TERMS_RETRY_CANDIDATES count={len(ids)} recent_days={args.only_recent_days}")

    if not args.apply:
        for tid in ids[:30]:
            print(f"  would_notify tid={tid}")
        if len(ids) > 30:
            print(f"  ... +{len(ids) - 30} more")
        print("TERMS_RETRY_DRY_RUN_OK (use --apply to send)")
        return 0

    token_path = Path(args.token_file)
    if not token_path.is_file():
        print(f"Missing bot token: {token_path}", file=sys.stderr)
        return 1
    token = token_path.read_text(encoding="ascii").strip()

    targets = [args.test_admin] if args.test_admin else ids
    ok_n = fail_n = 0
    for tid in targets:
        if tid <= 0:
            continue
        ok, detail = _tg_send(tid, MESSAGE_HTML, token)
        if ok:
            ok_n += 1
            print(f"OK tid={tid}")
        else:
            fail_n += 1
            print(f"FAIL tid={tid} {detail}", file=sys.stderr)
        time.sleep(1.0 / RATE_PER_SEC)

    print(f"TERMS_RETRY_SENT ok={ok_n} fail={fail_n}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
