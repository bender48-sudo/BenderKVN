#!/usr/bin/env python3
"""Independent exit path canary artifact — NEW-INDEPENDENT-EXIT-PATH-001 /
NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-AND-PROMOTION-001.

Produces an owner/staging-only artifact under .local/ (never committed) that
captures the INDEPENDENT_EXIT_PATH_V1 criteria scorecard for a candidate exit
node (default nl-node-1), the synthetic CANARY preview if it were promoted, and
the controlled traffic-smoke + rollback runbook.

HARD SAFETY:
    * Output ONLY to .local/ — never the production registry/templates.
    * No Remna/Caddy/subscription/deploy mutation. No live secrets.
    * Asserts the candidate is NOT counted capacity (delivery_path_eligible=false /
      not active) so the artifact cannot imply production readiness.
    * Egress shown as redacted ep_<hash>:port tokens only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
ROOT = _OPS.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from generate_vpn_config_from_registry import (  # noqa: E402
    GeneratedConfig,
    apply_synthetic_canary_overlay,
    format_markdown,
    generate_for_cohort,
)
from validate_vpn_node_registry import (  # noqa: E402
    DEFAULT_REGISTRY,
    count_independent_exit_paths,
)
from vpn_node_selector import load_validated_registry  # noqa: E402
from vpn_registry_model import (  # noqa: E402
    COHORT_CANARY,
    architecture_compliance,
    is_independent_exit,
    is_independent_exit_candidate,
    path_role,
    shared_upstream_group,
)

DEFAULT_OUT_DIR = ROOT / ".local"
DEFAULT_NODE_ID = "nl-node-1"
TASK_ID = "NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-AND-PROMOTION-001"
PROFILE_LABEL = (
    "BenderVPN Independent Exit Canary — owner/staging only — do NOT refresh subscription"
)

# Redacted egress evidence captured read-only on 2026-06-17 (no raw IPs in repo).
EGRESS_EVIDENCE = {
    "nl-node-1": "ep_2a1adf7b",
    "lv-exit-1": "ep_82c23da5",
    "ru_shared_upstream": "ep_4b84b15b",
}

IMPORT_INSTRUCTIONS = [
    "Keep the normal BenderVPN Auto profile untouched — do NOT refresh subscription.",
    "Create a NEW Happ profile named exactly per the label above.",
    "Paste owner-held NL direct VLESS/REALITY config from vault/.secrets (never into git).",
    "Set routing profile to the standard BenderVPN RU routing bundle if prompted.",
    "DISABLE auto-update / subscription refresh on the NL canary profile.",
    "Confirm the profile shows NL direct hosts in Intl_Direct only (not stealth/TG/Meta).",
    "Do NOT use server picker or manual host selection in user-facing copy.",
]

SMOKE_CHECKLIST = [
    "[PRE] Confirm normal BenderVPN profile still works (LV path unchanged).",
    "[PRE] Import NL canary as a NEW profile; auto-refresh OFF.",
    "[CONNECT] Connect via NL canary profile; wait until TUN/Proxy shows connected.",
    "[CONNECT] Verify no immediate dial storm or reset loop in Happ logs.",
    "[SESSION 10–15 min] Keep an active browser tab on Google Docs or Gmail open.",
    "[SESSION 10–15 min] Browse Google/search; confirm pages load without repeated reconnects.",
    "[SESSION 10–15 min] Confirm general Intl_Direct traffic uses NL egress (not LV/RU relay).",
    "[STEALTH] Open Telegram — must stay on stealth relay path (NOT NL direct exit).",
    "[STEALTH] Open Instagram/Meta if available — must NOT exit via NL direct.",
    "[DNS] Resolve a blocked/non-RU site; confirm DNS works without leak to broken relay1.",
    "[ROUTE] Confirm no fallback to ru-relay-1 (known unstable desktop path).",
    "[ROUTE] Confirm route integrity: stealth apps on relay, direct apps on NL where expected.",
    "[SLEEP/WAKE] One sleep/wake cycle on desktop (if safe); reconnect without dial storms.",
    "[POST] Record pass/fail per step below; export Happ report.zip if any FAIL.",
    "[POST] Switch back to normal profile when done; do NOT refresh subscription.",
]

EXPECTED_BEHAVIOR = {
    "nl_direct": "Google/search/general Intl_Direct browsing exits via NL independent path.",
    "stealth": "Telegram, Instagram, Meta stay on stealth relay — never NL direct.",
    "lv_preserved": "Normal BenderVPN profile unchanged; LV production path intact.",
    "no_relay1": "No dependency on ru-relay-1 (excluded from desktop canary).",
    "stability": "10–15 min active session without frequent reset/drop/reconnect loops.",
    "dns": "DNS resolution works; no obvious leak or broken resolver.",
}

RECORD_TEMPLATE = {
    "smoke_date_utc": "<fill>",
    "device": "<desktop|mobile>",
    "happ_mode": "<TUN|Proxy>",
    "connect_result": "<PASS|FAIL>",
    "session_10_15_min": "<PASS|FAIL|PARTIAL>",
    "google_docs_gmail": "<PASS|FAIL|N/A>",
    "google_search": "<PASS|FAIL>",
    "telegram_stealth": "<PASS|FAIL>",
    "meta_instagram_stealth": "<PASS|FAIL|N/A>",
    "dns_resolution": "<PASS|FAIL>",
    "route_integrity": "<PASS|FAIL>",
    "sleep_wake": "<PASS|FAIL|SKIPPED>",
    "relay1_fallback_seen": "<NO|YES>",
    "overall_verdict": "<PASS|PARTIAL|FAIL>",
    "notes_redacted": "<short notes — no secrets/IPs>",
    "report_export_path": "<local path to report.zip if FAIL — do not commit>",
}

FAILURE_EXPORT = [
    "In Happ: Settings → Diagnostics → Export report (report.zip).",
    "Save to a local ignored path only (e.g. .secrets/diagnostics/ or Downloads).",
    "Do NOT paste subscription URLs, UUIDs, raw IPs, or tokens into chat/git.",
    "Share only: overall verdict, redacted step failures, report filename + date.",
    "Agent can analyze a copied report via ops/analyze_happ_report_tun.py locally.",
]

PASS_CRITERIA = [
    "NL canary connects successfully.",
    "Traffic flows through NL independent exit for Intl_Direct as expected.",
    "Long-lived session stable 10–15 minutes.",
    "Stealth apps (TG/Meta/IG) stay on relay — not NL direct.",
    "No obvious route leak or LV regression.",
    "No ru-relay-1 dependency or reset storm.",
    "DNS and route integrity OK.",
]

PARTIAL_CRITERIA = [
    "Connects but one app/path unstable.",
    "Route unclear or insufficient session duration (<10 min).",
    "Sleep/wake skipped with other checks PASS.",
    "Report/log missing for a suspected failure.",
]

FAIL_CRITERIA = [
    "Cannot connect.",
    "Wrong egress (LV/RU relay instead of NL for direct traffic).",
    "DirectIp/stealth regression (TG/Meta via NL direct).",
    "Frequent reset/drop/reconnect loops.",
    "DNS failure or app-breaking behavior.",
]

ROLLBACK = [
    "Switch back to the normal 'BenderVPN' profile in the client.",
    "Delete the independent-exit canary profile if no longer needed.",
    "No server rollback required (read-only; no remote mutation unless separate task).",
    "Registry stays status=staging, delivery_path_eligible=false, canary_percent=0 until smoke PASS + promotion task.",
]

REQUIRED_OWNER_INPUT = [
    "Owner-held NL direct VLESS/REALITY config (from vault/.secrets) — never paste into git.",
    "Run the checklist in this artifact; fill RECORD_TEMPLATE in the JSON copy locally.",
    "Reply with overall_verdict (PASS/PARTIAL/FAIL) + redacted notes to trigger promotion task.",
]


def _criteria_scorecard(node: dict[str, Any]) -> list[dict[str, Any]]:
    sug = shared_upstream_group(node)
    egress = EGRESS_EVIDENCE.get(node.get("node_id", ""))
    lv = EGRESS_EVIDENCE["lv-exit-1"]
    ru = EGRESS_EVIDENCE["ru_shared_upstream"]
    independent_egress = bool(egress) and egress not in {lv, ru}
    return [
        {
            "criterion": "independent upstream/provider or independent egress",
            "status": "PASS" if independent_egress else "PENDING",
            "evidence": (
                f"egress {egress} != LV {lv} and != RU shared upstream {ru}"
                if egress
                else "egress token not captured"
            ),
        },
        {
            "criterion": "not same shared_upstream_group as relays",
            "status": "PASS" if sug is None else "FAIL",
            "evidence": f"shared_upstream_group={sug}",
        },
        {
            "criterion": "path_role=exit (not relay_frontend)",
            "status": "PASS" if path_role(node) == "exit" else "FAIL",
            "evidence": f"path_role={path_role(node)}",
        },
        {
            "criterion": "service architecture documented & compliant",
            "status": "PASS" if architecture_compliance(node) == "compliant" else "PENDING",
            "evidence": "remnanode VLESS/REALITY exit container; no hysteria forwarder",
        },
        {
            "criterion": "health checks (node-level smoke)",
            "status": "PASS",
            "evidence": "read-only SSH PASS: ports 443/8443 listening, ufw scoped, outbound OK",
        },
        {
            "criterion": "generator support (CANARY preview)",
            "status": "PASS",
            "evidence": "apply_synthetic_canary_overlay produces NL outbound in CANARY",
        },
        {
            "criterion": "canary/drain + rollback support",
            "status": "PASS",
            "evidence": "registry rollout fields + client-side profile rollback (no server change)",
        },
        {
            "criterion": "acceptance smoke (controlled traffic)",
            "status": "PENDING_OWNER",
            "evidence": "A2/A4 traffic smoke owner-gated; delivery_path_eligible stays false until pass",
        },
    ]


def build_artifact(registry: dict[str, Any], node_id: str) -> dict[str, Any]:
    nodes = registry.get("nodes") or []
    node = next((n for n in nodes if n.get("node_id") == node_id), None)
    if node is None:
        raise ValueError(f"node {node_id!r} not in registry")
    if not is_independent_exit_candidate(node):
        raise ValueError(
            f"{node_id} is not an independent_exit_candidate; refusing to build artifact"
        )
    # Honesty guard: a candidate must NOT already be counted capacity.
    if is_independent_exit(node):
        raise ValueError(
            f"{node_id} already counts as an independent exit; this artifact is for candidates only"
        )

    synthetic = apply_synthetic_canary_overlay(registry, node_id)
    canary_gen = generate_for_cohort(synthetic, COHORT_CANARY)
    scorecard = _criteria_scorecard(node)
    blocking = [c for c in scorecard if c["status"] not in {"PASS"}]
    return {
        "task": TASK_ID,
        "criteria_standard": "INDEPENDENT_EXIT_PATH_V1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": PROFILE_LABEL,
        "candidate_node_id": node_id,
        "owner_only": True,
        "do_not_refresh": True,
        "production_default_changed": False,
        "traffic_smoke_status": "WAITING_FOR_OWNER_TRAFFIC_SMOKE",
        "independent_exit_paths_now": count_independent_exit_paths(nodes),
        "candidate_counts_as_capacity": is_independent_exit(node),
        "egress_independence": EGRESS_EVIDENCE,
        "criteria_scorecard": scorecard,
        "remaining_blockers": [c["criterion"] for c in blocking],
        "node_current": {
            "status": node.get("status"),
            "path_role": path_role(node),
            "architecture_compliance": architecture_compliance(node),
            "delivery_path_eligible": node.get("delivery_path_eligible"),
            "acceptance_status": node.get("acceptance_status"),
            "canary_percent": (node.get("rollout") or {}).get("canary_percent"),
            "shared_upstream_group": shared_upstream_group(node),
        },
        "import_instructions": IMPORT_INSTRUCTIONS,
        "synthetic_canary_preview": canary_gen.to_dict(),
        "smoke_checklist": SMOKE_CHECKLIST,
        "expected_behavior": EXPECTED_BEHAVIOR,
        "record_template": RECORD_TEMPLATE,
        "failure_export": FAILURE_EXPORT,
        "pass_criteria": PASS_CRITERIA,
        "partial_criteria": PARTIAL_CRITERIA,
        "fail_criteria": FAIL_CRITERIA,
        "rollback": ROLLBACK,
        "required_owner_input": REQUIRED_OWNER_INPUT,
        "promotion_on_pass": {
            "acceptance_status": "traffic_smoke_pass",
            "status": "canary",
            "canary_percent": 5,
            "allow_new_assignments": False,
            "delivery_path_eligible": True,
            "note": "Repo-side only after owner PASS; PUBLIC_PROD apply still blocked separately.",
        },
    }


def format_markdown_artifact(artifact: dict[str, Any]) -> str:
    preview = artifact["synthetic_canary_preview"]
    lines = [
        f"# {artifact['label']}",
        "",
        f"> Candidate independent exit: **{artifact['candidate_node_id']}** · "
        f"standard {artifact['criteria_standard']} · owner/staging only.",
        "",
        f"- task: {artifact['task']}",
        f"- generated_at: {artifact['generated_at']}",
        f"- traffic_smoke_status: **{artifact['traffic_smoke_status']}**",
        f"- independent_exit_paths_now: {artifact['independent_exit_paths_now']} (LV only)",
        f"- candidate_counts_as_capacity: {artifact['candidate_counts_as_capacity']} (must be False)",
        f"- production_default_changed: {artifact['production_default_changed']}",
        "",
        "## Egress independence (redacted tokens)",
        "",
        f"- candidate NL egress: `{artifact['egress_independence']['nl-node-1']}`",
        f"- LV exit egress: `{artifact['egress_independence']['lv-exit-1']}`",
        f"- RU relay shared upstream: `{artifact['egress_independence']['ru_shared_upstream']}`",
        "- Verdict: NL egress is DISTINCT from LV and the RU shared upstream → independent path.",
        "",
        "## INDEPENDENT_EXIT_PATH_V1 scorecard",
        "",
        "| Criterion | Status | Evidence |",
        "|-----------|--------|----------|",
    ]
    for c in artifact["criteria_scorecard"]:
        lines.append(f"| {c['criterion']} | {c['status']} | {c['evidence']} |")
    lines += [
        "",
        f"Remaining blockers: {', '.join(artifact['remaining_blockers']) or 'none'}",
        "",
        "## Candidate registry state (not synthetic)",
        "",
        f"- status: {artifact['node_current']['status']}",
        f"- path_role: {artifact['node_current']['path_role']}",
        f"- architecture_compliance: {artifact['node_current']['architecture_compliance']}",
        f"- delivery_path_eligible: {artifact['node_current']['delivery_path_eligible']}",
        f"- acceptance_status: {artifact['node_current'].get('acceptance_status')}",
        f"- canary_percent: {artifact['node_current']['canary_percent']}",
        f"- shared_upstream_group: {artifact['node_current']['shared_upstream_group']}",
        "",
        "## Synthetic CANARY preview (if promoted to canary status)",
        "",
        format_markdown(
            GeneratedConfig(
                cohort=preview["cohort"],
                go=preview["go"],
                outbounds=preview["outbounds"],
                selector_groups=preview["selector_groups"],
                route_policy=preview.get("route_policy", {}),
                capacity_summary=preview["capacity_summary"],
                blockers=preview["blockers"],
                warnings=preview["warnings"],
            )
        ),
        "## Import instructions (owner/staging)",
        "",
    ]
    for i, step in enumerate(artifact["import_instructions"], 1):
        lines.append(f"{i}. {step}")
    lines += ["", "## Expected behavior", ""]
    for k, v in artifact["expected_behavior"].items():
        lines.append(f"- **{k}**: {v}")
    lines += [
        "",
        "## Controlled traffic smoke (owner/staging)",
        "",
    ]
    for i, step in enumerate(artifact["smoke_checklist"], 1):
        lines.append(f"{i}. {step}")
    lines += ["", "## Pass / partial / fail criteria", "", "### PASS", ""]
    lines += [f"- {c}" for c in artifact["pass_criteria"]]
    lines += ["", "### PARTIAL", ""]
    lines += [f"- {c}" for c in artifact["partial_criteria"]]
    lines += ["", "### FAIL", ""]
    lines += [f"- {c}" for c in artifact["fail_criteria"]]
    lines += ["", "## What to record (fill in JSON copy locally)", "", "```json"]
    lines.append(json.dumps(artifact["record_template"], indent=2, ensure_ascii=False))
    lines += ["```", "", "## If failure — export report (local only)", ""]
    lines += [f"- {r}" for r in artifact["failure_export"]]
    lines += ["", "## Rollback", ""]
    lines += [f"- {r}" for r in artifact["rollback"]]
    lines += ["", "## Required owner input", ""]
    lines += [f"- {r}" for r in artifact["required_owner_input"]]
    lines += [
        "",
        "## Promotion on PASS (repo-side — not applied until owner reports PASS)",
        "",
        f"- acceptance_status → `{artifact['promotion_on_pass']['acceptance_status']}`",
        f"- status → `{artifact['promotion_on_pass']['status']}`",
        f"- canary_percent → `{artifact['promotion_on_pass']['canary_percent']}` (owner/staging cohort only)",
        f"- delivery_path_eligible → `{artifact['promotion_on_pass']['delivery_path_eligible']}` (canary context only)",
        f"- Note: {artifact['promotion_on_pass']['note']}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate independent-exit canary artifact (.local only)"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--node-id", default=DEFAULT_NODE_ID)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        artifact = build_artifact(registry, args.node_id)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(PROFILE_LABEL)
    print(f"  candidate: {artifact['candidate_node_id']} status={artifact['node_current']['status']}")
    print(f"  independent_exit_paths_now: {artifact['independent_exit_paths_now']}")
    print(f"  remaining_blockers: {artifact['remaining_blockers']}")

    if args.dry_run:
        print("  dry-run: no files written")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "independent_exit_nl_canary.json"
    md_path = args.out_dir / "independent_exit_nl_canary.md"
    json_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(format_markdown_artifact(artifact), encoding="utf-8")
    for p in (json_path, md_path):
        print(f"  wrote: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
