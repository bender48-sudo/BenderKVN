#!/usr/bin/env python3
"""Owner-friendly customer journey visual preview index (QA-OWNER-PREVIEW-001).

Builds an HTML index from QA scenario matrix data: portal/cabinet/setup URLs,
bot transcripts, drift classification, and owner instructions.
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
DEFAULT_MATRIX_JSON = ROOT / "screenshots" / "qa-preview" / "matrix-report.json"

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
GROUP_TITLES = {
    "full": "Fully reviewable now",
    "partial": "Partially reviewable",
    "blocked": "Blocked / placeholder",
}
GROUP_HINTS = {
    "full": "Open portal/cabinet/setup URLs while qa_serve_portal_preview.py is running.",
    "partial": "Some UI is visible; known backend gaps remain — see limitation per scenario.",
    "blocked": "URLs may exist for fixture preview only; scenario is not end-to-end testable yet.",
}


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


def _rel_href(index_path: Path, target: str | None) -> str | None:
    if not target:
        return None
    p = Path(target)
    if not p.is_absolute():
        return html.escape(target)
    try:
        return html.escape(str(p.relative_to(index_path.parent)))
    except ValueError:
        return html.escape(target)


def _link(url: str | None, label: str) -> str:
    if not url:
        return f'<span class="muted">—</span>'
    safe = html.escape(url)
    return f'<a href="{safe}" target="_blank" rel="noopener">{html.escape(label)}</a>'


def render_open_instructions(*, portal_base: str = "http://127.0.0.1:8765") -> str:
    return f"""BenderVPN owner visual preview — local workflow
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

4. Build owner preview index:
   python ops/qa_owner_preview.py --build --out screenshots/qa-preview/index.html

5. Open in browser:
   screenshots/qa-preview/index.html

6. Click scenario links (portal / cabinet / setup) from the index.

