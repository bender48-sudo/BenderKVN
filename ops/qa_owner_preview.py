#!/usr/bin/env python3
"""Owner-friendly customer journey visual preview index (QA-OWNER-PREVIEW-001).

End-to-end journey walkthrough per scenario: portal -> bot -> cabinet -> setup -> final state.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
DEFAULT_OUT = ROOT / "screenshots" / "qa-preview" / "index.html"

START_HERE_SCENARIOS = (
    "new_no_referral",
    "new_from_referral",
    "paid_wallet_user",
    "user_one_active_config",
    "expired_stopped_user",
    "insufficient_balance_user",
    "temporary_1d_active",
    "temporary_1d_expired",
)

SCENARIO_LABELS: dict[str, str] = {
    "new_no_referral": "New user (no referral)",
    "new_from_referral": "New user (referral invitee)",
    "existing_tg_user": "Returning Telegram user",
    "web_lead_without_tg_bind": "Web lead (no Telegram bind)",
    "trial_eligible_before_cap": "Trial eligible (before cap)",
    "after_trial_cap": "After trial cap closed",
    "temporary_1d_active": "Temporary 1-day access (active)",
    "temporary_1d_expired": "Temporary 1-day access (expired)",
    "temporary_converted_to_paid": "Temp access converted to paid",
    "paid_wallet_user": "Paid wallet user",
    "insufficient_balance_user": "Insufficient balance",
    "expired_stopped_user": "Expired / stopped subscription",
    "legacy_manual_user": "Legacy manual user",
    "user_without_config": "User without VPN config",
    "user_one_active_config": "User with one active config",
    "user_multiple_device_configs": "User with multiple device configs",
    "referral_inviter_view": "Referral inviter view",
    "referral_invitee_view": "Referral invitee view",
    "referrer_reward_not_live": "Referrer reward (not live)",
    "slots_counter_states": "Slots counter states",
}

GROUP_ORDER = ("full", "partial", "blocked")
MATRIX_GROUP_LABELS = {
    "full": "Matrix: full",
    "partial": "Matrix: partial",
    "blocked": "Matrix: blocked",
}
OWNER_GROUP_LABELS = {
    "full": "Owner: visually reviewable",
    "partial": "Owner: limited preview",
    "blocked": "Owner: blocked",
}
GROUP_HINTS = {
    "full": "Follow the journey steps while qa_serve_portal_preview.py is running.",
    "partial": "Walkthrough shows what is visible; backend gap noted in each scenario.",
    "blocked": "Fixture URLs only — scenario not end-to-end testable yet.",
}

PORTAL_CTA_DUPLICATION_BACKLOG = "PORTAL-LANDING-CTA-DEDUP-001"  # resolved repo — browser landing UX


def _ensure_guards(db_path: Path) -> Path:
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import qa_scenario_matrix as matrix

    return matrix._ensure_guards(db_path)


def _resolve_db_path(cli_db: str | None) -> Path:
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import qa_portal_fixtures as qpf

    return qpf._resolve_db_path(cli_db)


def _scenario_label(name: str) -> str:
    return SCENARIO_LABELS.get(name, name.replace("_", " ").title())


def _user_status(row: dict[str, Any]) -> str:
    checks = row.get("actual_checks") or {}
    profile = checks.get("billing_profile")
    if profile:
        return str(profile)
    if checks.get("terms_required"):
        return "terms_required"
    if row.get("email"):
        return "web_only"
    if row.get("tg_user_id"):
        return "telegram_user"
    return row.get("runnable", "unknown")


def investigate_portal_cta_duplication() -> dict[str, Any]:
    """Document portal landing CTA duplication root cause (QA-OWNER-PREVIEW-FIX-001)."""
    index_html = (ROOT / "web" / "portal" / "index.html").read_text(encoding="utf-8")
    portal_js = (ROOT / "web" / "portal" / "assets" / "portal.js").read_text(encoding="utf-8")
    blocks = []
    if 'id="landing-paths"' in index_html:
        blocks.append("landing-paths (primary browser acquisition: Telegram + email 1d)")
    if 'id="home-cta"' in index_html:
        blocks.append("home-cta (legacy CTA block; hidden when landing-paths active)")
    if 'id="account-fold"' in index_html:
        blocks.append("account-fold inline cabinet (bot + setup links when expanded)")
    return {
        "root_cause": (
            "Browser landing renders Telegram + 1-day temp CTAs in #landing-paths. "
            "Legacy #home-cta duplicated the same labels via updateHomeCtas(); "
            "renderLandingPaths() hides #home-cta for non-Mini-App users. "
            "#account-fold still exposes bot/setup links below the fold — product overlap, not fixture injection."
        ),
        "fixture_issue": False,
        "product_issue": True,
        "decision": (
            f"{PORTAL_CTA_DUPLICATION_BACKLOG} resolved in repo: "
            "#landing-paths visible by default with after-click copy; "
            "#home-cta hidden for browser; #events-card hidden until incident; "
            "account-fold bot/setup hidden for new browser users."
        ),
        "blocks": blocks,
        "fixed_in_preview": "landing-paths primary + journey steps + existing-user entry; no duplicate home-cta",
    }


def _rel_href(index_path: Path, target: str | Path | None) -> str | None:
    if not target:
        return None
    p = Path(target)
    if not p.is_absolute():
        return html.escape(str(p).replace("\\", "/"))
    try:
        return html.escape(str(p.relative_to(index_path.parent)).replace("\\", "/"))
    except ValueError:
        return html.escape(str(p))


def _link(url: str | None, label: str) -> str:
    if not url:
        return '<span class="muted">—</span>'
    safe = html.escape(url)
    return f'<a href="{safe}" target="_blank" rel="noopener">{html.escape(label)}</a>'


def _transcript_unavailable_reason(row: dict[str, Any]) -> str:
    if not row.get("bot_actions"):
        return "No bot harness actions for this scenario (web-only or blocked)."
    if row.get("runnable") == "blocked":
        return "Scenario blocked — bot harness not run."
    if row.get("errors"):
        return f"Bot harness error: {'; '.join(row['errors'])}"
    return "Transcript not generated — re-run --build after seeding."


def _resolve_transcripts(row: dict[str, Any], preview_dir: Path) -> None:
    scenario = row.get("scenario", "")
    bot_dir = preview_dir / "bot"
    transcripts: dict[str, str] = {}
    for action in row.get("bot_actions") or []:
        fname = f"{scenario}-{action}.md"
        path = bot_dir / fname
        if path.is_file():
            transcripts[action] = f"bot/{fname}"
    row["bot_transcripts"] = transcripts
    if transcripts:
        primary = row.get("bot_actions") or []
        first_action = primary[0] if primary else next(iter(transcripts))
        row["bot_transcript_path"] = transcripts.get(first_action) or next(iter(transcripts.values()))
        row["bot_transcript_reason"] = ""
    else:
        row["bot_transcript_path"] = None
        row["bot_transcript_reason"] = _transcript_unavailable_reason(row)


def _final_state(row: dict[str, Any]) -> str:
    runnable = row.get("runnable", "partial")
    if runnable == "blocked":
        return "Blocked — not end-to-end testable"
    status = _user_status(row)
    mapping = {
        "terms_required": "Terms required — access not granted yet",
        "wallet": "Wallet active — paid access path",
        "expired": "Expired — renewal/payment required",
        "legacy": "Legacy manual access state",
        "web_only": "Web-only lead — Telegram bind required",
    }
    if status in mapping:
        return mapping[status]
    checks = row.get("actual_checks") or {}
    if checks.get("cabinet_ok"):
        return "Cabinet loads — review state in Step 3"
    if runnable == "partial":
        return f"Partial — {row.get('next_blocker') or 'see limitation'}"
    return "Review final cabinet/setup screens"


def _journey_hints(scenario: str) -> dict[str, str]:
    hints: dict[str, dict[str, str]] = {
        "new_no_referral": {
            "portal_sees": "Hero + «Как начать»: Telegram 90d primary, email 1d secondary",
            "portal_cta": "Открыть Telegram-бота",
            "portal_dest": "Telegram bot /start",
            "bot_receives": "Terms agreement screen (capture-only transcript)",
            "bot_next": "Accept terms in bot (staging bot / second TG for real tap)",
            "cabinet_sees": "terms_required error until bot terms accepted",
            "setup_sees": "Setup not primary until access granted",
        },
        "new_from_referral": {
            "portal_sees": "Referral welcome block + same dual-path landing",
            "portal_cta": "Открыть Telegram-бота (ref preserved)",
            "portal_dest": "Telegram bot /start ref_QA_REF_INVITER",
            "bot_receives": "Referral linked + terms or menu",
            "bot_next": "Accept terms or open menu",
            "cabinet_sees": "terms_required until terms accepted",
            "setup_sees": "After terms — trial/setup per product path",
        },
        "paid_wallet_user": {
            "portal_sees": "Returning-user landing or direct cabinet deep link",
            "portal_cta": "Open cabinet with seeded tid",
            "portal_dest": "Cabinet balance + active config",
            "bot_receives": "Main menu + account status + setup link",
            "bot_next": "Open setup from bot or cabinet",
            "cabinet_sees": "Wallet balance, active config count",
            "setup_sees": "Device setup / Happ import steps",
        },
        "web_lead_without_tg_bind": {
            "portal_sees": "Email 1d path primary; Telegram bind CTA",
            "portal_cta": "Временный доступ на 1 сутки",
            "portal_dest": "/setup/ email form",
            "bot_receives": "N/A — web lead without TG bind",
            "bot_next": "Complete email form, then bind Telegram in bot",
            "cabinet_sees": "Web-only cabinet by email",
            "setup_sees": "Email signup + temp access flow",
        },
        "temporary_1d_active": {
            "portal_sees": "Email/temp path messaging",
            "portal_cta": "Cabinet by email",
            "portal_dest": "Active temp configuration",
            "bot_receives": "Usually N/A (email path)",
            "bot_next": "Bind Telegram for full cabinet",
            "cabinet_sees": "Temporary access active (~1 day)",
            "setup_sees": "Import temp config",
        },
        "after_trial_cap": {
            "portal_sees": "Trial CTA should hide when cap closed (fixture only)",
            "portal_cta": "Trial CTA (expected hidden)",
            "portal_dest": "Not implemented — ACQ-TRIAL-CAP-001",
            "bot_receives": "Not seeded",
            "bot_next": "Blocked",
            "cabinet_sees": "Not applicable",
            "setup_sees": "Not applicable",
        },
        "slots_counter_states": {
            "portal_sees": "Slots card via qa_capacity_fixture param",
            "portal_cta": "Registration CTA gated by slots",
            "portal_dest": "Fixture only until capacity API ships",
            "bot_receives": "N/A",
            "bot_next": "Blocked",
            "cabinet_sees": "N/A",
            "setup_sees": "N/A",
        },
    }
    default = {
        "portal_sees": row_expected_portal(scenario),
        "portal_cta": "See CTA map below",
        "portal_dest": "Portal / bot / cabinet per scenario",
        "bot_receives": "See bot transcript when available",
        "bot_next": "Follow transcript buttons (staging for real taps)",
        "cabinet_sees": row_expected_cabinet(scenario),
        "setup_sees": "Setup instructions when config exists",
    }
    return {**default, **hints.get(scenario, {})}


def row_expected_portal(scenario: str) -> str:
    import qa_scenario_matrix as matrix

    cfg = matrix.MATRIX.get(scenario)
    return cfg.expected_portal if cfg else "Portal landing for scenario"


def row_expected_cabinet(scenario: str) -> str:
    import qa_scenario_matrix as matrix

    cfg = matrix.MATRIX.get(scenario)
    if not cfg:
        return "Cabinet state for scenario"
    return cfg.expected_cabinet or cfg.expected_cabinet_profile or "Cabinet snapshot from QA DB"


def _cta_transition_map(row: dict[str, Any]) -> list[dict[str, str]]:
    scenario = row.get("scenario", "")
    runnable = row.get("runnable", "partial")
    hints = _journey_hints(scenario)
    ctas: list[dict[str, str]] = []

    def support(clickable: bool, *, transcript: bool = False, blocked: bool = False) -> str:
        if blocked or runnable == "blocked":
            return "not implemented yet"
        if transcript:
            return "transcript only"
        if clickable:
            return "clickable now"
        return "requires staging bot / second TG"

    if row.get("portal_url"):
        ctas.append(
            {
                "label": hints.get("portal_cta", "Открыть Telegram-бота"),
                "source": "Portal landing",
                "target": hints.get("portal_dest", "Telegram bot / cabinet / setup"),
                "support": support(runnable != "blocked"),
            }
        )
        ctas.append(
            {
                "label": "Временный доступ на 1 сутки",
                "source": "Portal landing (#landing-paths)",
                "target": "/setup/ email form",
                "support": support(scenario not in ("after_trial_cap", "slots_counter_states")),
            }
        )
    if row.get("bot_actions"):
        ctas.append(
            {
                "label": "Bot menu / status / setup",
                "source": "Telegram bot (harness)",
                "target": "Bot handlers — see transcript",
                "support": support(False, transcript=bool(row.get("bot_transcripts"))),
            }
        )
    if row.get("cabinet_url"):
        ctas.append(
            {
                "label": "Личный кабинет",
                "source": "Cabinet page",
                "target": row.get("cabinet_url", ""),
                "support": support(runnable == "full" or runnable == "partial"),
            }
        )
    if row.get("setup_url") and scenario not in ("after_trial_cap",):
        ctas.append(
            {
                "label": "Подключить устройство",
                "source": "Setup page",
                "target": row.get("setup_url", ""),
                "support": support(runnable != "blocked"),
            }
        )
    if runnable == "partial" and "payment" in (row.get("next_blocker") or "").lower():
        ctas.append(
            {
                "label": "Оплата / пополнение",
                "source": "Bot top-up",
                "target": "YooKassa dry-run only in QA",
                "support": "requires staging bot / dry-run payment",
            }
        )
    return ctas


def _render_journey_walkthrough(row: dict[str, Any], index_path: Path) -> str:
    hints = _journey_hints(row.get("scenario", ""))
    parts = ['<div class="journey">', "<h4>Journey walkthrough</h4>", "<ol class=journey-steps>"]

    parts.append("<li><strong>Step 1 — Portal</strong>")
    parts.append(f"<div>Open: {_link(row.get('portal_url'), 'Open Portal')}</div>")
    parts.append(f"<div>User sees: {html.escape(hints['portal_sees'])}</div>")
    parts.append(f"<div>Primary CTA: {html.escape(hints['portal_cta'])}</div>")
    parts.append(f"<div>Expected destination: {html.escape(hints['portal_dest'])}</div></li>")

    transcripts = row.get("bot_transcripts") or {}
    parts.append("<li><strong>Step 2 — Bot / Telegram</strong>")
    if transcripts:
        links = []
        for action, rel in transcripts.items():
            href = _rel_href(index_path, rel)
            if href:
                links.append(f'<a href="{href}">{html.escape(f"Transcript: {action}")}</a>')
        parts.append("<div>Open transcript: " + " · ".join(links) + "</div>")
    elif row.get("bot_actions"):
        reason = row.get("bot_transcript_reason") or _transcript_unavailable_reason(row)
        parts.append(f'<div class=muted>Bot transcript not available — {html.escape(reason)}</div>')
    else:
        parts.append('<div class=muted>Bot step skipped — web-only or blocked scenario</div>')
    parts.append(f"<div>User receives: {html.escape(hints['bot_receives'])}</div>")
    parts.append(f"<div>Next expected action: {html.escape(hints['bot_next'])}</div></li>")

    parts.append("<li><strong>Step 3 — Cabinet</strong>")
    parts.append(f"<div>Open: {_link(row.get('cabinet_url'), 'Open Cabinet')}</div>")
    parts.append(f"<div>User sees: {html.escape(hints['cabinet_sees'])}</div>")
    parts.append(f"<div>Expected state: {_user_status(row)}</div></li>")

    parts.append("<li><strong>Step 4 — Setup</strong>")
    parts.append(f"<div>Open: {_link(row.get('setup_url'), 'Open Setup')}</div>")
    parts.append(f"<div>User sees: {html.escape(hints['setup_sees'])}</div>")
    parts.append(f"<div>Expected result: device import instructions when config exists</div></li>")

    parts.append("<li><strong>Step 5 — Final state</strong>")
    parts.append(f"<div>{html.escape(_final_state(row))}</div></li>")
    parts.append("</ol></div>")
    return "\n".join(parts)


def _support_css_class(support: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in support.lower())
    while "--" in safe:
        safe = safe.replace("--", "-")
    return f"support-{safe.strip('-')}"


def _render_cta_map(ctas: list[dict[str, str]]) -> str:
    if not ctas:
        return '<p class=muted>No CTAs for this scenario.</p>'
    rows = [
        "<table class=cta-map><thead><tr>"
        "<th>CTA</th><th>Source</th><th>Target</th><th>Preview support</th>"
        "</tr></thead><tbody>"
    ]
    for cta in ctas:
        rows.append(
            "<tr>"
            f"<td>{html.escape(cta['label'])}</td>"
            f"<td>{html.escape(cta['source'])}</td>"
            f"<td>{html.escape(cta['target'])}</td>"
            f"<td><span class=\"{_support_css_class(cta['support'])}\">{html.escape(cta['support'])}</span></td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "\n".join(rows)


def _render_scenario_card(row: dict[str, Any], index_path: Path) -> str:
    name = row.get("scenario", "")
    label = _scenario_label(name)
    runnable = row.get("runnable", "partial")
    parts = ['<article class=card id="' + html.escape(name) + '">']
    parts.append(
        f"<h3>{html.escape(label)}"
        f'<span class="badge {html.escape(runnable)}">{html.escape(OWNER_GROUP_LABELS[runnable])}</span>'
        f'<span class="badge matrix">{html.escape(MATRIX_GROUP_LABELS[runnable])}</span></h3>'
    )
    parts.append(f'<div class=muted><code>{html.escape(name)}</code> · user status: {html.escape(_user_status(row))}</div>')

    parts.append(_render_journey_walkthrough(row, index_path))

    parts.append('<div class=section><h4>CTA transition map</h4>')
    parts.append(_render_cta_map(_cta_transition_map(row)))
    parts.append("</div>")

    expected = row.get("expected_behavior") or "—"
    parts.append(f'<div class=section><h4>Expected user-visible behavior</h4><p>{html.escape(expected)}</p></div>')

    blocker = row.get("next_blocker") or ""
    if blocker or runnable in ("partial", "blocked"):
        text = blocker or GROUP_HINTS.get(runnable, "")
        parts.append(f'<div class=section><h4>Why partial/blocked</h4><p class=limitation>{html.escape(text)}</p></div>')

    parts.append('<details class=tech><summary>Technical details</summary>')
    parts.append('<div class=grid>')
    for fld, val in (
        ("Telegram ID", row.get("tg_user_id") or "—"),
        ("Email", row.get("email") or "—"),
        ("Referral", row.get("ref_code") or "—"),
    ):
        parts.append(f'<div class=field><label>{html.escape(fld)}</label><div>{html.escape(str(val))}</div></div>')
    parts.append("</div>")
    drift = row.get("drift") or {}
    for bucket, title in (
        ("production_identical", "Production-identical"),
        ("dry_run_mocked", "Dry-run / mocked"),
        ("not_verified_without_staging_or_prod", "Not verified without staging/prod"),
    ):
        items = drift.get(bucket) or []
        if items:
            parts.append(f"<p><strong>{html.escape(title)}</strong></p><ul class=compact>")
            for item in items:
                parts.append(f"<li>{html.escape(str(item))}</li>")
            parts.append("</ul>")
    parts.append("</details></article>")
    return "\n".join(parts)


def render_open_instructions(*, portal_base: str = "http://127.0.0.1:8765") -> str:
    cta = investigate_portal_cta_duplication()
    return f"""BenderVPN owner journey preview — local workflow
