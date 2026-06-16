"""Tests for registry-driven node/outbound model — VPN-INVENTORY-DRIVEN-CONFIG-GENERATOR-001."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from vpn_registry_model import (  # noqa: E402
    COHORT_CANARY,
    COHORT_LAB_OWNER,
    COHORT_PUBLIC_PROD,
    ROUTE_OWNER_LAB,
    build_node_model,
    build_registry_model,
    is_production_delivery,
    outbound_tag_for_node,
    select_for_cohort,
)


def _node(node_id, role, status, *, eligible=False, groups=None, monitor="ok",
          smoke="pass", canary=0, weight=0, country="LV"):
    return {
        "node_id": node_id,
        "role": role,
        "status": status,
        "country": country,
        "region": "EU",
        "delivery_path_eligible": eligible,
        "groups": groups or [],
        "health": {"monitor_status": monitor, "last_smoke_status": smoke},
        "rollout": {"canary_percent": canary, "cohort_weight": weight},
        "capacity": {"max_active_configs": None},
    }


def test_outbound_tag_is_node_id_based_not_positional():
    assert outbound_tag_for_node("lv-exit-1") == "out-lv-exit-1"
    assert outbound_tag_for_node("ru-relay-2") == "out-ru-relay-2"
    # never a bare positional proxy-N
    assert "proxy" not in outbound_tag_for_node("lv-exit-1")


def test_node_id_maps_to_stable_tag():
    n = _node("lv-exit-1", "exit", "active", eligible=True, groups=["INTL_STEALTH_ACTIVE"], weight=100)
    m1 = build_node_model(n)
    m2 = build_node_model(n)
    assert m1.outbound_tag == m2.outbound_tag == "out-lv-exit-1"


def test_disabled_node_excluded_from_prod():
    m = build_node_model(_node("nl", "exit", "disabled", groups=["INTL_DIRECT_ACTIVE"]))
    assert m.is_production_delivery is False
    assert COHORT_PUBLIC_PROD not in m.allowed_cohorts
    assert m.excluded_reason


def test_suspect_node_excluded_from_prod():
    m = build_node_model(_node("ru1", "relay", "active", monitor="suspect", groups=["RU_RELAY_ACTIVE"]))
    assert m.is_production_delivery is False
    assert m.excluded_reason and "suspect" in m.excluded_reason


def test_lab_only_not_prod():
    m = build_node_model(_node("lab", "lab", "staging", groups=["LAB_OWNER"]))
    assert m.allowed_cohorts == [COHORT_LAB_OWNER]
    assert m.route_classes == [ROUTE_OWNER_LAB]
    assert m.is_production_delivery is False


def test_staging_node_not_public_prod():
    m = build_node_model(_node("nl", "exit", "staging", groups=["INTL_DIRECT_ACTIVE"]))
    assert COHORT_PUBLIC_PROD not in m.allowed_cohorts
    assert m.is_production_delivery is False


def test_canary_node_canary_cohort_only():
    m = build_node_model(_node("nl", "exit", "canary", groups=["INTL_DIRECT_ACTIVE"], canary=10))
    assert COHORT_CANARY in m.allowed_cohorts
    assert COHORT_PUBLIC_PROD not in m.allowed_cohorts


def test_backup_not_capacity():
    m = build_node_model(_node("ams", "backup", "active", groups=["FALLBACK_MANUAL"]))
    assert m.is_production_delivery is False
    assert m.allowed_cohorts == []


def test_clean_exit_is_production_delivery():
    n = _node("lv-exit-1", "exit", "active", eligible=True, groups=["INTL_STEALTH_ACTIVE"], weight=100)
    assert is_production_delivery(n) is True
    m = build_node_model(n)
    assert COHORT_PUBLIC_PROD in m.allowed_cohorts


def test_select_for_cohort_weight_sorted():
    models = build_registry_model(
        {
            "nodes": [
                _node("b-exit", "exit", "active", eligible=True, groups=["INTL_DIRECT_ACTIVE"], weight=10),
                _node("a-exit", "exit", "active", eligible=True, groups=["INTL_DIRECT_ACTIVE"], weight=90),
            ]
        }
    )
    sel = select_for_cohort(models, COHORT_PUBLIC_PROD)
    assert [m.node_id for m in sel] == ["a-exit", "b-exit"]


def test_no_position_based_proxy_dependency_in_model():
    models = build_registry_model(
        {"nodes": [_node("lv-exit-1", "exit", "active", eligible=True, groups=["INTL_STEALTH_ACTIVE"])]}
    )
    for m in models:
        assert not m.outbound_tag.startswith("proxy")
