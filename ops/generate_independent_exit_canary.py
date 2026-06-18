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
import copy
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
from validate_happ_importable_profile import (  # noqa: E402
    METADATA_ARTIFACT_TYPE,
    validate_importable_profile,
)
from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
    NL_DIRECT_SELECTOR,
)
from relay_latency_probe import RELAY1_IP, RELAY2_IP  # noqa: E402
from subscription_fetch import (  # noqa: E402
    node_label,
    outbound_endpoint,
    xray_config_root,
)

DEFAULT_OUT_DIR = ROOT / ".local"
DEFAULT_NODE_ID = "nl-node-1"
TASK_ID = "NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-AND-PROMOTION-001"
ARTIFACT_FIX_TASK_ID = "NL-CANARY-IMPORT-ARTIFACT-FIX-001"
NL_FIX_TASK_ID = "NL-INDEPENDENT-EXIT-FIX-001"
RUNBOOK_FILENAME = "independent_exit_nl_canary_RUNBOOK.md"
METADATA_FILENAME = "independent_exit_nl_canary_METADATA.json"
IMPORTABLE_FILENAME = "independent_exit_nl_canary_IMPORTABLE_PROFILE.json"
from nl_canary_profile_builder import (  # noqa: E402
    DIRECT_BASIC_FILENAME,
    PROFILE_LABEL_DIRECT_BASIC,
    PROFILE_LABEL_LEGACY,
    PROFILE_LABEL_SPLIT_STEALTH,
    SPLIT_STEALTH_FILENAME,
    build_nl_direct_basic_profile,
    build_nl_split_stealth_profile,
    google_routes_via_stealth,
    nl_proxy_tags,
    relay2_proxy_tags,
)
from validate_happ_importable_profile import (  # noqa: E402
    validate_nl_canary_variant,
)
from nl_canary_smoke_guard import generator_smoke_metadata  # noqa: E402
LEGACY_AMBIGUOUS_FILENAMES = (
    "independent_exit_nl_canary.json",
    "independent_exit_nl_canary.md",
)
OWNER_CONFIG_PATHS = (
    ROOT / ".secrets" / "nl_owner_direct_config.json",
    ROOT / ".secrets" / "owner_sub.json",
    ROOT / ".secrets" / "owner_sub_dump.json",
)
METADATA_WARNING = (
    "DO NOT IMPORT THIS JSON INTO HAPP. This is metadata/runbook only."
)
PROFILE_LABEL = PROFILE_LABEL_SPLIT_STEALTH

# Redacted egress evidence captured read-only on 2026-06-17 (no raw IPs in repo).
EGRESS_EVIDENCE = {
    "nl-node-1": "ep_2a1adf7b",
    "lv-exit-1": "ep_82c23da5",
    "ru_shared_upstream": "ep_4b84b15b",
}

IMPORT_INSTRUCTIONS = [
    "Read `.local/independent_exit_nl_canary_RUNBOOK.md` (instructions only — not importable).",
    "DO NOT import `*_METADATA.json` into Happ.",
    "Phase 1: import ONLY `.local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json` first.",
    "Phase 2 (only after DIRECT_BASIC PASS): import `.local/independent_exit_nl_SPLIT_STEALTH_IMPORTABLE_PROFILE.json`.",
    "In Happ: disable external routing profile overlay — use JSON-embedded routing only (do NOT apply separate BenderVPN RU routing on top).",
    "Create NEW profiles; auto-refresh OFF; do not overwrite BenderVPN Auto.",
]

SMOKE_PREFLIGHT_CHECKLIST = [
    "[1] Active profile name = BenderVPN NL Direct Basic Canary — owner only (not legacy Independent Exit).",
    "[2] Happ external routing overlay OFF (no BenderVPN RU selectedRoutingRule; useRouting=false).",
    "[3] Auto-refresh OFF on the canary profile.",
    "[4] Telegram / Instagram / Meta apps CLOSED for Direct Basic phase.",
    "[5] Import file = .local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json only.",
    "[6] Delete or ignore legacy profile: BenderVPN NL Independent Exit Canary — owner only.",
]

