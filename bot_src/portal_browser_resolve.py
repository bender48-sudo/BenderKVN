"""Resolve subscription URL for browser setup (no Telegram client)."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys

import aiohttp

from shop_bot.data_manager.database import lookup_telegram_ids_by_hint
from shop_bot.modules import remnawave_api

logger = logging.getLogger(__name__)

_NUMERIC_RE = re.compile(r"^\d{5,15}$")


async def _panel_sub_url(telegram_id: int) -> str | None:
    async with aiohttp.ClientSession() as session:
        user_data = await remnawave_api.get_user_by_telegram_id(session, str(telegram_id))
        if not user_data:
            return None
        return (user_data.get("subscriptionUrl") or "").strip() or None


async def resolve_browser_setup(
    *,
    username: str = "",
    telegram_id: int | None = None,
) -> dict:
    """
    Returns dict with ok, error code, sub_url, telegram_id, username (display).
    Does not provision new keys — only existing panel subscription.
    """
    tid = telegram_id
    display_name = ""

    if tid is None and username:
        hint = username.strip()
        if _NUMERIC_RE.match(hint.lstrip("@")):
            tid = int(hint.lstrip("@"))
        else:
            matches = lookup_telegram_ids_by_hint(hint, limit=5)
            if not matches:
                return {
                    "ok": False,
                    "error": "user_not_found",
                    "message": "Аккаунт не найден. Сначала откройте бота и нажмите /start.",
                }
            if len(matches) > 1:
                names = ", ".join(
                    f"@{m['username']}" if m.get("username") else str(m["telegram_id"])
                    for m in matches[:3]
                )
                return {
                    "ok": False,
                    "error": "ambiguous",
                    "message": f"Найдено несколько аккаунтов ({names}). Укажите точный @ник или Telegram ID.",
                }
            tid = int(matches[0]["telegram_id"])
            display_name = matches[0].get("username") or ""

    if tid is None:
        return {
            "ok": False,
            "error": "missing_hint",
            "message": "Укажите @ник в Telegram или числовой Telegram ID.",
        }

    sub_url = await _panel_sub_url(tid)
    if not sub_url:
        return {
            "ok": False,
            "error": "no_subscription",
            "message": "Подписка не найдена. Откройте бота, получите trial или пополните баланс.",
            "telegram_id": tid,
        }

    return {
        "ok": True,
        "telegram_id": tid,
        "username": display_name,
        "sub_url": sub_url,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Browser setup resolve (JSON stdout)")
    ap.add_argument("--username", default="")
    ap.add_argument("--telegram-id", type=int, default=0)
    args = ap.parse_args()
    tid = args.telegram_id if args.telegram_id else None
    doc = asyncio.run(
        resolve_browser_setup(username=args.username, telegram_id=tid)
    )
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
