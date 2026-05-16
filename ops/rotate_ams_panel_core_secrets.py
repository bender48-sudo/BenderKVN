#!/usr/bin/env python3
"""
P0-SEC-05 phase 1 (AMS): rotate JWT_AUTH_SECRET, JWT_API_TOKENS_SECRET, POSTGRES_PASSWORD
in /opt/remnawave/.env and ALTER USER in Postgres. Restarts only the remnawave app container.

Does NOT update REMNA_API_TOKEN — after this script, admin must log into the panel and
generate a new API token, then update 4 consumers (runbook §3).

Usage (on AMS, root, from /opt/remnawave or pass --compose-dir):
  python3 /path/to/rotate_ams_panel_core_secrets.py --compose-dir /opt/remnawave --dry-run
  python3 /path/to/rotate_ams_panel_core_secrets.py --compose-dir /opt/remnawave --apply
"""

from __future__ import annotations

import argparse
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus


def parse_env_lines(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        out[key] = val
    return out


def rebuild_database_url(user: str, password: str, db: str) -> str:
    enc = quote_plus(password, safe="")
    return f"postgresql://{user}:{enc}@remnawave-db:5432/{db}"


def sql_escape_literal(s: str) -> str:
    return s.replace("'", "''")


def rewrite_env(text: str, updates: dict[str, str]) -> str:
    keys_remaining = set(updates)
    key_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
    out_lines: list[str] = []
    for line in text.splitlines():
        m = key_pattern.match(line)
        if m and m.group(1) in keys_remaining:
            k = m.group(1)
            val = updates[k]
            if k == "DATABASE_URL":
                out_lines.append(f'DATABASE_URL="{val}"')
            else:
                out_lines.append(f"{k}={val}")
            keys_remaining.discard(k)
        else:
            out_lines.append(line)
    for k in sorted(keys_remaining):
        val = updates[k]
        if k == "DATABASE_URL":
            out_lines.append(f'DATABASE_URL="{val}"')
        else:
            out_lines.append(f"{k}={val}")
    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(out_lines) + trailing


def run(cmd: list[str], *, cwd: Path) -> None:
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Rotate AMS remnawave core secrets (panel .env + Postgres).")
    ap.add_argument("--compose-dir", type=Path, default=Path("/opt/remnawave"))
    ap.add_argument("--dry-run", action="store_true", help="Print planned changes only.")
    ap.add_argument("--apply", action="store_true", help="Execute ALTER USER, rewrite .env, restart remnawave.")
    args = ap.parse_args()

    if args.dry_run == args.apply:
        print("Specify exactly one of --dry-run or --apply", file=sys.stderr)
        return 2

    compose_dir: Path = args.compose_dir.resolve()
    env_path = compose_dir / ".env"
    compose_file = compose_dir / "docker-compose.yml"
    if not env_path.is_file():
        print(f"Missing {env_path}", file=sys.stderr)
        return 1
    if not compose_file.is_file():
        print(f"Missing {compose_file}", file=sys.stderr)
        return 1

    raw = env_path.read_text(encoding="utf-8", errors="replace")
    cur = parse_env_lines(raw)
    pg_user = cur.get("POSTGRES_USER", "postgres")
    pg_db = cur.get("POSTGRES_DB", "postgres")

    new_pg = secrets.token_hex(24)
    new_auth = secrets.token_hex(64)
    new_api = secrets.token_hex(64)
    new_db_url = rebuild_database_url(pg_user, new_pg, pg_db)

    updates = {
        "POSTGRES_PASSWORD": new_pg,
        "JWT_AUTH_SECRET": new_auth,
        "JWT_API_TOKENS_SECRET": new_api,
        "DATABASE_URL": new_db_url,
    }

    if args.dry_run:
        print("--- dry-run ---")
        print(f"compose-dir: {compose_dir}")
        print(f"Will ALTER USER {pg_user!r} WITH PASSWORD <{len(new_pg)} chars hex>")
        print("Will replace JWT_AUTH_SECRET, JWT_API_TOKENS_SECRET, POSTGRES_PASSWORD, DATABASE_URL")
        print("Will recreate remnawave container (reload env_file — plain restart is NOT enough)")
        print("(REMNA_API_TOKEN unchanged — refresh via panel after apply; see RUNBOOK §3)")
        return 0

    # Path(".env").stem/suffix в pathlib даёт суффикс "" — with_suffix ломает имя (.env.env.bak…).
    bak = env_path.with_name(f"{env_path.name}.bak-p0sec05-{secrets.token_hex(4)}")
    bak.write_text(raw, encoding="utf-8")
    print(f"Backup: {bak}", file=sys.stderr)

    alter_sql = f"ALTER USER {pg_user} WITH PASSWORD '{sql_escape_literal(new_pg)}';"
    run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file.name),
            "exec",
            "-T",
            "remnawave-db",
            "psql",
            "-U",
            pg_user,
            "-d",
            pg_db,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            alter_sql,
        ],
        cwd=compose_dir,
    )

    new_raw = rewrite_env(raw, updates)
    env_path.write_text(new_raw, encoding="utf-8")

    # `compose restart` keeps old Config.Env from create time — DATABASE_URL would stay stale (Prisma P1000).
    run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file.name),
            "up",
            "-d",
            "--no-deps",
            "--force-recreate",
            "remnawave",
        ],
        cwd=compose_dir,
    )

    print("--- apply OK ---")
    print(f"Backed up prior .env to {bak}")
    print("Next: log into panel (sessions invalidated), generate new REMNA_API_TOKEN, update 4 consumers — RUNBOOK §3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
