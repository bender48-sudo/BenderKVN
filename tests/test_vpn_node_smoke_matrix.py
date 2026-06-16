"""Tests for VPN node smoke matrix — NODE-SMOKE-MATRIX-RUNNER-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_smoke_matrix import (  # noqa: E402
    VERDICT_BLOCKED,
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_WARN,
    build_smoke_matrix,
    format_matrix_markdown,
    is_production_capacity,
    main,
)
from vpn_node_selector import load_validated_registry  # noqa: E402


@pytest.fixture
def registry_doc():
    return load_validated_registry(DEFAULT_REGISTRY)


def _node(**overrides):
    node = {
        "node_id": "n",
        "display_name": "n",
        "region": "EU",
        "country": "LV",
        "city": "redacted",
        "provider_label": "redacted",
        "role": "exit",
        "status": "active",
        "delivery_path_eligible": True,
        "groups": ["RU_RELAY_ACTIVE"],
        "capacity": {
            "max_active_configs": None,
            "max_concurrent_sessions": None,
            "max_mbps": None,
            "reserved_headroom_percent": 40,
        },
        "health": {
            "monitor_status": "ok",
            "last_smoke_status": "pass",
            "last_smoke_at": None,
            "last_owner_test_status": None,
            "last_owner_test_at": None,
        },
        "rollout": {
            "cohort_weight": 10,
            "canary_percent": 0,
            "allow_new_assignments": True,
            "drain_after": None,
        },
        "client_support": {
            "happ_supported": True,
            "karing_supported": False,
            "v2rayn_supported": False,
            "mobile_supported": False,
        },
    }
    node.update(overrides)
    return node


def _registry(nodes):
    return {
        "schema_version": 1,
        "capacity_policy": {"delivery_path_gate_300": 2, "delivery_path_gate_30k": 2},
        "nodes": nodes,
        "_validation_warnings": [],
    }


def test_single_delivery_path_blocks_public_prod(registry_doc):
    matrix = build_smoke_matrix(registry_doc, cohort="PUBLIC_PROD")
    assert matrix.delivery_path_nodes == 1
    assert matrix.public_prod_go is False
    assert matrix.configs_300_go is False
    assert matrix.go_30k is False
    assert any("delivery path" in b for b in matrix.blockers)


def test_lab_only_not_production_capacity():
    lab = _node(
        node_id="lab", role="lab", status="staging", groups=["LAB_OWNER"],
        delivery_path_eligible=False,
    )
    assert is_production_capacity(lab) is False
    matrix = build_smoke_matrix(_registry([lab]))
    row = next(r for r in matrix.rows if r.node_id == "lab")
    assert row.production_capacity is False
    assert row.lab_only is True
    assert row.verdict == VERDICT_WARN


def test_disabled_nl_does_not_count():
    nl = _node(
        node_id="nl", country="NL", status="disabled", delivery_path_eligible=False,
        groups=["INTL_DIRECT_ACTIVE"],
    )
    matrix = build_smoke_matrix(_registry([nl]))
    row = next(r for r in matrix.rows if r.node_id == "nl")
    assert row.production_capacity is False
    assert row.verdict == VERDICT_BLOCKED
    assert matrix.production_capacity_nodes == 0


def test_backup_edge_does_not_count():
    backup = _node(
        node_id="ams", role="backup", country="NL", groups=["FALLBACK_MANUAL"],
        delivery_path_eligible=False,
    )
    assert is_production_capacity(backup) is False
    matrix = build_smoke_matrix(_registry([backup]))
    row = next(r for r in matrix.rows if r.node_id == "ams")
    assert row.backup_only is True
    assert row.verdict == VERDICT_WARN
    assert matrix.production_capacity_nodes == 0


def test_suspect_relay_blocks_capacity_unless_diagnostic():
    suspect = _node(
        node_id="r1", role="relay", country="RU", delivery_path_eligible=False,
        health={
            "monitor_status": "suspect",
            "last_smoke_status": "needs_diagnosis",
            "last_smoke_at": None,
            "last_owner_test_status": None,
            "last_owner_test_at": None,
        },
    )
    assert is_production_capacity(suspect) is False
    matrix = build_smoke_matrix(_registry([suspect]), cohort="PUBLIC_PROD")
    row = next(r for r in matrix.rows if r.node_id == "r1")
    assert row.suspect is True
    assert row.verdict == VERDICT_FAIL
    assert row.selector_eligible is False
    # diagnostic mode only changes selector eligibility, never production capacity
    diag = build_smoke_matrix(_registry([suspect]), cohort="LAB_OWNER", diagnostic_mode=True)
    row_d = next(r for r in diag.rows if r.node_id == "r1")
    assert row_d.production_capacity is False


def test_two_clean_exits_can_pass_paid_beta():
    a = _node(node_id="a", country="LV")
    b = _node(node_id="b", country="DE")
    matrix = build_smoke_matrix(_registry([a, b]), cohort="PUBLIC_PROD")
    assert matrix.production_capacity_nodes == 2
    assert matrix.delivery_path_nodes == 2
    assert matrix.public_prod_go is True
    assert matrix.small_paid_beta_go is True
    a_row = next(r for r in matrix.rows if r.node_id == "a")
    assert a_row.verdict == VERDICT_PASS


def test_no_secret_or_endpoint_in_output(registry_doc, capsys):
    code = main(["--json"])
    assert code == 0
    out = capsys.readouterr().out
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey", "shortId"):
        assert bad not in out


def test_json_schema_is_stable(registry_doc):
    matrix = build_smoke_matrix(registry_doc)
    d = matrix.to_dict()
    assert set(d.keys()) >= {"banner", "dry_run", "cohort", "summary", "blockers", "nodes"}
    summary_keys = {
        "delivery_path_nodes",
        "production_capacity_nodes",
        "canary_ready_nodes",
        "delivery_path_gate",
        "public_prod_go",
        "small_paid_beta_go",
        "configs_300_go",
        "go_30k",
        "selector_apply_enabled",
    }
    assert set(d["summary"].keys()) == summary_keys
    node_keys = {
        "node_id", "role", "status", "region", "country",
        "delivery_path_eligible", "lab_only", "backup_only", "suspect",
        "disabled", "canary_percent", "selector_eligible",
        "production_capacity", "reason", "verdict",
    }
    for n in d["nodes"]:
        assert set(n.keys()) == node_keys
    # round-trips through json
    assert json.loads(json.dumps(d)) == d


def test_markdown_contains_blockers(registry_doc):
    matrix = build_smoke_matrix(registry_doc)
    md = format_matrix_markdown(matrix)
    assert "## Blockers" in md
    assert "delivery path" in md
    assert "selector apply disabled" in md


def test_exit_code_zero_for_no_go(registry_doc, capsys):
    # NO-GO verdict must NOT be a nonzero exit code
    code = main(["--markdown"])
    assert code == 0
    out = capsys.readouterr().out
    assert "public_prod_go | False" in out


def test_selector_apply_always_disabled_this_sprint(registry_doc):
    matrix = build_smoke_matrix(registry_doc)
    assert matrix.selector_apply_enabled is False
    assert any("selector apply disabled" in b for b in matrix.blockers)