SMOKE_CHECKLIST_DIRECT_BASIC = [
    "[PRE] Complete one-screen preflight checklist above — agent rejects invalid smoke otherwise.",
    "[IMPORT] New profile from DIRECT_BASIC JSON only; auto-refresh OFF; external routing profile OFF.",
    "[CONNECT] Connect; wait for TUN up without immediate error storm.",
    "[NL PROOF — ROUTE CLASS] Open Google search + Gmail + YouTube — must route via NL (Intl_Direct).",
    "[NOT PROOF] Yandex/VK/Mail.ru/Ozon/Rutube are DIRECT_BYPASS — success does NOT prove NL.",
    "[NL PROOF] 10–15 min stable session on Google/Docs (not Telegram, not RU sites).",
    "[NEG] Do NOT use Telegram/Meta in this phase — not in profile scope.",
    "[POST] Record pass/fail; export report.zip if FAIL.",
]

SMOKE_CHECKLIST_SPLIT_STEALTH = [
    "[PRE] DIRECT_BASIC already PASS.",
    "[IMPORT] New profile from SPLIT_STEALTH JSON; auto-refresh OFF; external routing OFF.",
    "[STEALTH PROOF] Telegram/Meta/Instagram/WhatsApp → relay-2 stealth (Intl_Stealth).",
    "[NL DIRECT PROOF] Google/YouTube/X/OpenAI → NL direct (Intl_Direct) — blocked intl sites.",
    "[NOT PROOF] RU/local sites (Yandex, VK, Mail.ru) are direct bypass — do not count as VPN proof.",
    "[SESSION] 10–15 min mixed usage; test BOTH stealth apps AND NL-direct blocked sites.",
    "[POST] Record pass/fail per route class; export report.zip if FAIL.",
]

SMOKE_CHECKLIST = SMOKE_CHECKLIST_DIRECT_BASIC + ["--- then SPLIT_STEALTH ---"] + SMOKE_CHECKLIST_SPLIT_STEALTH

EXPECTED_BEHAVIOR = {
    "nl_direct": "Google/YouTube/X/OpenAI and catch-all Intl_Direct browsing exits via NL independent path.",
    "stealth": "Telegram, Instagram, Meta, WhatsApp stay on stealth relay — never NL direct.",
    "direct_bypass": "RU/local domains and geoip:ru go direct — do NOT prove NL or VPN success.",
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
    "Agent analyzes via: python ops/analyze_nl_canary_smoke.py --report <zip> --variant direct_basic",
    "INVALID smoke (wrong profile / overlay / Telegram in Direct Basic) → NOT_TESTED_INVALID_SMOKE — not NL FAIL.",
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


def _load_owner_config() -> tuple[Path | None, dict[str, Any] | None]:
    for path in OWNER_CONFIG_PATHS:
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return path, xray_config_root(raw)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return None, None


def try_generate_importable_profiles(out_dir: Path) -> dict[str, Any]:
    """Generate DIRECT_BASIC + SPLIT_STEALTH importable profiles (.local only)."""
    status: dict[str, Any] = {
        "status": "IMPORTABLE_PROFILE_NOT_GENERATED_MISSING_OWNER_CONFIG",
        "generated": False,
        "profiles": {},
        "expected_owner_config_paths": [str(p) for p in OWNER_CONFIG_PATHS],
        "validation_errors": [],
        "owner_smoke_status": "FAIL_PROFILE_ROUTING_PROTOCOL",
        "owner_smoke_note": (
            "Prior single profile routed geosite:google via Intl_Stealth — Gmail did not prove NL."
        ),
    }

    src_path, cfg = _load_owner_config()
    if cfg is None:
        status["reason"] = (
            "Owner-held NL subscription JSON not found. Place config at "
            ".secrets/nl_owner_direct_config.json (preferred), .secrets/owner_sub.json, "
            "or .secrets/owner_sub_dump.json with NL direct + relay-2 vless outbounds."
        )
        return status

    status["source_config"] = src_path.name
    out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("direct_basic", DIRECT_BASIC_FILENAME, build_nl_direct_basic_profile, "direct_basic"),
        ("split_stealth", SPLIT_STEALTH_FILENAME, build_nl_split_stealth_profile, "split_stealth"),
    ]
    profiles: dict[str, Any] = {}
    all_errors: list[str] = []

    for key, filename, builder, variant in variants:
        try:
            profile = builder(cfg)
        except ValueError as exc:
            all_errors.append(f"{key}: {exc}")
            profiles[key] = {"generated": False, "error": str(exc)}
            continue

        val = validate_nl_canary_variant(profile, variant)
        if not val.ok:
            all_errors.extend([f"{key}: {e}" for e in val.errors])
            profiles[key] = {"generated": False, "validation_errors": val.errors}
            continue

        out_path = out_dir / filename
        out_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
        profiles[key] = {
            "generated": True,
            "output_file": str(out_path),
            "variant": variant,
            "vless_proxy_count": val.summary.get("vless_proxy_count"),
            "google_on_stealth": val.summary.get("google_on_stealth"),
        }

    status["profiles"] = profiles
    direct_ok = profiles.get("direct_basic", {}).get("generated")
    if direct_ok:
        status.update(
            {
                "status": "GENERATED",
                "generated": True,
                "output_file": profiles["direct_basic"]["output_file"],
                "primary_import_file": f".local/{DIRECT_BASIC_FILENAME}",
                "secondary_import_file": f".local/{SPLIT_STEALTH_FILENAME}",
            }
        )
    if all_errors:
        status["validation_errors"] = all_errors
        if not direct_ok:
            status["status"] = "IMPORTABLE_PROFILE_VALIDATION_FAILED"
            status["generated"] = False
    return status


