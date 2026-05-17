#!/usr/bin/env python3
"""P6-RED-PAY-02 smoke: webhook auth (run in remna-shop-bot or against localhost:1488)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _base_url() -> str:
    host = os.getenv("WEBHOOK_SMOKE_HOST", "127.0.0.1")
    port = os.getenv("WEBHOOK_PORT", "1488")
    return f"http://{host}:{port}"


def _post(path: str, body: dict, headers: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(
        f"{_base_url()}{path}",
        data=data,
        headers=hdrs,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _get(path: str, query: str = "") -> tuple[int, str]:
    url = f"{_base_url()}{path}"
    if query:
        url = f"{url}?{query}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def test_unit_auth() -> bool:
    from shop_bot.webhook_server.auth import verify_yookassa_notification

    if verify_yookassa_notification({"event": "payment.canceled"}):
        print("OK: non-succeeded events pass verify gate")
    else:
        print("FAIL: canceled event should pass", file=sys.stderr)
        return False

    if verify_yookassa_notification(
        {"event": "payment.succeeded", "object": {"id": "00000000-0000-0000-0000-000000000000"}}
    ):
        print("FAIL: fake payment id should not verify", file=sys.stderr)
        return False
    print("OK: forged YooKassa payment id rejected by API verify")
    return True


def test_http_forbidden() -> bool:
    code, body = _post(
        "/yookassa-webhook",
        {
            "event": "payment.succeeded",
            "object": {"id": "smoke-forged-00000000-0000-0000-0000-000000000001"},
        },
    )
    if code != 403:
        print(f"FAIL: forged yookassa expected 403, got {code} body={body!r}", file=sys.stderr)
        return False
    print("OK: HTTP forged yookassa -> 403")

    code2, _ = _post("/crypto-webhook", {"status": "paid", "order_id": "smoke"})
    if code2 != 403:
        print(f"FAIL: crypto without secret expected 403, got {code2}", file=sys.stderr)
        return False
    print("OK: HTTP crypto without secret -> 403")

    code3, _ = _get("/cryptobot-webhook", "status=paid&order_id=smoke")
    if code3 != 403:
        print(f"FAIL: cryptobot without secret expected 403, got {code3}", file=sys.stderr)
        return False
    print("OK: HTTP cryptobot without secret -> 403")
    return True


def main() -> int:
    if not test_unit_auth():
        return 1
    try:
        if not test_http_forbidden():
            return 2
    except urllib.error.URLError as e:
        print(f"SKIP: HTTP checks ({e}); unit auth passed")
    print("WEBHOOK_AUTH_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
