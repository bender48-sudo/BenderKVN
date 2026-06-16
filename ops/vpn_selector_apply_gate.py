#!/usr/bin/env python3
"""Selector apply gate — SUB-GEN-SELECTOR-APPLY-GATE-001.

Single source of truth for the question: "Is it safe to apply the node selector
to real subscription generation for cohort X?" The answer is `APPLY_ALLOWED`.

HARD SAFETY (read before extending):
    * READ-ONLY. This tool NEVER writes templates, never mutates Remna, never
      changes subscriptions, never deploys, never applies anything.
    * It only evaluates registry + smoke matrix + selector dry-run and reports
      whether every hard gate passes.
    * `APPLY_ALLOWED=true` is a *precondition signal only*. The actual apply is a
      separate, explicit, owner-approved task. This tool refuses to imply that
      apply has happened.
    * Owner approval alone NEVER overrides a technical blocker.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from validate_vpn_node_registry import DEFAULT_REGISTRY
from vpn_node_selector import (
    COHORTS,
    VERDICT_GO,
    build_assignment_plan,
    load_validated_registry,
)
from vpn_node_smoke_matrix import build_smoke_matrix

BANNER = (
    "APPLY GATE - read-only. No template/Remna/subscription/deploy mutation. "
    "APPLY_ALLOWED is a precondition signal; real apply is a separate owner task."
)

# Cohorts for which a production-grade apply gate is meaningful.
GATED_COHORTS = frozenset({"PUBLIC_PROD", "OWNER_FF", "PAID_BETA_MANUAL", "CANARY"})

REQUIRED_PRE_APPLY_SNAPSHOT = [
    "current live injectHosts / subscription node set (owner export)",
    "current Remna template digest",
    "current selected cohort assignment baseline",
]

ROLLBACK_REQUIREMENTS = [
    "documented one-command revert to previous subscription node set",
    "owner can switch affected cohort back within 5 minutes",
    "drain plan for any newly added node (canary_percent step-down)",
]


@dataclass
class ApplyGateResult:
    cohort: str
    apply_allowed: bool = False
    selector_verdict: str = ""
    delivery_path_nodes: int = 0
    delivery_path_gate: int = 2
    production_capacity_nodes: int = 0
    blockers: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    required_pre_apply_snapshot: list[str] = field(default_factory=list)
    rollback_requirements: list[str] = field(default_factory=list)
    affected_cohorts: list[str] = field(default_factory=list)
    next_safe_command: str = ""
    owner_approved: bool = False
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "banner": BANNER,
            "dry_run": self.dry_run,
            "cohort": self.cohort,
            "APPLY_ALLOWED": self.apply_allowed,
            "selector_verdict": self.selector_verdict,
            "delivery_path_nodes": self.delivery_path_nodes,
            "delivery_path_gate": self.delivery_path_gate,
            "production_capacity_nodes": self.production_capacity_nodes,
            "owner_approved": self.owner_approved,
            "blockers": self.blockers,
            "required_approvals": self.required_approvals,
            "required_pre_apply_snapshot": self.required_pre_apply_snapshot,
            "rollback_requirements": self.rollback_requirements,
            "affected_cohorts": self.affected_cohorts,
            "next_safe_command": self.next_safe_command,
        }


def evaluate_apply_gate(
    cohort: str,
    registry: dict[str, Any],
    *,
    owner_approved: bool = False,
    rollback_ready: bool = False,
) -> ApplyGateResult:
    if cohort not in COHORTS:
        raise ValueError(f"unknown cohort {cohort!r}; expected one of {sorted(COHORTS)}")

    plan = build_assignment_plan(cohort, registry)
    matrix = build_smoke_matrix(registry, cohort=cohort)

    result = ApplyGateResult(
        cohort=cohort,
        selector_verdict=plan.verdict,
        delivery_path_nodes=matrix.delivery_path_nodes,
        delivery_path_gate=matrix.delivery_path_gate,
        production_capacity_nodes=matrix.production_capacity_nodes,
        owner_approved=owner_approved,
        required_pre_apply_snapshot=list(REQUIRED_PRE_APPLY_SNAPSHOT),
        rollback_requirements=list(ROLLBACK_REQUIREMENTS),
        affected_cohorts=[cohort],
        dry_run=True,
    )

    blockers: list[str] = []

    # --- Hard technical blockers (owner approval cannot override) ---
    if matrix.delivery_path_nodes < matrix.delivery_path_gate:
        blockers.append(
            f"delivery_path_nodes={matrix.delivery_path_nodes} < "
            f"{matrix.delivery_path_gate}"
        )
    if matrix.production_capacity_nodes < 2:
        blockers.append("no second production-capable node")

    suspect_capacity = [
        r.node_id for r in matrix.rows
        if r.suspect and not r.lab_only and not r.backup_only and r.selector_eligible
    ]
    if suspect_capacity:
        blockers.append(
            "suspect node counted as capacity: " + ", ".join(sorted(suspect_capacity))
        )

    lab_in_selection = [nid for nid in plan.selected_node_ids if _is_lab_node(registry, nid)]
    if lab_in_selection:
        blockers.append("lab-only node in selection: " + ", ".join(sorted(lab_in_selection)))

    disabled_nl_capacity = [
        r.node_id for r in matrix.rows
        if r.country == "NL" and r.disabled and r.selector_eligible
    ]
    if disabled_nl_capacity:
        blockers.append("disabled NL counted as capacity: " + ", ".join(disabled_nl_capacity))

    if cohort in GATED_COHORTS and plan.verdict != VERDICT_GO:
        blockers.append(f"selector verdict for {cohort} is {plan.verdict}, not GO")

    if not plan.selected_node_ids:
        blockers.append("selector dry-run selected no nodes")

    # registry validation already enforced by load_validated_registry (raises).

    # --- Process blockers (can be satisfied by owner) ---
    if not rollback_ready:
        blockers.append("no rollback plan confirmed (pass --rollback-ready when true)")
    if not owner_approved:
        blockers.append("no owner APPROVE APPLY confirmation (pass --owner-approved)")

    # de-duplicate, preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            ordered.append(b)
    result.blockers = ordered

    result.required_approvals = [
        "owner: APPROVE APPLY <cohort>",
        "owner: confirm rollback plan",
        "owner: confirm pre-apply snapshot captured",
    ]

    result.apply_allowed = len(result.blockers) == 0

    if result.apply_allowed:
        result.next_safe_command = (
            f"# All gates pass for {cohort}. Owner-reviewed apply is a SEPARATE task "
            "(SUB-GEN-SELECTOR-APPLY-001). Capture snapshot, then proceed under owner "
            "supervision."
        )
    else:
        result.next_safe_command = (
            "python ops/vpn_node_smoke_matrix.py --markdown  "
            "# resolve blockers above before any apply"
        )

    return result


def _is_lab_node(registry: dict[str, Any], node_id: str) -> bool:
    for node in registry.get("nodes") or []:
        if isinstance(node, dict) and str(node.get("node_id")) == node_id:
            groups = set(node.get("groups") or [])
            return node.get("role") == "lab" or "LAB_OWNER" in groups
    return False


def format_result(result: ApplyGateResult) -> str:
    lines = [
        f"Selector apply gate — cohort {result.cohort}",
        f"  {BANNER}",
        f"  APPLY_ALLOWED: {result.apply_allowed}",
        f"  selector_verdict: {result.selector_verdict}",
        f"  delivery_path_nodes: {result.delivery_path_nodes} / "
        f"{result.delivery_path_gate}",
        f"  production_capacity_nodes: {result.production_capacity_nodes}",
        f"  owner_approved: {result.owner_approved}",
    ]
    if result.blockers:
        lines.append("  blockers:")
        for b in result.blockers:
            lines.append(f"    - {b}")
    else:
        lines.append("  blockers: none")
    lines.append("  required_pre_apply_snapshot:")
    for s in result.required_pre_apply_snapshot:
        lines.append(f"    - {s}")
    lines.append("  rollback_requirements:")
    for r in result.rollback_requirements:
        lines.append(f"    - {r}")
    lines.append(f"  affected_cohorts: {result.affected_cohorts}")
    lines.append(f"  next_safe_command: {result.next_safe_command}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Selector apply gate (read-only; never applies anything)"
    )
    parser.add_argument("--cohort", choices=sorted(COHORTS), default="PUBLIC_PROD")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--owner-approved",
        action="store_true",
        help="Owner has issued APPROVE APPLY (does NOT override technical blockers)",
    )
    parser.add_argument(
        "--rollback-ready",
        action="store_true",
        help="Owner confirms a tested rollback plan exists",
    )
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        result = evaluate_apply_gate(
            args.cohort,
            registry,
            owner_approved=args.owner_approved,
            rollback_ready=args.rollback_ready,
        )
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
