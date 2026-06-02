#!/usr/bin/env python3
"""One-shot AMS bot deploy drift probe (read-only)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AMS = "root@168.100.11.140"
SSH_KEY = Path.home() / ".ssh" / "bvpn_ams_ed25519"
PORT = "3344"

REMOTE = r"""
set -e
echo '=== containers ==='
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -8
echo '=== bot code markers ==='
docker exec remna-shop-bot python3 <<'PY'
import sqlite3
from shop_bot.bot import handlers
from shop_bot.data_manager.database import DB_FILE, initialize_db
import shop_bot.config as cfg

markers = {
    "pay_yookassa_topup_handler": hasattr(handlers, "pay_yookassa_topup_handler"),
    "validate_required_config": hasattr(cfg, "validate_required_config"),
    "db_connection": hasattr(__import__("shop_bot.data_manager.database", fromlist=["db_connection"]), "db_connection"),
    "try_acquire_topup_idempotency": hasattr(__import__("shop_bot.data_manager.database", fromlist=["x"]), "try_acquire_topup_idempotency"),
    "toggle_autorenew": "toggle_autorenew" in open("/app/src/shop_bot/bot/handlers.py", encoding="utf-8", errors="replace").read(),
}
for k, v in markers.items():
    print(f"  {k}: {v}")
initialize_db()
try:
    c = sqlite3.connect(DB_FILE)
    row = c.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    print("  schema_version:", row[0] if row else "?")
except Exception as e:
    print("  schema_version: err", e)
PY
echo '=== health ==='
curl -sS -m 5 http://127.0.0.1:1488/health || echo HEALTH_FAIL
echo
echo '=== webhook deliveries (last 3) ==='
docker exec remna-shop-bot python3 -c "import sqlite3; from shop_bot.data_manager.database import DB_FILE; c=sqlite3.connect(DB_FILE); rows=c.execute('SELECT idempotency_key, source, status, updated_at FROM webhook_deliveries ORDER BY updated_at DESC LIMIT 3').fetchall(); print(rows or 'none')"
"""


def main() -> int:
    cmd = [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=25",
        "-p",
        PORT,
        AMS,
        REMOTE,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