def try_generate_importable_profile(out_dir: Path) -> dict[str, Any]:
    """Backward-compatible wrapper — returns combined generation status."""
    return try_generate_importable_profiles(out_dir)


def build_metadata_document(
    artifact: dict[str, Any],
    import_status: dict[str, Any],
) -> dict[str, Any]:
    """Wrap runbook payload with loud non-importable metadata envelope."""
    return {
        "artifact_type": METADATA_ARTIFACT_TYPE,
        "importable_profile": False,
        "do_not_import_this_file": True,
        "warning": METADATA_WARNING,
        "client_import_file": f".local/{DIRECT_BASIC_FILENAME}",
        "client_import_file_secondary": f".local/{SPLIT_STEALTH_FILENAME}",
        "runbook_file": f".local/{RUNBOOK_FILENAME}",
        "importable_profile_status": import_status.get("status"),
        "importable_profile_generated": import_status.get("generated", False),
        "importable_profile_details": {
            k: v
            for k, v in import_status.items()
            if k not in {"validation_errors"}
        },
        "artifact_fix_task": ARTIFACT_FIX_TASK_ID,
        "nl_fix_task": NL_FIX_TASK_ID,
        **artifact,
    }


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
        "traffic_smoke_status": "WAITING_OWNER_NL_DIRECT_BASIC_ROUTE_CLASS_SMOKE",
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
        "smoke_preflight_checklist": SMOKE_PREFLIGHT_CHECKLIST,
        "smoke_checklist": SMOKE_CHECKLIST,
        "smoke_guard_analyzer": "ops/analyze_nl_canary_smoke.py",
        "direct_basic_smoke_metadata": generator_smoke_metadata("direct_basic"),
        "split_stealth_smoke_metadata": generator_smoke_metadata("split_stealth"),
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


