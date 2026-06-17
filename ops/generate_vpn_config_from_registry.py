#!/usr/bin/env python3
"""Registry-driven config/subscription generator (DRY-RUN) — VPN-INVENTORY-DRIVEN-CONFIG-GENERATOR-001.

Generates a *preview* of outbounds/selectors/route policy from the registry model
for a cohort. Strictly dry-run:

    * reads only the redacted registry (no secrets, no UUIDs, no endpoints);
    * writes ONLY redacted artifacts under .local/ (never committed);
    * NEVER touches Remna / Caddy / subscription / template;
    * PUBLIC_PROD stays NO-GO until >= 2 clean production delivery paths.

Output (default .local/): generated_vpn_config_preview.{json,md}
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
ROOT = _OPS.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_config_integrity import verify_selector_outbound_mapping  # noqa: E402
from vpn_registry_model import (  # noqa: E402
    COHORT_CANARY,
    COHORT_LAB_OWNER,
    COHORT_PUBLIC_PROD,
    NodeModel,
    build_registry_model,
    select_for_cohort,
)
from vpn_node_selector import load_validated_registry  # noqa: E402
from vpn_production_guardrails import (  # noqa: E402
    GuardrailConfig,
    capacity_state_from_nodes,
)

DEFAULT_OUT_DIR = ROOT / ".local"
COHORTS = (COHORT_LAB_OWNER, COHORT_CANARY, COHORT_PUBLIC_PROD)

BANNER = (
    "DRY-RUN GENERATOR - registry-derived preview only. Synthetic outbound tags "
    "(no real UUID/endpoint). No Remna/Caddy/subscription/template mutation."
)

SYNTHETIC_CANARY_BANNER = (
    "SYNTHETIC CANARY PREVIEW - in-memory overlay only; registry file unchanged. "
    "Does NOT enable live canary or count as production capacity."
)


def apply_synthetic_canary_overlay(registry: dict[str, Any], node_id: str) -> dict[str, Any]:
    """In-memory preview: show what CANARY cohort would look like if node promoted.

    Keeps delivery_path_eligible=false and allow_new_assignments=false so the
    preview cannot be mistaken for a production-capacity increase.
    """
    reg = copy.deepcopy(registry)
    for node in reg.get("nodes") or []:
        if not isinstance(node, dict) or node.get("node_id") != node_id:
            continue
        node["status"] = "canary"
        rollout = node.setdefault("rollout", {})
        rollout["canary_percent"] = 5
        rollout["allow_new_assignments"] = False
        node["delivery_path_eligible"] = False
        return reg
    raise ValueError(f"synthetic canary preview: node_id {node_id!r} not found in registry")


@dataclass
class GeneratedConfig:
    cohort: str
    go: bool
    outbounds: list[dict[str, Any]] = field(default_factory=list)
    selector_groups: dict[str, list[str]] = field(default_factory=dict)
    route_policy: dict[str, list[str]] = field(default_factory=dict)
    capacity_summary: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "banner": BANNER,
            "cohort": self.cohort,
            "go": self.go,
            "outbounds": self.outbounds,
            "selector_groups": self.selector_groups,
            "route_policy": self.route_policy,
            "capacity_summary": self.capacity_summary,
            "blockers": self.blockers,
            "warnings": self.warnings,
        }


def _selector_groups(models: list[NodeModel]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for m in models:
        groups.setdefault(m.selector_group, []).append(m.outbound_tag)
    for k in groups:
        groups[k] = sorted(groups[k])
    return groups


def _route_policy(models: list[NodeModel]) -> dict[str, list[str]]:
    policy: dict[str, list[str]] = {}
    for m in models:
        for rc in m.route_classes:
            policy.setdefault(rc, []).append(m.outbound_tag)
    for k in policy:
        policy[k] = sorted(policy[k])
    return policy


def generate_for_cohort(
    registry: dict[str, Any],
    cohort: str,
    *,
    config: GuardrailConfig | None = None,
) -> GeneratedConfig:
    cfg = config or GuardrailConfig()
    models = build_registry_model(registry)
    selected = select_for_cohort(models, cohort)
    nodes = [n for n in (registry.get("nodes") or []) if isinstance(n, dict)]
    cap = capacity_state_from_nodes(nodes)

    outbounds = [
        {
            "tag": m.outbound_tag,
            "node_id": m.node_id,
            "selector_group": m.selector_group,
            "route_classes": m.route_classes,
            "weight": m.weight,
            "lifecycle_status": m.lifecycle_status,
        }
        for m in selected
    ]
    selector_groups = _selector_groups(selected)
    route_policy = _route_policy(selected)

    blockers: list[str] = []
    warnings: list[str] = []

    # selector→outbound integrity (model-based, never positional)
    known_tags = {m.outbound_tag for m in selected}
    for grp, tags in selector_groups.items():
        for err in verify_selector_outbound_mapping(tags, known_tags):
            blockers.append(f"{grp}: {err}")

    prod_paths = cap.production_capacity_nodes
    go = True
    if cohort == COHORT_PUBLIC_PROD:
        if prod_paths < cfg.minimum_delivery_paths:
            go = False
            blockers.append(
                f"PUBLIC_PROD NO-GO: production delivery paths={prod_paths} "
                f"< minimum {cfg.minimum_delivery_paths}"
            )
    if not selected:
        go = False
        blockers.append(f"no nodes eligible for cohort {cohort}")

    if cohort == COHORT_CANARY:
        canary_nodes = [m for m in selected if m.lifecycle_status == "canary" or m.canary_percent > 0]
        if not canary_nodes:
            warnings.append("CANARY: no node with canary_percent>0 / canary status (preview only)")

    return GeneratedConfig(
        cohort=cohort,
        go=go,
        outbounds=outbounds,
        selector_groups=selector_groups,
        route_policy=route_policy,
        capacity_summary={
            "delivery_path_nodes": cap.delivery_path_nodes,
            "production_capacity_nodes": cap.production_capacity_nodes,
            "relay_ips": cap.relay_ips,
            "geos": cap.geos,
            "minimum_delivery_paths": cfg.minimum_delivery_paths,
        },
        blockers=blockers,
        warnings=warnings,
    )


def format_markdown(gen: GeneratedConfig) -> str:
    lines = [
        f"# Generated VPN config preview — cohort {gen.cohort}",
        "",
        f"> {BANNER}",
        "",
        f"- GO: {gen.go}",
        "",
        "## Outbounds (node_id → synthetic tag)",
        "",
        "| node_id | outbound_tag | group | routes | weight | status |",
        "|---------|--------------|-------|--------|--------|--------|",
    ]
    for o in gen.outbounds:
        lines.append(
            f"| {o['node_id']} | {o['tag']} | {o['selector_group']} | "
            f"{','.join(o['route_classes'])} | {o['weight']} | {o['lifecycle_status']} |"
        )
    if not gen.outbounds:
        lines.append("| (none) | - | - | - | - | - |")
    lines += ["", "## Selector groups", ""]
    for grp, tags in sorted(gen.selector_groups.items()):
        lines.append(f"- **{grp}**: {', '.join(tags)}")
    lines += ["", "## Capacity summary", ""]
    for k, v in gen.capacity_summary.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Blockers", ""]
    lines += [f"- {b}" for b in gen.blockers] or ["- none"]
    if gen.warnings:
        lines += ["", "## Warnings", ""] + [f"- {w}" for w in gen.warnings]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Registry-driven VPN config generator (dry-run; .local only)"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--cohort", choices=COHORTS, default=COHORT_PUBLIC_PROD)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="print summary; no files written")
    parser.add_argument(
        "--synthetic-canary-node",
        metavar="NODE_ID",
        help="In-memory canary overlay for preview only (registry file unchanged)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        if args.synthetic_canary_node:
            registry = apply_synthetic_canary_overlay(registry, args.synthetic_canary_node)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    gen = generate_for_cohort(registry, args.cohort)
    if args.synthetic_canary_node:
        gen.warnings.insert(0, SYNTHETIC_CANARY_BANNER)

    if args.json:
        print(json.dumps(gen.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(BANNER)
        print(f"  cohort: {gen.cohort}")
        print(f"  GO: {gen.go}")
        print(f"  outbounds: {[o['node_id'] for o in gen.outbounds] or '[]'}")
        for b in gen.blockers:
            print(f"  blocker: {b}")

    if args.dry_run:
        print("  dry-run: no files written")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "generated_vpn_config_preview.json"
    md_path = args.out_dir / "generated_vpn_config_preview.md"
    json_path.write_text(json.dumps(gen.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(format_markdown(gen), encoding="utf-8")
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
