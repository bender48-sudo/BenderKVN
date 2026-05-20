#!/usr/bin/env python3
"""Send fresh /start terms message with inline «Принимаю» button to specific user(s)."""
from __future__ import annotations

import argparse
import json
import sqlite3
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT_TOKEN_PATH = ROOT / ".secrets" / "bot-token.txt"


def _post(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _terms_urls(db: Path) -> tuple[str, str]:
    conn = sqlite3.connect(db)
    terms = conn.execute(
        "SELECT value FROM bot_settings WHERE key='terms_url'"
    ).fetchone()
    privacy = conn.execute(
        "SELECT value FROM bot_settings WHERE key='privacy_url'"
    ).fetchone()
    conn.close()
    if not terms or not privacy:
        raise RuntimeError("terms_url or privacy_url missing in bot_settings")
    return terms[0], privacy[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("telegram_ids", nargs="+", type=int)
    ap.add_argument("--db", default=str(ROOT / ".secrets" / "shop_bot_probe.db"))
    ap.add_argument("--token-file", default=str(BOT_TOKEN_PATH))
    args = ap.parse_args()

    token = Path(args.token_file).read_text(encoding="ascii").strip()
    terms_url, privacy_url = _terms_urls(Path(args.db))

    text = (
        "<b>Добро пожаловать!</b>\n\n"
        "Перед началом использования бота, пожалуйста, ознакомьтесь и примите наши "
        f"<a href='{terms_url}'>Условия использования</a> и "
        f"<a href='{privacy_url}'>Политику конфиденциальности</a>.\n\n"
        "Нажмите кнопку <b>«Принимаю»</b> на этом сообщении "
        "(не на старых — они могли устареть после обновления бота)."
    )
    keyboard = {
        "inline_keyboard": [[{"text": "✅ Принимаю", "callback_data": "agree_to_terms"}]]
    }

    for tid in args.telegram_ids:
        data = _post(
            token,
            "sendMessage",
            {
                "chat_id": tid,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": keyboard,
            },
        )
        if data.get("ok"):
            print(f"TERMS_PROMPT_OK tid={tid}")
        else:
            print(f"TERMS_PROMPT_FAIL tid={tid} {data}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