def format_runbook_markdown(
    artifact: dict[str, Any],
    import_status: dict[str, Any],
) -> str:
    preview = artifact["synthetic_canary_preview"]
    lines = [
        f"# {artifact['label']}",
        "",
        "> **DO NOT IMPORT THE METADATA JSON** (`.local/independent_exit_nl_canary_METADATA.json`) into Happ.",
        "> **Phase 1:** import `.local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json` only.",
        "> **Phase 2 (after DIRECT_BASIC PASS):** import `.local/independent_exit_nl_SPLIT_STEALTH_IMPORTABLE_PROFILE.json`.",
        "> Disable Happ external routing profile overlay — use JSON-embedded routing only.",
        "",
        "## Owner preflight (one screen — mandatory before Direct Basic)",
        "",
    ]
    for step in SMOKE_PREFLIGHT_CHECKLIST:
        lines.append(f"- {step}")
    lines += [
        "",
        "> If Telegram is opened, overlay is ON, or legacy profile is active → smoke is **INVALID**, not FAIL.",
        "",
        f"> Candidate independent exit: **{artifact['candidate_node_id']}** · "
        f"standard {artifact['criteria_standard']} · owner/staging only.",
        "",
        f"- task: {artifact['task']}",
        f"- artifact_fix: {ARTIFACT_FIX_TASK_ID}",
        f"- generated_at: {artifact['generated_at']}",
        f"- traffic_smoke_status: **{artifact['traffic_smoke_status']}**",
        f"- importable_profile_status: **{import_status.get('status')}**",
        f"- independent_exit_paths_now: {artifact['independent_exit_paths_now']} (LV only)",
        f"- candidate_counts_as_capacity: {artifact['candidate_counts_as_capacity']} (must be False)",
        "",
        "## Which file to import into Happ",
        "",
        "| File | Import into Happ? | Purpose |",
        "|------|-------------------|---------|",
        f"| `{RUNBOOK_FILENAME}` | **NO** | This runbook (instructions only) |",
        f"| `{METADATA_FILENAME}` | **NO — will crash/fail** | Metadata/scorecard/checklist JSON |",
        f"| `{DIRECT_BASIC_FILENAME}` | **YES — Phase 1 first** | NL-only connectivity proof (Google via NL) |",
        f"| `{SPLIT_STEALTH_FILENAME}` | **YES — Phase 2 after PASS** | NL direct + relay-2 stealth split |",
        f"| `{IMPORTABLE_FILENAME}` | **DEPRECATED — do not use** | Old single profile (google→stealth bug) |",
        "",
        f"Current importable status: `{import_status.get('status')}`",
        "",
        "## Incident notes (2026-06-18)",
        "",
        "1. Owner imported metadata JSON into Happ — immediate fail (not importable).",
        "2. Owner imported legacy single `IMPORTABLE_PROFILE` — **FAIL_PROFILE_ROUTING_PROTOCOL**: "
        "`geosite:google` routed via Intl_Stealth (relay-2), so Gmail did **not** prove NL egress. "
        "Report(11) also showed external Happ routing profile `BenderVPN RU` overlay active.",
        "3. NL traffic smoke remains **WAITING_CLEAN_DIRECT_BASIC_SMOKE** — use DIRECT_BASIC first.",
        "4. report(12): owner used legacy profile + BenderVPN RU overlay + Telegram during Direct Basic → "
        "**NOT_TESTED_INVALID_SMOKE** (guard: `ops/analyze_nl_canary_smoke.py`).",
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

    import_status = try_generate_importable_profile(args.out_dir)
    metadata = build_metadata_document(artifact, import_status)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    runbook_path = args.out_dir / RUNBOOK_FILENAME
    metadata_path = args.out_dir / METADATA_FILENAME
    runbook_path.write_text(
        format_runbook_markdown(artifact, import_status), encoding="utf-8"
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"  importable_profile_status: {import_status.get('status')}")
    print(f"  owner_smoke_status: {import_status.get('owner_smoke_status', artifact['traffic_smoke_status'])}")
    print(f"  wrote runbook: {runbook_path}")
    print(f"  wrote metadata: {metadata_path} (DO NOT IMPORT INTO HAPP)")
    profiles = import_status.get("profiles") or {}
    for key in ("direct_basic", "split_stealth"):
        p = profiles.get(key) or {}
        if p.get("generated"):
            print(f"  wrote {key}: {p.get('output_file')}")
        elif p.get("error") or p.get("validation_errors"):
            print(f"  {key}: NOT generated")
    if not import_status.get("generated"):
        print("  importable profiles NOT generated — see expected_owner_config_paths")

    for legacy in LEGACY_AMBIGUOUS_FILENAMES:
        legacy_path = args.out_dir / legacy
        if legacy_path.exists():
            print(f"  WARNING: legacy ambiguous file still present: {legacy_path} — delete manually")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
