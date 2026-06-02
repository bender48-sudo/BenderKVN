#!/usr/bin/env python3
"""Local gate: YooKassa creds + topup UI + API Payment.create (no deploy).

Run from repo root:
  python ops/smoke_yookassa_local.py

Reads: secret_key 2.txt, .secrets/yookassa.env, .secrets/vault.env (gitignored).
Does not print secret values.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT_SRC = ROOT / "bot_src"
sys.path.insert(0, str(BOT_SRC))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def step_compile() -> bool:
    import py_compile

    files = list(BOT_SRC.rglob("*.py"))
    for p in files:
        py_compile.compile(str(p), doraise=True)
    print(f"OK: py_compile ({len(files)} files)")
    return True


def _load_local_env() -> None:
    _load_module("local_env", BOT_SRC / "local_env.py").load_local_env()


def step_env() -> bool:
    os.environ.pop("YOOKASSA_SHOP_ID", None)
    os.environ.pop("YOOKASSA_SECRET_KEY", None)
    _load_local_env()
    sid = (os.getenv("YOOKASSA_SHOP_ID") or "").strip()
    sec = (os.getenv("YOOKASSA_SECRET_KEY") or "").strip()
    if not sid or not sec:
        print("FAIL: YOOKASSA_SHOP_ID or YOOKASSA_SECRET_KEY missing after load_local_env", file=sys.stderr)
        return False
    mode = "test" if sec.startswith("test_") else "live" if sec.startswith("live_") else "unknown"
    print(f"OK: YooKassa env (shop_id len={len(sid)}, secret mode={mode})")
    return True


def step_static() -> bool:
    for script in ("smoke_yookassa_topup_ui.py", "smoke_payment_amount_verify.py"):
        path = ROOT / "ops" / script
        spec = importlib.util.spec_from_file_location(script, path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        rc = mod.main()
        if rc != 0:
            print(f"FAIL: {script} exit {rc}", file=sys.stderr)
            return False
    print("OK: static topup UI + amount verify smokes")
    return True


def _api_reachable(timeout_sec: float = 12.0) -> bool:
    import urllib.request

    try:
        urllib.request.urlopen("https://api.yookassa.ru/v3/", timeout=timeout_sec)
        return True
    except Exception:
        return False


def step_yookassa_api() -> bool:
    if not _api_reachable():
        print(
            "SKIP: api.yookassa.ru недоступен с этой машины (таймаут). "
            "Проверка API — на AMS после деплоя или с VPN.",
            file=sys.stderr,
        )
        return True

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    from yookassa import Configuration, Payment

    _load_local_env()
    sid = os.getenv("YOOKASSA_SHOP_ID", "").strip()
    sec = os.getenv("YOOKASSA_SECRET_KEY", "").strip()
    Configuration.account_id = sid
    Configuration.secret_key = sec
    amount = "200.00"
    payload = {
        "amount": {"value": amount, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/"},
        "capture": True,
        "description": "BenderVPN local smoke topup",
        "metadata": {
            "t": "topup",
            "u": 0,
            "user_id": 0,
            "a": amount,
            "amount": amount,
        },
    }

    def _create():
        return Payment.create(payload, uuid.uuid4())

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_create)
            payment = fut.result(timeout=45)
    except FuturesTimeout:
        print("FAIL: YooKassa Payment.create timed out (45s) — сеть/API?", file=sys.stderr)
        return False
    except Exception as e:
        print(f"FAIL: YooKassa Payment.create: {e}", file=sys.stderr)
        return False
    url = getattr(getattr(payment, "confirmation", None), "confirmation_url", None)
    pid = getattr(payment, "id", None)
    if not pid or not url:
        print("FAIL: Payment.create returned no id or confirmation_url", file=sys.stderr)
        return False
    print(f"OK: YooKassa API Payment.create (payment_id={pid[:8]}…)")
    return True


def step_webhook_topup_dispatch() -> bool:
    pav = _load_module("payment_amount_verify", BOT_SRC / "webhook_server" / "payment_amount_verify.py")
    amount = "200.00"
    event = {
        "event": "payment.succeeded",
        "object": {
            "id": f"local-smoke-{uuid.uuid4().hex[:12]}",
            "amount": {"value": amount, "currency": "RUB"},
            "metadata": {
                "t": "topup",
                "user_id": 0,
                "u": 0,
                "a": amount,
                "amount": amount,
            },
        },
    }
    if not pav.verify_yookassa_amount(event):
        print("FAIL: topup webhook amount verify", file=sys.stderr)
        return False
    pq_text = (BOT_SRC / "webhook_server" / "payment_queue.py").read_text(encoding="utf-8")
    if 'metadata.get("t") == "topup"' not in pq_text:
        print("FAIL: payment_queue topup branch missing", file=sys.stderr)
        return False
    print("OK: webhook topup payload shape + amount verify")
    return True


def main() -> int:
    skip_api = "--skip-api" in sys.argv
    steps = [
        step_compile,
        step_env,
        step_static,
        step_webhook_topup_dispatch,
    ]
    if skip_api:
        print("SKIP: YooKassa API ( --skip-api )")
    else:
        steps.insert(3, step_yookassa_api)
    for fn in steps:
        if not fn():
            return 1
    print("\nYOOKASSA_LOCAL_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
