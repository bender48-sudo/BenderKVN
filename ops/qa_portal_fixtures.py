#!/usr/bin/env python3
"""QA portal/cabinet/setup fixture resolver (QA-PORTAL-FIXTURES-001).

Resolves seeded scenario states to preview URLs and cabinet API payloads.
Uses real portal_cabinet.cabinet_snapshot shapes against isolated QA DB.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"
OPS = ROOT / "ops"

QA_REF_INVITER = "QA_REF_INVITER"
QA_EMAIL_DOMAIN = "sandbox.invalid"
DEFAULT_LOCAL_BASE = "http://127.0.0.1:8765"
_PREVIEW_INDEX = OPS / "qa_portal_preview_index.json"

CAPACITY_FIXTURES: dict[str, dict[str, Any]] = {
    "slots_high": {
        "ok": True,
        "registration_open": True,
        "remaining_slots": 25_000,
        "active_configurations": 5_000,
        "access_cap": 30_000,
        "fixture": "slots_high",
    },
    "slots_low": {
        "ok": True,
        "registration_open": True,
        "remaining_slots": 120,
        "active_configurations": 29_880,
        "access_cap": 30_000,
        "fixture": "slots_low",
    },
    "slots_zero": {
        "ok": True,
        "registration_open": False,
        "remaining_slots": 0,
        "active_configurations": 30_000,
        "access_cap": 30_000,
        "fixture": "slots_zero",
    },
}

TRIAL_CAP_FIXTURES: dict[str, dict[str, Any]] = {
    "trial_cap_open": {
        "ok": True,
        "trial_open": True,
        "fixture": "trial_cap_open",
        "note": "Placeholder — ACQ-TRIAL-CAP-001 gate API not in repo",
    },
    "trial_cap_closed": {
        "ok": True,
        "trial_open": False,
        "fixture": "trial_cap_closed",
        "note": "Placeholder — ACQ-TRIAL-CAP-001 gate API not in repo",
    },
}


def _bootstrap_shop_bot() -> None:
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import types

    if "shop_bot" not in sys.modules:
        pkg = types.ModuleType("shop_bot")
        pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
        sys.modules["shop_bot"] = pkg
    if "shop_bot.data_manager" not in sys.modules:
        import importlib

        database = importlib.import_module("database")
        dm = types.ModuleType("shop_bot.data_manager")
        dm.database = database
        sys.modules["shop_bot.data_manager"] = dm
        sys.modules["shop_bot.data_manager.database"] = database
    if "shop_bot.runtime_env" not in sys.modules:
        import importlib

        importlib.import_module("runtime_env")
        sys.modules["shop_bot.runtime_env"] = sys.modules["runtime_env"]
    if "shop_bot.portal_cabinet" not in sys.modules:
        import importlib

        for mod in ("config", "subscription_profile", "web_trial_db"):
            importlib.import_module(mod)
            sys.modules[f"shop_bot.{mod}"] = sys.modules[mod]
        importlib.import_module("portal_cabinet")
        sys.modules["shop_bot.portal_cabinet"] = sys.modules["portal_cabinet"]


def _ensure_guards(db_path: Path) -> Path:
    _bootstrap_shop_bot()
    from shop_bot.runtime_env import (
        assert_db_path_allowed_for_qa,
        require_non_production,
        require_qa_tooling_enabled,
    )

    require_non_production("qa_portal_fixtures")
    require_qa_tooling_enabled("qa_portal_fixtures")
    resolved = db_path.expanduser().resolve()
    assert_db_path_allowed_for_qa(resolved, "qa_portal_fixtures")
    return resolved


def _apply_db_path(db_path: Path) -> None:
    os.environ["SHOP_BOT_DB_PATH"] = str(db_path)
    _bootstrap_shop_bot()
    from shop_bot.data_manager import database as dbmod

    dbmod.DB_FILE = db_path
    dbmod.DATA_DIR = db_path.parent


def _resolve_db_path(cli_db: str | None) -> Path:
    if cli_db:
        return Path(cli_db).expanduser().resolve()
    override = (os.getenv("SHOP_BOT_DB_PATH") or os.getenv("BVPN_QA_DB_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (ROOT / "data" / "shop_bot_qa.db").resolve()


def _portal_base() -> str:
    return (os.getenv("BVPN_QA_PORTAL_BASE") or DEFAULT_LOCAL_BASE).rstrip("/")


def _qa_email(slug: str) -> str:
    return f"qa+{slug}@{QA_EMAIL_DOMAIN}"


@dataclass
class PortalPreviewFixture:
    name: str
    support: str
    tg_user_id: int | None = None
    email: str | None = None
    ref_code: str | None = None
    capacity_fixture: str | None = None
    trial_cap_fixture: str | None = None
    expected_portal: str = ""
    expected_cabinet: str = ""
    expected_setup: str = ""
    limitations: str = ""
    urls: dict[str, str] = field(default_factory=dict)
    cabinet_snapshot: dict[str, Any] | None = None
    capacity_payload: dict[str, Any] | None = None
    trial_cap_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _scenario_specs() -> dict[str, dict[str, Any]]:
    from qa_bot_fake_tg import SCENARIO_TG_ID

    return {
        "new_no_referral": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["new_no_referral"],
            "expected_portal": "Landing; no referral block; bot CTA",
            "expected_cabinet": "terms_required or grace until /start in bot",
            "expected_setup": "Signup paths visible",
            "limitations": "Cabinet needs bot terms acceptance for full TG cabinet",
        },
        "new_from_referral": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["new_from_referral"],
            "ref_code": QA_REF_INVITER,
            "expected_portal": "Referral welcome block; ref preserved in localStorage",
            "expected_cabinet": "Invited user; terms flow",
            "expected_setup": "ref_code passed on web trial signup",
        },
        "trial_eligible_before_cap": {
            "support": "partial",
            "tg_user_id": SCENARIO_TG_ID["trial_eligible_before_cap"],
            "trial_cap_fixture": "trial_cap_open",
            "expected_portal": "Trial CTAs visible",
            "expected_cabinet": "No config; trial eligible in bot",
            "limitations": "ACQ-TRIAL-CAP-001 gate not wired — trial_cap fixture is placeholder only",
        },
        "paid_wallet_user": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["paid_wallet_user"],
            "expected_cabinet": "billing_profile=wallet; balance visible",
            "expected_setup": "Telegram setup available",
        },
        "insufficient_balance_user": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["insufficient_balance_user"],
            "expected_cabinet": "wallet; low days_left; top-up CTA",
        },
        "expired_stopped_user": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["expired_stopped_user"],
            "expected_cabinet": "billing_profile=expired; expired configuration",
        },
        "legacy_manual_user": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["legacy_manual_user"],
            "expected_cabinet": "billing_profile=legacy; frozen balance display",
        },
        "user_without_config": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["user_without_config"],
            "expected_cabinet": "Empty configurations; trial/setup CTA",
        },
        "user_one_active_config": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["user_one_active_config"],
            "expected_cabinet": "active_config_count=1",
            "expected_setup": "Primary setup link",
        },
        "user_multiple_device_configs": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["user_multiple_device_configs"],
            "expected_cabinet": "multiple_configs_anomaly=true",
        },
        "referral_inviter_view": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["referral_inviter_view"],
            "ref_code": QA_REF_INVITER,
            "expected_portal": "Share ref=QA_REF_INVITER link",
        },
        "referral_invitee_view": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["referral_invitee_view"],
            "ref_code": QA_REF_INVITER,
            "expected_portal": "Referral welcome for invitee",
            "expected_cabinet": "referred_by set; trial profile",
        },
        "referrer_reward_not_live": {
            "support": "full",
            "tg_user_id": SCENARIO_TG_ID["referrer_reward_not_live"],
            "expected_portal": "No hidden invitee bonus copy",
            "limitations": "REF-BONUS-001 deferred; flags OFF in config",
        },
        "temporary_1d_active": {
            "support": "full",
            "email": _qa_email("temp-1d-active"),
            "expected_cabinet": "Web-only temp access active",
            "expected_setup": "Email recover / setup path",
        },
        "temporary_1d_expired": {
            "support": "full",
            "email": _qa_email("temp-1d-expired"),
            "expected_cabinet": "Expired temp configuration",
        },
        "after_trial_cap": {
            "support": "blocked",
            "trial_cap_fixture": "trial_cap_closed",
            "expected_portal": "Trial CTA should hide when cap closed",
            "limitations": "ACQ-TRIAL-CAP-001 — portal gate API missing; use qa_trial_cap_fixture URL param on localhost only",
        },
        "slots_counter_states": {
            "support": "blocked",
            "capacity_fixture": "slots_low",
            "expected_portal": "Slots card with remaining count",
            "limitations": "Use qa_capacity_fixture=slots_high|slots_low|slots_zero on localhost; meta.capacity_api_enabled still false in ru.json — fixture param bypasses API",
        },
    }


def _build_url(path: str, params: dict[str, str | int | None]) -> str:
    base = _portal_base()
    clean = {k: str(v) for k, v in params.items() if v is not None and str(v) != ""}
    clean.setdefault("qa_scenario", "")
    if clean.get("qa_scenario") == "":
        clean.pop("qa_scenario", None)
    qs = urlencode(clean)
    return f"{base}{path}" + (f"?{qs}" if qs else "")


def _normalize_vpn_key_expiry_for_handlers(tg_id: int) -> None:
    from shop_bot.data_manager.database import db_connection

    with db_connection() as conn:
        rows = conn.execute(
            "SELECT key_id, expiry_date FROM vpn_keys WHERE user_id = ?",
            (tg_id,),
        ).fetchall()
        for key_id, raw in rows:
            if not raw:
                continue
            text = str(raw).replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                continue
            if dt.tzinfo is not None:
                naive = dt.replace(tzinfo=None).isoformat(sep=" ")
                conn.execute(
                    "UPDATE vpn_keys SET expiry_date = ? WHERE key_id = ?",
                    (naive, key_id),
                )
        conn.commit()


def cabinet_api_response(
    *,
    telegram_id: int | None = None,
    email: str = "",
    customer_id: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return cabinet_snapshot dict for /setup/api/cabinet (no secrets)."""
    if db_path is not None:
        _apply_db_path(db_path)
    from shop_bot.portal_cabinet import cabinet_snapshot

    tid = int(telegram_id) if telegram_id else 0
    if tid > 0:
        _normalize_vpn_key_expiry_for_handlers(tid)
        return cabinet_snapshot(telegram_id=tid)
    return cabinet_snapshot(customer_id=customer_id, email=email)


