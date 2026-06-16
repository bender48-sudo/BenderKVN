#!/usr/bin/env python3
"""Central VPN production guardrails — VPN-PRODUCTION-GUARDRAILS-001.

ONE place that answers: "Is this proposed VPN production state change allowed?"

CORE RULE (VPN-AUTO-CUTTING-GUARD-001):
    Stability must NOT be achieved by silently reducing production capacity.
    Any capacity reduction must be an explicit degrade/drain/incident/manual
    decision with owner approval, a rollback snapshot, and (for incidents) a TTL.

HARD SAFETY:
    * Pure validation logic. NO network, NO Remna, NO Caddy, NO template writes,
      NO subscription writes, NO secrets, NO live apply.
    * Operates on synthetic before/after CapacityState objects so the selector
      apply gate and (later) migrated patch scripts can share one rule set.
    * `allowed=True` is a precondition signal only; the actual apply remains a
      separate, owner-approved step.

Architecture:
    node inventory -> node smoke matrix -> production guardrails -> selector
    apply gate -> owner-approved apply
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from vpn_node_smoke_matrix import is_production_capacity
except ImportError:  # pragma: no cover - allow import when ops not on path yet
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from vpn_node_smoke_matrix import is_production_capacity

# Operational modes (kept separate on purpose).
MODE_DRY_RUN = "dry_run"
MODE_SCALE = "scale"
MODE_DEGRADE = "degrade"
MODE_INCIDENT = "incident"
MODE_MANUAL_EMERGENCY = "manual_emergency"

APPLY_MODES = frozenset({MODE_SCALE, MODE_DEGRADE, MODE_INCIDENT, MODE_MANUAL_EMERGENCY})
CAPACITY_REDUCING_MODES = frozenset({MODE_DEGRADE, MODE_INCIDENT, MODE_MANUAL_EMERGENCY})
ALL_MODES = frozenset({MODE_DRY_RUN}) | APPLY_MODES

BANNER = (
    "VPN PRODUCTION GUARDRAILS - validation only. No live apply, no Remna/Caddy/"
    "template/subscription mutation. Stability must not silently cut capacity."
)


@dataclass(frozen=True)
class GuardrailConfig:
    minimum_delivery_paths: int = 2
    minimum_relay_ips: int = 2
    minimum_geos: int | None = None
    preserve_canary: bool = True
    block_relay_only_collapse: bool = True


@dataclass
class CapacityState:
    """Snapshot of VPN delivery capacity (redacted counts + node-id sets only)."""

    delivery_path_nodes: int = 0
    production_capacity_nodes: int = 0
    relay_ips: int = 0
    geos: int = 0
    selector_total_paths: int = 0
    selector_relay_only: bool = False
    canary_node_ids: frozenset[str] = field(default_factory=frozenset)
    unknown_status_in_capacity: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "delivery_path_nodes": self.delivery_path_nodes,
            "production_capacity_nodes": self.production_capacity_nodes,
            "relay_ips": self.relay_ips,
            "geos": self.geos,
            "selector_total_paths": self.selector_total_paths,
            "selector_relay_only": self.selector_relay_only,
            "canary_node_ids": sorted(self.canary_node_ids),
            "unknown_status_in_capacity": self.unknown_status_in_capacity,
        }


@dataclass
class GuardrailResult:
    allowed: bool
    mode: str
    is_live_apply: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
    capacity_before: dict[str, Any] = field(default_factory=dict)
    capacity_after: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "banner": BANNER,
            "allowed": self.allowed,
            "mode": self.mode,
            "is_live_apply": self.is_live_apply,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "summary": self.summary,
            "capacity_before": self.capacity_before,
            "capacity_after": self.capacity_after,
        }


def capacity_reduces(before: CapacityState, after: CapacityState) -> bool:
    return (
        after.production_capacity_nodes < before.production_capacity_nodes
        or after.delivery_path_nodes < before.delivery_path_nodes
        or after.relay_ips < before.relay_ips
        or after.selector_total_paths < before.selector_total_paths
    )


def evaluate_guardrail(
    *,
    mode: str,
    before: CapacityState,
    after: CapacityState,
    owner_approved: bool = False,
    rollback_snapshot_present: bool = False,
    incident_ttl_minutes: int | None = None,
    explicit_drain: bool = False,
    config: GuardrailConfig | None = None,
) -> GuardrailResult:
    if mode not in ALL_MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {sorted(ALL_MODES)}")
    cfg = config or GuardrailConfig()

    blockers: list[str] = []
    warnings: list[str] = []
    reduces = capacity_reduces(before, after)
    is_live_apply = mode in APPLY_MODES

    # --- dry-run never represents a live apply ---
    if mode == MODE_DRY_RUN:
        if reduces:
            warnings.append("guardrail: dry-run shows a capacity reduction (advisory)")
        # still surface the same hard-minimum checks as advisory blockers
        _check_minimums(after, cfg, blockers)
        _check_relay_only(after, cfg, mode, blockers)
        _check_canary(before, after, explicit_drain, mode, blockers)
        _check_unknown(after, blockers)
        result = GuardrailResult(
            allowed=False,
            mode=mode,
            is_live_apply=False,
            blockers=blockers,
            warnings=warnings,
            summary="dry_run: validation only, no live apply",
            capacity_before=before.to_dict(),
            capacity_after=after.to_dict(),
        )
        return result

    # --- apply modes ---
    if not owner_approved:
        blockers.append("guardrail: owner approval required for apply")
    if not rollback_snapshot_present:
        blockers.append("guardrail: rollback snapshot required for apply")

    if reduces and mode == MODE_SCALE:
        blockers.append(
            "guardrail: capacity reduction not allowed in scale mode "
            "(use degrade/incident/manual_emergency)"
        )
    if reduces and mode == MODE_INCIDENT and not incident_ttl_minutes:
        blockers.append("guardrail: incident capacity reduction requires incident_ttl_minutes")
    if incident_ttl_minutes is not None and incident_ttl_minutes <= 0:
        blockers.append("guardrail: incident_ttl_minutes must be > 0")

    _check_minimums(after, cfg, blockers)
    _check_relay_only(after, cfg, mode, blockers)
    _check_canary(before, after, explicit_drain, mode, blockers)
    _check_unknown(after, blockers)

    allowed = not blockers
    summary = (
        f"mode={mode} reduces_capacity={reduces} "
        f"delivery {before.delivery_path_nodes}->{after.delivery_path_nodes} "
        f"prod_cap {before.production_capacity_nodes}->{after.production_capacity_nodes} "
        f"allowed={allowed}"
    )
    return GuardrailResult(
        allowed=allowed,
        mode=mode,
        is_live_apply=is_live_apply,
        blockers=blockers,
        warnings=warnings,
        summary=summary,
        capacity_before=before.to_dict(),
        capacity_after=after.to_dict(),
    )


def _check_minimums(after: CapacityState, cfg: GuardrailConfig, blockers: list[str]) -> None:
    if after.delivery_path_nodes < cfg.minimum_delivery_paths:
        blockers.append(
            f"guardrail: delivery_path_nodes after={after.delivery_path_nodes} "
            f"< minimum {cfg.minimum_delivery_paths}"
        )
    if after.relay_ips < cfg.minimum_relay_ips:
        blockers.append(
            f"guardrail: relay_ips after={after.relay_ips} < minimum {cfg.minimum_relay_ips}"
        )
    if cfg.minimum_geos is not None and after.geos < cfg.minimum_geos:
        blockers.append(
            f"guardrail: geos after={after.geos} < minimum {cfg.minimum_geos}"
        )


def _check_relay_only(
    after: CapacityState, cfg: GuardrailConfig, mode: str, blockers: list[str]
) -> None:
    if after.selector_relay_only and cfg.block_relay_only_collapse and mode != MODE_MANUAL_EMERGENCY:
        blockers.append(
            "guardrail: selector relay-only collapse blocked "
            "(stability must not silently drop to relay-only pool)"
        )


def _check_canary(
    before: CapacityState,
    after: CapacityState,
    explicit_drain: bool,
    mode: str,
    blockers: list[str],
) -> None:
    disappeared = before.canary_node_ids - after.canary_node_ids
    if disappeared and not explicit_drain:
        blockers.append(
            "guardrail: canary node(s) disappeared without explicit drain: "
            + ", ".join(sorted(disappeared))
        )


def _check_unknown(after: CapacityState, blockers: list[str]) -> None:
    if after.unknown_status_in_capacity:
        blockers.append(
            "guardrail: unknown-status node counted as production capacity (not allowed)"
        )


# --- helpers to derive a CapacityState from registry nodes (redacted) ---

_RELAY_ACTIVE_STATUSES = frozenset({"active", "canary"})


def production_capacity_node_ids(nodes: list[dict[str, Any]]) -> list[str]:
    return [
        str(n.get("node_id"))
        for n in nodes
        if isinstance(n, dict) and is_production_capacity(n)
    ]


def relay_ip_count(nodes: list[dict[str, Any]]) -> int:
    """Active relay-role nodes (proxy for distinct relay IPs in redacted registry)."""
    count = 0
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if n.get("role") == "relay" and n.get("status") in _RELAY_ACTIVE_STATUSES:
            count += 1
    return count


def geo_count(nodes: list[dict[str, Any]]) -> int:
    countries = {
        str(n.get("country"))
        for n in nodes
        if isinstance(n, dict) and is_production_capacity(n)
    }
    return len(countries)


def capacity_state_from_nodes(
    nodes: list[dict[str, Any]],
    *,
    selector_total_paths: int = 0,
    selector_relay_only: bool = False,
) -> CapacityState:
    prod_ids = production_capacity_node_ids(nodes)
    canary_ids = frozenset(
        str(n.get("node_id"))
        for n in nodes
        if isinstance(n, dict) and n.get("status") == "canary"
    )
    return CapacityState(
        delivery_path_nodes=len(prod_ids),
        production_capacity_nodes=len(prod_ids),
        relay_ips=relay_ip_count(nodes),
        geos=geo_count(nodes),
        selector_total_paths=selector_total_paths,
        selector_relay_only=selector_relay_only,
        canary_node_ids=canary_ids,
    )
