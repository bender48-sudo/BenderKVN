#!/usr/bin/env python3
"""AMS read-only helper for LIVE-TERMS-UX-SMOKE-001 (owner-assisted).

Default: structural billing-guard checks only (no charges, no autopay batch).
Optional: `--check-user` reads agreed_to_terms / trial_used / balance for one
Telegram user ID passed via env ``BVPN_TERMS_SMOKE_TG_ID`` (never printed).

Owner must perform Telegram taps manually; this script verifies DB markers only.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def _bool_env(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def smoke_structural() -> bool:
    """Reuse deployed smoke when run inside remna-shop-bot container."""
    try:
        from smoke_billing_guards_ams import main as structural_main
    except ImportError:
        print("FAIL: smoke_billing_guards_ams not importable", file=sys.stderr)
        return False
    return structural_main() == 0


def _db_path() -> Path:
    raw = (os.getenv("SHOP_BOT_DB_PATH") or "/app/data/shop_bot.db").strip()
    return Path(raw)


def check_user_state() -> bool:
    tg_raw = (os.getenv("BVPN_TERMS_SMOKE_TG_ID") or "").strip()
    if not tg_raw.isdigit():
        print("SKIP: BVPN_TERMS_SMOKE_TG_ID not set (owner DB check skipped)")
        return True
    tg_id = int(tg_raw)
    db = _db_path()
    if not db.is_file():
        print(f"FAIL: DB not found at configured path", file=sys.stderr)
        return False
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT agreed_to_terms, trial_used, balance, yookassa_autopay_enabled "
            "FROM users WHERE telegram_id = ?",
            (tg_id,),
        ).fetchone()
        if row is None:
            print("USER_ROW=missing")
            return False
        agreed, trial_used, balance, autopay = row
        print(f"USER_CHECK agreed_to_terms={bool(agreed)} trial_used={bool(trial_used)}")
        print(f"USER_CHECK balance_present={balance is not None} autopay_enabled={bool(autopay)}")
        recent_pay_actions = conn.execute(
            "SELECT COUNT(*) FROM user_actions WHERE user_id = ? AND action LIKE '%pay%'",
            (tg_id,),
        ).fetchone()
        cnt = int(recent_pay_actions[0]) if recent_pay_actions else 0
        print(f"USER_CHECK payment_action_rows={cnt}")
        return True
    finally:
        conn.close()


def print_owner_matrix() -> None:
    print("OWNER_MANUAL_CASES:")
    print("  CASE-1 Unaccepted trial: tap get_trial → expect terms; no key/trial_used")
    print("  CASE-2 Unaccepted topup: tap balance/top-up → terms; no payment URL")
    print("  CASE-3 Unaccepted autorenew enable → terms; no bind payment")
    print("  CASE-4 Stale promo/wizard → terms before flow")
    print("  CASE-5 Accept terms then trial/topup → pass guard; STOP before pay/provision")
    print("  CASE-6 Disable autorenew (accepted user) → no terms re-prompt")
    print("Set BVPN_TERMS_SMOKE_TG_ID=<owner test account> then re-run with --check-user")


def main() -> int:
    parser = argparse.ArgumentParser(description="AMS live terms guard smoke helper")
    parser.add_argument(
        "--check-user",
        action="store_true",
        help="Read-only user row check (requires BVPN_TERMS_SMOKE_TG_ID env)",
    )
    parser.add_argument(
        "--owner-matrix",
        action="store_true",
        help="Print owner manual smoke steps",
    )
    args = parser.parse_args()

    if args.owner_matrix:
        print_owner_matrix()
        return 0

    ok = smoke_structural()
    if args.check_user:
        ok = check_user_state() and ok

    payments_live = _bool_env("BOT_PAYMENTS_LIVE")
    print(f"BOT_PAYMENTS_LIVE={'true' if payments_live else 'false'}")
    if payments_live:
        print("NOTE: autopay batch and live payment smokes must NOT run")

    if ok:
        print("LIVE_TERMS_GUARD_AMS_HELPER_OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