def resolve_fixture(
    scenario: str,
    *,
    db_path: Path | None = None,
) -> PortalPreviewFixture:
    key = scenario.strip().lower()
    specs = _scenario_specs()
    if key not in specs:
        raise ValueError(f"Unknown scenario {scenario!r}. Use --list.")

    spec = dict(specs[key])
    support = spec.pop("support")
    tid = spec.get("tg_user_id")
    email = spec.get("email")
    ref = spec.get("ref_code")
    cap_fx = spec.get("capacity_fixture")
    trial_fx = spec.get("trial_cap_fixture")

    params_base: dict[str, str | int | None] = {"qa_scenario": key}
    urls = {
        "portal": _build_url("/start/", {**params_base, **({"ref": ref} if ref else {})}),
        "cabinet": _build_url(
            "/portal/cabinet.html",
            {**params_base, **({"tid": tid} if tid else {}), **({"email": email} if email else {})},
        ),
        "setup": _build_url(
            "/setup",
            {**params_base, **({"tid": tid} if tid else {})},
        ),
        "guide": _build_url("/portal/guide.html", params_base),
    }
    if cap_fx:
        urls["portal_slots"] = _build_url(
            "/start/",
            {**params_base, "qa_capacity_fixture": cap_fx},
        )
    if trial_fx:
        urls["portal_trial_cap"] = _build_url(
            "/start/",
            {**params_base, "qa_trial_cap_fixture": trial_fx},
        )

    snap = None
    if db_path is not None and (tid or email):
        try:
            snap = cabinet_api_response(
                telegram_id=tid if tid else None,
                email=email or "",
                db_path=db_path,
            )
        except Exception as exc:
            spec["limitations"] = (
                (spec.get("limitations") or "")
                + f" cabinet_snapshot failed: {exc}"
            ).strip()

    return PortalPreviewFixture(
        name=key,
        support=support,
        tg_user_id=tid,
        email=email,
        ref_code=ref,
        capacity_fixture=cap_fx,
        trial_cap_fixture=trial_fx,
        expected_portal=spec.get("expected_portal", ""),
        expected_cabinet=spec.get("expected_cabinet", ""),
        expected_setup=spec.get("expected_setup", ""),
        limitations=spec.get("limitations", ""),
        urls=urls,
        cabinet_snapshot=snap,
        capacity_payload=CAPACITY_FIXTURES.get(cap_fx or ""),
        trial_cap_payload=TRIAL_CAP_FIXTURES.get(trial_fx or ""),
    )


