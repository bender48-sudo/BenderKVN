#!/usr/bin/env python3
"""QA-BOT-FAKE-TG-001: fake Telegram handler harness regression checks."""
from __future__ import annotations

import asyncio
import html
import importlib
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

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


def _reload_harness():
    for name in list(sys.modules):
        if name.startswith(("qa_bot_fake_tg", "qa_seed_scenarios", "shop_bot")):
            del sys.modules[name]
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    return importlib.import_module("qa_bot_fake_tg")


def _static_checks() -> None:
    src = (OPS / "qa_bot_fake_tg.py").read_text(encoding="utf-8")
    for needle, label in (
        ("require_non_production", "non-prod guard"),
        ("require_qa_tooling_enabled", "QA tools guard"),
        ("assert_db_path_allowed_for_qa", "DB path guard"),
        ("class CapturingBot", "capture-only bot"),
        ("Telegram send API: DISABLED", "no real send banner"),
        ("handlers.start_handler", "real start handler"),
        ("handlers.main_menu_handler", "real menu handler"),
        ("menu_get_setup_handler", "real get_setup handler"),
        ("sandbox.invalid", "fake subscription host"),
        ("render_bot_preview_html", "telegram-like bot preview"),
    ):
        if needle not in src:
            raise AssertionError(f"static check failed: {label} ({needle!r})")
    for bad in ("TELEGRAM_BOT_TOKEN", "api.telegram.org", "kitsura.fun"):
        if bad in src:
            raise AssertionError(f"harness must not embed {bad!r}")


async def _async_tests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "qa_bot_harness.db"
        prod_db = Path(tmp) / "prod_marker.db"
        prod_db.write_text("", encoding="utf-8")

        prev = _set_env(
            BVPN_ENV="production",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(db_path),
            BVPN_PROD_DB_PATH=str(prod_db),
            TELEGRAM_WEBAPP_URL="",
        )
        try:
            harness = _reload_harness()
            try:
                harness._ensure_guards(db_path)
                raise AssertionError("production must block harness")
            except Exception as exc:
                if "production" not in str(exc).lower():
                    raise
        finally:
            _restore_env(prev)

        prev = _set_env(
            BVPN_ENV="test",
            BVPN_QA_TOOLS_ENABLED=None,
            SHOP_BOT_DB_PATH=str(db_path),
            TELEGRAM_WEBAPP_URL="",
        )
        try:
            harness = _reload_harness()
            try:
                harness._ensure_guards(db_path)
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
            TELEGRAM_WEBAPP_URL="",
        )
        try:
            harness = _reload_harness()
            try:
                harness._ensure_guards(prod_db)
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
            TELEGRAM_WEBAPP_URL="",
        )
        try:
            harness = _reload_harness()
            seed = importlib.import_module("qa_seed_scenarios")
            harness._ensure_guards(db_path)
            conn = seed._init_db(db_path)
            seed.seed_all_scenarios(conn)
            conn.close()

            from shop_bot.data_manager.database import upsert_setting

            upsert_setting("terms_url", "https://sandbox.invalid/terms")
            upsert_setting("privacy_url", "https://sandbox.invalid/privacy")

            with patch("aiogram.client.bot.Bot.send_message", side_effect=AssertionError("real TG send")):
                start_res = await harness.run_harness(
                    scenario="new_no_referral",
                    tg_id=None,
                    action="start",
                    db_path=db_path,
                )
            assert start_res.tg_user_id == harness.SCENARIO_TG_ID["new_no_referral"]
            assert start_res.outbound, "start must capture outbound messages"
            assert not start_res.errors
            joined = " ".join(m.text for m in start_res.outbound).lower()
            assert "привет" in joined or "условия" in joined or "принимаю" in joined

            menu_res = await harness.run_harness(
                scenario="paid_wallet_user",
                tg_id=None,
                action="menu",
                db_path=db_path,
            )
            assert menu_res.outbound
            menu_text = " ".join(m.text for m in menu_res.outbound)
            assert menu_text

            setup_res = await harness.run_harness(
                scenario="user_one_active_config",
                tg_id=None,
                action="get_setup",
                db_path=db_path,
            )
            assert setup_res.outbound
            setup_joined = " ".join(
                b.value for m in setup_res.outbound for b in m.buttons
            ) + " ".join(m.text for m in setup_res.outbound)
            assert (
                "настройк" in setup_joined.lower()
                or "setup" in setup_joined.lower()
                or "back_to_main_menu" in setup_joined
            )

            transcript = harness.render_transcript(setup_res)
            assert "QA bot preview" in transcript
            assert "TELEGRAM_BOT_TOKEN" not in transcript

            preview_html = harness.render_bot_preview_html(setup_res, transcript_basename="setup.md")
            assert "tg-msg" in preview_html
            assert "Expected next action" in preview_html
            assert "tg-btn" in preview_html or "No captured outbound" in preview_html
            if setup_res.outbound and setup_res.outbound[0].text:
                assert html.escape(setup_res.outbound[0].text[:20])[:10] in preview_html or setup_res.outbound[0].text[:8] in preview_html
        finally:
            _restore_env(prev)


def main() -> int:
    _static_checks()
    asyncio.run(_async_tests())
    print("QA_BOT_FAKE_TG_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
