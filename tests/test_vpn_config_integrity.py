"""Tests for central config integrity verifier — VPN-CONFIG-INTEGRITY-VERIFIER-001."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from vpn_config_integrity import (  # noqa: E402
    assert_already_applied,
    verify_outbound_nodes_active,
    verify_selector_outbound_mapping,
    verify_template_integrity,
)


def _doc(inject_uuids, selector_tags):
    return {
        "remnawave": {"injectHosts": [{"selector": {"values": list(inject_uuids)}}]},
        "routing": {"balancers": [{"tag": "Intl_Direct", "selector": list(selector_tags)}]},
    }


def _hosts(uuids, *, disabled=(), node_name="lv-exit-1"):
    return {
        u: {"uuid": u, "isDisabled": u in disabled, "nodes": [f"node-{u}"]}
        for u in uuids
    }


def test_count_only_ok_but_proxy_overreach_fails():
    # 4 inject slots but selector references proxy-10 → over-reach (count-only would pass)
    doc = _doc([f"u{i}" for i in range(4)], ["proxy", "proxy-2", "proxy-3", "proxy-10"])
    res = verify_template_integrity(doc)
    assert res.ok is False
    assert any("proxy-10" in e for e in res.errors)


def test_selector_references_missing_outbound_fails():
    errs = verify_selector_outbound_mapping(["out-lv-exit-1", "out-ghost"], {"out-lv-exit-1"})
    assert any("out-ghost" in e for e in errs)


def test_outbound_referencing_disabled_node_fails_for_prod():
    errs = verify_outbound_nodes_active(
        {"out-nl": {"status": "disabled"}, "out-lv": {"status": "active"}}
    )
    assert any("out-nl" in e for e in errs)
    assert not any("out-lv" in e for e in errs)


def test_inject_uuid_without_host_fails():
    doc = _doc(["u1", "u2"], ["proxy", "proxy-2"])
    res = verify_template_integrity(doc, hosts_by_uuid=_hosts(["u1"]))
    assert res.ok is False
    assert any("u2" in e or "no panel host" in e for e in res.errors)


def test_inject_uuid_disabled_host_fails():
    doc = _doc(["u1", "u2"], ["proxy", "proxy-2"])
    res = verify_template_integrity(
        doc, hosts_by_uuid=_hosts(["u1", "u2"], disabled={"u2"})
    )
    assert res.ok is False
    assert any("disabled" in e for e in res.errors)


def test_count_only_mismatch_node_mapping_fails():
    # UUIDs exist & enabled but map to wrong node group (by-assumption ordering)
    doc = _doc(["u1", "u2"], ["proxy", "proxy-2"])
    hosts = {
        "u1": {"uuid": "u1", "isDisabled": False, "nodes": ["nodeA"]},
        "u2": {"uuid": "u2", "isDisabled": False, "nodes": ["nodeB"]},
    }
    nodes_by_uuid = {"nodeA": {"name": "lv-exit-1"}, "nodeB": {"name": "some-other"}}
    res = verify_template_integrity(
        doc,
        hosts_by_uuid=hosts,
        expected_node_ids={"lv-exit-1"},
        nodes_by_uuid=nodes_by_uuid,
    )
    assert res.ok is False
    assert any("does not map" in e for e in res.errors)


def test_correct_synthetic_mapping_passes():
    doc = _doc(["u1", "u2"], ["proxy", "proxy-2"])
    hosts = {
        "u1": {"uuid": "u1", "isDisabled": False, "nodes": ["nodeA"]},
        "u2": {"uuid": "u2", "isDisabled": False, "nodes": ["nodeA"]},
    }
    nodes_by_uuid = {"nodeA": {"name": "lv-exit-1"}}
    res = verify_template_integrity(
        doc,
        hosts_by_uuid=hosts,
        expected_node_ids={"lv-exit-1"},
        nodes_by_uuid=nodes_by_uuid,
    )
    assert res.ok is True
    assert res.errors == []


def test_already_applied_requires_injected_and_enabled():
    doc = _doc(["u1"], ["proxy"])
    # required u2 missing from inject
    res = assert_already_applied(doc, ["u1", "u2"], _hosts(["u1", "u2"]))
    assert res.ok is False
    assert any("u2" in e for e in res.errors)


def test_already_applied_disabled_host_fails():
    doc = _doc(["u1", "u2"], ["proxy", "proxy-2"])
    res = assert_already_applied(doc, ["u1", "u2"], _hosts(["u1", "u2"], disabled={"u2"}))
    assert res.ok is False
    assert any("disabled" in e for e in res.errors)


def test_already_applied_correct_passes():
    doc = _doc(["u1", "u2"], ["proxy", "proxy-2"])
    res = assert_already_applied(doc, ["u1", "u2"], _hosts(["u1", "u2"]))
    assert res.ok is True
