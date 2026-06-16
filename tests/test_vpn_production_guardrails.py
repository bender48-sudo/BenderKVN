"""Tests for central VPN production guardrails — VPN-PRODUCTION-GUARDRAILS-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from vpn_production_guardrails import (  # noqa: E402
    MODE_DEGRADE,
    MODE_DRY_RUN,
    MODE_INCIDENT,
    MODE_MANUAL_EMERGENCY,
    MODE_SCALE,
    CapacityState,
    GuardrailConfig,
    capacity_state_from_nodes,
    evaluate_guardrail,
    geo_count,
    production_capacity_node_ids,
    relay_ip_count,
)


def _state(dp=2, pc=2, relay=2, geos=2, paths=12, relay_only=False, canary=(), unknown=False):
    return CapacityState(
        delivery_path_nodes=dp,
        production_capacity_nodes=pc,
        relay_ips=relay,
        geos=geos,
        selector_total_paths=paths,
        selector_relay_only=relay_only,
        canary_node_ids=frozenset(canary),
        unknown_status_in_capacity=unknown,
    )


HEALTHY = _state()
ZERO = CapacityState()


def test_dry_run_is_not_live_apply():
    r = evaluate_guardrail(mode=MODE_DRY_RUN, before=HEALTHY, after=HEALTHY)
    assert r.is_live_apply is False
    assert r.allowed is False  # dry-run never applies
    assert "dry_run" in r.summary


def test_dry_run_reports_blockers_advisory():
    after = _state(dp=1, pc=1, relay=1)
    r = evaluate_guardrail(mode=MODE_DRY_RUN, before=HEALTHY, after=after)
    assert any("delivery_path_nodes" in b for b in r.blockers)
    assert r.is_live_apply is False


def test_apply_without_owner_approval_blocked():
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=ZERO, after=HEALTHY,
        owner_approved=False, rollback_snapshot_present=True,
    )
    assert r.allowed is False
    assert any("owner approval" in b for b in r.blockers)


def test_rollback_missing_blocks_apply():
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=ZERO, after=HEALTHY,
        owner_approved=True, rollback_snapshot_present=False,
    )
    assert r.allowed is False
    assert any("rollback" in b for b in r.blockers)


def test_capacity_reduction_in_scale_mode_blocked():
    after = _state(dp=1, pc=1)
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=HEALTHY, after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert r.allowed is False
    assert any("capacity reduction not allowed in scale" in b for b in r.blockers)


def test_incident_reduction_without_ttl_blocked():
    after = _state(dp=2, pc=2, relay=2)  # keep minimums, just smaller selector
    after.selector_total_paths = 4
    r = evaluate_guardrail(
        mode=MODE_INCIDENT, before=HEALTHY, after=after,
        owner_approved=True, rollback_snapshot_present=True,
        incident_ttl_minutes=None,
    )
    assert r.allowed is False
    assert any("incident_ttl_minutes" in b for b in r.blockers)


def test_delivery_paths_below_minimum_blocked():
    after = _state(dp=1, pc=1)
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=_state(dp=1, pc=1), after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert any("delivery_path_nodes after=1 < minimum 2" in b for b in r.blockers)


def test_relay_ip_below_minimum_blocked():
    after = _state(relay=1)
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=_state(relay=1), after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert any("relay_ips after=1 < minimum 2" in b for b in r.blockers)


def test_geo_minimum_blocked_when_configured():
    cfg = GuardrailConfig(minimum_geos=2)
    after = _state(geos=1)
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=_state(geos=1), after=after,
        owner_approved=True, rollback_snapshot_present=True, config=cfg,
    )
    assert any("geos after=1 < minimum 2" in b for b in r.blockers)


def test_canary_disappearance_blocked():
    before = _state(canary=("canary-a",))
    after = _state(canary=())
    r = evaluate_guardrail(
        mode=MODE_DEGRADE, before=before, after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert any("canary node(s) disappeared" in b for b in r.blockers)


def test_canary_drain_allowed_with_explicit_drain():
    before = _state(canary=("canary-a",))
    after = _state(canary=())
    r = evaluate_guardrail(
        mode=MODE_DEGRADE, before=before, after=after,
        owner_approved=True, rollback_snapshot_present=True, explicit_drain=True,
    )
    assert not any("canary node(s) disappeared" in b for b in r.blockers)


def test_relay_only_collapse_blocked():
    after = _state(relay_only=True)
    r = evaluate_guardrail(
        mode=MODE_DEGRADE, before=HEALTHY, after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert any("relay-only collapse" in b for b in r.blockers)


def test_lab_only_node_not_counted_as_production():
    lab = {"node_id": "lab", "role": "lab", "status": "staging", "groups": ["LAB_OWNER"],
           "delivery_path_eligible": False, "health": {}}
    assert production_capacity_node_ids([lab]) == []


def test_disabled_node_not_counted_as_production():
    nl = {"node_id": "nl", "role": "exit", "status": "disabled", "groups": ["INTL_DIRECT_ACTIVE"],
          "delivery_path_eligible": False, "health": {}}
    assert production_capacity_node_ids([nl]) == []


def test_backup_edge_not_counted_as_delivery():
    backup = {"node_id": "ams", "role": "backup", "status": "active", "groups": ["FALLBACK_MANUAL"],
              "delivery_path_eligible": False, "health": {}}
    assert production_capacity_node_ids([backup]) == []
    assert relay_ip_count([backup]) == 0


def test_degrade_weight_reduction_allowed_if_minimum_preserved():
    # capacity counts preserved, only selector paths lowered slightly
    before = _state(dp=2, pc=2, relay=2, paths=12)
    after = _state(dp=2, pc=2, relay=2, paths=10)
    r = evaluate_guardrail(
        mode=MODE_DEGRADE, before=before, after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert r.allowed is True


def test_incident_with_ttl_rollback_approval_allows_temp_reduction():
    before = _state(dp=2, pc=2, relay=2, paths=12)
    after = _state(dp=2, pc=2, relay=2, paths=6)
    r = evaluate_guardrail(
        mode=MODE_INCIDENT, before=before, after=after,
        owner_approved=True, rollback_snapshot_present=True,
        incident_ttl_minutes=60,
    )
    assert r.allowed is True


def test_scale_mode_adding_node_allowed():
    before = _state(dp=2, pc=2)
    after = _state(dp=3, pc=3, geos=3)
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=before, after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert r.allowed is True


def test_unknown_status_not_clean_capacity():
    after = _state(unknown=True)
    r = evaluate_guardrail(
        mode=MODE_SCALE, before=_state(), after=after,
        owner_approved=True, rollback_snapshot_present=True,
    )
    assert any("unknown-status" in b for b in r.blockers)


def test_no_secrets_in_output():
    r = evaluate_guardrail(
        mode=MODE_MANUAL_EMERGENCY, before=HEALTHY, after=_state(relay_only=True),
        owner_approved=True, rollback_snapshot_present=True, incident_ttl_minutes=30,
    )
    blob = json.dumps(r.to_dict())
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey", "shortId"):
        assert bad not in blob


def test_capacity_state_from_registry_excludes_non_production():
    nodes = [
        {"node_id": "lv", "role": "exit", "status": "active", "delivery_path_eligible": True,
         "groups": ["INTL_STEALTH_ACTIVE"], "country": "LV", "health": {"monitor_status": "ok", "last_smoke_status": "pass"}},
        {"node_id": "lab", "role": "lab", "status": "staging", "delivery_path_eligible": False,
         "groups": ["LAB_OWNER"], "country": "RU", "health": {}},
        {"node_id": "relay", "role": "relay", "status": "active", "delivery_path_eligible": False,
         "groups": ["RU_RELAY_ACTIVE"], "country": "RU", "health": {"monitor_status": "ok", "last_smoke_status": "pass"}},
    ]
    st = capacity_state_from_nodes(nodes)
    assert st.production_capacity_nodes == 1
    assert st.relay_ips == 1
    assert geo_count(nodes) == 1
