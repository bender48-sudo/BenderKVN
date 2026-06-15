#!/usr/bin/env python3
"""Dry-run VPN node selector — SUB-GEN-SELECTOR-STRATEGY-001.

Reads ops/config/vpn_node_registry.yaml and produces a deterministic assignment
plan for a target cohort. Does NOT change live subscription generation.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from validate_vpn_node_registry import (
    DEFAULT_REGISTRY,
    count_delivery_path_nodes,
    load_registry,
    validate_registry,
)

ROOT = Path(__file__).resolve().parent.parent

COHORTS = frozenset(
    {
        "LAB_OWNER",
        "OWNER_FF",
        "PAID_BETA_MANUAL",
        "PUBLIC_PROD",
        "CANARY",
        "FALLBACK_MANUAL",
    }
)

VERDICT_GO = "GO"
VERDICT_CONDITIONAL = "CONDITIONAL"
VERDICT_NO_GO = "NO-GO"

BLOCKED_STATUSES = frozenset({"disabled", "failed", "decommissioned", "draining"})

PRODUCTION_GROUPS = frozenset(
    {
        "RU_RELAY_ACTIVE",
        "RU_RELAY_CANARY",
        "INTL_DIRECT_ACTIVE",
        "INTL_STEALTH_ACTIVE",
    }
)

SUSPECT_MONITOR_STATUSES = frozenset({"suspect", "needs_diagnosis"})
SUSPECT_SMOKE_STATUSES = frozenset({"needs_diagnosis", "fail", "failed"})


@dataclass(frozen=True)
class CohortPolicy:
    name: str
    allowed_groups: frozenset[str] | None  # None = any except forbidden
    forbidden_groups: frozenset[str]
    allowed_statuses: frozenset[str]
    require_canary: bool = False
    require_fallback_group: bool = False
    allow_suspect_default: bool = False
    ignore_allow_new_for_groups: frozenset[str] = frozenset()
    min_delivery_path_nodes: int = 0
    hard_fail_below_delivery_gate: bool = False
    empty_verdict: str = VERDICT_NO_GO
    success_verdict: str = VERDICT_GO
    partial_verdict: str = VERDICT_CONDITIONAL


COHORT_POLICIES: dict[str, CohortPolicy] = {
    "LAB_OWNER": CohortPolicy(
        name="LAB_OWNER",
        allowed_groups=frozenset({"LAB_OWNER"}),
        forbidden_groups=frozenset(),
        allowed_statuses=frozenset({"staging", "canary", "active"}),
        allow_suspect_default=True,
        ignore_allow_new_for_groups=frozenset({"LAB_OWNER"}),
        empty_verdict=VERDICT_NO_GO,
        success_verdict=VERDICT_GO,
    ),
    "OWNER_FF": CohortPolicy(
        name="OWNER_FF",
        allowed_groups=PRODUCTION_GROUPS,
        forbidden_groups=frozenset({"LAB_OWNER", "FALLBACK_MANUAL"}),
        allowed_statuses=frozenset({"active", "canary"}),
        min_delivery_path_nodes=0,
        empty_verdict=VERDICT_NO_GO,
        success_verdict=VERDICT_CONDITIONAL,
        partial_verdict=VERDICT_CONDITIONAL,
    ),
    "PAID_BETA_MANUAL": CohortPolicy(
        name="PAID_BETA_MANUAL",
        allowed_groups=PRODUCTION_GROUPS,
        forbidden_groups=frozenset({"LAB_OWNER", "FALLBACK_MANUAL"}),
        allowed_statuses=frozenset({"active", "canary"}),
        empty_verdict=VERDICT_NO_GO,
        success_verdict=VERDICT_CONDITIONAL,
        partial_verdict=VERDICT_CONDITIONAL,
    ),
    "PUBLIC_PROD": CohortPolicy(
        name="PUBLIC_PROD",
        allowed_groups=PRODUCTION_GROUPS,
        forbidden_groups=frozenset({"LAB_OWNER", "FALLBACK_MANUAL"}),
        allowed_statuses=frozenset({"active", "canary"}),
        min_delivery_path_nodes=2,
        hard_fail_below_delivery_gate=True,
        empty_verdict=VERDICT_NO_GO,
        success_verdict=VERDICT_GO,
    ),
    "CANARY": CohortPolicy(
        name="CANARY",
        allowed_groups=frozenset({"RU_RELAY_CANARY"}),
        forbidden_groups=frozenset({"LAB_OWNER", "FALLBACK_MANUAL"}),
        allowed_statuses=frozenset({"canary", "active"}),
        require_canary=True,
        empty_verdict=VERDICT_NO_GO,
        success_verdict=VERDICT_CONDITIONAL,
    ),
    "FALLBACK_MANUAL": CohortPolicy(
        name="FALLBACK_MANUAL",
        allowed_groups=frozenset({"FALLBACK_MANUAL"}),
        forbidden_groups=frozenset({"LAB_OWNER"}),
        allowed_statuses=frozenset({"active", "staging", "canary"}),
        require_fallback_group=True,
        ignore_allow_new_for_groups=frozenset({"FALLBACK_MANUAL"}),
        empty_verdict=VERDICT_NO_GO,
        success_verdict=VERDICT_CONDITIONAL,
    ),
}


@dataclass
class NodeRejection:
    node_id: str
    reason: str


@dataclass
class AssignmentPlan:
    cohort: str
    verdict: str
    selected_node_ids: list[str] = field(default_factory=list)
    rejections: list[NodeRejection] = field(default_factory=list)
    delivery_path_nodes: int = 0
    delivery_path_gate: int = 2
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = True
    allow_suspect: bool = False
    diagnostic_mode: bool = False


def load_validated_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = load_registry(path)
    errors, warnings = validate_registry(data, raw)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"registry validation failed: {joined}")
    data["_validation_warnings"] = warnings
    return data


def _node_groups(node: dict[str, Any]) -> set[str]:
    return set(node.get("groups") or [])


def _is_suspect(node: dict[str, Any]) -> bool:
    health = node.get("health") or {}
    monitor = str(health.get("monitor_status", "")).lower()
    smoke = str(health.get("last_smoke_status", "")).lower()
    if monitor in SUSPECT_MONITOR_STATUSES:
        return True
    if smoke in SUSPECT_SMOKE_STATUSES:
        return True
    return False


def _canary_eligible(node: dict[str, Any]) -> bool:
    rollout = node.get("rollout") or {}
    status = node.get("status")
    groups = _node_groups(node)
    canary_percent = rollout.get("canary_percent") or 0
    allow_new = rollout.get("allow_new_assignments")
    if status == "canary":
        return allow_new is not False
    if "RU_RELAY_CANARY" in groups and canary_percent > 0 and allow_new is True:
        return True
    return False


def evaluate_node_for_cohort(
    node: dict[str, Any],
    policy: CohortPolicy,
    *,
    allow_suspect: bool = False,
) -> tuple[bool, str | None]:
    node_id = str(node.get("node_id", "?"))
    status = node.get("status")
    groups = _node_groups(node)
    rollout = node.get("rollout") or {}

    if status in BLOCKED_STATUSES:
        return False, f"status={status} blocked for new assignments"

    if status not in policy.allowed_statuses:
        return False, f"status={status} not allowed for cohort {policy.name}"

    if groups & policy.forbidden_groups:
        forbidden = ", ".join(sorted(groups & policy.forbidden_groups))
        return False, f"forbidden group(s): {forbidden}"

    if policy.require_fallback_group:
        if "FALLBACK_MANUAL" not in groups:
            return False, "not in FALLBACK_MANUAL group"
    elif policy.allowed_groups is not None:
        if not (groups & policy.allowed_groups):
            allowed = ", ".join(sorted(policy.allowed_groups))
            return False, f"no required group ({allowed})"

    ignore_allow = groups & policy.ignore_allow_new_for_groups
    if rollout.get("allow_new_assignments") is False and not ignore_allow:
        return False, "allow_new_assignments=false"

    if policy.require_canary and not _canary_eligible(node):
        return False, "canary_percent=0 or not in RU_RELAY_CANARY/canary status"

    if _is_suspect(node) and not (allow_suspect or policy.allow_suspect_default):
        return False, "suspect node excluded (use --allow-suspect for diagnostic)"

    if policy.name in {"OWNER_FF", "PAID_BETA_MANUAL", "PUBLIC_PROD"}:
        if "LAB_OWNER" in groups:
            return False, "LAB_OWNER node excluded from production cohort"

    if node_id == "nl-node-1" and status == "disabled":
        return False, "NL disabled awaiting A2/A4 gates"

    cohort_weight = rollout.get("cohort_weight")
    if policy.name in {"OWNER_FF", "PAID_BETA_MANUAL", "PUBLIC_PROD"}:
        if isinstance(cohort_weight, (int, float)) and cohort_weight <= 0 and status != "canary":
            return False, "cohort_weight=0"

    return True, None


def _sort_key(node: dict[str, Any]) -> tuple:
    rollout = node.get("rollout") or {}
    weight = rollout.get("cohort_weight") or 0
    return (-int(weight) if isinstance(weight, (int, float)) else 0, str(node.get("node_id", "")))


def build_assignment_plan(
    cohort: str,
    registry: dict[str, Any],
    *,
    allow_suspect: bool = False,
    diagnostic_mode: bool = False,
) -> AssignmentPlan:
    if cohort not in COHORTS:
        raise ValueError(f"unknown cohort {cohort!r}; expected one of {sorted(COHORTS)}")

    policy = COHORT_POLICIES[cohort]
    nodes = registry.get("nodes") or []
    capacity_policy = registry.get("capacity_policy") or {}
    delivery_gate = int(capacity_policy.get("delivery_path_gate_300", 2))
    delivery_count = count_delivery_path_nodes(nodes)

    plan = AssignmentPlan(
        cohort=cohort,
        verdict=VERDICT_NO_GO,
        delivery_path_nodes=delivery_count,
        delivery_path_gate=delivery_gate,
        allow_suspect=allow_suspect,
        diagnostic_mode=diagnostic_mode,
        warnings=list(registry.get("_validation_warnings") or []),
    )

    if policy.hard_fail_below_delivery_gate and delivery_count < policy.min_delivery_path_nodes:
        plan.warnings.append(
            f"delivery_path_nodes={delivery_count} < {policy.min_delivery_path_nodes}: "
            f"cohort {cohort} hard NO-GO"
        )

    selected: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ok, reason = evaluate_node_for_cohort(
            node,
            policy,
            allow_suspect=allow_suspect or diagnostic_mode,
        )
        node_id = str(node.get("node_id", "?"))
        if ok:
            selected.append(node)
        elif reason:
            plan.rejections.append(NodeRejection(node_id=node_id, reason=reason))

    selected.sort(key=_sort_key)
    plan.selected_node_ids = [str(n.get("node_id")) for n in selected]

    if policy.hard_fail_below_delivery_gate and delivery_count < policy.min_delivery_path_nodes:
        plan.verdict = VERDICT_NO_GO
        plan.selected_node_ids = []
        return plan

    if not plan.selected_node_ids:
        plan.verdict = policy.empty_verdict
        return plan

    if delivery_count < delivery_gate and cohort in {"OWNER_FF", "PAID_BETA_MANUAL", "CANARY"}:
        plan.warnings.append(
            f"delivery_path_nodes={delivery_count} < {delivery_gate}: capacity gate not met"
        )
        plan.verdict = policy.partial_verdict if hasattr(policy, "partial_verdict") else VERDICT_CONDITIONAL
    elif cohort in {"OWNER_FF", "PAID_BETA_MANUAL", "FALLBACK_MANUAL", "CANARY"}:
        plan.verdict = policy.success_verdict
    elif cohort == "LAB_OWNER":
        plan.verdict = VERDICT_GO
    elif cohort == "PUBLIC_PROD" and delivery_count >= delivery_gate:
        plan.verdict = VERDICT_GO
    else:
        plan.verdict = policy.success_verdict

    return plan


def format_assignment_plan(plan: AssignmentPlan) -> str:
    lines = [
        "VPN node selector dry-run",
        f"  cohort: {plan.cohort}",
        f"  verdict: {plan.verdict}",
        f"  dry_run: {plan.dry_run}",
        f"  delivery_path_nodes: {plan.delivery_path_nodes}",
        f"  delivery_path_gate: {plan.delivery_path_gate}",
        f"  selected_node_ids: {plan.selected_node_ids or '[]'}",
    ]
    if plan.rejections:
        lines.append("  rejected:")
        for rej in sorted(plan.rejections, key=lambda r: r.node_id):
            lines.append(f"    - {rej.node_id}: {rej.reason}")
    for warning in plan.warnings:
        lines.append(f"  WARNING: {warning}")
    return "\n".join(lines)


def run_selector(
    cohort: str,
    registry_path: Path = DEFAULT_REGISTRY,
    *,
    allow_suspect: bool = False,
    diagnostic_mode: bool = False,
) -> AssignmentPlan:
    registry = load_validated_registry(registry_path)
    return build_assignment_plan(
        cohort,
        registry,
        allow_suspect=allow_suspect,
        diagnostic_mode=diagnostic_mode,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run VPN node cohort selector")
    parser.add_argument(
        "--cohort",
        required=True,
        choices=sorted(COHORTS),
        help="Target assignment cohort",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help=f"Registry YAML path (default: {DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--allow-suspect",
        action="store_true",
        help="Allow suspect nodes (diagnostic mode)",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Diagnostic/lab mode (allows suspect nodes)",
    )
    args = parser.parse_args(argv)

    try:
        plan = run_selector(
            args.cohort,
            args.registry,
            allow_suspect=args.allow_suspect,
            diagnostic_mode=args.diagnostic,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(format_assignment_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
