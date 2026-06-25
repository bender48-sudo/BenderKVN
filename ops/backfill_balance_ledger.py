#!/usr/bin/env python3
"""One-time, idempotent backfill of balance_ledger from user_actions (REF-LEDGER-001).

Copies existing money moves into the new journal so /portal-transactions can later switch its
source to balance_ledger without losing history:

  * action='topup', numeric meta            -> kind='topup'        ref='legacy:topup:<action_id>'  (+)
  * action LIKE 'daily_balance:%', numeric  -> kind='daily_charge' ref='daily:<DATE>'              (-)
  * meta 'insufficient' / 'waived_topup'    -> skipped (not a money move)
  * idempotency rows 'yk:' / 'crypto:'      -> skipped (dup of the topup)

balance_after_kopeks is left NULL for backfilled rows (historic running balance is unknown — an
honest NULL beats a guessed number). Idempotent: stable refs + the UNIQUE(user_id, ref) index
mean re-running inserts nothing new. Does NOT mutate users.balance. Read-only w.r.t. wallets.

Run on staging first:  SHOP_BOT_DB_PATH=/path/staging.db python ops/backfill_balance_ledger.py
Add --dry-run to only report what would be inserted.
"""
from __future__ import annotations

import argparse
import importlib
import sqlite3
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"
if str(BOT) not in sys.path:
    sys.path.insert(0, str(BOT))


def _bootstrap_shop_bot() -> None:
    """Register the shop_bot package alias so bot_src modules import cleanly when run standalone."""
    if "shop_bot" not in sys.modules:
        pkg = types.ModuleType("shop_bot")
        pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
        sys.modules["shop_bot"] = pkg
    if "shop_bot.data_manager" not in sys.modules:
        dm = types.ModuleType("shop_bot.data_manager")
        sys.modules["shop_bot.data_manager"] = dm
        sys.modules["shop_bot"].data_manager = dm  # type: ignore[attr-defined]
    if "shop_bot.data_manager.database" not in sys.modules:
        database = importlib.import_module("database")
        sys.modules["shop_bot.data_manager.database"] = database
        sys.modules["shop_bot.data_manager"].database = database  # type: ignore[attr-defined]


def _amount_kopeks(meta: str | None) -> int | None:
    try:
        rub = float(meta)
    except (TypeError, ValueError):
        return None
    if rub <= 0:
        return None
    return round(rub * 100)


def backfill(conn: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, user_id, action, meta, created_at FROM user_actions "
        "WHERE action = 'topup' OR action LIKE 'daily_balance:%' ORDER BY id ASC"
    ).fetchall()

    inserted = {"topup": 0, "daily_charge": 0}
    skipped = 0
    for r in rows:
        action = (r["action"] or "").strip()
        kopeks = _amount_kopeks(r["meta"])
        if kopeks is None:  # insufficient / waived_topup / non-numeric
            skipped += 1
            continue
        if action == "topup":
            kind, amount, ref = "topup", kopeks, f"legacy:topup:{r['id']}"
        elif action.startswith("daily_balance:"):
            date = action.split(":", 1)[1]
            kind, amount, ref = "daily_charge", -kopeks, f"daily:{date}"
        else:
            skipped += 1
            continue
        if dry_run:
            inserted[kind] += 1
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO balance_ledger "
            "(user_id, kind, amount_kopeks, balance_after_kopeks, ref, meta, created_at_utc) "
            "VALUES (?, ?, ?, NULL, ?, ?, ?)",
            (r["user_id"], kind, amount, ref, "backfill", r["created_at"]),
        )
        if cur.rowcount > 0:
            inserted[kind] += 1
    if not dry_run:
        conn.commit()
    return {"inserted": inserted, "skipped": skipped, "scanned": len(rows)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    _bootstrap_shop_bot()
    from shop_bot.data_manager.database import db_connection  # type: ignore
    from shop_bot.schema_migrations import run_schema_migrations  # type: ignore

    with db_connection() as conn:
        run_schema_migrations(conn)  # ensure balance_ledger (v8) exists
        result = backfill(conn, dry_run=args.dry_run)

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(
        f"[{mode}] scanned={result['scanned']} "
        f"topup+={result['inserted']['topup']} "
        f"daily+={result['inserted']['daily_charge']} skipped={result['skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
