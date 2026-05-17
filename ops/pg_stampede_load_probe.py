#!/usr/bin/env python3
"""Postgres + subscription stampede load probe (P6-RED-PG-01).

Models a busy hour of client subscription refreshes hitting panel DB indirectly:
parallel GETs to ``/api/sub/{shortUuid}`` while sampling Postgres connection counts on AMS.

Example::

  python ops/pg_stampede_load_probe.py
  python ops/pg_stampede_load_probe.py --total 150 --concurrency 30 --json

Exit 0 with ``PG_STAMPEDE_LOAD_OK`` when refresh probe and connection headroom pass.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402
from pg_remnawave_audit import _ssh_ams_psql  # noqa: E402


def _pg_conn_snapshot() -> dict[str, int]:
    max_conn = int(_ssh_ams_psql("SHOW max_connections;") or "100")
    active = int(
        _ssh_ams_psql(
            "SELECT count(*) FROM pg_stat_activity WHERE datname IS NOT NULL;"
        )
        or "0"
    )
    remnawave = int(
        _ssh_ams_psql(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE application_name ILIKE '%prisma%' OR usename = 'postgres';"
        )
        or "0"
    )
    return {
        "max_connections": max_conn,
        "active_connections": active,
        "prisma_or_postgres_connections": remnawave,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--total",
        type=int,
        default=120,
        help="parallel refresh GETs (proxy for 1h stampede slice)",
    )
    ap.add_argument("--concurrency", type=int, default=25)
    ap.add_argument(
        "--max-conn-pct",
        type=float,
        default=0.85,
        help="fail if peak active/max_connections exceeds this fraction",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    probe_script = ROOT / "ops" / "panel_refresh_load_probe.py"
    if not probe_script.is_file():
        print(f"FAIL: missing {probe_script}", file=sys.stderr)
        return 2

    def _run_refresh(origin: str, total: int, concurrency: int) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable,
            str(probe_script),
            "--origin",
            origin,
            "--concurrency",
            str(concurrency),
            "--total",
            str(total),
        ]
        if args.json:
            cmd.append("--json")
        return subprocess.run(cmd, capture_output=True, text=True)

    alt = (
        site_urls.SUB_ALT_PUBLIC_ORIGINS[0]
        if site_urls.SUB_ALT_PUBLIC_ORIGINS
        else site_urls.SUB_PUBLIC_ORIGIN
    )
    origins = [
        site_urls.SUB_PUBLIC_ORIGIN.rstrip("/"),
        alt.rstrip("/"),
    ]
    half = max(1, args.total // 2)
    rest = args.total - half

    before = _pg_conn_snapshot()
    runs: list[dict] = []
    worst_exit = 0
    combined_stdout = []
    for i, origin in enumerate(origins):
        n = half if i == 0 else rest
        proc = _run_refresh(origin, n, args.concurrency)
        worst_exit = max(worst_exit, proc.returncode)
        combined_stdout.append(proc.stdout)
        summary: dict | None = None
        if args.json and proc.stdout.strip():
            try:
                summary = json.loads(proc.stdout.strip().splitlines()[-1])
            except json.JSONDecodeError:
                summary = {"raw_stdout": proc.stdout[-300:]}
        runs.append(
            {
                "origin": origin,
                "total": n,
                "exit_code": proc.returncode,
                "summary": summary,
                "stderr_tail": proc.stderr[-400:] if proc.stderr else "",
            }
        )
    after = _pg_conn_snapshot()

    peak_active = max(before["active_connections"], after["active_connections"])
    max_conn = after["max_connections"]
    conn_pct = peak_active / max_conn if max_conn else 1.0

    report = {
        "probe": "pg_stampede_load",
        "pg_before": before,
        "pg_after": after,
        "peak_active_connections": peak_active,
        "connection_utilization": round(conn_pct, 4),
        "panel_refresh_exit": worst_exit,
        "refresh_runs": runs,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"PG stampede: peak_conn={peak_active}/{max_conn} ({conn_pct:.1%}) "
            f"panel_refresh_exit={worst_exit} origins={len(origins)}"
        )
        for block in combined_stdout:
            if block.strip():
                print(block.strip())

    if worst_exit != 0:
        print("FAIL: panel_refresh_load_probe", file=sys.stderr)
        return 1
    if conn_pct > args.max_conn_pct:
        print(
            f"FAIL: connection utilization {conn_pct:.1%} > {args.max_conn_pct:.0%}",
            file=sys.stderr,
        )
        return 1

    print("PG_STAMPEDE_LOAD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
