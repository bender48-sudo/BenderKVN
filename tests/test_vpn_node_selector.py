"""Tests for VPN node selector dry-run — SUB-GEN-SELECTOR-STRATEGY-001."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import (  # noqa: E402
    VERDICT_CONDITIONAL,
    VERDICT_GO,
    VERDICT_NO_GO,
    build_assignment_plan,
    evaluate_node_for_cohort,
    format_assignment_plan,
    load_validated_registry,
    main,
    COHORT_POLICIES,
)

CANONICAL = DEFAULT_REGISTRY


def _minimal_node(**overrides):
    node = {
        "node_id": "test-node",
        "display_name": "Test",
        "region": "EU",
        "country": "LV",
        "city": "redacted",
        "provider_label": "redacted",
        "role": "exit",
        "status": "active",
        "delivery_path_eligible": False,
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


@pytest.fixture
def registry_doc():
    return load_validated_registry(CANONICAL)


def test_lab_owner_selects_lab_node_only(registry_doc):
    plan = build_assignment_plan("LAB_OWNER", registry_doc)
    assert plan.verdict == VERDICT_GO
    assert plan.selected_node_ids == ["ru-relay-2-lab"]


def test_public_prod_no_go_below_delivery_gate(registry_doc):
    plan = build_assignment_plan("PUBLIC_PROD", registry_doc)
    assert plan.verdict == VERDICT_NO_GO
    assert plan.selected_node_ids == []
    assert plan.delivery_path_nodes == 1
    assert any("hard NO-GO" in w for w in plan.warnings)


def test_nl_staging_never_selected(registry_doc):
    # NL moved disabled->staging after SSH PASS, but stays hard-gated on
    # A2/A4 controlled smoke + owner approval — never auto-selected.
    plan = build_assignment_plan("OWNER_FF", registry_doc)
    assert "nl-node-1" not in plan.selected_node_ids
    nl_rej = [r for r in plan.rejections if r.node_id == "nl-node-1"]
    assert nl_rej
    assert "A2/A4" in nl_rej[0].reason


def test_draining_node_rejected():
    node = _minimal_node(node_id="draining-node", status="draining")
    ok, reason = evaluate_node_for_cohort(node, COHORT_POLICIES["OWNER_FF"])
    assert not ok
    assert reason and "draining" in reason


def test_failed_and_decommissioned_rejected():
    for status in ("failed", "decommissioned"):
        node = _minimal_node(node_id=f"{status}-node", status=status)
        ok, reason = evaluate_node_for_cohort(node, COHORT_POLICIES["PUBLIC_PROD"])
        assert not ok
        assert reason and status in reason


def test_suspect_not_selected_for_owner_ff(registry_doc):
    plan = build_assignment_plan("OWNER_FF", registry_doc)
    assert "ru-relay-1" not in plan.selected_node_ids
    suspect = [r for r in plan.rejections if r.node_id == "ru-relay-1"]
    assert suspect
    assert "suspect" in suspect[0].reason.lower()


def test_suspect_allowed_with_diagnostic_flag():
    node = _minimal_node(
        node_id="ru-relay-1",
        health={
            "monitor_status": "suspect",
            "last_smoke_status": "needs_diagnosis",
            "last_smoke_at": None,
            "last_owner_test_status": None,
            "last_owner_test_at": None,
        },
    )
    ok, _ = evaluate_node_for_cohort(
        node, COHORT_POLICIES["OWNER_FF"], allow_suspect=True
    )
    assert ok


def test_canary_respects_canary_percent(registry_doc):
    plan = build_assignment_plan("CANARY", registry_doc)
    assert plan.verdict == VERDICT_NO_GO
    assert plan.selected_node_ids == []
    assert any("canary" in r.reason.lower() for r in plan.rejections)


def test_canary_selects_when_eligible():
    registry = {
        "schema_version": 1,
        "capacity_policy": {"delivery_path_gate_300": 2},
        "nodes": [
            _minimal_node(
                node_id="canary-node",
                groups=["RU_RELAY_CANARY"],
                status="active",
                rollout={
                    "cohort_weight": 5,
                    "canary_percent": 5,
                    "allow_new_assignments": True,
                    "drain_after": None,
                },
            )
        ],
        "_validation_warnings": [],
    }
    plan = build_assignment_plan("CANARY", registry)
    assert plan.selected_node_ids == ["canary-node"]
    assert plan.verdict == VERDICT_CONDITIONAL


def test_fallback_manual_explicit(registry_doc):
    plan = build_assignment_plan("FALLBACK_MANUAL", registry_doc)
    assert "ams-backup-edge" in plan.selected_node_ids
    assert plan.verdict == VERDICT_CONDITIONAL


def test_rejection_reasons_present(registry_doc):
    plan = build_assignment_plan("PUBLIC_PROD", registry_doc)
    assert plan.rejections
    text = format_assignment_plan(plan)
    assert "rejected:" in text
    assert "ru-relay-1:" in text


def test_cli_output_has_no_secret_patterns(capsys):
    for cohort in ("LAB_OWNER", "PUBLIC_PROD", "CANARY"):
        code = main(["--cohort", cohort])
        assert code == 0
        out = capsys.readouterr().out
        assert "vless://" not in out
        assert "token=" not in out.lower()
        assert "/sub/" not in out


def test_owner_ff_conservative_selection(registry_doc):
    plan = build_assignment_plan("OWNER_FF", registry_doc)
    assert "lv-exit-1" in plan.selected_node_ids
    assert "ru-relay-2" in plan.selected_node_ids
    assert "ru-relay-2-lab" not in plan.selected_node_ids
    assert plan.verdict == VERDICT_CONDITIONAL
