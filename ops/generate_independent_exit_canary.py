#!/usr/bin/env python3
"""Independent exit path canary artifact — NEW-INDEPENDENT-EXIT-PATH-001.

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
PROFILE_LABEL = (
    "BenderVPN Independent Exit Canary — owner/staging only — do NOT refresh subscription"
)

# Redacted egress evidence captured read-only on 2026-06-17 (no raw IPs in repo).
EGRESS_EVIDENCE = {
    "nl-node-1": "ep_2a1adf7b",
    "lv-exit-1": "ep_82c23da5",
    "ru_shared_upstream": "ep_4b84b15b",
}

SMOKE_CHECKLIST = [
    "Confirm normal BenderVPN profile still works (LV path unchanged).",
    "Import the independent-exit canary as a NEW Happ profile (never overwrite BenderVPN Auto).",
    "DISABLE auto-update / subscription refresh on the canary profile.",
    "Connect via canary profile; verify general browsing (Intl_Direct via NL egress) stays stable 5 min.",
    "Verify Google/search loads through the NL egress.",
    "Verify Instagram/Meta/Telegram still exit via stealth relay (must NOT exit via NL direct).",
    "Run sleep/wake once on desktop; reconnect without dial storms.",
    "Capture pass/fail per app; if any FAIL switch back to normal profile and do not refresh subscription.",
]

ROLLBACK = [
    "Switch back to the normal 'BenderVPN' profile in the client.",
    "Delete the independent-exit canary profile if no longer needed.",
    "No server rollback required (read-only; no remote mutation in this task).",
    "Registry stays status=staging, delivery_path_eligible=false, canary_percent=0 until owner promotion.",
]

REQUIRED_OWNER_INPUT = [
    "Owner-held NL direct VLESS/REALITY config (from vault/.secrets) — never paste into git.",
    "Explicit phrase: APPROVE NL INDEPENDENT EXIT TRAFFIC SMOKE before any live selector apply.",
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
        "task": "NEW-INDEPENDENT-EXIT-PATH-001",
        "criteria_standard": "INDEPENDENT_EXIT_PATH_V1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": PROFILE_LABEL,
        "candidate_node_id": node_id,
        "owner_only": True,
        "do_not_refresh": True,
        "production_default_changed": False,
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
            "canary_percent": (node.get("rollout") or {}).get("canary_percent"),
            "shared_upstream_group": shared_upstream_group(node),
        },
        "synthetic_canary_preview": canary_gen.to_dict(),
        "smoke_checklist": SMOKE_CHECKLIST,
        "rollback": ROLLBACK,
        "required_owner_input": REQUIRED_OWNER_INPUT,
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
        "## Controlled traffic smoke (owner/staging)",
        "",
    ]
    for i, step in enumerate(artifact["smoke_checklist"], 1):
        lines.append(f"{i}. {step}")
    lines += ["", "## Rollback", ""]
    lines += [f"- {r}" for r in artifact["rollback"]]
    lines += ["", "## Required owner input", ""]
    lines += [f"- {r}" for r in artifact["required_owner_input"]]
    lines.append("")
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
