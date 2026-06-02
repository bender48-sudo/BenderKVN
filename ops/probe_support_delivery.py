#!/usr/bin/env python3
"""Check whether bot can reach a user (getChat + optional test ping)."""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT_TOKEN_PATH = ROOT / ".secrets" / "bot-token.txt"


def _api(token: str, method: str, payload: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("telegram_id", type=int)
    ap.add_argument("--token-file", default=str(BOT_TOKEN_PATH))
    ap.add_argument("--ping", action="store_true", help="Send a short test message")
    args = ap.parse_args()

    token = Path(args.token_file).read_text(encoding="ascii").strip()
    tid = args.telegram_id

    chat = _api(token, "getChat", {"chat_id": tid})
    if not chat.get("ok"):
        print(f"GET_CHAT_FAIL tid={tid} {chat.get('description', chat)}", file=sys.stderr)
        return 1
    c = chat["result"]
    print(f"GET_CHAT_OK tid={tid} type={c.get('type')} username={c.get('username')}")
    if c.get("has_private_forwards") is not None:
        print(f"  has_private_forwards={c.get('has_private_forwards')}")

    if args.ping:
        data = _api(
            token,
            "sendMessage",
            {
                "chat_id": tid,
                "text": "🔔 Тест доставки от BenderVPN (можно не отвечать).",
            },
        )
        if data.get("ok"):
            print(f"SEND_PING_OK tid={tid} message_id={data['result'].get('message_id')}")
        else:
            print(f"SEND_PING_FAIL tid={tid} {data.get('description', data)}", file=sys.stderr)
            return 1
    print("PROBE_SUPPORT_DELIVERY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
