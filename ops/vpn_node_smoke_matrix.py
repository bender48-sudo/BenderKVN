#!/usr/bin/env python3
"""VPN node smoke matrix — NODE-SMOKE-MATRIX-RUNNER-001.

Converts the redacted node registry + selector policy into a production
readiness matrix. READ-ONLY / DRY-RUN by default:

    * reads only ops/config/vpn_node_registry.yaml (redacted, no secrets);
    * NO live network calls;
    * NO Remna/Caddy/subscription/template mutation;
    * output redacted: node_id, role, status, region/country only.

It answers the standing scalability question: how many delivery paths exist,
which nodes count as production capacity, and which gates (PUBLIC_PROD / paid
beta / 300 / 30k) can pass. A NO-GO verdict is NOT a tool error — exit code is
0 for any successfully generated report and nonzero only for invalid registry
or tool failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from validate_vpn_node_registry import (
    DEFAULT_REGISTRY,
    count_delivery_path_nodes,
)
from vpn_node_selector import (
    COHORTS,
    COHORT_POLICIES,
    _canary_eligible,
    _is_suspect,
    _node_groups,
    evaluate_node_for_cohort,
    load_validated_registry,
)

VERDICT_PASS = "PASS"
VERDICT_WARN = "WARN"
VERDICT_FAIL = "FAIL"
VERDICT_BLOCKED = "BLOCKED"
VERDICT_NOT_TESTED = "NOT_TESTED"

BLOCKED_STATUSES = frozenset({"disabled", "failed", "decommissioned", "draining"})
NOT_TESTED_SMOKE = frozenset(
    {"", "pending", "not_in_live_subs", "n/a", "none", "unknown", "needs_diagnosis"}
)

BANNER = (
    "DRY-RUN MATRIX - registry-derived readiness only. No live network calls, "
    "no Remna/Caddy/subscription mutation. NO-GO is a verdict, not a tool error."
)

# Standing sprint invariant: selector apply to production is disabled (dry-run /
# shadow only) until SUB-GEN-SELECTOR-APPLY-GATE-001 + owner APPROVE APPLY.
SELECTOR_APPLY_ENABLED = False


@dataclass
class NodeMatrixRow:
    node_id: str
    role: str
    status: str
    region: str
    country: str
    delivery_path_eligible: bool
    lab_only: bool
    backup_only: bool
    suspect: bool
    disabled: bool
    canary_percent: int
    selector_eligible: bool
    production_capacity: bool
    reason: str
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "status": self.status,
            "region": self.region,
            "country": self.country,
            "delivery_path_eligible": self.delivery_path_eligible,
            "lab_only": self.lab_only,
            "backup_only": self.backup_only,
            "suspect": self.suspect,
            "disabled": self.disabled,
            "canary_percent": self.canary_percent,
            "selector_eligible": self.selector_eligible,
            "production_capacity": self.production_capacity,
            "reason": self.reason,
            "verdict": self.verdict,
        }


@dataclass
class SmokeMatrix:
    cohort: str
    rows: list[NodeMatrixRow] = field(default_factory=list)
    delivery_path_nodes: int = 0
    production_capacity_nodes: int = 0
    canary_ready_nodes: int = 0
    delivery_path_gate: int = 2
    public_prod_go: bool = False
    small_paid_beta_go: bool = False
    configs_300_go: bool = False
    go_30k: bool = False
    selector_apply_enabled: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "banner": BANNER,
            "dry_run": self.dry_run,
            "cohort": self.cohort,
            "summary": {
                "delivery_path_nodes": self.delivery_path_nodes,
                "production_capacity_nodes": self.production_capacity_nodes,
                "canary_ready_nodes": self.canary_ready_nodes,
                "delivery_path_gate": self.delivery_path_gate,
                "public_prod_go": self.public_prod_go,
                "small_paid_beta_go": self.small_paid_beta_go,
                "configs_300_go": self.configs_300_go,
                "go_30k": self.go_30k,
                "selector_apply_enabled": self.selector_apply_enabled,
            },
            "blockers": self.blockers,
            "warnings": self.warnings,
            "nodes": [r.to_dict() for r in self.rows],
        }


def _is_lab_only(node: dict[str, Any]) -> bool:
    groups = _node_groups(node)
    return node.get("role") == "lab" or "LAB_OWNER" in groups


def _is_backup_only(node: dict[str, Any]) -> bool:
    groups = _node_groups(node)
    return node.get("role") == "backup" or "FALLBACK_MANUAL" in groups


def is_production_capacity(node: dict[str, Any]) -> bool:
    """A node that genuinely counts as a production delivery path.

    Strict by design: a lab-only, backup, suspect, disabled, or non-exit node
    NEVER counts. This is the count that gates 300/30k.
    """
    if node.get("role") != "exit":
        return False
    if node.get("status") != "active":
        return False
    if node.get("delivery_path_eligible") is not True:
        return False
    if _is_suspect(node):
        return False
    if _is_lab_only(node):
        return False
    if _is_backup_only(node):
        return False
    return True


def evaluate_node_row(
    node: dict[str, Any],
    cohort: str,
    *,
    diagnostic_mode: bool = False,
) -> NodeMatrixRow:
    node_id = str(node.get("node_id", "?"))
    role = str(node.get("role", "?"))
    status = str(node.get("status", "?"))
    region = str(node.get("region", "?"))
    country = str(node.get("country", "?"))
    rollout = node.get("rollout") or {}
    health = node.get("health") or {}

    canary_percent = rollout.get("canary_percent") or 0
    try:
        canary_percent = int(canary_percent)
    except (TypeError, ValueError):
        canary_percent = 0

    suspect = _is_suspect(node)
    lab_only = _is_lab_only(node)
    backup_only = _is_backup_only(node)
    disabled = status in BLOCKED_STATUSES
    delivery_eligible = node.get("delivery_path_eligible") is True
    prod_capacity = is_production_capacity(node)

    policy = COHORT_POLICIES[cohort]
    selector_ok, selector_reason = evaluate_node_for_cohort(
        node, policy, allow_suspect=diagnostic_mode
    )

    smoke = str(health.get("last_smoke_status", "")).lower().strip()

    # Verdict precedence (most blocking first).
    if disabled:
        verdict = VERDICT_BLOCKED
        reason = f"status={status} blocked from delivery"
    elif suspect:
        verdict = VERDICT_FAIL
        reason = "health=suspect/needs_diagnosis; excluded from production capacity"
    elif lab_only:
        verdict = VERDICT_WARN
        reason = "lab-only (owner/F&F); not production capacity"
    elif backup_only:
        verdict = VERDICT_WARN
        reason = "backup edge / fallback; not VPN delivery capacity"
    elif prod_capacity:
        verdict = VERDICT_PASS
        reason = "active exit, delivery_path_eligible, healthy"
    elif status in {"staging", "canary"}:
        verdict = VERDICT_WARN
        reason = f"status={status}; promotion gate pending"
    elif smoke in NOT_TESTED_SMOKE:
        verdict = VERDICT_NOT_TESTED
        reason = f"smoke={smoke or 'unknown'}; not proven for delivery"
    else:
        verdict = VERDICT_WARN
        reason = selector_reason or "not counted as production delivery path"

    return NodeMatrixRow(
        node_id=node_id,
        role=role,
        status=status,
        region=region,
        country=country,
        delivery_path_eligible=delivery_eligible,
        lab_only=lab_only,
        backup_only=backup_only,
        suspect=suspect,
        disabled=disabled,
        canary_percent=canary_percent,
        selector_eligible=selector_ok,
        production_capacity=prod_capacity,
        reason=reason,
        verdict=verdict,
    )


def build_smoke_matrix(
    registry: dict[str, Any],
    *,
    cohort: str = "PUBLIC_PROD",
    diagnostic_mode: bool = False,
) -> SmokeMatrix:
    if cohort not in COHORTS:
        raise ValueError(f"unknown cohort {cohort!r}; expected one of {sorted(COHORTS)}")

    nodes = [n for n in (registry.get("nodes") or []) if isinstance(n, dict)]
    capacity_policy = registry.get("capacity_policy") or {}
    gate = int(capacity_policy.get("delivery_path_gate_300", 2))

    rows = [evaluate_node_row(n, cohort, diagnostic_mode=diagnostic_mode) for n in nodes]
    rows.sort(key=lambda r: r.node_id)

    delivery_path_nodes = count_delivery_path_nodes(nodes)
    production_capacity_nodes = sum(1 for r in rows if r.production_capacity)
    canary_ready_nodes = sum(1 for n in nodes if _canary_eligible(n))

    matrix = SmokeMatrix(
        cohort=cohort,
        rows=rows,
        delivery_path_nodes=delivery_path_nodes,
        production_capacity_nodes=production_capacity_nodes,
        canary_ready_nodes=canary_ready_nodes,
        delivery_path_gate=gate,
        selector_apply_enabled=SELECTOR_APPLY_ENABLED,
        warnings=list(registry.get("_validation_warnings") or []),
        dry_run=True,
    )

    # GO booleans — conservative; current state must yield all False.
    matrix.public_prod_go = (
        production_capacity_nodes >= gate and delivery_path_nodes >= gate
    )
    matrix.small_paid_beta_go = production_capacity_nodes >= 2
    matrix.configs_300_go = (
        delivery_path_nodes >= gate and production_capacity_nodes >= 2
    )
    matrix.go_30k = (
        delivery_path_nodes >= int(capacity_policy.get("delivery_path_gate_30k", 2))
        and production_capacity_nodes >= 2
    )

    matrix.blockers = compute_blockers(matrix, nodes)
    return matrix


def compute_blockers(matrix: SmokeMatrix, nodes: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if matrix.delivery_path_nodes < matrix.delivery_path_gate:
        blockers.append(
            f"only {matrix.delivery_path_nodes} delivery path(s); "
            f"need >= {matrix.delivery_path_gate}"
        )
    if matrix.production_capacity_nodes < 2:
        blockers.append(
            f"production_capacity_nodes={matrix.production_capacity_nodes}; "
            "no second production-capable node"
        )
    for r in matrix.rows:
        if r.suspect and not r.lab_only and not r.backup_only:
            blockers.append(f"{r.node_id}: suspect node not counted as capacity")
    for r in matrix.rows:
        if r.lab_only and r.status in {"active", "staging", "canary"}:
            blockers.append(f"{r.node_id}: lab-only, must not be production default")
    for n in nodes:
        nid = str(n.get("node_id"))
        if n.get("country") == "NL" and n.get("status") in BLOCKED_STATUSES:
            blockers.append(f"{nid}: NL not active normal delivery capacity")
        if _is_backup_only(n) and n.get("status") == "active":
            blockers.append(f"{nid}: backup edge, not delivery capacity")
    if matrix.canary_ready_nodes == 0:
        blockers.append("no canary-ready second node (canary_percent=0 everywhere)")
    if not matrix.selector_apply_enabled:
        blockers.append("selector apply disabled (dry-run/shadow; needs APPROVE APPLY)")
    # de-duplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            ordered.append(b)
    return ordered


def format_matrix_markdown(matrix: SmokeMatrix) -> str:
    s = matrix
    lines = [
        f"# VPN node smoke matrix — cohort {s.cohort}",
        "",
        f"> {BANNER}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| delivery_path_nodes | {s.delivery_path_nodes} |",
        f"| delivery_path_gate | {s.delivery_path_gate} |",
        f"| production_capacity_nodes | {s.production_capacity_nodes} |",
        f"| canary_ready_nodes | {s.canary_ready_nodes} |",
        f"| selector_apply_enabled | {s.selector_apply_enabled} |",
        f"| public_prod_go | {s.public_prod_go} |",
        f"| small_paid_beta_go | {s.small_paid_beta_go} |",
        f"| configs_300_go | {s.configs_300_go} |",
        f"| go_30k | {s.go_30k} |",
        "",
        "## Nodes",
        "",
        "| Node | Role | Status | Geo | Prod capacity? | Verdict | Reason |",
        "|------|------|--------|-----|----------------|---------|--------|",
    ]
    for r in s.rows:
        geo = f"{r.region}/{r.country}"
        cap = "yes" if r.production_capacity else "no"
        lines.append(
            f"| {r.node_id} | {r.role} | {r.status} | {geo} | {cap} | "
            f"{r.verdict} | {r.reason} |"
        )
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if s.blockers:
        for b in s.blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- none")
    if s.warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        for w in s.warnings:
            lines.append(f"- {w}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VPN node smoke matrix (dry-run readiness; no prod mutation)"
    )
    parser.add_argument(
        "--cohort",
        choices=sorted(COHORTS),
        default="PUBLIC_PROD",
        help="Cohort to evaluate selector eligibility against (default PUBLIC_PROD)",
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown")
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Diagnostic mode: include suspect nodes in selector eligibility only",
    )
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
        matrix = build_smoke_matrix(
            registry, cohort=args.cohort, diagnostic_mode=args.diagnostic
        )
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json and not args.markdown:
        print(json.dumps(matrix.to_dict(), indent=2, ensure_ascii=False))
    elif args.markdown and not args.json:
        print(format_matrix_markdown(matrix))
    else:
        # default: markdown to stdout (human first), JSON suppressed
        print(format_matrix_markdown(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
