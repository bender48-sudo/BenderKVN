#!/usr/bin/env python3
"""QA-OWNER-PREVIEW-001 / FIX-001: owner journey preview regression checks."""
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
FIXED_TS = "2026-06-10T12:00:00+00:00"


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


def _reload_preview():
    for name in list(sys.modules):
        if name.startswith(
            (
                "qa_owner_preview",
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
    return importlib.import_module("qa_owner_preview")


def _fixture_rows() -> list[dict]:
    drift = {
        "production_identical": ["portal_cabinet.cabinet_snapshot schema"],
        "dry_run_mocked": ["Telegram send capture-only harness"],
        "not_verified_without_staging_or_prod": ["Real Telegram Mini App WebView"],
    }
    return [
        {
            "scenario": "paid_wallet_user",
            "support": "full",
            "runnable": "full",
            "tg_user_id": 900_000_010,
            "email": None,
            "phone": None,
            "ref_code": None,
            "portal_url": "http://127.0.0.1:8765/start/?qa_scenario=paid_wallet_user&tid=900000010",
            "cabinet_url": "http://127.0.0.1:8765/portal/cabinet.html?qa_scenario=paid_wallet_user&tid=900000010",
            "setup_url": "http://127.0.0.1:8765/setup?qa_scenario=paid_wallet_user&tid=900000010",
            "bot_actions": ["menu"],
            "bot_transcript_path": None,
            "expected_behavior": "Wallet menu + setup link",
            "actual_checks": {"billing_profile": "wallet", "cabinet_ok": True},
            "drift": drift,
            "next_blocker": "",
            "errors": [],
        },
        {
            "scenario": "trial_eligible_before_cap",
            "support": "partial",
            "runnable": "partial",
            "tg_user_id": 900_000_005,
            "portal_url": "http://127.0.0.1:8765/start/?qa_scenario=trial_eligible_before_cap",
            "cabinet_url": "http://127.0.0.1:8765/portal/cabinet.html?qa_scenario=trial_eligible_before_cap&tid=900000005",
            "setup_url": "http://127.0.0.1:8765/setup?qa_scenario=trial_eligible_before_cap&tid=900000005",
            "bot_actions": ["menu"],
            "bot_transcript_path": None,
            "expected_behavior": "Trial CTA available",
            "actual_checks": {},
            "drift": drift,
            "next_blocker": "ACQ-TRIAL-CAP-001 gate API not in repo",
            "errors": [],
        },
        {
            "scenario": "after_trial_cap",
            "support": "blocked",
            "runnable": "blocked",
            "tg_user_id": None,
            "portal_url": "http://127.0.0.1:8765/start/?qa_scenario=after_trial_cap",
            "cabinet_url": "",
            "setup_url": "",
            "bot_actions": [],
            "bot_transcript_path": None,
            "expected_behavior": "Trial CTA hidden when cap closed",
            "actual_checks": {},
            "drift": drift,
            "next_blocker": "ACQ-TRIAL-CAP-001",
            "errors": [],
        },
    ]


def _static_checks() -> None:
    src = (OPS / "qa_owner_preview.py").read_text(encoding="utf-8")
    for needle, label in (
        ("_ensure_guards", "guard delegation"),
        ("Journey walkthrough", "journey section"),
        ("CTA transition map", "cta map"),
        ("Start here", "start here section"),
        ("Owner: visually reviewable", "owner count label"),
        ("Matrix: full", "matrix count label"),
        ("investigate_portal_cta_duplication", "cta duplication analysis"),
        ("bot_transcript_reason", "transcript unavailable reason"),
        ("bot_visual_previews", "bot visual preview paths"),
        ("Open Bot Visual Preview", "visual preview journey link"),
        ("Technical raw transcript", "raw transcript collapsible"),
        ("visual preview available", "cta map visual preview status"),
        ("build_preview", "preview builder"),
    ):
        if needle not in src:
            raise AssertionError(f"static check failed: {label} ({needle!r})")
    for bad in ("YOOKASSA_SECRET", "api.telegram.org", "live_", "https://kitsura", "vless://"):
        if bad in src:
            raise AssertionError(f"preview module must not embed {bad!r}")


async def _run_tests() -> None:
    _static_checks()

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "qa_owner.db"
        prod_db = Path(tmp) / "prod_marker.db"
        prod_db.write_text("", encoding="utf-8")
        preview_dir = Path(tmp)
        out = preview_dir / "index.html"

        prev = _set_env(
            BVPN_ENV="production",
            BVPN_QA_TOOLS_ENABLED="1",
            SHOP_BOT_DB_PATH=str(db_path),
            BVPN_PROD_DB_PATH=str(prod_db),
        )
        try:
            mod = _reload_preview()
            try:
                mod._ensure_guards(db_path)
                raise AssertionError("production must block owner preview")
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
            mod = _reload_preview()
            try:
                mod._ensure_guards(db_path)
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
            mod = _reload_preview()
            try:
                mod._ensure_guards(prod_db)
                raise AssertionError("production DB path must be rejected")
            except Exception as exc:
                if "production" not in str(exc).lower() and "refusing" not in str(exc).lower():
                    raise
        finally:
            _restore_env(prev)

        mod = _reload_preview()
        rows = _fixture_rows()
        transcript = preview_dir / "bot" / "paid_wallet_user-menu.md"
        visual = preview_dir / "bot" / "paid_wallet_user-menu.html"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("# Bot transcript\n", encoding="utf-8")
        visual.write_text("<html><body>Bot preview</body></html>", encoding="utf-8")
        mod._resolve_transcripts(rows[0], preview_dir)
        assert rows[0]["bot_transcript_path"] == "bot/paid_wallet_user-menu.md"
        assert rows[0]["bot_transcripts"]["menu"] == "bot/paid_wallet_user-menu.md"
        assert rows[0]["bot_visual_preview_path"] == "bot/paid_wallet_user-menu.html"
        assert rows[0]["bot_visual_previews"]["menu"] == "bot/paid_wallet_user-menu.html"

        matrix_json = preview_dir / "matrix-report.json"
        matrix_json.write_text(
            json.dumps({"scenarios": rows, "generated_at": FIXED_TS}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        html_a = mod.render_html_index(
            rows,
            db_path=db_path,
            generated_at=FIXED_TS,
            portal_base="http://127.0.0.1:8765",
            index_path=out,
            matrix_json_path=matrix_json,
            matrix_summary={"full": 1, "partial": 1, "blocked": 1},
        )
        html_b = mod.render_html_index(
            rows,
            db_path=db_path,
            generated_at=FIXED_TS,
            portal_base="http://127.0.0.1:8765",
            index_path=out,
            matrix_json_path=matrix_json,
            matrix_summary={"full": 1, "partial": 1, "blocked": 1},
        )
        assert html_a == html_b
        assert "Start here" in html_a
        assert "Journey walkthrough" in html_a
        assert "Step 1 — Portal" in html_a
        assert "Step 5 — Final state" in html_a
        assert "CTA transition map" in html_a
        assert "Open Bot Visual Preview" in html_a
        assert 'href="bot/paid_wallet_user-menu.html"' in html_a
        assert "Technical raw transcript" in html_a
        assert 'href="bot/paid_wallet_user-menu.md"' in html_a
        assert "Bot visual preview not available" in html_a
        assert "Owner: visually reviewable: 1" in html_a
        assert "Owner: limited preview: 1" in html_a
        assert "Counts match matrix JSON" in html_a
        assert "Technical JSON" in html_a
        assert "vless://" not in html_a
        assert "kitsura.fun" not in html_a

        cta = mod.investigate_portal_cta_duplication()
        assert cta["fixture_issue"] is False
        assert cta["product_issue"] is True
        assert "cabinet-actions" in cta["root_cause"] or "cabinet-grace" in cta["root_cause"]
        assert "landing-paths" in cta["root_cause"] or "cabinet-grace" in str(cta.get("blocks", []))

        index_html = (ROOT / "web" / "portal" / "index.html").read_text(encoding="utf-8")
        assert 'id="home-cta"' in index_html
        assert 'class="cta hidden" id="home-cta"' in index_html

        instructions = mod.render_open_instructions()
        assert "qa_serve_portal_preview.py" in instructions
        assert "NOT production" in instructions

        result = await mod.build_preview(
            db_path=db_path,
            out_path=out,
            reuse_matrix_json=matrix_json,
            generated_at=FIXED_TS,
        )
        assert out.is_file()
        assert result["summary"]["total"] == 3
        assert result["summary"]["full"] == 1
        saved = out.read_text(encoding="utf-8")
        assert "paid_wallet_user" in saved
        assert FIXED_TS in saved

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
            mod = _reload_preview()
            mod._ensure_guards(db_path)
            built = await mod.build_preview(
                db_path=db_path,
                out_path=preview_dir / "full-index.html",
                scenarios=["paid_wallet_user"],
                reset_seed=True,
                generated_at=FIXED_TS,
            )
            assert built["summary"]["total"] == 1
            row = built["scenarios"][0]
            assert row["portal_url"] and row["cabinet_url"] and row["setup_url"]
            tpath = preview_dir / "bot" / "paid_wallet_user-menu.md"
            vpath = preview_dir / "bot" / "paid_wallet_user-menu.html"
            assert tpath.is_file(), "bot transcript must be generated for paid_wallet_user"
            assert vpath.is_file(), "bot visual preview must be generated for paid_wallet_user"
            assert row.get("bot_transcript_path") == "bot/paid_wallet_user-menu.md"
            assert row.get("bot_visual_preview_path") == "bot/paid_wallet_user-menu.html"
            html_full = (preview_dir / "full-index.html").read_text(encoding="utf-8")
            assert "Open Bot Visual Preview" in html_full
            assert 'href="bot/paid_wallet_user-menu.html"' in html_full
            preview_html = vpath.read_text(encoding="utf-8")
            assert "tg-msg" in preview_html
            assert "Expected next action" in preview_html
            menu_res = await importlib.import_module("qa_bot_fake_tg").run_harness(
                scenario="paid_wallet_user",
                tg_id=None,
                action="menu",
                db_path=db_path,
            )
            labels = [b.label for m in menu_res.outbound for b in m.buttons]
            if labels:
                assert any(lbl in preview_html for lbl in labels[:3])
            dumped = json.dumps(built["scenarios"], ensure_ascii=False)
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


def _run() -> None:
    asyncio.run(_run_tests())


if __name__ == "__main__":
    _run()
    print("ops/test_qa_owner_preview.py: OK")
