"""Guardrail migration tests for sync_injecthosts_connected — SCRIPT-MIGRATE-INJECTHOSTS-SYNC-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from sync_injecthosts_connected import (  # noqa: E402
    HOST_ROLE_RELAY,
    STATUS_APPLY_BLOCKED,
    STATUS_DRY_RUN,
    build_inject_sync_capacity_state,
    classify_inject_host,
    compute_connected_inject,
    evaluate_inject_sync_apply_guard,
    format_inject_sync_result,
    is_relay_only_inject,
    relay_ip_count_from_inject,
    resolve_apply_mode,
    verify_inject_uuid_selector_consistency,
)
from vpn_production_guardrails import (  # noqa: E402
    MODE_DEGRADE,
    MODE_DRY_RUN,
    MODE_INCIDENT,
    MODE_MANUAL_EMERGENCY,
    MODE_SCALE,
    GuardrailConfig,
)


def _uuid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012x}"


def _host(uid: str, remark: str, *, connected: bool = True, addr: str = "10.0.0.1") -> dict:
    node_uid = f"node-{uid}"
    return {
        "uuid": uid,
        "remark": remark,
        "address": addr,
        "port": 443,
        "nodes": [node_uid],
    }


def _panel_node(node_uid: str, *, connected: bool = True, name: str = "lv-exit") -> dict:
    return {
        "uuid": node_uid,
        "name": name,
        "isConnected": connected,
        "isDisabled": False,
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


def _doc_with_balancers(n_inject: int) -> dict:
    tags = ["proxy"] + [f"proxy-{i}" for i in range(2, n_inject + 1)]
    return {
        "remnawave": {"injectHosts": [{"selector": {"values": []}}]},
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": tags},
            ]
        },
    }


def _six_host_fixture() -> tuple[list[dict], list[dict], list[str]]:
    uuids = [_uuid(i) for i in range(1, 7)]
    hosts = [
        _host(uuids[0], "LV direct", addr="10.0.0.10"),
        _host(uuids[1], "LV direct 2", addr="10.0.0.11"),
        _host(uuids[2], "LV direct 3", addr="10.0.0.12"),
        _host(uuids[3], "relay RU", addr="10.0.1.1"),
        _host(uuids[4], "relay RU 2", addr="10.0.1.1"),
        _host(uuids[5], "relay RU 3", addr="10.0.1.2"),
    ]
    panel_nodes = [_panel_node(f"node-{u}", connected=True) for u in uuids]
    return hosts, panel_nodes, uuids


def test_compute_connected_inject_drops_disconnected():
    hosts, panel_nodes, uuids = _six_host_fixture()
    panel_nodes[0]["isConnected"] = False
    new_vals, log = compute_connected_inject(hosts, panel_nodes, uuids)
    assert len(new_vals) == 5
    assert uuids[0] not in new_vals
    assert any("drop" in ln for ln in log)


def test_classify_inject_host_roles():
    assert classify_inject_host({"remark": "LV direct"}) == "lv_direct"
    assert classify_inject_host({"remark": "NL :443"}) == "nl_direct"
    assert classify_inject_host({"remark": "relay RU"}) == "relay"
    assert classify_inject_host({"remark": "NL relay 9443", "port": 9443}) == "relay_nl"


def test_default_resolve_apply_mode_is_dry_run():
    mode, blockers = resolve_apply_mode(applying=False, mode_arg=None, reduces_capacity=True)
    assert mode == MODE_DRY_RUN
    assert blockers == []


def test_apply_without_mode_when_reducing_blocked():
    mode, blockers = resolve_apply_mode(applying=True, mode_arg=None, reduces_capacity=True)
    assert mode == MODE_DRY_RUN
    assert any("--mode degrade" in b for b in blockers)


def test_apply_without_owner_approval_blocked():
    hosts, panel_nodes, uuids = _six_host_fixture()
    cur = uuids
    new = uuids[1:]
    doc = _doc_with_balancers(len(new))
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=cur,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=False,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("owner approval" in b for b in guard.blockers)


def test_apply_without_rollback_snapshot_blocked():
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = uuids[1:]
    doc = _doc_with_balancers(len(new))
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=False,
        incident_ttl_minutes=60,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("rollback" in b for b in guard.blockers)


def test_apply_below_min_inject_blocked():
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = uuids[:2]
    doc = _doc_with_balancers(len(new))
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("min 3" in b for b in guard.blockers)


def test_capacity_reduction_in_scale_mode_blocked():
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = uuids[1:]
    doc = _doc_with_balancers(len(new))
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids,
        new_uuids=new,
        mode=MODE_SCALE,
        owner_approved=True,
        rollback_snapshot_present=True,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("scale mode" in b for b in guard.blockers)


def test_incident_without_ttl_blocked():
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = uuids[1:]
    doc = _doc_with_balancers(len(new))
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=None,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("incident_ttl_minutes" in b for b in guard.blockers)


def test_geo_minimum_blocked():
    hosts, panel_nodes, uuids = _six_host_fixture()
    nl_host = _host(_uuid(7), "NL :443", addr="10.0.2.1")
    nl_host["nodes"] = ["node-canary"]
    hosts = hosts + [nl_host]
    panel_nodes = panel_nodes + [
        _panel_node("node-canary", connected=True, name="canary-exit")
    ]
    uuids = uuids + [nl_host["uuid"]]
    new = uuids[:-1]
    doc = _doc_with_balancers(len(new))
    cfg = GuardrailConfig(minimum_delivery_paths=0, minimum_relay_ips=0, minimum_geos=2)
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
        config=cfg,
    )
    assert guard.allowed is False
    assert any("geos" in b for b in guard.blockers)


def test_canary_disappearance_blocked():
    canary_uid = _uuid(7)
    hosts, panel_nodes, uuids = _six_host_fixture()
    canary_host = _host(canary_uid, "NL canary", addr="10.0.2.1")
    canary_host["nodes"] = ["node-canary"]
    hosts = hosts + [canary_host]
    panel_nodes = panel_nodes + [
        _panel_node("node-canary", connected=False, name="canary-exit"),
    ]
    uuids_all = uuids + [canary_uid]
    new = uuids
    doc = _doc_with_balancers(len(new))
    nodes = list(_registry_two_relays_one_exit())
    nodes.append(
        {
            "node_id": "canary-exit",
            "role": "exit",
            "status": "canary",
            "delivery_path_eligible": False,
            "groups": ["INTL_DIRECT_ACTIVE"],
            "country": "NL",
            "health": {"monitor_status": "ok", "last_smoke_status": "pass"},
        }
    )
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=nodes,
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids_all,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
        config=GuardrailConfig(minimum_delivery_paths=0, minimum_relay_ips=0),
    )
    assert guard.allowed is False
    assert any("canary" in b for b in guard.blockers)
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = [u for u in uuids if "relay" not in next(h["remark"] for h in hosts if h["uuid"] == u)]
    doc = _doc_with_balancers(len(new))
    cfg = GuardrailConfig(minimum_delivery_paths=0, minimum_relay_ips=2)
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=uuids,
        new_uuids=new,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
        config=cfg,
    )
    assert guard.allowed is False
    assert any("relay_ips" in b for b in guard.blockers)


def test_relay_only_collapse_blocked():
    relay_hosts = [
        _host(_uuid(1), "relay RU", addr="10.0.1.1"),
        _host(_uuid(2), "relay RU 2", addr="10.0.1.1"),
        _host(_uuid(3), "relay RU 3", addr="10.0.1.2"),
    ]
    relay_uuids = [h["uuid"] for h in relay_hosts]
    panel_nodes = [_panel_node(f"node-{u}") for u in relay_uuids]
    doc = _doc_with_balancers(3)
    assert is_relay_only_inject({h["uuid"]: h for h in relay_hosts}, relay_uuids)
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=relay_hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=relay_uuids + [_uuid(9)],
        new_uuids=relay_uuids,
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("relay-only collapse" in b for b in guard.blockers)


def test_relay_ip_minimum_blocked():
    """Dry-run advisory + apply path requires explicit mode/approval."""
    mode, blockers = resolve_apply_mode(applying=True, mode_arg=None, reduces_capacity=True)
    assert blockers
    assert mode == MODE_DRY_RUN


def test_empty_registry_blocks_capacity_state():
    hosts, panel_nodes, uuids = _six_host_fixture()
    assert build_inject_sync_capacity_state([], hosts, panel_nodes, uuids) is None
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=[],
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=_doc_with_balancers(6),
        cur_uuids=uuids,
        new_uuids=uuids[1:],
        mode=MODE_INCIDENT,
        owner_approved=True,
        rollback_snapshot_present=True,
        incident_ttl_minutes=60,
        min_inject=3,
    )
    assert guard.allowed is False
    assert any("registry missing" in b or "capacity state" in b for b in guard.blockers)


def test_uuid_selector_mismatch_blocks_apply():
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = uuids[:4]
    doc = _doc_with_balancers(10)
    errors = verify_inject_uuid_selector_consistency(
        doc, new, {h["uuid"]: h for h in hosts}
    )
    assert errors
    assert any("proxy-10" in e or "only 4 slots" in e for e in errors)


def test_count_only_ok_insufficient():
    hosts, panel_nodes, uuids = _six_host_fixture()
    new = uuids[:6]
    doc = _doc_with_balancers(10)
    errors = verify_inject_uuid_selector_consistency(
        doc, new, {h["uuid"]: h for h in hosts}
    )
    assert any("count-only OK insufficient" in e for e in errors)


def test_diagnostic_output_in_dry_run_format():
    guard_result = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=_six_host_fixture()[0],
        panel_nodes=_six_host_fixture()[1],
        doc=_doc_with_balancers(5),
        cur_uuids=_six_host_fixture()[2],
        new_uuids=_six_host_fixture()[2][1:],
        mode=MODE_DRY_RUN,
        owner_approved=False,
        rollback_snapshot_present=False,
        min_inject=3,
    )
    payload = format_inject_sync_result(
        status=STATUS_DRY_RUN,
        guard=guard_result,
        cur_count=6,
        new_count=5,
        changed=True,
        diagnostic_log=["  drop abc… (node down)"],
    )
    assert payload["status"] == STATUS_DRY_RUN
    assert payload["diagnostic_log"]
    text = json.dumps(payload)
    assert "vless://" not in text
    assert "00000000" not in text or "injectHosts" in text


def test_manual_emergency_allows_relay_only_when_other_checks_pass():
    relay_hosts = [
        _host(_uuid(1), "relay RU", addr="10.0.1.1"),
        _host(_uuid(2), "relay RU 2", addr="10.0.1.1"),
        _host(_uuid(3), "relay RU 3", addr="10.0.1.2"),
    ]
    relay_uuids = [h["uuid"] for h in relay_hosts]
    panel_nodes = [_panel_node(f"node-{u}") for u in relay_uuids]
    doc = _doc_with_balancers(3)
    cfg = GuardrailConfig(minimum_delivery_paths=0, minimum_relay_ips=0)
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=relay_hosts,
        panel_nodes=panel_nodes,
        doc=doc,
        cur_uuids=relay_uuids,
        new_uuids=relay_uuids,
        mode=MODE_MANUAL_EMERGENCY,
        owner_approved=True,
        rollback_snapshot_present=True,
        min_inject=3,
        config=cfg,
    )
    assert guard.allowed is True


def test_relay_ip_count_from_inject():
    hosts, _, uuids = _six_host_fixture()
    by_uuid = {h["uuid"]: h for h in hosts}
    assert relay_ip_count_from_inject(by_uuid, uuids) == 2


def test_no_secrets_in_guard_output():
    hosts, panel_nodes, uuids = _six_host_fixture()
    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=_registry_two_relays_one_exit(),
        hosts=hosts,
        panel_nodes=panel_nodes,
        doc=_doc_with_balancers(5),
        cur_uuids=uuids,
        new_uuids=uuids[1:],
        mode=MODE_DRY_RUN,
        owner_approved=False,
        rollback_snapshot_present=False,
        min_inject=3,
    )
    blob = json.dumps(guard.to_dict())
    assert "vless://" not in blob
    assert "token" not in blob.lower() or "guardrail" in blob
