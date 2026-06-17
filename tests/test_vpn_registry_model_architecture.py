"""Tests for RU-RELAY-ARCH-UNIFICATION-001 architecture-compliance gating."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from vpn_registry_model import (  # noqa: E402
    COHORT_CANARY,
    COHORT_PUBLIC_PROD,
    allowed_cohorts_for_node,
    architecture_compliance,
    build_node_model,
    is_architecture_compliant,
    path_role,
    shared_upstream_group,
)


def _exit(**over):
    node = {
        "node_id": "exit-x",
        "role": "exit",
        "status": "active",
        "delivery_path_eligible": True,
        "groups": ["INTL_DIRECT_ACTIVE"],
        "health": {"monitor_status": "ok", "last_smoke_status": "pass"},
        "rollout": {"cohort_weight": 100, "canary_percent": 0},
    }
    node.update(over)
    return node


def test_compliant_exit_enters_prod_and_canary():
    node = _exit(architecture_compliance="compliant")
    cohorts = allowed_cohorts_for_node(node)
    assert COHORT_PUBLIC_PROD in cohorts
    assert COHORT_CANARY in cohorts


def test_unverified_defaults_fail_closed():
    node = _exit()  # no architecture_compliance
    assert architecture_compliance(node) == "unverified"
    assert is_architecture_compliant(node) is False
    assert allowed_cohorts_for_node(node) == []


def test_non_compliant_excluded_from_pools():
    node = _exit(architecture_compliance="non_compliant")
    assert allowed_cohorts_for_node(node) == []
    m = build_node_model(node)
    assert m.architecture_compliant is False
    assert "architecture=non_compliant" in (m.excluded_reason or "")


def test_replace_required_excluded():
    node = _exit(architecture_compliance="replace_required")
    assert allowed_cohorts_for_node(node) == []


def test_path_role_and_shared_upstream_helpers():
    relay = {
        "node_id": "ru-relay-1",
        "role": "relay",
        "path_role": "relay",
        "status": "active",
        "groups": ["RU_RELAY_ACTIVE"],
        "architecture_compliance": "compliant",
        "shared_upstream_group": "ru-fwd-upstream-1",
        "health": {"monitor_status": "ok", "last_smoke_status": "pass"},
        "rollout": {"cohort_weight": 50, "canary_percent": 0},
    }
    assert path_role(relay) == "relay"
    assert shared_upstream_group(relay) == "ru-fwd-upstream-1"
    m = build_node_model(relay)
    assert m.shared_upstream_group == "ru-fwd-upstream-1"
    # relay is compliant but still not a standalone delivery path
    assert m.is_production_delivery is False
    assert allowed_cohorts_for_node(relay) == []


def test_path_role_falls_back_to_role():
    assert path_role({"role": "exit"}) == "exit"
