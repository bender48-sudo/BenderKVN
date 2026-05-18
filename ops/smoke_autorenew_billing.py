#!/usr/bin/env python3
"""P6-RED-PAY-03: auto-renew must deduct balance before provision_key."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"


def main() -> int:
    scheduler = (BOT / "scheduler.py").read_text(encoding="utf-8")
    db_py = (BOT / "database.py").read_text(encoding="utf-8")

    for needle in (
        "try_deduct_balance",
        "auto_renew_skip",
        "balance_covers_renew",
        "plan_renew_cost",
    ):
        if needle not in scheduler:
            print(f"AUTO_RENEW_BILLING_FAIL: scheduler missing {needle!r}", file=sys.stderr)
            return 1

    if "def try_deduct_balance" not in db_py:
        print("AUTO_RENEW_BILLING_FAIL: database.try_deduct_balance missing", file=sys.stderr)
        return 1

    idx_deduct = scheduler.find("try_deduct_balance")
    idx_prov = scheduler.find("provision_key", idx_deduct)
    if idx_deduct < 0 or idx_prov < 0 or idx_deduct > idx_prov:
        print(
            "AUTO_RENEW_BILLING_FAIL: try_deduct_balance must appear before provision_key",
            file=sys.stderr,
        )
        return 1

    if "add_balance(user_id, cost_rub)" not in scheduler:
        print("AUTO_RENEW_BILLING_FAIL: refund on provision fail missing", file=sys.stderr)
        return 1

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "auto_renew_billing", BOT / "auto_renew_billing.py"
    )
    arb = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    cfg_spec = importlib.util.spec_from_file_location("config", BOT / "config.py")
    cfg = importlib.util.module_from_spec(cfg_spec)
    assert cfg_spec and cfg_spec.loader
    cfg_spec.loader.exec_module(cfg)
    import sys as _sys

    _sys.modules["shop_bot"] = type(_sys)("shop_bot")
    _sys.modules["shop_bot.config"] = cfg
    spec.loader.exec_module(arb)

    cost, months, days = arb.plan_renew_cost("buy_1_month")
    if months != 1 or days != 30 or cost <= 0:
        print(f"AUTO_RENEW_BILLING_FAIL: bad plan cost {cost=} {months=} {days=}", file=sys.stderr)
        return 1
    if arb.balance_covers_renew(199.0, cost) or not arb.balance_covers_renew(cost, cost):
        print("AUTO_RENEW_BILLING_FAIL: balance_covers_renew logic", file=sys.stderr)
        return 1

    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)"
        )
        conn.execute("INSERT INTO users (telegram_id, balance) VALUES (1, 100)")
        conn.commit()

        def _try_deduct(uid: int, amount: float) -> bool:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET balance = COALESCE(balance, 0) - ? "
                "WHERE telegram_id = ? AND COALESCE(balance, 0) >= ?",
                (amount, uid, amount),
            )
            conn.commit()
            return cur.rowcount > 0

        def _balance(uid: int) -> float:
            row = conn.execute(
                "SELECT balance FROM users WHERE telegram_id = ?", (uid,)
            ).fetchone()
            return float(row[0]) if row else 0.0

        if _try_deduct(1, 200):
            print("AUTO_RENEW_BILLING_FAIL: deduct should fail on low balance", file=sys.stderr)
            return 1
        if not _try_deduct(1, 50):
            print("AUTO_RENEW_BILLING_FAIL: deduct should succeed", file=sys.stderr)
            return 1
        if _balance(1) != 50.0:
            print("AUTO_RENEW_BILLING_FAIL: balance after deduct", file=sys.stderr)
            return 1
    finally:
        conn.close()

    print("AUTO_RENEW_BILLING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
