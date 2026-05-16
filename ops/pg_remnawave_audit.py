#!/usr/bin/env python3
"""Read-only Postgres health audit for remnawave-db (P6-SCALE-03).

Runs SQL via ``docker exec remnawave-db`` on AMS (default) or local container.

Example::

  python ops/pg_remnawave_audit.py
  python ops/pg_remnawave_audit.py --json
  python ops/pg_remnawave_audit.py --host ams --no-docker  # psql on host :6767
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

DEFAULT_CONTAINER = "remnawave-db"


def _docker_psql(container: str, sql: str) -> str:
    cmd = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-v",
        "ON_ERROR_STOP=1",
        "-At",
        "-c",
        sql,
    ]
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()


def _ssh_ams_psql(sql: str) -> str:
    remote = (
        f"docker exec {DEFAULT_CONTAINER} psql -U postgres -d postgres "
        f"-v ON_ERROR_STOP=1 -At -c {json.dumps(sql)}"
    )
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=40",
        "-p",
        "3344",
        "-i",
        f"{__import__('pathlib').Path.home() / '.ssh' / 'id_ed25519'}",
        "root@168.100.11.140",
        remote,
    ]
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()


def run_audit(exec_sql) -> dict[str, Any]:
    report: dict[str, Any] = {"container": DEFAULT_CONTAINER}

    version = exec_sql("SHOW server_version;")
    report["server_version"] = version

    ext = exec_sql(
        "SELECT extname FROM pg_extension WHERE extname = 'pg_stat_statements';"
    )
    report["pg_stat_statements"] = "enabled" if ext else "disabled"

    sizes_raw = exec_sql(
        "SELECT relname || '|' || pg_size_pretty(pg_total_relation_size(c.oid)) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' "
        "ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 15;"
    )
    tables: list[dict[str, str]] = []
    for line in sizes_raw.splitlines():
        if "|" not in line:
            continue
        name, size = line.split("|", 1)
        tables.append({"table": name, "total_size": size})
    report["top_tables_by_size"] = tables

    idx_count = exec_sql(
        "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public';"
    )
    report["public_index_count"] = int(idx_count or 0)

    no_pk = exec_sql(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT EXISTS "
        "(SELECT 1 FROM pg_constraint con WHERE con.conrelid = c.oid AND con.contype = 'p');"
    )
    report["tables_without_pk"] = [x for x in no_pk.splitlines() if x] if no_pk else []

    conns = exec_sql(
        "SELECT count(*) FROM pg_stat_activity WHERE datname IS NOT NULL;"
    )
    report["connections"] = int(conns or 0)

    if report["pg_stat_statements"] == "enabled":
        top = exec_sql(
            "SELECT left(query, 80) || '|' || calls::text || '|' || "
            "round(total_exec_time::numeric, 2)::text FROM pg_stat_statements "
            "ORDER BY total_exec_time DESC LIMIT 8;"
        )
        queries: list[dict[str, str | int]] = []
        for line in top.splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                queries.append(
                    {
                        "query_prefix": parts[0],
                        "calls": int(parts[1]),
                        "total_ms": parts[2],
                    }
                )
        report["top_queries_by_time"] = queries

    notices: list[str] = []
    if report["tables_without_pk"]:
        notices.append(
            f"tables_without_pk={len(report['tables_without_pk'])} (review schema)"
        )
    if report["pg_stat_statements"] == "disabled":
        notices.append(
            "pg_stat_statements disabled — run ops/pg_enable_stat_statements_ams.sh"
        )
    report["notices"] = notices
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--host",
        choices=("local", "ams"),
        default="ams",
        help="local: docker exec on this machine; ams: ssh root@AMS",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        if args.host == "ams":
            exec_sql = _ssh_ams_psql
        else:
            exec_sql = lambda sql: _docker_psql(DEFAULT_CONTAINER, sql)
        report = run_audit(exec_sql)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: audit failed: {e.output if hasattr(e, 'output') else e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== Remnawave Postgres audit ===")
        print(f"version={report['server_version']}  pg_stat_statements={report['pg_stat_statements']}")
        print(f"connections={report['connections']}  public_indexes={report['public_index_count']}")
        print("top tables:")
        for t in report.get("top_tables_by_size", [])[:8]:
            print(f"  {t['table']:40} {t['total_size']}")
        if report.get("top_queries_by_time"):
            print("top queries (pg_stat_statements):")
            for q in report["top_queries_by_time"]:
                print(f"  calls={q['calls']} total_ms={q['total_ms']}  {q['query_prefix'][:70]}")
        for n in report.get("notices", []):
            print(f"NOTICE: {n}")

    if report.get("notices") and report["pg_stat_statements"] == "disabled":
        return 0  # audit OK but extension not yet enabled
    print("PG_REMNAWAVE_AUDIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
