#!/usr/bin/env python3
"""P3-FLOW-07: FAQ / onboarding / portal — one truth about live payments."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = (
    ROOT / "docs" / "FAQ.md",
    ROOT / "docs" / "ONBOARDING.md",
    ROOT / "web" / "portal" / "content" / "ru.json",
    ROOT / "bot_src" / "config.py",
)

FORBIDDEN = (
    "оплата не подключена",
    "оплата недоступна",
    "ожидание кассы",
    "до оплаты и поддержки",
    "когда доступен)",
)

REQUIRED_ANY = (
    ("Telegram Stars", "⭐"),
    ("6,67", "6.67"),
    ("Пополнить баланс", "пополнение баланса"),
)


def main() -> int:
    blob = ""
    for path in FILES:
        if not path.is_file():
            print(f"PAYMENT_COPY_SYNC_FAIL: missing {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
        blob += text + "\n"
        for bad in FORBIDDEN:
            if bad.lower() in text.lower():
                print(f"PAYMENT_COPY_SYNC_FAIL: forbidden {bad!r} in {path.name}", file=sys.stderr)
                return 1

    for group in REQUIRED_ANY:
        if not any(g in blob for g in group):
            print(f"PAYMENT_COPY_SYNC_FAIL: missing any of {group}", file=sys.stderr)
            return 1

    ru = json.loads((ROOT / "web" / "portal" / "content" / "ru.json").read_text(encoding="utf-8"))
    hint = (ru.get("cabinet") or {}).get("balance_hint", "")
    if "Stars" not in hint and "пополн" not in hint.lower():
        print("PAYMENT_COPY_SYNC_FAIL: ru.json cabinet.balance_hint stale", file=sys.stderr)
        return 1

    print("PAYMENT_COPY_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
