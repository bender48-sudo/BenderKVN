#!/usr/bin/env python3
"""QA-DB-SEED-001: scenario seed/reset regression checks."""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"


def _set_env(**kwargs: str | None) -> dict[str, str | None]:
    prev: dict[str, str | None] = {}
    for key, value in kwargs.items():
        prev[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return prev


def _restore_env(prev: dict[str, str | None]) -> None:
    for key, value in prev.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _reload_seed_module():
    for name in list(sys.modules):
        if name in ("qa_seed_scenarios", "shop_bot.runtime_env") or name.startswith(
            "shop_bot.data_manager"
        ):
            del sys.modules[name]
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    return importlib.import_module("qa_seed_scenarios")


def _static_checks() -> None:
    src = (OPS / "qa_seed_scenarios.py").read_text(encoding="utf-8")
    for needle, label in (
        ("require_non_production", "non-prod guard"),
        ("require_qa_tooling_enabled", "QA tools guard"),
        ("assert_db_path_allowed_for_qa", "DB path guard"),
        ("QA_TG_ID_MIN = 900_000_001", "synthetic tg range"),
        ("sandbox.invalid", "sandbox email domain"),
        ("def reset_qa_scenarios", "reset helper"),
        ("DELETE FROM users WHERE telegram_id IN", "scoped user delete"),
    ):
        if needle not in src:
            raise AssertionError(f"static check failed: {label} ({needle!r})")
    for bad in ("kitsura.fun", "YOOKASSA_SECRET", "yookassa.ru/v3", "live_"):
        if bad in src:
            raise AssertionError(f"seed module must not embed {bad!r}")


def _run_tests() -> None:
    _static_checks()

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "qa_seed_test.db"
        prod_db = Path(tmp) / "prod_marker.db"
        prod_db.write_text("", encoding="utf-8")

        prev = _set_env(
            BVPN_ENV="production",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(db_path),
            BVPN_PROD_DB_PATH=str(prod_db),
        )
        try:
            seed = _reload_seed_module()
            try:
                seed._ensure_guards(db_path)
                raise AssertionError("production must block seed")
            except Exception as exc:
                if "production" not in str(exc).lower():
                    raise
        finally:
            _restore_env(prev)

        prev = _set_env(
            BVPN_ENV="test",
            BVPN_QA_TOOLS_ENABLED=None,
            SHOP_BOT_DB_PATH=str(db_path),
        )
        try:
            seed = _reload_seed_module()
            try:
                seed._ensure_guards(db_path)
                raise AssertionError("missing BVPN_QA_TOOLS_ENABLED must block")
            except Exception as exc:
                if "BVPN_QA_TOOLS_ENABLED" not in str(exc):
                    raise
        finally:
            _restore_env(prev)

        prev = _set_env(
            BVPN_ENV="test",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(prod_db),
            BVPN_PROD_DB_PATH=str(prod_db),
        )
        try:
            seed = _reload_seed_module()
            try:
                seed._ensure_guards(prod_db)
                raise AssertionError("production DB path must be rejected")
            except Exception as exc:
                if "production" not in str(exc).lower() and "refusing" not in str(exc).lower():
                    raise
        finally:
            _restore_env(prev)

        prev = _set_env(
            BVPN_ENV="local",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(db_path),
            BVPN_PROD_DB_PATH=str(prod_db),
        )
        try:
            seed = _reload_seed_module()
            seed._ensure_guards(db_path)
            conn = seed._init_db(db_path)

            conn.execute(
                "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
                (42, "real_user_keep"),
            )
            conn.commit()

            seed.reset_qa_scenarios(conn)
            m1 = seed.seed_scenario(conn, "new_no_referral")
            m2 = seed.seed_scenario(conn, "new_no_referral")
            assert m1.tg_user_id == m2.tg_user_id == seed.QA_TG_ID_MIN
            assert m1.support == "full"

            row = conn.execute(
                "SELECT username, trial_used FROM users WHERE telegram_id = ?",
                (seed.QA_TG_ID_MIN,),
            ).fetchone()
            assert row["username"] == "qa_new_no_referral"
            assert row["trial_used"] == 0

            seed.seed_scenario(conn, "paid_wallet_user")
            kept = conn.execute(
                "SELECT username FROM users WHERE telegram_id = 42"
            ).fetchone()
            assert kept and kept["username"] == "real_user_keep"

            seed.reset_qa_scenarios(conn)
            qa_row = conn.execute(
                "SELECT 1 FROM users WHERE telegram_id = ?",
                (seed.QA_TG_ID_MIN,),
            ).fetchone()
            kept2 = conn.execute(
                "SELECT username FROM users WHERE telegram_id = 42"
            ).fetchone()
            assert qa_row is None
            assert kept2 and kept2["username"] == "real_user_keep"

            manifest = seed.seed_all_scenarios(conn)
            assert len(manifest) == len(seed.SCENARIO_ORDER)
            blocked = [m.name for m in manifest if m.support == "blocked"]
            assert "after_trial_cap" in blocked
            assert "slots_counter_states" in blocked

            keys = conn.execute(
                "SELECT key_email FROM vpn_keys WHERE key_email LIKE ?",
                (f"%@{seed.QA_EMAIL_DOMAIN}",),
            ).fetchall()
            assert keys
            for row in keys:
                email = row[0]
                assert "kitsura" not in email
                assert seed.QA_EMAIL_DOMAIN in email

            from shop_bot.portal_cabinet import cabinet_snapshot

            cab = cabinet_snapshot(telegram_id=seed.QA_TG_ID_MIN + 9)
            assert cab.get("ok") is True
            assert cab.get("billing_profile") == "wallet"

            manifest_path = Path(tmp) / "manifest.json"
            seed.write_manifest(manifest, manifest_path)
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert len(data["scenarios"]) == len(seed.SCENARIO_ORDER)
            conn.close()
        finally:
            _restore_env(prev)


def main() -> int:
    _run_tests()
    print("QA_SEED_SCENARIOS_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