============================================================

WARNING: Local/staging QA preview only. NOT production.

1. Set environment:
   BVPN_ENV=local
   BVPN_QA_TOOLS_ENABLED=1
   SHOP_BOT_DB_PATH=/path/to/isolated/qa.db
   BVPN_QA_PORTAL_BASE={portal_base}

2. Seed QA scenarios:
   python ops/qa_seed_scenarios.py --reset --seed-all

3. Start portal preview server (keep running):
   python ops/qa_serve_portal_preview.py

4. Build owner journey preview:
   python ops/qa_owner_preview.py --build --out screenshots/qa-preview/index.html

5. Open screenshots/qa-preview/index.html

6. Use «Start here» scenarios — follow Step 1→5 per card (not isolated technical links).

Portal CTA note: {cta['root_cause']}
Decision: {cta['decision']}
"""


def render_html_index(
    scenarios: list[dict[str, Any]],
    *,
    db_path: Path,
    generated_at: str,
    portal_base: str,
    matrix_json_path: Path | None = None,
    index_path: Path | None = None,
    matrix_summary: dict[str, int] | None = None,
) -> str:
    index_path = index_path or DEFAULT_OUT
    matrix_counts = matrix_summary or {g: 0 for g in GROUP_ORDER}
    if not matrix_summary:
        for row in scenarios:
            r = row.get("runnable", "partial")
            if r in matrix_counts:
                matrix_counts[r] += 1

    by_group: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUP_ORDER}
    for row in scenarios:
        by_group.setdefault(row.get("runnable", "partial"), []).append(row)

    cta_note = investigate_portal_cta_duplication()
    start_rows = [r for r in scenarios if r.get("scenario") in START_HERE_SCENARIOS]

    css = """
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#0f1419;color:#e7ecf3;line-height:1.45}
.wrap{max-width:1100px;margin:0 auto;padding:24px 20px 48px}
.banner{background:#3d1f1f;border:1px solid #8b3a3a;color:#ffd6d6;padding:14px 16px;border-radius:10px;margin-bottom:20px}
.banner--info{background:#1a2740;border-color:#2a4a7a;color:#d6e6ff}
h1{font-size:1.6rem;margin:0 0 8px}
.steps{background:#151b24;border:1px solid #2a3544;border-radius:10px;padding:14px 16px;margin-bottom:22px}
.summary{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 8px}
.pill{padding:8px 12px;border-radius:999px;font-size:.85rem;border:1px solid #2a3544;background:#151b24}
.pill.full{border-color:#2f6f4a;color:#b8f0d0}.pill.partial{border-color:#8a6b2e;color:#ffe6a8}.pill.blocked{border-color:#7a3b3b;color:#ffc9c9}
.pill.matrix{opacity:.85;font-size:.8rem}
h2{font-size:1.15rem;margin:28px 0 8px}.hint{color:#9fb0c3;font-size:.9rem;margin-bottom:12px}
.card{background:#151b24;border:1px solid #2a3544;border-radius:12px;padding:16px 18px;margin-bottom:14px}
.card h3{margin:0 0 8px;font-size:1.05rem}
.badge{display:inline-block;font-size:.72rem;padding:2px 8px;border-radius:6px;margin-left:6px;vertical-align:middle}
.badge.full{background:#1e3d2f;color:#b8f0d0}.badge.partial{background:#3d3218;color:#ffe6a8}.badge.blocked{background:#3d1f1f;color:#ffc9c9}.badge.matrix{background:#243041;color:#9fb0c3}
.journey{background:#101820;border:1px solid #243041;border-radius:10px;padding:12px 14px;margin:12px 0}
.journey-steps{margin:8px 0 0 20px;padding:0}.journey-steps li{margin:10px 0}
.cta-map{width:100%;border-collapse:collapse;font-size:.88rem;margin-top:8px}
.cta-map th,.cta-map td{border:1px solid #2a3544;padding:6px 8px;text-align:left;vertical-align:top}
.cta-map th{color:#9fb0c3;font-weight:600}
.support-clickable-now{color:#b8f0d0}.support-transcript-only{color:#ffe6a8}.support-not-implemented-yet{color:#ffc9c9}
.support-requires-staging-bot-second-tg{color:#9fb0c3}.support-requires-staging-bot-dry-run-payment{color:#9fb0c3}
.section{margin-top:12px}.section h4{margin:0 0 6px;font-size:.88rem;color:#9fb0c3;text-transform:uppercase;letter-spacing:.04em}
.start-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:12px 0}
.start-card{background:#101820;border:1px solid #2a3544;border-radius:10px;padding:10px 12px}
.start-card a{color:#7ec8ff;font-weight:600}
.tech{margin-top:12px;font-size:.88rem;color:#9fb0c3}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px 16px;margin:8px 0}
.field label{display:block;color:#7d8da0;font-size:.78rem}
.limitation{color:#ffc9c9}.muted{color:#7d8da0}a{color:#7ec8ff}
details.tech summary{cursor:pointer;color:#9fb0c3}
"""

    parts = [
        "<!DOCTYPE html>",
        '<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>BenderVPN — Owner Journey Preview</title>",
        f"<style>{css}</style></head><body><div class=wrap>",
        '<div class=banner><strong>Local / staging QA preview only</strong>',
        "Real portal/cabinet/setup frontend + QA DB. Not production.</div>",
        "<h1>BenderVPN — Customer Journey Walkthrough</h1>",
        '<div class=steps><strong>How to review</strong><ol>',
        "<li>Start <code>qa_serve_portal_preview.py</code>.</li>",
        "<li>Open a scenario from <strong>Start here</strong>.</li>",
        "<li>Follow <strong>Step 1 → 5</strong> in order (portal → bot transcript → cabinet → setup → final).</li>",
        "<li>Use CTA map to see what is clickable vs transcript-only vs blocked.</li>",
        "</ol></div>",
        '<div class="banner banner--info"><strong>Portal CTA duplication note</strong> ',
        html.escape(cta_note["root_cause"]),
        " ",
        html.escape(cta_note["decision"]),
        "</div>",
        '<div class=summary>',
        f'<span class="pill full">{html.escape(OWNER_GROUP_LABELS["full"])}: {matrix_counts.get("full", 0)}</span>',
        f'<span class="pill partial">{html.escape(OWNER_GROUP_LABELS["partial"])}: {matrix_counts.get("partial", 0)}</span>',
        f'<span class="pill blocked">{html.escape(OWNER_GROUP_LABELS["blocked"])}: {matrix_counts.get("blocked", 0)}</span>',
        '<span class="pill matrix">Counts match matrix JSON (same full/partial/blocked semantics)</span>',
        "</div>",
    ]

    if matrix_json_path and matrix_json_path.is_file():
        rel = _rel_href(index_path, matrix_json_path)
        if rel:
            parts.append(f'<p class=muted><a href="{rel}">Technical JSON (matrix report)</a></p>')

    parts.append("<h2>Start here</h2><p class=hint>Priority scenarios for first owner review.</p><div class=start-grid>")
    for row in start_rows:
        sid = row.get("scenario", "")
        parts.append(
            f'<div class=start-card><a href="#{html.escape(sid)}">{html.escape(_scenario_label(sid))}</a>'
            f'<div class=muted>{html.escape(OWNER_GROUP_LABELS.get(row.get("runnable", "partial"), ""))}</div></div>'
        )
    parts.append("</div>")

    for group in GROUP_ORDER:
        rows = by_group.get(group) or []
        if not rows:
            continue
        parts.append(f"<h2>{html.escape(OWNER_GROUP_LABELS[group])}</h2>")
        parts.append(f'<p class=hint>{html.escape(GROUP_HINTS[group])} ({html.escape(MATRIX_GROUP_LABELS[group])})</p>')
        for row in rows:
            parts.append(_render_scenario_card(row, index_path))

    parts.append(
        '<details class=tech><summary>Build metadata</summary>'
        f"<p>Generated: {html.escape(generated_at)}</p>"
        f"<p>DB: {html.escape(str(db_path))}</p>"
        f"<p>Portal: {html.escape(portal_base)}</p></details>"
    )
    parts.extend(["</div></body></html>"])
    return "\n".join(parts)


def _matrix_rows_from_json(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(payload.get("scenarios") or [])


async def build_preview(
    *,
    db_path: Path,
    out_path: Path,
    scenarios: list[str] | None = None,
    reset_seed: bool = True,
    reuse_matrix_json: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import qa_portal_fixtures as qpf
    import qa_scenario_matrix as matrix

    _ensure_guards(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_dir = out_path.parent / "bot"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    ts = generated_at or datetime.now(timezone.utc).isoformat()
    portal_base = qpf._portal_base()

    if reuse_matrix_json and reuse_matrix_json.is_file():
        payload = json.loads(reuse_matrix_json.read_text(encoding="utf-8"))
        rows = _matrix_rows_from_json(payload)
        if scenarios:
            wanted = {s.strip().lower() for s in scenarios}
            rows = [r for r in rows if r.get("scenario") in wanted]
    else:
        matrix_rows = await matrix.run_matrix(
            db_path=db_path,
            scenarios=scenarios,
            reset_seed=reset_seed,
            transcript_dir=transcript_dir,
        )
        rows = [r.to_dict() for r in matrix_rows]
        matrix_json_path = out_path.parent / "matrix-report.json"
        payload = {
            "generated_at": ts,
            "db_path": str(db_path),
            "summary": {
                "total": len(rows),
                "full": sum(1 for r in rows if r.get("runnable") == "full"),
                "partial": sum(1 for r in rows if r.get("runnable") == "partial"),
                "blocked": sum(1 for r in rows if r.get("runnable") == "blocked"),
            },
            "drift": matrix._drift_payload(),
            "portal_cta_duplication": investigate_portal_cta_duplication(),
            "scenarios": rows,
        }
        matrix_json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    preview_dir = out_path.parent
    for row in rows:
        _resolve_transcripts(row, preview_dir)

    summary = {
        "total": len(rows),
        "full": sum(1 for r in rows if r.get("runnable") == "full"),
        "partial": sum(1 for r in rows if r.get("runnable") == "partial"),
        "blocked": sum(1 for r in rows if r.get("runnable") == "blocked"),
    }

    html_doc = render_html_index(
        rows,
        db_path=db_path,
        generated_at=ts,
        portal_base=portal_base,
        matrix_json_path=out_path.parent / "matrix-report.json",
        index_path=out_path,
        matrix_summary=summary,
    )
    out_path.write_text(html_doc, encoding="utf-8")

    md_path = out_path.with_suffix(".md")
    md_path.write_text(
        _render_markdown_index(rows, db_path=db_path, generated_at=ts, portal_base=portal_base),
        encoding="utf-8",
    )

    return {
        "html": out_path,
        "markdown": md_path,
        "matrix_json": out_path.parent / "matrix-report.json",
        "summary": summary,
        "scenarios": rows,
        "portal_cta_duplication": investigate_portal_cta_duplication(),
    }


def _render_markdown_index(
    scenarios: list[dict[str, Any]],
    *,
    db_path: Path,
    generated_at: str,
    portal_base: str,
) -> str:
    lines = [
        "# BenderVPN Owner Journey Preview",
        "",
        "> **Local/staging only — NOT production.**",
        "",
        "## Start here",
        "",
    ]
    for sid in START_HERE_SCENARIOS:
        row = next((r for r in scenarios if r.get("scenario") == sid), None)
        if row:
            lines.append(f"- [{_scenario_label(sid)}](#{sid}) — {OWNER_GROUP_LABELS[row.get('runnable', 'partial')]}")
    lines.extend(["", f"- generated: {generated_at}", f"- portal: {portal_base}", ""])
    for row in scenarios:
        name = row.get("scenario", "")
        lines.append(f"## {_scenario_label(name)} (`{name}`)")
        lines.append("")
        lines.append(f"- owner status: {OWNER_GROUP_LABELS.get(row.get('runnable', ''), '')}")
        lines.append(f"- matrix status: {MATRIX_GROUP_LABELS.get(row.get('runnable', ''), '')}")
        lines.append(f"1. Portal: {row.get('portal_url') or '-'}")
        lines.append(f"2. Bot transcript: {row.get('bot_transcript_path') or row.get('bot_transcript_reason', '-')}")
        lines.append(f"3. Cabinet: {row.get('cabinet_url') or '-'}")
        lines.append(f"4. Setup: {row.get('setup_url') or '-'}")
        lines.append(f"5. Final: {_final_state(row)}")
        if row.get("next_blocker"):
            lines.append(f"- limitation: {row['next_blocker']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_scenario_detail(row: dict[str, Any], *, portal_base: str) -> str:
    name = row.get("scenario", "")
    lines = [
        f"Scenario: {_scenario_label(name)} ({name})",
        f"Owner status: {OWNER_GROUP_LABELS.get(row.get('runnable', ''), '')}",
        f"Matrix status: {MATRIX_GROUP_LABELS.get(row.get('runnable', ''), '')}",
        "",
        "Journey:",
        f"1. Portal: {row.get('portal_url') or '-'}",
        f"2. Bot: {row.get('bot_transcript_path') or row.get('bot_transcript_reason', '-')}",
        f"3. Cabinet: {row.get('cabinet_url') or '-'}",
        f"4. Setup: {row.get('setup_url') or '-'}",
        f"5. Final: {_final_state(row)}",
    ]
    if row.get("next_blocker"):
        lines.append(f"Limitation: {row['next_blocker']}")
    lines.append(f"Portal server: {portal_base}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BenderVPN owner QA journey preview index")
    parser.add_argument("--db", help="SQLite path")
    parser.add_argument("--build", action="store_true", help="Build HTML preview index")
    parser.add_argument("--out", help="HTML output path", default=str(DEFAULT_OUT))
    parser.add_argument("--scenario", help="Build or print one scenario")
    parser.add_argument("--open-instructions", action="store_true", help="Print local workflow")
    parser.add_argument("--reuse-matrix", help="Reuse existing matrix-report.json")
    parser.add_argument("--no-reset", action="store_true", help="Skip DB reset when running matrix")
    parser.add_argument("--investigate-cta", action="store_true", help="Print portal CTA duplication analysis")
    args = parser.parse_args(argv)

    if args.investigate_cta:
        print(json.dumps(investigate_portal_cta_duplication(), indent=2, ensure_ascii=False))
        return 0

    if args.open_instructions:
        if str(OPS) not in sys.path:
            sys.path.insert(0, str(OPS))
        import qa_portal_fixtures as qpf

        print(render_open_instructions(portal_base=qpf._portal_base()))
        return 0

    if not args.build and not args.scenario:
        parser.error("Specify --build, --scenario NAME, or --open-instructions")

    db_path = _resolve_db_path(args.db)
    _ensure_guards(db_path)
    out_path = Path(args.out)
    reuse = Path(args.reuse_matrix) if args.reuse_matrix else None

    result = asyncio.run(
        build_preview(
            db_path=db_path,
            out_path=out_path,
            scenarios=[args.scenario] if args.scenario else None,
            reset_seed=not args.no_reset,
            reuse_matrix_json=reuse,
        )
    )

    if args.scenario and len(result["scenarios"]) == 1:
        if str(OPS) not in sys.path:
            sys.path.insert(0, str(OPS))
        import qa_portal_fixtures as qpf

        print(render_scenario_detail(result["scenarios"][0], portal_base=qpf._portal_base()))

    print(f"Owner preview HTML: {result['html']}")
    print(f"Owner preview Markdown: {result['markdown']}")
    print(f"Matrix JSON: {result['matrix_json']}")
    print(
        "Summary: "
        f"total={result['summary']['total']} "
        f"full={result['summary']['full']} "
        f"partial={result['summary']['partial']} "
        f"blocked={result['summary']['blocked']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
