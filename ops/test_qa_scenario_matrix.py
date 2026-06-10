#!/usr/bin/env python3
"""QA-SCENARIO-MATRIX-001: scenario matrix runner regression checks."""
from __future__ import annotations

import asyncio
import importlib
import json
import os
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


def _reload_matrix():
    for name in list(sys.modules):
        if name.startswith(
            (
                "qa_scenario_matrix",
                "qa_portal_fixtures",
                "qa_bot_fake_tg",
                "qa_seed_scenarios",
                "shop_bot",
            )
        ):
            del sys.modules[name]
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    return importlib.import_module("qa_scenario_matrix")


def _static_checks() -> None:
    src = (OPS / "qa_scenario_matrix.py").read_text(encoding="utf-8")
    for needle, label in (
        ("_ensure_guards", "non-prod guard via portal fixtures"),
        ("production_identical", "drift classification"),
        ("dry_run_mocked", "dry-run drift bucket"),
        ("not_verified_without_staging_or_prod", "staging drift bucket"),
        ("render_markdown_report", "markdown report"),
        ("run_matrix", "matrix runner"),
        ("after_trial_cap", "blocked scenario"),
        ("slots_counter_states", "blocked scenario"),
        ("temporary_converted_to_paid", "partial scenario"),
    ):
        if needle not in src:
            raise AssertionError(f"static check failed: {label} ({needle!r})")
    for bad in ("YOOKASSA_SECRET", "api.telegram.org", "live_", "https://kitsura"):
        if bad in src:
            raise AssertionError(f"matrix module must not embed {bad!r}")


async def _run_matrix_tests() -> None:
    _static_checks()

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "qa_matrix.db"
        prod_db = Path(tmp) / "prod_marker.db"
        prod_db.write_text("", encoding="utf-8")
        report_md = Path(tmp) / "matrix-report.md"
        report_json = Path(tmp) / "matrix-report.json"

        prev = _set_env(
            BVPN_ENV="production",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(db_path),
            BVPN_PROD_DB_PATH=str(prod_db),
        )
        try:
            matrix = _reload_matrix()
            try:
                matrix._ensure_guards(db_path)
                raise AssertionError("production must block matrix")
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
            matrix = _reload_matrix()
            try:
                matrix._ensure_guards(db_path)
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
            matrix = _reload_matrix()
            try:
                matrix._ensure_guards(prod_db)
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
            BVPN_QA_DRY_RUN_REMNA="1",
            BVPN_QA_DRY_RUN_PAYMENTS="1",
            BVPN_QA_PORTAL_BASE="http://127.0.0.1:8765",
            TELEGRAM_WEBAPP_URL="",
        )
        try:
            matrix = _reload_matrix()
            seed = importlib.import_module("qa_seed_scenarios")
            matrix._ensure_guards(db_path)

            assert len(matrix.MATRIX) == 20
            assert list(seed.SCENARIO_ORDER) == list(matrix.MATRIX.keys())

            paid = await matrix.run_scenario(
                "paid_wallet_user",
                db_path=db_path,
                seeded=False,
            )
            assert paid.runnable == "full"
            assert paid.tg_user_id == 900_000_010
            assert paid.portal_url
            assert paid.cabinet_url
            assert paid.setup_url
            assert paid.actual_checks.get("cabinet_ok") is True
            assert paid.actual_checks.get("profile_match") is True
            assert paid.drift.get("production_identical")
            assert paid.drift.get("dry_run_mocked")
            assert paid.drift.get("not_verified_without_staging_or_prod")

            blocked = await matrix.run_scenario(
                "after_trial_cap",
                db_path=db_path,
                seeded=True,
            )
            assert blocked.support == "blocked"
            assert blocked.runnable == "blocked"
            assert "ACQ-TRIAL-CAP" in blocked.next_blocker

            partial = await matrix.run_scenario(
                "temporary_converted_to_paid",
                db_path=db_path,
                seeded=True,
            )
            assert partial.support == "partial"
            assert partial.runnable == "partial"
            assert "QA-PAYMENT-WEBHOOK" in partial.next_blocker or "ACQ" in partial.next_blocker

            slots = await matrix.run_scenario(
                "slots_counter_states",
                db_path=db_path,
                seeded=True,
            )
            assert slots.runnable == "blocked"

            rows = await matrix.run_matrix(db_path=db_path, reset_seed=True)
            assert len(rows) == 20
            counts = {"full": 0, "partial": 0, "blocked": 0}
            for row in rows:
                counts[row.runnable] = counts.get(row.runnable, 0) + 1
            assert counts["blocked"] == 2
            assert counts["partial"] >= 2
            assert counts["full"] >= 14

            md = matrix.render_markdown_report(rows, db_path=db_path)
            assert "QA Customer Journey Matrix Report" in md
            assert "Production-identical" in md
            assert "Dry-run / mocked boundaries" in md
            assert "after_trial_cap" in md
            report_md.write_text(md, encoding="utf-8")

            payload = {
                "summary": {
                    "total": len(rows),
                    "full": counts["full"],
                    "partial": counts["partial"],
                    "blocked": counts["blocked"],
                },
                "drift": matrix._drift_payload(),
                "scenarios": [r.to_dict() for r in rows],
            }
            report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            loaded = json.loads(report_json.read_text(encoding="utf-8"))
            assert loaded["summary"]["total"] == 20
            assert loaded["drift"]["production_identical"]
            assert loaded["drift"]["dry_run_mocked"]
            scenario_names = {s["scenario"] for s in loaded["scenarios"]}
            assert scenario_names == set(seed.SCENARIO_ORDER)

            for row in rows:
                dumped = json.dumps(row.to_dict(), ensure_ascii=False)
                assert "vless://" not in dumped
                assert "kitsura.fun" not in dumped

            try:
                from shop_bot.web_trial_db import _pool  # noqa: PLC2701

                if _pool is not None:
                    while True:
                        try:
                            _pool.get_nowait().close()
                        except Exception:
                            break
            except Exception:
                pass
        finally:
            _restore_env(prev)


def _run_tests() -> None:
    asyncio.run(_run_matrix_tests())


if __name__ == "__main__":
    _run_tests()
    print("ops/test_qa_scenario_matrix.py: OK")
