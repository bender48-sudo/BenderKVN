#!/usr/bin/env python3
"""Shadow-mode subscription assignment diff — SUB-GEN-SELECTOR-INTEGRATION-001.

PURPOSE
    Show what the backend node selector *would* assign per cohort, compared to the
    current production pool, WITHOUT touching live subscription generation.

SAFETY (hard invariants — read before extending):
    * SHADOW ONLY. This script never edits the Remna template, never patches
      injectHosts, never writes subscriptions, and never calls any live API.
    * It reads only the redacted repo registry (ops/config/vpn_node_registry.yaml)
      and an optional owner-exported baseline file of node IDs.
    * Output is redacted: node IDs and group names only — no UUIDs, vless URLs,
      subscription URLs, tokens, IPs, or endpoints.
    * Applying the selector to real subscription generation is a SEPARATE,
      owner-reviewed task (SUB-GEN-SELECTOR-APPLY-001). This tool only produces
      evidence for that review.

The "current pool" is DERIVED from the registry (status=active, production group,
new assignments allowed), clearly labelled as registry-derived and NOT a live
confirmation. For a true comparison the owner can pass --baseline-file with a JSON
list of node IDs currently emitted in live subscriptions.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from validate_vpn_node_registry import DEFAULT_REGISTRY, count_delivery_path_nodes
from vpn_node_selector import (
    COHORTS,
    PRODUCTION_GROUPS,
    VERDICT_GO,
    AssignmentPlan,
    build_assignment_plan,
    load_validated_registry,
)

# Groups that never represent normal production delivery pool membership.
_NON_POOL_GROUPS = frozenset({"LAB_OWNER", "FALLBACK_MANUAL"})

SHADOW_BANNER = (
    "SHADOW MODE - no live subscription generation was read or modified. "
    "Apply is a separate owner-reviewed task (SUB-GEN-SELECTOR-APPLY-001)."
)


@dataclass
class ShadowReport:
    cohort: str
    verdict: str
    selector_node_ids: list[str] = field(default_factory=list)
    baseline_node_ids: list[str] = field(default_factory=list)
    baseline_source: str = "registry-derived (not live-confirmed)"
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    delivery_path_nodes: int = 0
    delivery_path_gate: int = 2
    apply_safe: bool = False
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = True
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort": self.cohort,
            "verdict": self.verdict,
            "selector_node_ids": self.selector_node_ids,
            "baseline_node_ids": self.baseline_node_ids,
            "baseline_source": self.baseline_source,
            "added": self.added,
            "removed": self.removed,
            "unchanged": self.unchanged,
            "delivery_path_nodes": self.delivery_path_nodes,
            "delivery_path_gate": self.delivery_path_gate,
            "apply_safe": self.apply_safe,
            "warnings": self.warnings,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "banner": SHADOW_BANNER,
        }


def derive_current_pool(registry: dict[str, Any]) -> list[str]:
    """Registry-derived current production pool (NOT a live confirmation).

    A node is treated as part of the current pool when it is active, in a
    production group, not a lab/fallback group, and accepts new assignments.
    """
    pool: list[str] = []
    for node in registry.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("status") != "active":
            continue
        groups = set(node.get("groups") or [])
        if not (groups & PRODUCTION_GROUPS):
            continue
        if groups & _NON_POOL_GROUPS:
            continue
        rollout = node.get("rollout") or {}
        if rollout.get("allow_new_assignments") is False:
            continue
        pool.append(str(node.get("node_id")))
    return sorted(pool)


def build_shadow_report(
    cohort: str,
    registry: dict[str, Any],
    *,
    baseline: list[str] | None = None,
    allow_suspect: bool = False,
) -> ShadowReport:
    plan: AssignmentPlan = build_assignment_plan(
        cohort, registry, allow_suspect=allow_suspect
    )
    if baseline is None:
        baseline_ids = derive_current_pool(registry)
        baseline_source = "registry-derived (not live-confirmed)"
    else:
        baseline_ids = sorted({str(b) for b in baseline})
        baseline_source = "owner-provided baseline file"

    selector_ids = list(plan.selected_node_ids)
    selector_set = set(selector_ids)
    baseline_set = set(baseline_ids)

    # apply_safe only when the cohort is GO and nothing would be removed blindly
    # is irrelevant here; apply remains owner-gated regardless. We only flag the
    # MINIMUM precondition: a GO verdict. Everything else stays NO/CONDITIONAL.
    apply_safe = plan.verdict == VERDICT_GO and bool(selector_ids)

    report = ShadowReport(
        cohort=cohort,
        verdict=plan.verdict,
        selector_node_ids=selector_ids,
        baseline_node_ids=baseline_ids,
        baseline_source=baseline_source,
        added=sorted(selector_set - baseline_set),
        removed=sorted(baseline_set - selector_set),
        unchanged=sorted(selector_set & baseline_set),
        delivery_path_nodes=plan.delivery_path_nodes,
        delivery_path_gate=plan.delivery_path_gate,
        apply_safe=apply_safe,
        warnings=list(plan.warnings),
        dry_run=True,
        applied=False,
    )
    return report


def format_shadow_report(report: ShadowReport) -> str:
    lines = [
        "VPN subscription assignment - SHADOW diff",
        f"  cohort: {report.cohort}",
        f"  verdict: {report.verdict}",
        f"  dry_run: {report.dry_run}",
        f"  applied: {report.applied}",
        f"  delivery_path_nodes: {report.delivery_path_nodes}",
        f"  delivery_path_gate: {report.delivery_path_gate}",
        f"  baseline_source: {report.baseline_source}",
        f"  baseline_node_ids: {report.baseline_node_ids or '[]'}",
        f"  selector_node_ids: {report.selector_node_ids or '[]'}",
        f"  would_add: {report.added or '[]'}",
        f"  would_remove: {report.removed or '[]'}",
        f"  unchanged: {report.unchanged or '[]'}",
        f"  apply_safe (GO precondition only): {report.apply_safe}",
    ]
    for warning in report.warnings:
        lines.append(f"  WARNING: {warning}")
    lines.append(f"  {SHADOW_BANNER}")
    return "\n".join(lines)


def _load_baseline(path: Path | None) -> list[str] | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("node_ids", [])
    if not isinstance(data, list):
        raise ValueError("baseline file must be a JSON list of node IDs (or {node_ids: [...]})")
    return [str(x) for x in data]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Shadow-mode subscription assignment diff (dry-run, no prod changes)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cohort", choices=sorted(COHORTS), help="Target cohort")
    group.add_argument("--all", action="store_true", help="Report for every cohort")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--baseline-file",
        type=Path,
        default=None,
        help="Optional JSON list of node IDs currently in live subs (owner export)",
    )
    parser.add_argument("--allow-suspect", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        baseline = _load_baseline(args.baseline_file)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    cohorts = sorted(COHORTS) if args.all else [args.cohort]
    reports = [
        build_shadow_report(c, registry, baseline=baseline, allow_suspect=args.allow_suspect)
        for c in cohorts
    ]

    if args.json:
        print(json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False))
    else:
        print(SHADOW_BANNER)
        for r in reports:
            print(format_shadow_report(r))
            print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
