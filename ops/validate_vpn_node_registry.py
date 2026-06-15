#!/usr/bin/env python3
"""Validate VPN node registry YAML — VPN-NODE-REGISTRY-001.

Read-only local validation. No network, Remna, Caddy, or prod calls.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "ops" / "config" / "vpn_node_registry.yaml"

SCHEMA_VERSION = 1

STATUSES = frozenset(
    {
        "disabled",
        "staging",
        "canary",
        "active",
        "draining",
        "failed",
        "decommissioned",
    }
)

ROLES = frozenset({"relay", "exit", "backup", "lab"})

GROUPS = frozenset(
    {
        "LAB_OWNER",
        "RU_RELAY_ACTIVE",
        "RU_RELAY_CANARY",
        "INTL_DIRECT_ACTIVE",
        "INTL_STEALTH_ACTIVE",
        "FALLBACK_MANUAL",
    }
)

PRODUCTION_GROUPS = frozenset(
    {
        "RU_RELAY_ACTIVE",
        "RU_RELAY_CANARY",
        "INTL_DIRECT_ACTIVE",
        "INTL_STEALTH_ACTIVE",
    }
)

REQUIRED_NODE_FIELDS = (
    "node_id",
    "display_name",
    "region",
    "country",
    "city",
    "provider_label",
    "role",
    "status",
    "groups",
    "capacity",
    "health",
    "rollout",
    "client_support",
)

CAPACITY_FIELDS = (
    "max_active_configs",
    "max_concurrent_sessions",
    "max_mbps",
    "reserved_headroom_percent",
)

HEALTH_FIELDS = (
    "monitor_status",
    "last_smoke_status",
    "last_smoke_at",
    "last_owner_test_status",
    "last_owner_test_at",
)

ROLLOUT_FIELDS = (
    "cohort_weight",
    "canary_percent",
    "allow_new_assignments",
    "drain_after",
)

CLIENT_SUPPORT_FIELDS = (
    "happ_supported",
    "karing_supported",
    "v2rayn_supported",
    "mobile_supported",
)

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"vless://", re.I), "vless:// URL"),
    (re.compile(r"vmess://", re.I), "vmess:// URL"),
    (UUID_RE, "UUID-like value"),
    (re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S{8,}"), "credential assignment"),
    (re.compile(r"(?i)subscription[_-]?url\s*[:=]"), "subscription URL marker"),
    (re.compile(r"(?i)public[_-]?key\s*[:=]\s*[A-Za-z0-9+/=]{20,}"), "publicKey value"),
    (re.compile(r"(?i)short[_-]?id\s*[:=]\s*[a-f0-9]{6,}", re.I), "shortId value"),
    (re.compile(r"https?://[^\s\"']+/sub/", re.I), "subscription HTTP path"),
]


def load_registry(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("registry root must be a mapping")
    return data


def scan_secrets(text: str) -> list[str]:
    errors: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"forbidden pattern detected: {label}")
    return errors


def _is_number_or_null(value: Any) -> bool:
    return value is None or isinstance(value, (int, float))


def _percent_ok(value: Any) -> bool:
    return isinstance(value, (int, float)) and 0 <= value <= 100


def _node_production_active(node: dict[str, Any]) -> bool:
    status = node.get("status")
    groups = node.get("groups") or []
    if status != "active":
        return False
    return any(g in PRODUCTION_GROUPS for g in groups)


def validate_registry(data: dict[str, Any], raw_text: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(scan_secrets(raw_text))

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty list")
        return errors, warnings

    seen_ids: set[str] = set()
    for idx, node in enumerate(nodes):
        prefix = f"nodes[{idx}]"
        if not isinstance(node, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue

        for field in REQUIRED_NODE_FIELDS:
            if field not in node:
                errors.append(f"{prefix}: missing required field {field!r}")

        node_id = node.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"{prefix}: node_id must be a non-empty string")
        elif node_id in seen_ids:
            errors.append(f"{prefix}: duplicate node_id {node_id!r}")
        else:
            seen_ids.add(node_id)

        role = node.get("role")
        if role not in ROLES:
            errors.append(f"{prefix}: invalid role {role!r}")

        status = node.get("status")
        if status not in STATUSES:
            errors.append(f"{prefix}: invalid status {status!r}")

        groups = node.get("groups")
        if not isinstance(groups, list):
            errors.append(f"{prefix}: groups must be a list")
        else:
            for g in groups:
                if g not in GROUPS:
                    errors.append(f"{prefix}: invalid group {g!r}")

        if role == "lab" and status == "active":
            if "LAB_OWNER" not in (groups or []):
                errors.append(f"{prefix}: lab role with status=active must include LAB_OWNER")

        if "LAB_OWNER" in (groups or []) and node.get("delivery_path_eligible") is True:
            errors.append(f"{prefix}: LAB_OWNER node must not be delivery_path_eligible")

        capacity = node.get("capacity")
        if isinstance(capacity, dict):
            for cf in CAPACITY_FIELDS:
                if cf not in capacity:
                    errors.append(f"{prefix}.capacity: missing {cf!r}")
                elif not _is_number_or_null(capacity[cf]):
                    errors.append(f"{prefix}.capacity.{cf}: must be number or null")
            rp = capacity.get("reserved_headroom_percent")
            if rp is not None and not _percent_ok(rp):
                errors.append(f"{prefix}.capacity.reserved_headroom_percent: must be 0..100")
            for numeric in ("max_active_configs", "max_concurrent_sessions", "max_mbps"):
                val = capacity.get(numeric)
                if isinstance(val, (int, float)) and val < 0:
                    errors.append(f"{prefix}.capacity.{numeric}: must be >= 0 or null")

        health = node.get("health")
        if isinstance(health, dict):
            for hf in HEALTH_FIELDS:
                if hf not in health:
                    errors.append(f"{prefix}.health: missing {hf!r}")

        rollout = node.get("rollout")
        if isinstance(rollout, dict):
            for rf in ROLLOUT_FIELDS:
                if rf not in rollout:
                    errors.append(f"{prefix}.rollout: missing {rf!r}")
            cp = rollout.get("canary_percent")
            if cp is not None and not _percent_ok(cp):
                errors.append(f"{prefix}.rollout.canary_percent: must be 0..100")
            cw = rollout.get("cohort_weight")
            if isinstance(cw, (int, float)) and cw < 0:
                errors.append(f"{prefix}.rollout.cohort_weight: must be >= 0")
            allow_new = rollout.get("allow_new_assignments")
            if status == "active" and allow_new is False and _node_production_active(node):
                errors.append(
                    f"{prefix}: active production node with allow_new_assignments=false "
                    "requires status=draining"
                )

        client_support = node.get("client_support")
        if isinstance(client_support, dict):
            for csf in CLIENT_SUPPORT_FIELDS:
                if csf not in client_support:
                    errors.append(f"{prefix}.client_support: missing {csf!r}")

        if _node_production_active(node):
            if isinstance(capacity, dict):
                for numeric in ("max_active_configs", "max_concurrent_sessions", "max_mbps"):
                    val = capacity.get(numeric)
                    if isinstance(val, (int, float)) and val == 0:
                        errors.append(
                            f"{prefix}: active production node cannot have {numeric}=0"
                        )

    delivery_count = count_delivery_path_nodes(nodes)
    gate_300 = (data.get("capacity_policy") or {}).get("delivery_path_gate_300", 2)
    if delivery_count < gate_300:
        warnings.append(
            f"delivery_path_nodes={delivery_count} < {gate_300}: "
            "300 active configs gate NO-GO; 30k gate NO-GO"
        )

    lab_mass_risk = [
        n.get("node_id")
        for n in nodes
        if isinstance(n, dict)
        and "LAB_OWNER" in (n.get("groups") or [])
        and n.get("status") == "active"
        and n.get("rollout", {}).get("allow_new_assignments") is True
        and n.get("rollout", {}).get("cohort_weight", 0) > 0
    ]
    if lab_mass_risk:
        errors.append(
            "LAB_OWNER nodes must not allow mass assignment: "
            + ", ".join(str(x) for x in lab_mass_risk)
        )

    return errors, warnings


def count_delivery_path_nodes(nodes: list[Any]) -> int:
    count = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("role") != "exit":
            continue
        if node.get("status") != "active":
            continue
        if node.get("delivery_path_eligible") is True:
            count += 1
    return count


def summarize_registry(data: dict[str, Any]) -> dict[str, Any]:
    nodes = data.get("nodes") or []
    by_status: dict[str, int] = {}
    by_group: dict[str, int] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        st = str(node.get("status", "unknown"))
        by_status[st] = by_status.get(st, 0) + 1
        for g in node.get("groups") or []:
            by_group[str(g)] = by_group.get(str(g), 0) + 1
    return {
        "total_nodes": len(nodes),
        "by_status": dict(sorted(by_status.items())),
        "by_group": dict(sorted(by_group.items())),
        "delivery_path_nodes": count_delivery_path_nodes(nodes),
    }


def print_summary(data: dict[str, Any], warnings: list[str]) -> None:
    summary = summarize_registry(data)
    print("VPN node registry summary")
    print(f"  total_nodes: {summary['total_nodes']}")
    print(f"  by_status: {summary['by_status']}")
    print(f"  by_group: {summary['by_group']}")
    print(f"  delivery_path_nodes: {summary['delivery_path_nodes']}")
    for w in warnings:
        print(f"  WARNING: {w}")


def validate_file(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    try:
        data = load_registry(path)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        print(f"ERROR: failed to load registry: {exc}", file=sys.stderr)
        return 1

    errors, warnings = validate_registry(data, raw)
    if errors:
        print("Registry validation FAILED", file=sys.stderr)
        for err in errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    print_summary(data, warnings)
    print("Registry validation OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate VPN node registry YAML")
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help=f"Path to registry YAML (default: {DEFAULT_REGISTRY})",
    )
    args = parser.parse_args(argv)
    return validate_file(args.registry)


if __name__ == "__main__":
    raise SystemExit(main())
