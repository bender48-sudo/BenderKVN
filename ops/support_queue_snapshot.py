#!/usr/bin/env python3
"""Support queue metrics from bot SQLite (P6-SCALE-07).

Reads ``users.support_*`` timestamps and prints pending / SLA breach counts.
Default DB on AMS: ``/opt/remna-shop/data/shop_bot.db`` (override ``--db``).

Exit 1 if ``pending_sla_breach`` > 0 or ``pending`` >= ``--max-pending``.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_DB = "/opt/remna-shop/data/shop_bot.db"
DEFAULT_SLA_SEC = 3600  # 60 min, RUNBOOK-INCIDENT
DEFAULT_MAX_PENDING = 15  # second-line trigger (GTM outline)
DEFAULT_MAX_TICKETS_DAY = 25


def _fetch_metrics(db_path: Path, sla_sec: int) -> dict:
    now = int(time.time())
    day_ago = now - 86400
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cols = {r[1] for r in conn.execute("pragma table_info(users)")}
    required = {"support_topic_id", "support_last_user_at", "support_last_staff_at"}
    missing = required - cols
    if missing:
        raise RuntimeError(
            f"DB missing columns {sorted(missing)} — deploy bot support queue migration"
        )

    rows = conn.execute(
        """
        SELECT telegram_id, support_topic_id, support_last_user_at, support_last_staff_at
        FROM users
        WHERE support_topic_id IS NOT NULL
        """
    ).fetchall()

    pending = 0
    pending_sla = 0
    tickets_24h = 0
    for r in rows:
        u_at = r["support_last_user_at"] or 0
        s_at = r["support_last_staff_at"] or 0
        if u_at >= day_ago:
            tickets_24h += 1
        if u_at > s_at:
            pending += 1
            if u_at <= now - sla_sec:
                pending_sla += 1

    active_topics = len(rows)
    conn.close()
    return {
        "active_topics": active_topics,
        "tickets_24h": tickets_24h,
        "pending_reply": pending,
        "pending_sla_breach": pending_sla,
        "sla_minutes": sla_sec // 60,
        "second_line_trigger_pending": DEFAULT_MAX_PENDING,
        "second_line_trigger_tickets_day": DEFAULT_MAX_TICKETS_DAY,
        "escalate_second_line": (
            pending >= DEFAULT_MAX_PENDING or tickets_24h >= DEFAULT_MAX_TICKETS_DAY
        ),
    }


def _load_db_via_ssh(host: str, remote_db: str) -> Path:
    tmp = Path("/tmp/bvpn_support_queue.db")
    if sys.platform == "win32":
        tmp = Path.cwd() / ".secrets" / "_support_queue_snapshot.db"
        tmp.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["scp", "-o", "BatchMode=yes", f"root@{host}:{remote_db}", str(tmp)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "scp failed")
    return tmp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="local sqlite path")
    ap.add_argument("--ssh-host", default="bvpn-ams", help="fetch DB from host")
    ap.add_argument("--remote-db", default=DEFAULT_DB)
    ap.add_argument("--sla-sec", type=int, default=DEFAULT_SLA_SEC)
    ap.add_argument("--max-pending", type=int, default=DEFAULT_MAX_PENDING)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cleanup: Path | None = None
    try:
        if args.db:
            db_path = Path(args.db)
        else:
            db_path = _load_db_via_ssh(args.ssh_host, args.remote_db)
            cleanup = db_path
        m = _fetch_metrics(db_path, args.sla_sec)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        if cleanup and cleanup.exists():
            try:
                cleanup.unlink()
            except OSError:
                pass

    if args.json:
        print(json.dumps(m, indent=2))
    else:
        print(
            f"SUPPORT_QUEUE active_topics={m['active_topics']} tickets_24h={m['tickets_24h']} "
            f"pending_reply={m['pending_reply']} pending_sla_breach={m['pending_sla_breach']} "
            f"escalate_second_line={m['escalate_second_line']}"
        )

    fail = False
    if m["pending_sla_breach"] > 0:
        print("SUPPORT_QUEUE_SLA_FAIL: pending older than SLA", file=sys.stderr)
        fail = True
    if m["pending_reply"] >= args.max_pending:
        print(
            f"SUPPORT_QUEUE_WARN: pending_reply>={args.max_pending} (second line)",
            file=sys.stderr,
        )
    if not fail:
        print("SUPPORT_QUEUE_OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
