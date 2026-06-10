#!/usr/bin/env python3
"""QA customer journey scenario matrix runner (QA-SCENARIO-MATRIX-001).

Chains seed → portal fixtures → bot harness → drift classification.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"

DRIFT_IDENTICAL = (
    "handlers.py / user_messages.py copy paths",
    "portal_cabinet.cabinet_snapshot schema",
    "DB schema + seeded lifecycle fields",
    "portal.js / setup.js frontend (local serve)",
    "ru.json content loader",
)
DRIFT_MOCKED = (
    "Telegram send → capture-only harness",
    "YooKassa → QA-PAYMENT-DRYRUN-001",
    "Remna → QA-REMNA-DRYRUN-001",
    "subscription URLs → sandbox.invalid at harness boundary",
    "isolated QA SQLite only",
)
DRIFT_NOT_VERIFIED = (
    "Real Telegram Mini App WebView",
    "Real YooKassa 3DS / production callbacks",
    "Real Remna routing under RU ISP",
    "Staging bot second-account E2E",
    "LV/AMS Caddy edge",
)


@dataclass
class MatrixScenarioDef:
    support: str
    bot_actions: tuple[str, ...] = ()
    expected_bot: str = ""
    expected_portal: str = ""
    expected_cabinet: str = ""
    expected_setup: str = ""
    expected_cabinet_profile: str | None = None
    expect_cabinet_ok: bool = True
    expect_multi_config_anomaly: bool = False
    expect_terms_required: bool = False
    next_blocker: str = ""
    portal_fixture: bool = True


@dataclass
class MatrixRow:
    scenario: str
    support: str
    runnable: str
    tg_user_id: int | None = None
    email: str | None = None
    phone: str | None = None
    ref_code: str | None = None
    portal_url: str = ""
    cabinet_url: str = ""
    setup_url: str = ""
    bot_actions: list[str] = field(default_factory=list)
    bot_transcript_path: str | None = None
    expected_behavior: str = ""
    actual_checks: dict[str, Any] = field(default_factory=dict)
    drift: dict[str, list[str]] = field(default_factory=dict)
    next_blocker: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MATRIX: dict[str, MatrixScenarioDef] = {
    "new_no_referral": MatrixScenarioDef(
        support="full",
        bot_actions=("start",),
        expected_bot="Terms agreement screen on /start",
        expected_portal="Landing without referral block",
        expected_cabinet="terms_required until bot /start + accept",
        expect_cabinet_ok=False,
        expect_terms_required=True,
    ),
    "new_from_referral": MatrixScenarioDef(
        support="full",
        bot_actions=("start_with_ref",),
        expected_bot="Referral linked; terms or menu",
        expected_portal="?ref=QA_REF_INVITER welcome",
        expected_cabinet="terms_required until bot /start + accept",
        expect_cabinet_ok=False,
        expect_terms_required=True,
    ),
    "existing_tg_user": MatrixScenarioDef(
        support="full",
        bot_actions=("menu", "status"),
        expected_bot="Returning user main menu + account status",
        expected_cabinet="Active config + balance",
    ),
    "web_lead_without_tg_bind": MatrixScenarioDef(
        support="full",
        bot_actions=(),
        expected_portal="Web trial path; needs_telegram_bind",
        expected_cabinet="cabinet by email; web_only",
    ),
    "trial_eligible_before_cap": MatrixScenarioDef(
        support="partial",
        bot_actions=("menu",),
        expected_bot="Trial CTA available",
        expected_portal="Trial CTAs visible",
        next_blocker="ACQ-TRIAL-CAP-001 gate API not in repo",
    ),
    "after_trial_cap": MatrixScenarioDef(
        support="blocked",
        bot_actions=(),
        expected_portal="Trial CTA hidden when cap closed",
        portal_fixture=True,
        next_blocker="ACQ-TRIAL-CAP-001 — trial cap gate not implemented",
    ),
    "temporary_1d_active": MatrixScenarioDef(
        support="full",
        bot_actions=(),
        expected_cabinet="Web temp access active (~1d)",
    ),
    "temporary_1d_expired": MatrixScenarioDef(
        support="full",
        bot_actions=(),
        expected_cabinet="Expired temp configuration",
        expected_cabinet_profile="expired",
    ),
    "temporary_converted_to_paid": MatrixScenarioDef(
        support="partial",
        bot_actions=(),
        expected_cabinet="Wallet state seeded directly",
        expected_cabinet_profile="wallet",
        next_blocker="QA-PAYMENT-WEBHOOK-001 / ACQ paid conversion path",
    ),
    "paid_wallet_user": MatrixScenarioDef(
        support="full",
        bot_actions=("menu", "status", "get_setup"),
        expected_cabinet_profile="wallet",
        expected_bot="Wallet menu + setup link",
    ),
    "insufficient_balance_user": MatrixScenarioDef(
        support="full",
        bot_actions=("menu", "status", "topup"),
        expected_cabinet_profile="wallet",
        expected_bot="Low balance + top-up keyboard",
    ),
    "expired_stopped_user": MatrixScenarioDef(
        support="full",
        bot_actions=("menu", "status"),
        expected_cabinet_profile="expired",
    ),
    "legacy_manual_user": MatrixScenarioDef(
        support="full",
        bot_actions=("status",),
        expected_cabinet_profile="legacy",
    ),
    "user_without_config": MatrixScenarioDef(
        support="full",
        bot_actions=("menu", "get_setup"),
        expected_cabinet_profile=None,
    ),
    "user_one_active_config": MatrixScenarioDef(
        support="full",
        bot_actions=("get_setup", "status"),
        expected_cabinet_profile="wallet",
    ),
    "user_multiple_device_configs": MatrixScenarioDef(
        support="full",
        bot_actions=("status",),
        expect_multi_config_anomaly=True,
    ),
    "referral_inviter_view": MatrixScenarioDef(
        support="full",
        bot_actions=("invite",),
        expected_bot="Referral invite link + count",
    ),
    "referral_invitee_view": MatrixScenarioDef(
        support="full",
        bot_actions=("start_with_ref", "status"),
    ),
    "referrer_reward_not_live": MatrixScenarioDef(
        support="full",
        bot_actions=("invite",),
        expected_bot="No hidden invitee +3d bonus copy",
        next_blocker="REF-BONUS-001 deferred",
    ),
    "slots_counter_states": MatrixScenarioDef(
        support="blocked",
        bot_actions=(),
        expected_portal="Slots card via qa_capacity_fixture on localhost",
        next_blocker="Production capacity API / ACQ slot gate not wired",
    ),
}


def _ensure_guards(db_path: Path) -> Path:
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import qa_portal_fixtures as qpf

    return qpf._ensure_guards(db_path)


def _resolve_db_path(cli_db: str | None) -> Path:
    import qa_portal_fixtures as qpf

    return qpf._resolve_db_path(cli_db)


def _seed_db(db_path: Path, *, reset: bool, scenario: str | None) -> int:
    import qa_seed_scenarios as seed

    seed._apply_db_path(db_path)
    conn = seed._init_db(db_path)
    removed = 0
    try:
        if reset:
            removed = seed.reset_qa_scenarios(conn)
        if scenario:
            seed.seed_scenario(conn, scenario)
        else:
            seed.seed_all_scenarios(conn)
    finally:
        conn.close()
    return removed


def _upsert_legal_settings() -> None:
    from shop_bot.data_manager.database import upsert_setting

    upsert_setting("terms_url", "https://sandbox.invalid/terms")
    upsert_setting("privacy_url", "https://sandbox.invalid/privacy")


def _resolve_portal(scenario: str, db_path: Path):
    import qa_portal_fixtures as qpf

    specs = qpf._scenario_specs()
    if scenario in specs:
        return qpf.resolve_fixture(scenario, db_path=db_path)
    return _synthetic_portal_fixture(scenario, db_path)


def _synthetic_portal_fixture(scenario: str, db_path: Path):
    """Portal URLs for scenarios not in qa_portal_fixtures._scenario_specs."""
    import qa_portal_fixtures as qpf
    from qa_bot_fake_tg import SCENARIO_TG_ID

    cfg = MATRIX[scenario]
    tid = SCENARIO_TG_ID.get(scenario)
    email = None
    if scenario == "web_lead_without_tg_bind":
        email = qpf._qa_email("web-lead-unbound")
    elif scenario == "temporary_converted_to_paid":
        email = qpf._qa_email("temp-converted-paid")
    elif scenario == "existing_tg_user":
        tid = SCENARIO_TG_ID.get("existing_tg_user", 900_000_003)

    params: dict[str, str | int | None] = {"qa_scenario": scenario}
    ref = None
    if scenario in ("referral_inviter_view", "referral_invitee_view", "new_from_referral"):
        ref = qpf.QA_REF_INVITER

    urls = {
        "portal": qpf._build_url("/start/", {**params, **({"ref": ref} if ref else {})}),
        "cabinet": qpf._build_url(
            "/portal/cabinet.html",
            {**params, **({"tid": tid} if tid else {}), **({"email": email} if email else {})},
        ),
        "setup": qpf._build_url("/setup", {**params, **({"tid": tid} if tid else {})}),
    }
    snap = None
    if tid or email:
        snap = qpf.cabinet_api_response(
            telegram_id=tid if tid and tid > 0 else None,
            email=email or "",
            db_path=db_path,
        )
    return qpf.PortalPreviewFixture(
        name=scenario,
        support=cfg.support,
        tg_user_id=tid if tid and tid > 0 else None,
        email=email,
        ref_code=ref,
        expected_portal=cfg.expected_portal,
        expected_cabinet=cfg.expected_cabinet,
        expected_setup=cfg.expected_setup,
        limitations=cfg.next_blocker,
        urls=urls,
        cabinet_snapshot=snap,
    )


def _drift_payload() -> dict[str, list[str]]:
    return {
        "production_identical": list(DRIFT_IDENTICAL),
        "dry_run_mocked": list(DRIFT_MOCKED),
        "not_verified_without_staging_or_prod": list(DRIFT_NOT_VERIFIED),
    }


def _run_checks(
    scenario: str,
    cfg: MatrixScenarioDef,
    portal_row,
    bot_results: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, Any] = {"seed": "skipped"}
    snap = portal_row.cabinet_snapshot

    if cfg.support != "blocked":
        checks["seed"] = "ok" if snap is not None or not cfg.expect_cabinet_ok else "no_snapshot"

    if snap is not None:
        checks["cabinet_ok"] = bool(snap.get("ok"))
        checks["billing_profile"] = snap.get("billing_profile")
        checks["active_config_count"] = snap.get("active_config_count")
        checks["multiple_configs_anomaly"] = snap.get("multiple_configs_anomaly")
        if cfg.expected_cabinet_profile:
            checks["profile_match"] = snap.get("billing_profile") == cfg.expected_cabinet_profile
        if cfg.expect_multi_config_anomaly:
            checks["anomaly_match"] = bool(snap.get("multiple_configs_anomaly"))
        if cfg.expect_terms_required:
            checks["terms_required"] = snap.get("error") == "terms_required"
        dumped = json.dumps(snap, ensure_ascii=False)
        checks["no_real_sub_url"] = "vless://" not in dumped and "kitsura.fun" not in dumped

    for action, result in bot_results.items():
        checks[f"bot_{action}"] = {
            "outbound_count": len(result.get("outbound", [])),
            "errors": result.get("errors", []),
        }

    return checks


def _classify_runnable(cfg: MatrixScenarioDef, checks: dict[str, Any], errors: list[str]) -> str:
    if cfg.support == "blocked":
        return "blocked"
    if errors:
        return "partial" if cfg.support == "full" else cfg.support
    if cfg.support == "partial":
        return "partial"
    if cfg.expect_cabinet_ok and checks.get("cabinet_ok") is False:
        return "partial"
    if cfg.expected_cabinet_profile and checks.get("profile_match") is False:
        return "partial"
    if cfg.expect_multi_config_anomaly and not checks.get("anomaly_match"):
        return "partial"
    if cfg.expect_terms_required and not checks.get("terms_required"):
        return "partial"
    bot_checks = [v for k, v in checks.items() if k.startswith("bot_")]
    if bot_checks and any(v.get("errors") for v in bot_checks):
        return "partial"
    return "full"


_EXTRA_BOT_TG: dict[str, int] = {"existing_tg_user": 900_000_003}


async def _run_bot_actions(
    scenario: str,
    actions: tuple[str, ...],
    db_path: Path,
    transcript_dir: Path | None,
) -> dict[str, Any]:
    import qa_bot_fake_tg as bot

    use_scenario = scenario if scenario in bot.SCENARIO_TG_ID else None
    use_tg = None if use_scenario else _EXTRA_BOT_TG.get(scenario)

    results: dict[str, Any] = {}
    for action in actions:
        try:
            result = await bot.run_harness(
                scenario=use_scenario,
                tg_id=use_tg,
                action=action,
                db_path=db_path,
                fresh_start=False,
            )
            payload = result.to_dict()
            if transcript_dir and (scenario in bot.SCENARIO_TG_ID or scenario in _EXTRA_BOT_TG):
                path = transcript_dir / f"{scenario}-{action}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(bot.render_transcript(result), encoding="utf-8")
                payload["transcript_path"] = str(path)
            results[action] = payload
        except Exception as exc:
            results[action] = {"errors": [str(exc)], "outbound": []}
    return results


async def run_scenario(
    scenario: str,
    *,
    db_path: Path,
    transcript_dir: Path | None = None,
    seeded: bool = True,
) -> MatrixRow:
    key = scenario.strip().lower()
    if key not in MATRIX:
        raise ValueError(f"Unknown scenario {scenario!r}")

    cfg = MATRIX[key]
    errors: list[str] = []

    if not seeded:
        _seed_db(db_path, reset=True, scenario=key)

    portal_row = _resolve_portal(key, db_path)

    bot_results: dict[str, Any] = {}
    transcript_path = None
    if cfg.bot_actions and (key in __import__("qa_bot_fake_tg", fromlist=["SCENARIO_TG_ID"]).SCENARIO_TG_ID or key in _EXTRA_BOT_TG):
        _upsert_legal_settings()
        bot_results = await _run_bot_actions(key, cfg.bot_actions, db_path, transcript_dir)
        for br in bot_results.values():
            if br.get("transcript_path"):
                transcript_path = br["transcript_path"]
            if br.get("errors"):
                errors.extend(br["errors"])

    checks = _run_checks(key, cfg, portal_row, bot_results)
    runnable = _classify_runnable(cfg, checks, errors)

    expected_parts = [
        p
        for p in (cfg.expected_bot, cfg.expected_portal, cfg.expected_cabinet, cfg.expected_setup)
        if p
    ]

    return MatrixRow(
        scenario=key,
        support=cfg.support,
        runnable=runnable,
        tg_user_id=portal_row.tg_user_id,
        email=portal_row.email,
        ref_code=portal_row.ref_code,
        portal_url=portal_row.urls.get("portal", ""),
        cabinet_url=portal_row.urls.get("cabinet", ""),
        setup_url=portal_row.urls.get("setup", ""),
        bot_actions=list(cfg.bot_actions),
        bot_transcript_path=transcript_path,
        expected_behavior="; ".join(expected_parts) or portal_row.expected_cabinet,
        actual_checks=checks,
        drift=_drift_payload(),
        next_blocker=cfg.next_blocker or portal_row.limitations,
        errors=errors,
    )


async def run_matrix(
    *,
    db_path: Path,
    scenarios: list[str] | None = None,
    reset_seed: bool = True,
    transcript_dir: Path | None = None,
) -> list[MatrixRow]:
    import qa_seed_scenarios as seed

    _ensure_guards(db_path)
    if reset_seed:
        _seed_db(db_path, reset=True, scenario=None)
    _upsert_legal_settings()

    names = scenarios or seed.SCENARIO_ORDER
    rows: list[MatrixRow] = []
    for name in names:
        rows.append(
            await run_scenario(name, db_path=db_path, transcript_dir=transcript_dir, seeded=True)
        )
    return rows


def render_markdown_report(rows: list[MatrixRow], *, db_path: Path) -> str:
    counts = {"full": 0, "partial": 0, "blocked": 0}
    for row in rows:
        counts[row.runnable] = counts.get(row.runnable, 0) + 1

    lines = [
        "# QA Customer Journey Matrix Report",
        "",
        f"- **generated:** {datetime.now(timezone.utc).isoformat()}",
        f"- **db:** `{db_path}`",
        f"- **scenarios:** {len(rows)}",
        f"- **runnable full:** {counts.get('full', 0)}",
        f"- **runnable partial:** {counts.get('partial', 0)}",
        f"- **blocked:** {counts.get('blocked', 0)}",
        "",
        "## Drift summary (all scenarios)",
        "",
        "### Production-identical",
        *[f"- {x}" for x in DRIFT_IDENTICAL],
        "",
        "### Dry-run / mocked boundaries",
        *[f"- {x}" for x in DRIFT_MOCKED],
        "",
        "### Not verified without staging/prod approval",
        *[f"- {x}" for x in DRIFT_NOT_VERIFIED],
        "",
        "## Scenarios",
        "",
    ]

    for row in rows:
        lines.extend(
            [
                f"### {row.scenario} — **{row.support}** -> runnable **{row.runnable}**",
                "",
                f"- tg_user_id: `{row.tg_user_id or '-'}`",
                f"- email: `{row.email or '-'}`",
                f"- ref_code: `{row.ref_code or '-'}`",
                f"- portal: {row.portal_url or '-'}",
                f"- cabinet: {row.cabinet_url or '-'}",
                f"- setup: {row.setup_url or '-'}",
                f"- bot_actions: `{', '.join(row.bot_actions) or '-'}`",
            ]
        )
        if row.bot_transcript_path:
            lines.append(f"- bot_transcript: `{row.bot_transcript_path}`")
        lines.append(f"- expected: {row.expected_behavior or '-'}")
        if row.next_blocker:
            lines.append(f"- next_blocker: {row.next_blocker}")
        if row.errors:
            lines.append(f"- errors: {row.errors}")
        lines.append(f"- checks: `{json.dumps(row.actual_checks, ensure_ascii=False)}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def list_scenarios() -> None:
    import qa_seed_scenarios as seed

    for name in seed.SCENARIO_ORDER:
        cfg = MATRIX.get(name)
        if not cfg:
            print(f"{name:32} MISSING_CONFIG")
            continue
        print(f"{name:32} {cfg.support:7} bot={len(cfg.bot_actions)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA customer journey scenario matrix")
    parser.add_argument("--db", help="SQLite path")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--scenario", help="Run one scenario")
    parser.add_argument("--out", help="Markdown report path")
    parser.add_argument("--json-out", help="JSON report path")
    parser.add_argument("--transcript-dir", help="Directory for bot transcript markdown files")
    parser.add_argument("--no-reset", action="store_true", help="Skip DB reset before --run-all")
    args = parser.parse_args(argv)

    if args.list:
        list_scenarios()
        return 0

    if not args.run_all and not args.scenario:
        parser.error("Specify --list, --run-all, or --scenario NAME")

    db_path = _resolve_db_path(args.db)
    _ensure_guards(db_path)
    print(f"QA matrix target DB: {db_path}")

    transcript_dir = Path(args.transcript_dir) if args.transcript_dir else None

    if args.run_all:
        rows = asyncio.run(
            run_matrix(
                db_path=db_path,
                reset_seed=not args.no_reset,
                transcript_dir=transcript_dir,
            )
        )
    else:
        if not args.no_reset:
            _seed_db(db_path, reset=True, scenario=args.scenario)
        rows = [
            asyncio.run(
                run_scenario(
                    args.scenario,
                    db_path=db_path,
                    transcript_dir=transcript_dir,
                    seeded=True,
                )
            )
        ]

    md = render_markdown_report(rows, db_path=db_path)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "summary": {
            "total": len(rows),
            "full": sum(1 for r in rows if r.runnable == "full"),
            "partial": sum(1 for r in rows if r.runnable == "partial"),
            "blocked": sum(1 for r in rows if r.runnable == "blocked"),
        },
        "drift": _drift_payload(),
        "scenarios": [r.to_dict() for r in rows],
    }
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"Markdown report: {out}")
    if args.json_out:
        jout = Path(args.json_out)
        jout.parent.mkdir(parents=True, exist_ok=True)
        jout.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"JSON report: {jout}")
    try:
        print(md)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(md.encode("utf-8", errors="replace") + b"\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
