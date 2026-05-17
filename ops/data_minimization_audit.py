#!/usr/bin/env python3
"""P3-RED-MIN-01: validate data inventory vs bot schema + code guards."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = Path(
    os.environ.get("DATA_INVENTORY", Path(__file__).resolve().parent / "data_field_inventory.json")
)
DB_PY = ROOT / "bot_src" / "database.py"
REDACT_CANDIDATES = [
    ROOT / "bot_src" / "webhook_server" / "payload_redact.py",
    Path("/app/src/shop_bot/webhook_server/payload_redact.py"),
]


def _table_columns_from_database_py() -> dict[str, set[str]]:
    text = DB_PY.read_text(encoding="utf-8")
    tables: dict[str, set[str]] = {}
    for m in re.finditer(
        r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\);",
        text,
        flags=re.DOTALL,
    ):
        table = m.group(1)
        cols: set[str] = set()
        for line in m.group(2).splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            head = line.split()[0]
            if head.upper() in ("PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "CONSTRAINT"):
                continue
            cols.add(head)
        tables[table] = cols
    for m in re.finditer(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", text):
        tables.setdefault(m.group(1), set()).add(m.group(2))
    for m in re.finditer(r'\("(\w+)",\s*"(?:INTEGER|REAL|TEXT|BOOLEAN)"\)', text):
        tables.setdefault("users", set()).add(m.group(1))
    return tables


def main() -> int:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    ok = True
    print("=== Data minimization audit (P3-RED-MIN-01) ===")
    schema: dict[str, set[str]] = {}
    if DB_PY.is_file():
        schema = _table_columns_from_database_py()
    else:
        print("NOTE: database.py not in container; schema check from inventory only")

    bot = inv["systems"]["bot_sqlite"]["tables"]
    for table, fields in bot.items():
        if schema:
            if table not in schema:
                print(f"FAIL: table {table} missing in database.py", file=sys.stderr)
                ok = False
                continue
            for entry in fields:
                col = entry["field"]
                if col not in schema[table]:
                    print(f"FAIL: {table}.{col} in inventory but not schema", file=sys.stderr)
                    ok = False
        print(f"OK: inventory covers {table} ({len(fields)} documented cols)")

    forbidden = inv.get("not_collected_global", [])
    for table, cols in schema.items():
        for col in cols:
            for bad in forbidden:
                if bad.replace("_", "") in col.replace("_", ""):
                    print(f"WARN: suspicious column {table}.{col} vs not_collected {bad}")

    redact_path = next((p for p in REDACT_CANDIDATES if p.is_file()), None)
    if redact_path is None:
        try:
            from shop_bot.webhook_server.payload_redact import (  # type: ignore
                redact_webhook_payload as _rw,
            )

            redact_fn = _rw
        except ImportError:
            print("FAIL: payload_redact not found", file=sys.stderr)
            ok = False
            redact_fn = None
    else:
        spec = importlib.util.spec_from_file_location("payload_redact", redact_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        redact_fn = mod.redact_webhook_payload

    if redact_fn is not None:
        sample = redact_fn(
            "yookassa",
            {
                "event": "payment.succeeded",
                "object": {
                    "id": "pay-1",
                    "payment_method": {"card": {"last4": "4242", "pan": "4111"}},
                    "metadata": {"user_id": 1, "amount": 100},
                },
            },
        )
        blob = json.dumps(sample)
        if "4111" in blob or "4242" in blob or "payment_method" in blob:
            print("FAIL: yookassa redaction leaked card fields", file=sys.stderr)
            ok = False
        else:
            print("OK: webhook payload redaction")
    else:
        ok = False

    reqs = inv.get("code_requirements", {})
    if "payload_redact" not in reqs.get("webhook_payload_redaction", ""):
        print("WARN: code_requirements.webhook_payload_redaction")

    if ok:
        print("DATA_MINIMIZATION_OK")
        return 0
    print("DATA_MINIMIZATION_FAIL", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
