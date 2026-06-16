"""Guardrail-migration tests for relay_failover_template — SCRIPT-MIGRATE-RELAY-FAILOVER-001."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import relay_failover_template as mod  # noqa: E402
from balancer_selectors import (  # noqa: E402
    LV_DIRECT_ONLY_SELECTOR,
    LV_RELAY_SELECTOR,
)
from vpn_production_guardrails import (  # noqa: E402
    MODE_DRY_RUN,
    MODE_INCIDENT,
    MODE_MANUAL_EMERGENCY,
    MODE_SCALE,
)


def _node(node_id, role, status, *, eligible=False, groups=None, monitor="ok", smoke="pass"):
    return {
        "node_id": node_id,
        "role": role,
        "status": status,
        "country": "LV",
        "region": "EU",
        "delivery_path_eligible": eligible,
        "groups": groups or [],
        "health": {"monitor_status": monitor, "last_smoke_status": smoke},
        "rollout": {"canary_percent": 0, "cohort_weight": 0},
    }


def _nodes():
    return [
        _node("lv-exit-1", "exit", "active", eligible=True, groups=["INTL_STEALTH_ACTIVE"]),
        _node("ru-relay-1", "relay", "active", groups=["RU_RELAY_ACTIVE"]),
        _node("ru-relay-2", "relay", "active", groups=["RU_RELAY_ACTIVE"]),
    ]


def _doc(selector):
    return {
        "routing": {
            "balancers": [
                {"tag": "Super_Balancer", "selector": list(selector)},
                {"tag": "Intl_Direct", "selector": list(selector)},
            ]
        }
    }


def test_resolve_mode_bare_apply_with_reduction_blocks():
    mode, blockers = mod.resolve_apply_mode(applying=True, mode_arg=None, reduces_capacity=True)
    assert mode == MODE_DRY_RUN
    assert blockers


def test_resolve_mode_dry_run_when_not_applying():
    mode, blockers = mod.resolve_apply_mode(applying=False, mode_arg=None, reduces_capacity=True)
    assert mode == MODE_DRY_RUN
    assert blockers == []


def test_trim_without_owner_blocked():
    guard = mod.evaluate_relay_failover_apply_guard(
        registry_nodes=_nodes(),
        before_doc=_doc(LV_RELAY_SELECTOR),
        after_doc=_doc(LV_DIRECT_ONLY_SELECTOR),
        mode=MODE_INCIDENT,
        owner_approved=False,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False
    assert any("owner approval" in b for b in guard.blockers)


def test_trim_incident_without_ttl_blocked():
    guard = mod.evaluate_relay_failover_apply_guard(
        registry_nodes=_nodes(),
        before_doc=_doc(LV_RELAY_SELECTOR),
        after_doc=_doc(LV_DIRECT_ONLY_SELECTOR),
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=None,
    )
    assert guard.allowed is False
    assert any("incident_ttl" in b for b in guard.blockers)


def test_trim_missing_rollback_blocked():
    guard = mod.evaluate_relay_failover_apply_guard(
        registry_nodes=_nodes(),
        before_doc=_doc(LV_RELAY_SELECTOR),
        after_doc=_doc(LV_DIRECT_ONLY_SELECTOR),
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=False,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False
    assert any("rollback snapshot" in b for b in guard.blockers)


def test_trim_capacity_collapse_blocked_even_with_full_approval():
    """Trimming all relay drops relay_ips below minimum → still blocked."""
    guard = mod.evaluate_relay_failover_apply_guard(
        registry_nodes=_nodes(),
        before_doc=_doc(LV_RELAY_SELECTOR),
        after_doc=_doc(LV_DIRECT_ONLY_SELECTOR),
        mode=MODE_MANUAL_EMERGENCY,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False
    assert any("relay_ips" in b for b in guard.blockers)


def test_registry_missing_fails_closed():
    guard = mod.evaluate_relay_failover_apply_guard(
        registry_nodes=[],
        before_doc=_doc(LV_RELAY_SELECTOR),
        after_doc=_doc(LV_DIRECT_ONLY_SELECTOR),
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False


def test_restore_not_reducing_scale_mode_ok():
    """Restoring relay back (scale) with owner+rollback should pass."""
    mode, blockers = mod.resolve_apply_mode(applying=True, mode_arg=None, reduces_capacity=False)
    assert mode == MODE_SCALE
    assert blockers == []
    healthy = _nodes() + [
        _node("nl-exit-2", "exit", "active", eligible=True, groups=["INTL_DIRECT_ACTIVE"]),
    ]
    guard = mod.evaluate_relay_failover_apply_guard(
        registry_nodes=healthy,
        before_doc=_doc(LV_DIRECT_ONLY_SELECTOR),
        after_doc=_doc(LV_RELAY_SELECTOR),
        mode=MODE_SCALE,
        owner_approved=True,
        rollback_snapshot_present=True,
    )
    assert guard.allowed is True
