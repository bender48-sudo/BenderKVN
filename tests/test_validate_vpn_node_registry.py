"""Tests for VPN node registry validation — VPN-NODE-REGISTRY-001."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import (  # noqa: E402
    DEFAULT_REGISTRY,
    count_delivery_path_nodes,
    load_registry,
    validate_registry,
)

CANONICAL = DEFAULT_REGISTRY


def _minimal_node(**overrides):
    node = {
        "node_id": "test-node-1",
        "display_name": "Test node",
        "region": "EU",
        "country": "LV",
        "city": "redacted",
        "provider_label": "redacted",
        "role": "exit",
        "status": "staging",
        "delivery_path_eligible": False,
        "groups": ["INTL_DIRECT_ACTIVE"],
        "capacity": {
            "max_active_configs": None,
            "max_concurrent_sessions": None,
            "max_mbps": None,
            "reserved_headroom_percent": 40,
        },
        "health": {
            "monitor_status": "unknown",
            "last_smoke_status": "pending",
            "last_smoke_at": None,
            "last_owner_test_status": None,
            "last_owner_test_at": None,
        },
        "rollout": {
            "cohort_weight": 0,
            "canary_percent": 0,
            "allow_new_assignments": False,
            "drain_after": None,
        },
        "client_support": {
            "happ_supported": True,
            "karing_supported": False,
            "v2rayn_supported": False,
            "mobile_supported": False,
        },
        "owner_approval_required": False,
        "notes": "test fixture",
    }
    node.update(overrides)
    return node


def _registry_doc(*nodes):
    return {
        "schema_version": 1,
        "updated_at": "2026-06-15T00:00:00Z",
        "capacity_policy": {"delivery_path_gate_300": 2},
        "nodes": list(nodes),
    }


def test_canonical_registry_passes():
    raw = CANONICAL.read_text(encoding="utf-8")
    data = load_registry(CANONICAL)
    errors, warnings = validate_registry(data, raw)
    assert errors == []
    assert any("delivery_path_nodes=1" in w for w in warnings)
    assert count_delivery_path_nodes(data["nodes"]) == 1


def test_valid_minimal_registry_passes():
    node = _minimal_node()
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, warnings = validate_registry(data, raw)
    assert errors == []


def test_invalid_status_fails():
    node = _minimal_node(status="online")
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, _ = validate_registry(data, raw)
    assert any("invalid status" in e for e in errors)


def test_missing_required_field_fails():
    node = _minimal_node()
    del node["node_id"]
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, _ = validate_registry(data, raw)
    assert any("missing required field 'node_id'" in e for e in errors)


@pytest.mark.parametrize(
    "secret_snippet",
    [
        "vless://example-config",
        "deadbeef-dead-beef-dead-beefdeadbeef",
        "token=supersecretvalue123456",
        "api_key=abcdefghijklmnopqrst",
        "subscription_url=https://example.com/sub/user",
    ],
)
def test_secret_like_content_fails(secret_snippet: str):
    node = _minimal_node(notes=secret_snippet)
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, _ = validate_registry(data, raw)
    assert errors


def test_canary_percent_out_of_range_fails():
    node = _minimal_node(
        rollout={
            "cohort_weight": 0,
            "canary_percent": 150,
            "allow_new_assignments": False,
            "drain_after": None,
        }
    )
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, _ = validate_registry(data, raw)
    assert any("canary_percent" in e for e in errors)


def test_active_production_without_assignments_fails():
    node = _minimal_node(
        status="active",
        groups=["RU_RELAY_ACTIVE"],
        rollout={
            "cohort_weight": 10,
            "canary_percent": 0,
            "allow_new_assignments": False,
            "drain_after": None,
        },
    )
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, _ = validate_registry(data, raw)
    assert any("allow_new_assignments=false" in e for e in errors)


def test_delivery_path_nodes_warning_when_below_gate():
    node = _minimal_node(
        status="active",
        delivery_path_eligible=True,
        groups=["INTL_DIRECT_ACTIVE"],
        rollout={
            "cohort_weight": 100,
            "canary_percent": 0,
            "allow_new_assignments": True,
            "drain_after": None,
        },
    )
    data = _registry_doc(node)
    raw = yaml.safe_dump(data)
    errors, warnings = validate_registry(data, raw)
    assert errors == []
    assert count_delivery_path_nodes(data["nodes"]) == 1
    assert any("300 active configs gate NO-GO" in w for w in warnings)


def test_delivery_path_counts_only_active_exits():
    nodes = [
        _minimal_node(node_id="exit-active", status="active", delivery_path_eligible=True),
        _minimal_node(
            node_id="exit-disabled",
            status="disabled",
            delivery_path_eligible=True,
        ),
        _minimal_node(
            node_id="relay-active",
            role="relay",
            status="active",
            delivery_path_eligible=False,
            groups=["RU_RELAY_ACTIVE"],
        ),
    ]
    assert count_delivery_path_nodes(nodes) == 1
