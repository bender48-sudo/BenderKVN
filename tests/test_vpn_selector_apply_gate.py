"""Tests for selector apply gate — SUB-GEN-SELECTOR-APPLY-GATE-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import load_validated_registry  # noqa: E402
from vpn_selector_apply_gate import (  # noqa: E402
    evaluate_apply_gate,
    format_result,
    main,
)


@pytest.fixture
def registry_doc():
    return load_validated_registry(DEFAULT_REGISTRY)


def _exit_node(node_id, country="LV"):
    return {
        "node_id": node_id,
        "display_name": node_id,
        "region": "EU",
        "country": country,
        "city": "redacted",
        "provider_label": "redacted",
        "role": "exit",
        "status": "active",
        "delivery_path_eligible": True,
        "groups": ["INTL_STEALTH_ACTIVE"],
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
            "last_owner_test_status": "pass",
            "last_owner_test_at": None,
        },
        "rollout": {
            "cohort_weight": 100,
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


def _two_clean_registry():
    return {
        "schema_version": 1,
        "capacity_policy": {"delivery_path_gate_300": 2, "delivery_path_gate_30k": 2},
        "nodes": [_exit_node("exit-a", "LV"), _exit_node("exit-b", "DE")],
        "_validation_warnings": [],
    }


def test_current_state_apply_not_allowed(registry_doc):
    result = evaluate_apply_gate("PUBLIC_PROD", registry_doc)
    assert result.apply_allowed is False
    assert any("delivery_path_nodes" in b for b in result.blockers)


def test_central_guardrail_blockers_present(registry_doc):
    # apply gate must surface the shared central guardrail (not just its own checks)
    result = evaluate_apply_gate("PUBLIC_PROD", registry_doc)
    assert any(b.startswith("guardrail:") for b in result.blockers)
    assert result.guardrail_summary


def test_single_delivery_path_blocks(registry_doc):
    result = evaluate_apply_gate("PUBLIC_PROD", registry_doc, owner_approved=True, rollback_ready=True)
    # owner approval + rollback cannot override the technical delivery-path blocker
    assert result.apply_allowed is False
    assert any("delivery_path_nodes=1" in b for b in result.blockers)


def test_owner_approval_alone_insufficient():
    reg = _two_clean_registry()
    # technically GO-capable, but no rollback plan -> still blocked
    result = evaluate_apply_gate("PUBLIC_PROD", reg, owner_approved=True, rollback_ready=False)
    assert result.apply_allowed is False
    assert any("rollback" in b for b in result.blockers)


def test_two_clean_nodes_plus_approval_plus_rollback_allows():
    reg = _two_clean_registry()
    result = evaluate_apply_gate(
        "PUBLIC_PROD", reg, owner_approved=True, rollback_ready=True
    )
    assert result.delivery_path_nodes == 2
    assert result.production_capacity_nodes == 2
    assert result.selector_verdict == "GO"
    assert result.blockers == []
    assert result.apply_allowed is True


def test_two_clean_nodes_without_approval_blocked():
    reg = _two_clean_registry()
    result = evaluate_apply_gate("PUBLIC_PROD", reg, owner_approved=False, rollback_ready=True)
    assert result.apply_allowed is False
    assert any("owner APPROVE APPLY" in b for b in result.blockers)


def test_output_redacts_secrets(capsys):
    code = main(["--cohort", "PUBLIC_PROD", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    for bad in ("vless://", "vmess://", "token=", "/sub/", "publicKey", "privateKey"):
        assert bad not in out


def test_json_has_apply_allowed_key(registry_doc):
    result = evaluate_apply_gate("PUBLIC_PROD", registry_doc)
    d = result.to_dict()
    assert d["APPLY_ALLOWED"] is False
    assert "rollback_requirements" in d
    assert "required_pre_apply_snapshot" in d
    assert json.loads(json.dumps(d)) == d


def test_format_result_mentions_read_only(registry_doc):
    result = evaluate_apply_gate("PUBLIC_PROD", registry_doc)
    text = format_result(result)
    assert "read-only" in text.lower()
    assert "APPLY_ALLOWED: False" in text
