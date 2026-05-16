"""Mass broadcast to all panel users via the Telegram bot.

Reads:
  - .secrets/bot-token.txt — Telegram Bot API token
  - .secrets/panel-token.txt — Remnawave panel API token

Modes:
  --dry-run    (default)  print recipients, do not send
  --test-admin            send only to ADMIN_TELEGRAM_ID
  --apply                 send to every active user with telegramId

Output:
  .secrets/broadcasts/<timestamp>.csv with one row per recipient.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PANEL_TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
BOT_TOKEN = (ROOT / ".secrets" / "bot-token.txt").read_text(encoding="ascii").strip()
ADMIN_ID = 924498094

PANEL_BASE = site_urls.PANEL_URL
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

MESSAGE_HTML = (
    "🛠 <b>Исправили конфигурацию на нашей стороне</b> (ошибка Xray после обновления маршрутизации).\n"
    "\n"
    "<b>Важно:</b> откройте ваш VPN-клиент и <b>обновите подписку</b> (pull / refresh), затем "
    "<b>попробуйте подключиться снова.</b>\n"
    "\n"
    "<b>Happ:</b> у профиля «🚀 BenderVPN Auto» — кнопка 🔄 возле названия.\n"
    "<b>Streisand / Hiddify / v2rayN и др.</b> — в меню подписки выберите «обновить» / "
    "\"Update subscription\".\n"
    "\n"
    "Если после обновления всё ещё ошибка — напишите в поддержку.\n"
    "Спасибо за терпение!"
)

# Conservative — Telegram allows ~30 msg/s to different chats.
RATE_PER_SEC = 20


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def panel_get(path: str) -> dict:
    req = urllib.request.Request(PANEL_BASE + path)
    req.add_header("Authorization", f"Bearer {PANEL_TOKEN}")
    with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def list_users() -> list[dict]:
    out: list[dict] = []
    size = 100
    start = 0
    while True:
        page = panel_get(f"/api/users?size={size}&start={start}")
        items = page.get("response", {}).get("users", [])
        out.extend(items)
        total = page.get("response", {}).get("total", len(out))
        start += size
        if start >= total or not items:
            break
    return out


def tg_send(chat_id: int, text: str) -> tuple[int, str]:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{TG_BASE}/sendMessage",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--test-admin", action="store_true", help="Send only to ADMIN_TELEGRAM_ID")
    group.add_argument("--apply", action="store_true", help="Send to every eligible user")
    ap.add_argument("--include-expired", action="store_true", help="Don't filter by status")
    args = ap.parse_args()

    print("# message preview ---")
    print(MESSAGE_HTML)
    print("# --- end preview\n")

    users = list_users()
    print(f"# panel users total: {len(users)}")

    def eligible(u: dict) -> bool:
        if not u.get("telegramId"):
            return False
        status = u.get("status")
        if not args.include_expired and status and status != "ACTIVE":
            return False
        return True

    eligible_users = [u for u in users if eligible(u)]
    skipped = len(users) - len(eligible_users)
    print(f"# eligible (telegramId + ACTIVE): {len(eligible_users)}; skipped: {skipped}")

    by_status: dict[str, int] = {}
    for u in users:
        by_status[u.get("status", "?")] = by_status.get(u.get("status", "?"), 0) + 1
    print(f"# by status: {by_status}")

    if not args.test_admin and not args.apply:
        print("\n# dry-run; first 15 recipients:")
        for u in eligible_users[:15]:
            print(f"  {u.get('telegramId')!s:>14} | {u.get('username')!r}")
        print("\n# rerun with --test-admin to send to admin only, or --apply for everyone")
        return

    if args.test_admin:
        targets = [{"telegramId": ADMIN_ID, "username": "admin"}]
    else:
        targets = eligible_users

    log_dir = ROOT / ".secrets" / "broadcasts"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{ts}.csv"
    print(f"# log: {log_path}")

    ok = fail = 0
    interval = 1.0 / RATE_PER_SEC
    with log_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["telegramId", "username", "status_code", "response"])
        for i, u in enumerate(targets, 1):
            tg_id = u["telegramId"]
            uname = u.get("username", "")
            t0 = time.monotonic()
            code, body = tg_send(int(tg_id), MESSAGE_HTML)
            # Handle Telegram 429 retry_after
            if code == 429:
                try:
                    j = json.loads(body)
                    retry = float(j.get("parameters", {}).get("retry_after", 5))
                except Exception:
                    retry = 5.0
                print(f"  [{i}/{len(targets)}] 429 retry in {retry:.1f}s")
                time.sleep(retry + 0.5)
                code, body = tg_send(int(tg_id), MESSAGE_HTML)
            mark = "OK" if code == 200 else f"ERR {code}"
            print(f"  [{i}/{len(targets)}] {tg_id:>14} {uname!r:30} {mark}")
            w.writerow([tg_id, uname, code, body[:300]])
            if code == 200:
                ok += 1
            else:
                fail += 1
            elapsed = time.monotonic() - t0
            sleep_for = interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    print(f"\nsent OK: {ok} ; failed: {fail}")


if __name__ == "__main__":
    main()
