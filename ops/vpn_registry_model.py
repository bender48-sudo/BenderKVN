#!/usr/bin/env python3
"""Registry-driven VPN node/outbound model — VPN-INVENTORY-DRIVEN-CONFIG-GENERATOR-001.

Converts the redacted node registry into a deterministic, position-independent model
that downstream generators/verifiers can consume WITHOUT brittle proxy-N assumptions.

CORE PRINCIPLES (VPN-PROXY-N-DECOUPLE-001):
    * Node identity comes from registry node_id, never from a selector position.
    * Outbound tags are DERIVED deterministically from node_id (stable, not "proxy-5").
    * disabled / suspect / lab / backup nodes are excluded from production by default.
    * staging/canary nodes are selectable only for their allowed cohorts.
    * PUBLIC_PROD requires >= minimum_delivery_paths clean production delivery paths.

HARD SAFETY:
    * Pure transformation of the redacted registry. No network, no Remna/Caddy,
      no template/subscription writes, no secrets. Outbound tags and selector
      groups are synthetic labels — they carry NO real UUID/endpoint.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import (  # noqa: E402
    BLOCKED_STATUSES,
    _is_suspect,
    _node_groups,
    load_validated_registry,
)

# Route classes (logical traffic intent, not a position).
ROUTE_STEALTH = "stealth"            # TG/Meta/IG sensitive → relay stealth path
ROUTE_DIRECT_INTL = "direct-intl"    # general international via direct exit (LV/NL)
ROUTE_RU_DIRECT = "ru-direct"        # RU domestic direct (bypass tunnel by design)
ROUTE_TG_META_STEALTH = "tg-meta-stealth"
ROUTE_OWNER_LAB = "owner-lab"
ROUTE_CANARY = "canary"

COHORT_LAB_OWNER = "LAB_OWNER"
COHORT_CANARY = "CANARY"
COHORT_PUBLIC_PROD = "PUBLIC_PROD"

OUTBOUND_TAG_PREFIX = "out"


def outbound_tag_for_node(node_id: str) -> str:
    """Stable, position-independent outbound tag derived from node_id.

    Deliberately NOT 'proxy-5'. The tag encodes node identity so a selector that
    references it cannot silently bind to a different node when ordering changes.
    """
    safe = "".join(c if c.isalnum() else "-" for c in str(node_id).strip().lower())
    safe = "-".join(filter(None, safe.split("-")))
    return f"{OUTBOUND_TAG_PREFIX}-{safe}"


def selector_group_for_node(node: dict[str, Any]) -> str:
    groups = _node_groups(node)
    role = node.get("role")
    if "LAB_OWNER" in groups or role == "lab":
        return ROUTE_OWNER_LAB
    if node.get("status") == "canary":
        return ROUTE_CANARY
    if "INTL_STEALTH_ACTIVE" in groups or role == "relay":
        return ROUTE_STEALTH
    if "INTL_DIRECT_ACTIVE" in groups:
        return ROUTE_DIRECT_INTL
    if "FALLBACK_MANUAL" in groups or role == "backup":
        return ROUTE_DIRECT_INTL
    return ROUTE_DIRECT_INTL


def route_classes_for_node(node: dict[str, Any]) -> list[str]:
    groups = _node_groups(node)
    role = node.get("role")
    classes: list[str] = []
    if "LAB_OWNER" in groups or role == "lab":
        return [ROUTE_OWNER_LAB]
    if role == "relay" or "INTL_STEALTH_ACTIVE" in groups:
        classes.append(ROUTE_STEALTH)
        classes.append(ROUTE_TG_META_STEALTH)
    if "INTL_DIRECT_ACTIVE" in groups or role == "exit":
        classes.append(ROUTE_DIRECT_INTL)
    if node.get("status") == "canary":
        classes.append(ROUTE_CANARY)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for c in classes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out or [ROUTE_DIRECT_INTL]


def _capacity_estimate(node: dict[str, Any]) -> int | None:
    cap = node.get("capacity") or {}
    val = cap.get("max_active_configs")
    if isinstance(val, (int, float)) and val >= 0:
        return int(val)
    return None


def _weight_for_node(node: dict[str, Any]) -> int:
    rollout = node.get("rollout") or {}
    w = rollout.get("cohort_weight")
    if isinstance(w, (int, float)) and w >= 0:
        return int(w)
    return 0


def allowed_cohorts_for_node(node: dict[str, Any]) -> list[str]:
    groups = _node_groups(node)
    role = node.get("role")
    status = node.get("status")
    cohorts: list[str] = []
    if "LAB_OWNER" in groups or role == "lab":
        return [COHORT_LAB_OWNER]
    if status == "canary":
        cohorts.append(COHORT_CANARY)
    if is_production_delivery(node):
        cohorts.append(COHORT_PUBLIC_PROD)
        cohorts.append(COHORT_CANARY)
    return cohorts


def is_production_delivery(node: dict[str, Any]) -> bool:
    if node.get("role") != "exit":
        return False
    if node.get("status") != "active":
        return False
    if node.get("delivery_path_eligible") is not True:
        return False
    if _is_suspect(node):
        return False
    groups = _node_groups(node)
    if "LAB_OWNER" in groups or node.get("role") == "backup" or "FALLBACK_MANUAL" in groups:
        return False
    return True


def exclusion_reason(node: dict[str, Any]) -> str | None:
    status = node.get("status")
    groups = _node_groups(node)
    role = node.get("role")
    if status in BLOCKED_STATUSES:
        return f"status={status} (blocked from delivery)"
    if _is_suspect(node):
        return "health=suspect/needs_diagnosis"
    if "LAB_OWNER" in groups or role == "lab":
        return "lab-only (owner/F&F)"
    if role == "backup" or "FALLBACK_MANUAL" in groups:
        return "backup/fallback (not delivery capacity)"
    if role == "relay":
        return "relay diversity (not standalone delivery path)"
    if status == "staging":
        return "staging (promotion gate pending)"
    if node.get("delivery_path_eligible") is not True:
        return "delivery_path_eligible=false"
    return None


@dataclass
class NodeModel:
    node_id: str
    lifecycle_status: str
    role: str
    region: str
    country: str
    delivery_path_eligible: bool
    canary_percent: int
    health_status: str
    capacity_estimate: int | None
    allowed_cohorts: list[str]
    outbound_tag: str
    selector_group: str
    route_classes: list[str]
    weight: int
    is_production_delivery: bool
    drain_after: Any
    incident: bool
    excluded_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "lifecycle_status": self.lifecycle_status,
            "role": self.role,
            "region": self.region,
            "country": self.country,
            "delivery_path_eligible": self.delivery_path_eligible,
            "canary_percent": self.canary_percent,
            "health_status": self.health_status,
            "capacity_estimate": self.capacity_estimate,
            "allowed_cohorts": self.allowed_cohorts,
            "outbound_tag": self.outbound_tag,
            "selector_group": self.selector_group,
            "route_classes": self.route_classes,
            "weight": self.weight,
            "is_production_delivery": self.is_production_delivery,
            "drain_after": self.drain_after,
            "incident": self.incident,
            "excluded_reason": self.excluded_reason,
        }


def build_node_model(node: dict[str, Any]) -> NodeModel:
    rollout = node.get("rollout") or {}
    health = node.get("health") or {}
    canary_percent = rollout.get("canary_percent") or 0
    try:
        canary_percent = int(canary_percent)
    except (TypeError, ValueError):
        canary_percent = 0
    return NodeModel(
        node_id=str(node.get("node_id", "?")),
        lifecycle_status=str(node.get("status", "?")),
        role=str(node.get("role", "?")),
        region=str(node.get("region", "?")),
        country=str(node.get("country", "?")),
        delivery_path_eligible=node.get("delivery_path_eligible") is True,
        canary_percent=canary_percent,
        health_status=str(health.get("monitor_status", "?")),
        capacity_estimate=_capacity_estimate(node),
        allowed_cohorts=allowed_cohorts_for_node(node),
        outbound_tag=outbound_tag_for_node(str(node.get("node_id", "?"))),
        selector_group=selector_group_for_node(node),
        route_classes=route_classes_for_node(node),
        weight=_weight_for_node(node),
        is_production_delivery=is_production_delivery(node),
        drain_after=rollout.get("drain_after"),
        incident=bool(node.get("incident")),
        excluded_reason=exclusion_reason(node),
    )


def build_registry_model(registry: dict[str, Any]) -> list[NodeModel]:
    nodes = [n for n in (registry.get("nodes") or []) if isinstance(n, dict)]
    models = [build_node_model(n) for n in nodes]
    models.sort(key=lambda m: m.node_id)
    return models


def select_for_cohort(models: list[NodeModel], cohort: str) -> list[NodeModel]:
    """Deterministic, weight-sorted selection of nodes eligible for a cohort."""
    selected = [m for m in models if cohort in m.allowed_cohorts]
    selected.sort(key=lambda m: (-m.weight, m.node_id))
    return selected


def model_to_dict(models: list[NodeModel]) -> dict[str, Any]:
    return {
        "schema": "vpn-registry-model/1",
        "note": "synthetic outbound tags; no real UUID/endpoint; position-independent",
        "nodes": [m.to_dict() for m in models],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Registry-driven node/outbound model (read-only)")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--cohort", default=None, help="Filter to a cohort's selection")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        registry = load_validated_registry(args.registry)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    models = build_registry_model(registry)
    if args.cohort:
        models = select_for_cohort(models, args.cohort)

    if args.json:
        print(json.dumps(model_to_dict(models), indent=2, ensure_ascii=False))
    else:
        print("registry-driven node model (no proxy-N positions)")
        for m in models:
            tag = m.outbound_tag
            cohorts = ",".join(m.allowed_cohorts) or "-"
            rc = ",".join(m.route_classes)
            excl = f" excluded={m.excluded_reason}" if m.excluded_reason else ""
            print(
                f"  {m.node_id} -> {tag} | {m.lifecycle_status}/{m.role} | "
                f"group={m.selector_group} routes={rc} cohorts=[{cohorts}] "
                f"weight={m.weight} prod={m.is_production_delivery}{excl}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