Bot menus: read bot transcript links in the index (capture-only harness).
Still needs staging bot + second Telegram account for real inline-button UX.
Playwright E2E (QA-E2E-001) and prod approval remain separate gates.
"""


def render_html_index(
    scenarios: list[dict[str, Any]],
    *,
    db_path: Path,
    generated_at: str,
    portal_base: str,
    matrix_json_path: Path | None = None,
    index_path: Path | None = None,
) -> str:
    index_path = index_path or DEFAULT_OUT
    counts = {g: 0 for g in GROUP_ORDER}
    for row in scenarios:
        runnable = row.get("runnable", "partial")
        if runnable in counts:
            counts[runnable] += 1

    by_group: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUP_ORDER}
    for row in scenarios:
        by_group.setdefault(row.get("runnable", "partial"), []).append(row)

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="ru">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>BenderVPN — Owner QA Preview</title>",
        "<style>",
        "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#0f1419;color:#e7ecf3;line-height:1.45}",
        ".wrap{max-width:1100px;margin:0 auto;padding:24px 20px 48px}",
        ".banner{background:#3d1f1f;border:1px solid #8b3a3a;color:#ffd6d6;padding:14px 16px;border-radius:10px;margin-bottom:20px}",
        ".banner strong{display:block;margin-bottom:6px}",
        "h1{font-size:1.6rem;margin:0 0 8px}",
        ".meta{color:#9fb0c3;font-size:.92rem;margin-bottom:18px}",
        ".steps{background:#151b24;border:1px solid #2a3544;border-radius:10px;padding:14px 16px;margin-bottom:22px}",
        ".steps ol{margin:8px 0 0 18px;padding:0}",
        ".summary{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 24px}",
        ".pill{padding:8px 12px;border-radius:999px;font-size:.85rem;border:1px solid #2a3544;background:#151b24}",
        ".pill.full{border-color:#2f6f4a;color:#b8f0d0}",
        ".pill.partial{border-color:#8a6b2e;color:#ffe6a8}",
        ".pill.blocked{border-color:#7a3b3b;color:#ffc9c9}",
        "h2{font-size:1.15rem;margin:28px 0 8px}",
        ".hint{color:#9fb0c3;font-size:.9rem;margin-bottom:12px}",
        ".card{background:#151b24;border:1px solid #2a3544;border-radius:12px;padding:16px 18px;margin-bottom:14px}",
        ".card h3{margin:0 0 6px;font-size:1.05rem}",
        ".badge{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:6px;margin-left:8px;vertical-align:middle}",
        ".badge.full{background:#1e3d2f;color:#b8f0d0}",
        ".badge.partial{background:#3d3218;color:#ffe6a8}",
        ".badge.blocked{background:#3d1f1f;color:#ffc9c9}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px 16px;margin:10px 0}",
        ".field label{display:block;color:#9fb0c3;font-size:.78rem}",
        ".field div{word-break:break-all}",
        ".links a{margin-right:12px}",
        ".section{margin-top:8px}",
        ".section h4{margin:0 0 6px;font-size:.88rem;color:#9fb0c3;text-transform:uppercase;letter-spacing:.04em}",
        "ul.compact{margin:4px 0 0 18px;padding:0}",
        "ul.compact li{margin:2px 0}",
        ".limitation{color:#ffc9c9}",
        ".muted{color:#7d8da0}",
        "a{color:#7ec8ff}",
        "</style>",
        "</head>",
        "<body><div class=wrap>",
        '<div class=banner><strong>Local / staging QA preview only</strong>'
        "Do not use production DB or production bot. "
        "Screens show real portal/cabinet/setup frontend against isolated QA DB.</div>",
        "<h1>BenderVPN — Customer Journey Preview</h1>",
        f'<div class=meta>Generated: {html.escape(generated_at)} · DB: {html.escape(str(db_path))} · Portal: {html.escape(portal_base)}</div>',
        '<div class=steps><strong>How to use</strong><ol>',
        "<li>Ensure <code>qa_serve_portal_preview.py</code> is running on the portal base URL.</li>",
        "<li>Click <strong>Portal</strong> / <strong>Cabinet</strong> / <strong>Setup</strong> for each scenario.</li>",
        "<li>Read <strong>What you should see</strong> and compare with the opened page.</li>",
        "<li>Open bot transcript links for capture-only handler output (not live Telegram).</li>",
        "<li>Partial/blocked scenarios explain what is not testable yet.</li>",
        "</ol></div>",
        '<div class=summary>',
        f'<span class="pill full">Full: {counts["full"]}</span>',
        f'<span class="pill partial">Partial: {counts["partial"]}</span>',
        f'<span class="pill blocked">Blocked: {counts["blocked"]}</span>',
        "</div>",
    ]

    if matrix_json_path:
        rel = _rel_href(index_path, str(matrix_json_path))
        if rel:
            parts.append(f'<p class=meta>Matrix JSON: <a href="{rel}">{rel}</a></p>')

    for group in GROUP_ORDER:
        rows = by_group.get(group) or []
        if not rows:
            continue
        parts.append(f"<h2>{html.escape(GROUP_TITLES[group])}</h2>")
        parts.append(f'<p class=hint>{html.escape(GROUP_HINTS[group])}</p>')
        for row in rows:
            name = row.get("scenario", "")
            label = _scenario_label(name)
            runnable = row.get("runnable", "partial")
            status = _user_status(row)
            parts.append('<article class=card>')
            parts.append(
                f"<h3>{html.escape(label)}"
                f'<span class="badge {html.escape(runnable)}">{html.escape(runnable)}</span></h3>'
            )
            parts.append(f'<div class=muted><code>{html.escape(name)}</code></div>')
            parts.append('<div class=grid>')
            for fld, val in (
                ("User status", status),
                ("Telegram ID", row.get("tg_user_id") or "—"),
                ("Email", row.get("email") or "—"),
                ("Phone", row.get("phone") or "—"),
                ("Referral code", row.get("ref_code") or "—"),
            ):
                parts.append(
                    f'<div class=field><label>{html.escape(fld)}</label>'
                    f"<div>{html.escape(str(val))}</div></div>"
                )
            parts.append("</div>")
            parts.append('<div class=links>')
            parts.append(_link(row.get("portal_url"), "Open Portal"))
            parts.append(_link(row.get("cabinet_url"), "Open Cabinet"))
            parts.append(_link(row.get("setup_url"), "Open Setup"))
            parts.append("</div>")
            transcript = row.get("bot_transcript_path")
            if transcript:
                rel = _rel_href(index_path, transcript)
                parts.append(
                    f'<p class=section><h4>Bot transcript</h4>'
                    f'<a href="{rel or html.escape(transcript)}">View capture-only bot output</a></p>'
                )
            elif row.get("bot_actions"):
                parts.append(
                    '<p class=section><h4>Bot transcript</h4>'
                    '<span class=muted>Re-run --build with transcript dir to generate.</span></p>'
                )
            expected = row.get("expected_behavior") or "—"
            parts.append(
                f'<div class=section><h4>What you should see</h4>'
                f"<p>{html.escape(expected)}</p></div>"
            )
            drift = row.get("drift") or {}
            for bucket, title in (
                ("production_identical", "Production-identical"),
                ("dry_run_mocked", "Dry-run / mocked"),
                ("not_verified_without_staging_or_prod", "Not verified without staging/prod"),
            ):
                items = drift.get(bucket) or []
                if not items:
                    continue
                parts.append(f'<div class=section><h4>{html.escape(title)}</h4><ul class=compact>')
                for item in items:
                    parts.append(f"<li>{html.escape(str(item))}</li>")
                parts.append("</ul></div>")
            blocker = row.get("next_blocker") or ""
            if blocker or runnable in ("partial", "blocked"):
                text = blocker or GROUP_HINTS.get(runnable, "")
                parts.append(
                    f'<div class=section><h4>Limitation</h4>'
                    f'<p class=limitation>{html.escape(text)}</p></div>'
                )
            parts.append("</article>")

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
    transcript_dir = out_path.parent

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
            transcript_dir=transcript_dir / "bot",
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
            "scenarios": rows,
        }
        matrix_json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    html_doc = render_html_index(
        rows,
        db_path=db_path,
        generated_at=ts,
        portal_base=portal_base,
        matrix_json_path=out_path.parent / "matrix-report.json",
        index_path=out_path,
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
        "summary": {
            "total": len(rows),
            "full": sum(1 for r in rows if r.get("runnable") == "full"),
            "partial": sum(1 for r in rows if r.get("runnable") == "partial"),
            "blocked": sum(1 for r in rows if r.get("runnable") == "blocked"),
        },
        "scenarios": rows,
    }


def _render_markdown_index(
    scenarios: list[dict[str, Any]],
    *,
    db_path: Path,
    generated_at: str,
    portal_base: str,
) -> str:
    lines = [
        "# BenderVPN Owner QA Preview",
        "",
        "> **Local/staging only — NOT production.**",
        "",
        f"- generated: {generated_at}",
        f"- db: `{db_path}`",
        f"- portal: {portal_base}",
        "",
    ]
    by_group: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUP_ORDER}
    for row in scenarios:
        by_group.setdefault(row.get("runnable", "partial"), []).append(row)
    for group in GROUP_ORDER:
        rows = by_group.get(group) or []
        if not rows:
            continue
        lines.append(f"## {GROUP_TITLES[group]}")
        lines.append("")
        lines.append(GROUP_HINTS[group])
        lines.append("")
        for row in rows:
            name = row.get("scenario", "")
            lines.append(f"### {_scenario_label(name)} (`{name}`) — **{row.get('runnable')}**")
            lines.append("")
            lines.append(f"- user_status: { _user_status(row) }")
            lines.append(f"- tg_user_id: `{row.get('tg_user_id') or '-'}`")
            lines.append(f"- email: `{row.get('email') or '-'}`")
            lines.append(f"- ref_code: `{row.get('ref_code') or '-'}`")
            lines.append(f"- portal: {row.get('portal_url') or '-'}")
            lines.append(f"- cabinet: {row.get('cabinet_url') or '-'}")
            lines.append(f"- setup: {row.get('setup_url') or '-'}")
            if row.get("bot_transcript_path"):
                lines.append(f"- bot_transcript: `{row.get('bot_transcript_path')}`")
            lines.append(f"- expected: {row.get('expected_behavior') or '-'}")
            if row.get("next_blocker"):
                lines.append(f"- limitation: {row.get('next_blocker')}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_scenario_detail(row: dict[str, Any], *, portal_base: str) -> str:
    name = row.get("scenario", "")
    lines = [
        f"Scenario: {_scenario_label(name)} ({name})",
        f"Status: {row.get('runnable')} / support={row.get('support')}",
        f"User status: {_user_status(row)}",
        f"Portal: {row.get('portal_url') or '-'}",
        f"Cabinet: {row.get('cabinet_url') or '-'}",
        f"Setup: {row.get('setup_url') or '-'}",
        f"Expected: {row.get('expected_behavior') or '-'}",
    ]
    if row.get("next_blocker"):
        lines.append(f"Limitation: {row['next_blocker']}")
    lines.append(f"Portal server required: {portal_base}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BenderVPN owner QA visual preview index")
    parser.add_argument("--db", help="SQLite path")
    parser.add_argument("--build", action="store_true", help="Build HTML preview index")
    parser.add_argument("--out", help="HTML output path", default=str(DEFAULT_OUT))
    parser.add_argument("--scenario", help="Build or print one scenario")
    parser.add_argument("--open-instructions", action="store_true", help="Print local workflow")
    parser.add_argument("--reuse-matrix", help="Reuse existing matrix-report.json")
    parser.add_argument("--no-reset", action="store_true", help="Skip DB reset when running matrix")
    args = parser.parse_args(argv)

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
