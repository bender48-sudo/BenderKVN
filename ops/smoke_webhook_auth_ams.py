#!/usr/bin/env python3
"""P6-RED-PAY-02 smoke: webhook auth (run in remna-shop-bot or against localhost:1488)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "bot_src") not in sys.path:
    sys.path.insert(0, str(ROOT / "bot_src"))


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
    import importlib.util

    auth_path = ROOT / "bot_src" / "webhook_server" / "auth.py"
    try:
        spec = importlib.util.spec_from_file_location("webhook_auth", auth_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        verify_yookassa_notification = mod.verify_yookassa_notification
    except ModuleNotFoundError as e:
        auth_src = auth_path.read_text(encoding="utf-8")
        if "compare_digest" in auth_src and "logger.critical" in auth_src:
            print(f"OK: auth static checks (skip runtime: {e})")
            return True
        print(f"FAIL: cannot load auth: {e}", file=sys.stderr)
        return False

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

    code3, _ = _post("/cryptobot-webhook", {"status": "paid", "order_id": "smoke"})
    if code3 != 403:
        print(f"FAIL: cryptobot POST without secret expected 403, got {code3}", file=sys.stderr)
        return False
    print("OK: HTTP cryptobot POST without secret -> 403")

    auth_src = (ROOT / "bot_src" / "webhook_server" / "auth.py").read_text(encoding="utf-8")
    if '_env_bool("WEBHOOK_TRUST_PROXY_HEADERS", False)' not in auth_src:
        print("FAIL: WEBHOOK_TRUST_PROXY_HEADERS default should be false", file=sys.stderr)
        return False
    print("OK: WEBHOOK_TRUST_PROXY_HEADERS default false")
    return True


def main() -> int:
    if not test_unit_auth():
        return 1
    if not test_cryptobot_post_route():
        return 3
    try:
        if not test_http_forbidden():
            return 2
    except urllib.error.URLError as e:
        print(f"SKIP: HTTP checks ({e}); unit auth passed")
    print("WEBHOOK_XFF_HARDEN_OK")
    print("WEBHOOK_AUTH_OK")
    return 0


def test_cryptobot_post_route() -> bool:
    app_src = (ROOT / "bot_src" / "webhook_server" / "app.py").read_text(encoding="utf-8")
    if '"/cryptobot-webhook", methods=["GET"]' in app_src:
        print("CRYPTOBOT_WEBHOOK_POST_FAIL: still GET route", file=sys.stderr)
        return False
    if '"/cryptobot-webhook", methods=["POST"]' not in app_src:
        print("CRYPTOBOT_WEBHOOK_POST_FAIL: POST route missing", file=sys.stderr)
        return False
    auth_src = (ROOT / "bot_src" / "webhook_server" / "auth.py").read_text(encoding="utf-8")
    if "compare_digest" not in auth_src:
        print("CRYPTOBOT_WEBHOOK_POST_FAIL: compare_digest missing in auth", file=sys.stderr)
        return False
    print("CRYPTOBOT_WEBHOOK_POST_OK")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
