"""Selector speed/stability policy — VPN-SELECTOR-SPEED-STABILITY-POLICY-001.

Proves the dry-run selector optimizes for stable owner/user experience:
  * PUBLIC_PROD excludes suspect / lab-only / disabled / backup nodes;
  * LAB_OWNER may include the lab relay2 profile;
  * CANARY requires a canary-ready node;
  * no cohort returns the full node set blindly;
  * selection is deterministic and ordered by stability weight.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_node_selector import (  # noqa: E402
    COHORTS,
    VERDICT_NO_GO,
    build_assignment_plan,
    load_validated_registry,
)


@pytest.fixture
def registry_doc():
    return load_validated_registry(DEFAULT_REGISTRY)


def test_public_prod_excludes_unstable_classes(registry_doc):
    plan = build_assignment_plan("PUBLIC_PROD", registry_doc)
    selected = set(plan.selected_node_ids)
    # suspect relay1, lab profile, disabled NL, backup edge must all be out
    for nid in ("ru-relay-1", "ru-relay-2-lab", "nl-node-1", "ams-backup-edge"):
        assert nid not in selected


def test_lab_owner_includes_lab_relay2(registry_doc):
    plan = build_assignment_plan("LAB_OWNER", registry_doc)
    assert "ru-relay-2-lab" in plan.selected_node_ids
    # lab cohort must NOT pull production exits
    assert "lv-exit-1" not in plan.selected_node_ids


def test_canary_requires_canary_ready_node(registry_doc):
    plan = build_assignment_plan("CANARY", registry_doc)
    # no canary-ready node in current registry → NO-GO, empty
    assert plan.verdict == VERDICT_NO_GO
    assert plan.selected_node_ids == []


def test_no_cohort_returns_all_nodes(registry_doc):
    total = len([n for n in registry_doc["nodes"] if isinstance(n, dict)])
    for cohort in COHORTS:
        plan = build_assignment_plan(cohort, registry_doc)
        assert len(plan.selected_node_ids) < total, f"{cohort} returned all nodes blindly"


def test_selection_is_deterministic(registry_doc):
    a = build_assignment_plan("OWNER_FF", registry_doc).selected_node_ids
    b = build_assignment_plan("OWNER_FF", registry_doc).selected_node_ids
    assert a == b


def test_owner_ff_orders_by_stability_weight(registry_doc):
    # lv-exit-1 (weight 100) should sort before ru-relay-2 (weight 50)
    plan = build_assignment_plan("OWNER_FF", registry_doc)
    ids = plan.selected_node_ids
    assert "lv-exit-1" in ids and "ru-relay-2" in ids
    assert ids.index("lv-exit-1") < ids.index("ru-relay-2")


def test_every_rejection_has_reason(registry_doc):
    for cohort in COHORTS:
        plan = build_assignment_plan(cohort, registry_doc)
        for rej in plan.rejections:
            assert rej.reason and isinstance(rej.reason, str)
