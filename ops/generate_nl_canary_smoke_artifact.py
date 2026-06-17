#!/usr/bin/env python3
"""NL A2/A4 controlled canary smoke artifact — NL-A2-A4-CONTROLLED-CANARY-SMOKE-001.

Produces owner/staging-only canary smoke artifacts under .local/ (never committed).
Does NOT mutate production, Remna, Caddy, subscription, or the registry file.

A2/A4 in repo context:
    * NL direct ×4 hosts appended to Intl_Direct selector only (VPN-AUD-220 /
      patch_add_nl_intl_gated.py).
    * Intl_Stealth stays relay-only (TG/Meta/IG never via NL direct).
    * No observatory, no Super_Balancer catch-all swallowing stealth split.
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
from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import build_assignment_plan, load_validated_registry  # noqa: E402
from vpn_registry_model import COHORT_CANARY  # noqa: E402

DEFAULT_OUT_DIR = ROOT / ".local"
NL_NODE_ID = "nl-node-1"
PROFILE_LABEL = "BenderVPN NL Canary — owner/staging only — do NOT refresh subscription"

SMOKE_CHECKLIST = [
    "Confirm normal BenderVPN profile still works (LV path unchanged).",
    "Import NL canary as a NEW Happ profile (never overwrite BenderVPN Auto).",
    "DISABLE auto-update / subscription refresh on the NL canary profile.",
    "Connect via NL canary profile; verify Telegram opens and stays stable 5 min.",
    "Verify Google/search loads (Intl_Direct path).",
    "Verify Instagram/Meta loads via stealth relay (must NOT exit via NL direct).",
    "Run sleep/wake once on desktop; reconnect without dial storms.",
    "If any FAIL: switch back to normal profile; do not refresh subscription.",
]

ROLLBACK = [
    "Switch back to the normal 'BenderVPN' profile in the client.",
    "Delete the NL canary profile if no longer needed.",
    "No server rollback required unless patch_add_nl_intl_gated.py --apply was run separately.",
    "Registry canary fields remain at canary_percent=0 until owner approves promotion.",
]

REQUIRED_OWNER_INPUT = [
    "Owner-held NL direct VLESS config (from vault/.secrets) — never paste into git.",
    "Explicit phrase: APPROVE NL CANARY TRAFFIC SMOKE before live A2/A4 patch --apply.",
    "MONITOR-FLAP-TUNE closeout reviewed or PARTIAL soak risk accepted.",
]


def build_artifact(registry: dict[str, Any]) -> dict[str, Any]:
    synthetic = apply_synthetic_canary_overlay(registry, NL_NODE_ID)
    canary_gen = generate_for_cohort(synthetic, COHORT_CANARY)
    selector = build_assignment_plan("CANARY", registry)
    nl_node = next(
        (n for n in registry.get("nodes") or [] if n.get("node_id") == NL_NODE_ID),
        {},
    )
    return {
        "task": "NL-A2-A4-CONTROLLED-CANARY-SMOKE-001",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": PROFILE_LABEL,
        "owner_only": True,
        "do_not_refresh": True,
        "production_default_changed": False,
        "a2_a4_interpretation": (
            "NL direct ×4 in Intl_Direct only; Intl_Stealth relay-only; "
            "controlled owner/staging cohort; no PUBLIC_PROD apply."
        ),
        "nl_node_current": {
            "node_id": NL_NODE_ID,
            "status": nl_node.get("status"),
            "delivery_path_eligible": nl_node.get("delivery_path_eligible"),
            "canary_percent": (nl_node.get("rollout") or {}).get("canary_percent"),
            "allow_new_assignments": (nl_node.get("rollout") or {}).get("allow_new_assignments"),
        },
        "selector_canary_current": {
            "verdict": selector.verdict,
            "selected_node_ids": selector.selected_node_ids,
            "nl_rejection": next(
                (r.reason for r in selector.rejections if r.node_id == NL_NODE_ID),
                None,
            ),
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
        f"> {artifact['a2_a4_interpretation']}",
        "",
        f"- task: {artifact['task']}",
        f"- generated_at: {artifact['generated_at']}",
        f"- owner_only: {artifact['owner_only']}",
        f"- do_not_refresh: {artifact['do_not_refresh']}",
        f"- production_default_changed: {artifact['production_default_changed']}",
        "",
        "## NL registry state (current — not synthetic)",
        "",
        f"- status: {artifact['nl_node_current']['status']}",
        f"- delivery_path_eligible: {artifact['nl_node_current']['delivery_path_eligible']}",
        f"- canary_percent: {artifact['nl_node_current']['canary_percent']}",
        f"- allow_new_assignments: {artifact['nl_node_current']['allow_new_assignments']}",
        "",
        "## Selector CANARY (live registry — NL excluded)",
        "",
        f"- verdict: {artifact['selector_canary_current']['verdict']}",
        f"- selected: {artifact['selector_canary_current']['selected_node_ids']}",
        f"- nl rejection: {artifact['selector_canary_current']['nl_rejection']}",
        "",
        "## Synthetic canary preview (if NL promoted to canary status)",
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
        "## Smoke checklist (owner/staging)",
        "",
    ]
    for i, step in enumerate(artifact["smoke_checklist"], 1):
        lines.append(f"{i}. {step}")
    lines += ["", "## Rollback", ""]
    for r in artifact["rollback"]:
        lines.append(f"- {r}")
    lines += ["", "## Required owner input", ""]
    for r in artifact["required_owner_input"]:
        lines.append(f"- {r}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate NL A2/A4 canary smoke artifact (.local only)"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        artifact = build_artifact(registry)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(PROFILE_LABEL)
    print(f"  nl status: {artifact['nl_node_current']['status']}")
    print(f"  synthetic preview outbounds: "
          f"{[o['node_id'] for o in artifact['synthetic_canary_preview']['outbounds']]}")

    if args.dry_run:
        print("  dry-run: no files written")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "nl_canary_owner_profile.json"
    md_path = args.out_dir / "nl_canary_owner_profile.md"
    preview_path = args.out_dir / "nl_canary_selector_preview.json"
    json_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(format_markdown_artifact(artifact), encoding="utf-8")
    preview_path.write_text(
        json.dumps(artifact["synthetic_canary_preview"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    for p in (json_path, md_path, preview_path):
        print(f"  wrote: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