def list_scenarios() -> None:
    for name, spec in _scenario_specs().items():
        print(f"{name:32} {spec['support']:7} tg={spec.get('tg_user_id', '-')}")


def seed_preview_index(
    *,
    db_path: Path,
    out_path: Path | None = None,
) -> Path:
    fixtures = [resolve_fixture(name, db_path=db_path) for name in _scenario_specs()]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portal_base": _portal_base(),
        "serve_hint": "python ops/qa_serve_portal_preview.py",
        "scenarios": [f.to_dict() for f in fixtures],
    }
    target = out_path or _PREVIEW_INDEX
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def print_fixture(fixture: PortalPreviewFixture) -> None:
    print(f"scenario: {fixture.name} ({fixture.support})")
    if fixture.tg_user_id:
        print(f"tg_user_id: {fixture.tg_user_id}")
    if fixture.email:
        print(f"email: {fixture.email}")
    if fixture.ref_code:
        print(f"ref_code: {fixture.ref_code}")
    if fixture.expected_portal:
        print(f"expected_portal: {fixture.expected_portal}")
    if fixture.expected_cabinet:
        print(f"expected_cabinet: {fixture.expected_cabinet}")
    if fixture.expected_setup:
        print(f"expected_setup: {fixture.expected_setup}")
    if fixture.limitations:
        print(f"limitations: {fixture.limitations}")
    print("urls:")
    for label, url in fixture.urls.items():
        print(f"  {label}: {url}")
    if fixture.cabinet_snapshot is not None:
        profile = fixture.cabinet_snapshot.get("billing_profile", "-")
        ok = fixture.cabinet_snapshot.get("ok")
        print(f"cabinet_snapshot: ok={ok} billing_profile={profile}")
    if fixture.capacity_payload:
        print(f"capacity_fixture: {json.dumps(fixture.capacity_payload, ensure_ascii=False)}")
    if fixture.trial_cap_payload:
        print(f"trial_cap_fixture: {json.dumps(fixture.trial_cap_payload, ensure_ascii=False)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA portal/cabinet fixture preview")
    parser.add_argument("--db", help="SQLite path (SHOP_BOT_DB_PATH)")
    parser.add_argument("--scenario", help="Scenario name")
    parser.add_argument("--list", action="store_true", help="List portal scenarios")
    parser.add_argument("--print-urls", action="store_true", help="Print preview URLs for scenario")
    parser.add_argument("--seed-preview-index", action="store_true", help="Write preview index JSON")
    parser.add_argument("--index-out", help="Preview index output path")
    args = parser.parse_args(argv)

    if args.list:
        list_scenarios()
        return 0

    db_path = _resolve_db_path(args.db)
    db_path = _ensure_guards(db_path)
    print(f"QA portal fixtures target DB: {db_path}")

    if args.seed_preview_index:
        out = seed_preview_index(db_path=db_path, out_path=Path(args.index_out) if args.index_out else None)
        print(f"Preview index written: {out}")
        return 0

    if not args.scenario:
        parser.error("Specify --scenario NAME, --list, or --seed-preview-index")

    fixture = resolve_fixture(args.scenario, db_path=db_path)
    if args.print_urls or not args.seed_preview_index:
        print_fixture(fixture)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
