#!/usr/bin/env python3
"""Post-deploy smoke for billing guards (AMS remna-shop-bot). No live charges."""
from __future__ import annotations

import inspect
import sys
from datetime import datetime


def smoke_legal() -> bool:
    from shop_bot.data_manager.database import get_setting

    stub = "не установлена"
    terms = get_setting("terms_url") or ""
    privacy = get_setting("privacy_url") or ""
    support = get_setting("support_user") or ""
    ok = bool(terms and privacy and support and stub not in terms and stub not in privacy)
    print(f"LEGAL_OK={ok}")
    return ok


def smoke_webhook_claim() -> bool:
    from shop_bot.data_manager.database import claim_webhook_delivery, mark_webhook_done

    key = f"smoke_bill_guard_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    s1 = claim_webhook_delivery(key, "smoke", "{}")
    s2 = claim_webhook_delivery(key, "smoke", "{}")
    if s1 != "new" or s2 not in ("in_progress", "duplicate"):
        print(f"FAIL: claim s1={s1} s2={s2}", file=sys.stderr)
        return False
    mark_webhook_done(key)
    s3 = claim_webhook_delivery(key, "smoke", "{}")
    if s3 != "duplicate":
        print(f"FAIL: after done expected duplicate, got {s3}", file=sys.stderr)
        return False
    print("OK: webhook claim atomic")
    return True


def smoke_autopay_guard() -> bool:
    from shop_bot.config import BOT_PAYMENTS_LIVE
    from shop_bot.yookassa_autopay_scheduler import run_yookassa_autopay_batch

    src = inspect.getsource(run_yookassa_autopay_batch)
    if "BOT_PAYMENTS_LIVE" not in src or "return 0" not in src:
        print("FAIL: autopay guard missing in scheduler", file=sys.stderr)
        return False
    print(f"OK: autopay guard present (BOT_PAYMENTS_LIVE={BOT_PAYMENTS_LIVE})")
    return True


def smoke_handlers_guard() -> bool:
    from pathlib import Path

    p = Path("/app/src/shop_bot/bot/handlers.py")
    text = p.read_text(encoding="utf-8")
    if "_ensure_terms_callback" not in text or text.count("_ensure_terms_callback") < 10:
        print("FAIL: terms callback guard missing in handlers", file=sys.stderr)
        return False
    if "set_trial_used(user_id)" not in text:
        print("FAIL: trial atomic marker missing", file=sys.stderr)
        return False
    print("OK: handlers terms/trial guard markers present")
    return True


def main() -> int:
    ok = all(
        [
            smoke_legal(),
            smoke_webhook_claim(),
            smoke_autopay_guard(),
            smoke_handlers_guard(),
        ]
    )
    if ok:
        print("BILLING_GUARDS_SMOKE_OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
