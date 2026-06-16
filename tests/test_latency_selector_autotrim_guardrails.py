"""Guardrail migration tests for latency_selector_autotrim — SCRIPT-MIGRATE-LATENCY-AUTOTRIM-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from latency_selector_autotrim import (  # noqa: E402
    STATUS_APPLY_BLOCKED,
    STATUS_DRY_RUN,
    _evaluate_relay,
    build_autotrim_capacity_state,
    evaluate_autotrim_apply_guard,
    format_autotrim_result,
    relay_ips_for_mode,
    resolve_apply_mode,
)
from relay_latency_probe import RELAY1_IP, RELAY2_IP, RelayIpProbe  # noqa: E402
from vpn_production_guardrails import (  # noqa: E402
    MODE_DEGRADE,
    MODE_DRY_RUN,
    MODE_INCIDENT,
    MODE_MANUAL_EMERGENCY,
    MODE_SCALE,
    GuardrailConfig,
)


def _doc_with_nl(n_inject: int = 10) -> dict:
    return {
        "remnawave": {"injectHosts": [{"selector": {"values": [f"u{i}" for i in range(n_inject)]}}]},
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": [f"proxy-{i}" if i else "proxy" for i in range(n_inject)]},
            ]
        },
    }


def _registry_two_relays_one_exit() -> list[dict]:
    return [
        {
            "node_id": "lv-exit-1",
            "role": "exit",
            "status": "active",
            "delivery_path_eligible": True,
            "groups": ["INTL_STEALTH_ACTIVE"],
            "country": "LV",
            "health": {"monitor_status": "ok", "last_smoke_status": "pass"},
        },
        {
            "node_id": "ru-relay-1",
            "role": "relay",
            "status": "active",
            "delivery_path_eligible": False,
            "groups": ["RU_RELAY_ACTIVE"],
            "country": "RU",
            "health": {"monitor_status": "ok", "last_smoke_status": "pass"},
        },
        {
            "node_id": "ru-relay-2",
            "role": "relay",
            "status": "active",
            "delivery_path_eligible": False,
            "groups": ["RU_RELAY_ACTIVE"],
            "country": "RU",
            "health": {"monitor_status": "ok", "last_smoke_status": "pass"},
        },
    ]


def _registry_one_exit() -> list[dict]:
    return [_registry_two_relays_one_exit()[0]]


def test_relay_ips_for_mode():
    assert relay_ips_for_mode("full") == 2
    assert relay_ips_for_mode("relay1_only") == 1
    assert relay_ips_for_mode("relay2_only") == 1


def test_default_resolve_apply_mode_is_dry_run():
    mode, blockers = resolve_apply_mode(applying=False, mode_arg=None, reduces_capacity=True)
    assert mode == MODE_DRY_RUN
    assert blockers == []


def test_apply_without_mode_when_reducing_blocked():
    mode, blockers = resolve_apply_mode(applying=True, mode_arg=None, reduces_capacity=True)
    assert mode == MODE_DRY_RUN
    assert any("--mode degrade" in b for b in blockers)


def test_apply_without_owner_approval_blocked():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=False,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False
    assert any("owner approval" in b for b in guard.blockers)


def test_apply_without_rollback_snapshot_blocked():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=False,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False
    assert any("rollback" in b for b in guard.blockers)


def test_capacity_reduction_in_scale_mode_blocked():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="relay1_only",
        include_nl_before=True,
        include_nl_after=True,
        mode=MODE_SCALE,
        owner_approved=True,
        rollback_snapshot_present=True,
    )
    assert guard.allowed is False
    assert any("capacity reduction not allowed in scale" in b for b in guard.blockers)


def test_incident_without_ttl_blocked():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=None,
    )
    assert guard.allowed is False
    assert any("incident_ttl_minutes" in b for b in guard.blockers)


def test_delivery_path_below_minimum_blocked():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    cfg = GuardrailConfig(minimum_delivery_paths=2)
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_DEGRADE,
        owner_approved=True,
        rollback_snapshot_present=True,
        config=cfg,
    )
    assert guard.allowed is False
    assert any("delivery_path_nodes after=1 < minimum 2" in b for b in guard.blockers)


def test_relay_only_collapse_blocked():
    doc = _doc_with_nl(n_inject=6)  # no NL in inject
    nodes = _registry_two_relays_one_exit()
    cfg = GuardrailConfig(minimum_delivery_paths=1, minimum_relay_ips=0)
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="relay1_only",
        include_nl_before=False,
        include_nl_after=False,
        mode=MODE_DEGRADE,
        owner_approved=True,
        rollback_snapshot_present=True,
        config=cfg,
    )
    assert guard.allowed is False
    assert any("relay-only collapse" in b for b in guard.blockers)


def test_relay_ip_reduction_blocked_even_with_incident():
    doc = _doc_with_nl(n_inject=6)
    nodes = _registry_two_relays_one_exit()
    cfg = GuardrailConfig(minimum_delivery_paths=1)
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="relay2_only",
        include_nl_before=False,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        config=cfg,
    )
    assert guard.allowed is False
    assert any("relay_ips after=1 < minimum 2" in b for b in guard.blockers)


def test_empty_registry_apply_blocked():
    doc = _doc_with_nl()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=[],
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
    )
    assert guard.allowed is False
    assert any("cannot build" in b for b in guard.blockers)


def test_build_capacity_state_none_on_empty_registry():
    assert build_autotrim_capacity_state([], _doc_with_nl(), "full", True) is None


def test_dry_run_status_in_format_output():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="relay1_only",
        include_nl_before=True,
        include_nl_after=True,
        mode=MODE_DRY_RUN,
        owner_approved=False,
        rollback_snapshot_present=False,
    )
    payload = format_autotrim_result(
        status=STATUS_DRY_RUN,
        guard=guard,
        relay_mode_before="full",
        relay_mode_after="relay1_only",
        include_nl_before=True,
        include_nl_after=True,
        changed=True,
        diagnostic_log=["relay2 slow → relay1_only"],
    )
    assert payload["status"] == STATUS_DRY_RUN
    assert "relay2 slow" in payload["diagnostic_log"][0]
    assert payload["guardrail_summary"]


def test_no_secrets_in_formatted_output():
    doc = _doc_with_nl()
    nodes = _registry_one_exit()
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=False,
        rollback_snapshot_present=False,
        incident_ttl_minutes=60,
    )
    payload = format_autotrim_result(
        status=STATUS_APPLY_BLOCKED,
        guard=guard,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        changed=True,
        diagnostic_log=[],
    )
    blob = json.dumps(payload)
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey", "shortId"):
        assert bad not in blob


def test_evaluate_relay_trim_diagnostics_preserved():
    """Core hysteresis logic unchanged — relay2 fail → relay1_only recommendation."""
    state = {
        "relay_mode": "full",
        "relay2_slow_streak": 1,
        "relay1_slow_streak": 0,
        "relay2_ok_streak": 0,
        "relay1_ok_streak": 0,
    }
    probes = {
        RELAY1_IP: RelayIpProbe(ip=RELAY1_IP, ok=True, tcp_connect_ms=50.0, tls_ok=True, error=None),
        RELAY2_IP: RelayIpProbe(ip=RELAY2_IP, ok=False, tcp_connect_ms=None, tls_ok=False, error="timeout"),
    }
    mode, log = _evaluate_relay(probes, state)
    assert mode == "relay1_only"
    assert any("relay2 fail" in line for line in log)


def test_manual_emergency_allows_nl_only_trim_when_minimums_met():
    """NL drop only (relay pool intact) can pass under incident with full gates."""
    doc = _doc_with_nl()
    nodes = _registry_two_relays_one_exit()
    cfg = GuardrailConfig(minimum_delivery_paths=1, minimum_relay_ips=2)
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="full",
        include_nl_before=True,
        include_nl_after=False,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        config=cfg,
    )
    assert guard.allowed is True


def test_degrade_mode_requires_explicit_mode_not_scale():
    mode, blockers = resolve_apply_mode(applying=True, mode_arg=MODE_DEGRADE, reduces_capacity=True)
    assert mode == MODE_DEGRADE
    assert blockers == []


def test_manual_emergency_bypasses_relay_only_block_but_not_relay_ip_min():
    doc = _doc_with_nl(n_inject=6)
    nodes = _registry_two_relays_one_exit()
    cfg = GuardrailConfig(minimum_delivery_paths=1, minimum_relay_ips=2)
    guard = evaluate_autotrim_apply_guard(
        registry_nodes=nodes,
        doc=doc,
        relay_mode_before="full",
        relay_mode_after="relay1_only",
        include_nl_before=False,
        include_nl_after=False,
        mode=MODE_MANUAL_EMERGENCY,
        owner_approved=True,
        rollback_snapshot_present=True,
        config=cfg,
    )
    # relay-only flag allowed in manual_emergency, but relay_ips minimum still blocks
    assert guard.allowed is False
    assert any("relay_ips after=1" in b for b in guard.blockers)
    assert not any("relay-only collapse" in b for b in guard.blockers)
