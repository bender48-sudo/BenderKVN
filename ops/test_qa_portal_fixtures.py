#!/usr/bin/env python3
"""QA-PORTAL-FIXTURES-001: portal fixture preview regression checks."""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def _reload_fixtures():
    for name in list(sys.modules):
        if name.startswith(("qa_portal_fixtures", "qa_bot_fake_tg", "qa_seed_scenarios", "shop_bot")):
            del sys.modules[name]
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    return importlib.import_module("qa_portal_fixtures")


def _static_checks() -> None:
    src = (OPS / "qa_portal_fixtures.py").read_text(encoding="utf-8")
    portal_js = (ROOT / "web" / "portal" / "assets" / "portal.js").read_text(encoding="utf-8")
    for needle, label in (
        ("require_non_production", "non-prod guard"),
        ("require_qa_tooling_enabled", "QA tools guard"),
        ("assert_db_path_allowed_for_qa", "DB path guard"),
        ("cabinet_api_response", "cabinet API shape"),
        ("cabinet_snapshot", "real cabinet_snapshot"),
        ("qa_scenario", "scenario query param"),
        ("sandbox.invalid", "sandbox-only URLs"),
        ("isLocalQaPreview", "localhost preview hook"),
        ("qa_capacity_fixture", "slots fixture param"),
        ("landing_tg_after", "landing after-click copy"),
        ("landing-existing-user", "existing user entry"),
        ("configureBrowserAccountFold", "account fold browser dedup"),
        ("renderExistingUserEntry", "existing user CTA"),
        ("browserCabinetUtilityItems", "cabinet actions browser dedup"),
        ("configureSharedSupportVisibility", "support block browser gate"),
    ):
        if needle not in (src + portal_js + (ROOT / "web" / "portal" / "content" / "ru.json").read_text(encoding="utf-8")):
            raise AssertionError(f"static check failed: {label} ({needle!r})")

    if "action_tg_bot" in portal_js and "browserCabinetUtilityItems" in portal_js:
        idx = portal_js.index("function browserCabinetUtilityItems")
        util_fn = portal_js[idx : portal_js.index("function configureSharedSupportVisibility", idx)]
        for bad in ("action_tg_bot", "action_email_access"):
            if bad in util_fn:
                raise AssertionError(f"browser cabinet actions must not repeat acquisition CTA {bad!r}")
    render_idx = portal_js.index("function renderCabinetActions")
    render_fn = portal_js[render_idx : portal_js.index("function updateCabinetChrome", render_idx)]
    if "shouldShowCabinetAccountPanel()" not in render_fn:
        raise AssertionError("renderCabinetActions must gate on shouldShowCabinetAccountPanel for browser")

    index_html = (ROOT / "web" / "portal" / "index.html").read_text(encoding="utf-8")
    if 'id="landing-paths"' not in index_html:
        raise AssertionError("landing-paths block required")
    if 'class="cta hidden" id="home-cta"' not in index_html:
        raise AssertionError("home-cta must default hidden for browser dedup")
    if 'class="status hidden" id="events-card"' not in index_html:
        raise AssertionError("events-card must default hidden to avoid empty dot")
    if 'class="sheet glass hidden" id="landing-paths"' in index_html:
        raise AssertionError("landing-paths must be visible without JS")
    if "paths && !paths.classList.contains" in portal_js:
        raise AssertionError("journey must not hide when landing-paths visible")
    for bad in ("kitsura.fun", "YOOKASSA_SECRET", "api.telegram.org", "live_"):
        if bad in src:
            raise AssertionError(f"fixture module must not embed {bad!r}")

    portal_css = (ROOT / "web" / "portal" / "assets" / "portal.css").read_text(encoding="utf-8")
    for needle, label in (
        ("html.tg-webapp .cabinet-balance", "Mini App cabinet balance contrast"),
        ("html.tg-webapp .config-list li", "Mini App config list contrast"),
        ("legacy_manual_user", "manual-access cabinet fixture"),
    ):
        bundle = portal_css if "cabinet-balance" in needle or "config-list" in needle else src
        if needle not in bundle:
            raise AssertionError(f"static check failed: {label} ({needle!r})")

    init_idx = portal_js.index("function initTelegram")
    init_fn = portal_js[init_idx : portal_js.index("function openExternal", init_idx)]
    if 'text_color: "--text"' in init_fn or 'hint_color: "--muted"' in init_fn:
        raise AssertionError("initTelegram must not override portal text/muted from Telegram theme")


def _run_tests() -> None:
    _static_checks()

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "qa_portal.db"
        prod_db = Path(tmp) / "prod_marker.db"
        prod_db.write_text("", encoding="utf-8")

        prev = _set_env(
            BVPN_ENV="production",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(db_path),
            BVPN_PROD_DB_PATH=str(prod_db),
        )
        try:
            qpf = _reload_fixtures()
            try:
                qpf._ensure_guards(db_path)
                raise AssertionError("production must block fixtures")
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
            qpf = _reload_fixtures()
            try:
                qpf._ensure_guards(db_path)
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
            BVPN_QA_PORTAL_BASE="http://127.0.0.1:8765",
        )
        try:
            qpf = _reload_fixtures()
            try:
                qpf._ensure_guards(prod_db)
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
            BVPN_QA_PORTAL_BASE="http://127.0.0.1:8765",
        )
        try:
            qpf = _reload_fixtures()
            seed = importlib.import_module("qa_seed_scenarios")
            qpf._ensure_guards(db_path)
            conn = seed._init_db(db_path)
            seed.seed_all_scenarios(conn)
            conn.close()

            fx1 = qpf.resolve_fixture("paid_wallet_user", db_path=db_path)
            fx2 = qpf.resolve_fixture("paid_wallet_user", db_path=db_path)
            assert fx1.tg_user_id == fx2.tg_user_id == 900_000_010
            cab_url = fx1.urls["cabinet"]
            qs = parse_qs(urlparse(cab_url).query)
            assert qs.get("tid") == ["900000010"]
            assert qs.get("qa_scenario") == ["paid_wallet_user"]
            assert "127.0.0.1" in cab_url

            ref_fx = qpf.resolve_fixture("new_from_referral", db_path=db_path)
            ref_qs = parse_qs(urlparse(ref_fx.urls["portal"]).query)
            assert ref_qs.get("ref") == ["QA_REF_INVITER"]

            blocked = qpf.resolve_fixture("after_trial_cap", db_path=db_path)
            assert blocked.support == "blocked"
            assert blocked.trial_cap_payload

            slots = qpf.resolve_fixture("slots_counter_states", db_path=db_path)
            assert "qa_capacity_fixture" in slots.urls["portal_slots"]

            snap = qpf.cabinet_api_response(telegram_id=900_000_010, db_path=db_path)
            assert snap.get("ok") is True
            assert snap.get("billing_profile") == "wallet"
            dumped = json.dumps(snap)
            assert "kitsura" not in dumped
            assert "vless://" not in dumped

            index_path = Path(tmp) / "index.json"
            qpf.seed_preview_index(db_path=db_path, out_path=index_path)
            data = json.loads(index_path.read_text(encoding="utf-8"))
            assert len(data["scenarios"]) >= 15

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


def main() -> int:
    _run_tests()
    print("QA_PORTAL_FIXTURES_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
