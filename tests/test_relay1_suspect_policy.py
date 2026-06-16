"""Relay1 suspect-exclusion policy — RELAY1-DRAIN-OR-RETEST-001.

Proves that a suspect node (ru-relay-1) is excluded from production/canary
selection and never counted as production capacity, unless an explicit
diagnostic flag is used (which still never grants production capacity).
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
    build_assignment_plan,
    load_validated_registry,
)
from vpn_node_smoke_matrix import build_smoke_matrix, is_production_capacity  # noqa: E402
from generate_owner_canary_profile import select_owner_canary_candidates  # noqa: E402

RELAY1 = "ru-relay-1"

PRODUCTION_COHORTS = ("PUBLIC_PROD", "OWNER_FF", "PAID_BETA_MANUAL", "CANARY")


@pytest.fixture
def registry_doc():
    return load_validated_registry(DEFAULT_REGISTRY)


@pytest.mark.parametrize("cohort", PRODUCTION_COHORTS)
def test_relay1_excluded_from_production_cohorts(registry_doc, cohort):
    plan = build_assignment_plan(cohort, registry_doc)
    assert RELAY1 not in plan.selected_node_ids


def test_relay1_rejection_reason_is_suspect(registry_doc):
    plan = build_assignment_plan("OWNER_FF", registry_doc)
    rej = [r for r in plan.rejections if r.node_id == RELAY1]
    assert rej
    assert "suspect" in rej[0].reason.lower()


def test_relay1_not_production_capacity(registry_doc):
    matrix = build_smoke_matrix(registry_doc, cohort="PUBLIC_PROD")
    row = next(r for r in matrix.rows if r.node_id == RELAY1)
    assert row.suspect is True
    assert row.production_capacity is False
    assert row.verdict == "FAIL"


def test_relay1_included_only_with_diagnostic_flag(registry_doc):
    # diagnostic/allow_suspect lets relay1 pass selector eligibility for a lab/
    # diagnostic cohort, but it still must not be counted as production capacity.
    diag_plan = build_assignment_plan("OWNER_FF", registry_doc, allow_suspect=True)
    assert RELAY1 in diag_plan.selected_node_ids
    node = next(n for n in registry_doc["nodes"] if n["node_id"] == RELAY1)
    assert is_production_capacity(node) is False


def test_relay1_excluded_from_owner_canary(registry_doc):
    candidates, excluded = select_owner_canary_candidates(registry_doc)
    assert RELAY1 not in {c.node_id for c in candidates}
    assert RELAY1 in {e["node_id"] for e in excluded}
