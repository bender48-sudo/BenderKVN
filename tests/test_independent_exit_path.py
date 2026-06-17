"""INDEPENDENT_EXIT_PATH_V1 — NEW-INDEPENDENT-EXIT-PATH-001.

Shared-upstream relay/exit pairs must not inflate independent delivery capacity.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from validate_vpn_node_registry import count_independent_exit_paths  # noqa: E402
from vpn_registry_model import (  # noqa: E402
    is_independent_exit,
    is_independent_exit_candidate,
)


def _exit(node_id, *, status="active", eligible=True, arch="compliant", sug=None,
          path="exit", candidate=False):
    return {
        "node_id": node_id,
        "role": "exit",
        "path_role": path,
        "status": status,
        "delivery_path_eligible": eligible,
        "architecture_compliance": arch,
        "shared_upstream_group": sug,
        "independent_exit_candidate": candidate,
    }


def test_lv_only_counts_as_one():
    assert count_independent_exit_paths([_exit("lv-exit-1")]) == 1


def test_shared_upstream_pair_counts_as_one():
    nodes = [
        _exit("e1", sug="ru-fwd-upstream-1"),
        _exit("e2", sug="ru-fwd-upstream-1"),
    ]
    assert count_independent_exit_paths(nodes) == 1


def test_two_independent_exits_count_as_two():
    nodes = [_exit("lv-exit-1"), _exit("second-exit")]
    assert count_independent_exit_paths(nodes) == 2


def test_relay_role_never_counts():
    relay = {
        "node_id": "ru-relay-1",
        "role": "relay",
        "path_role": "relay",
        "status": "active",
        "delivery_path_eligible": True,
        "architecture_compliance": "compliant",
        "shared_upstream_group": "ru-fwd-upstream-1",
    }
    assert count_independent_exit_paths([relay]) == 0


def test_staging_candidate_not_counted():
    nl = _exit("nl-node-1", status="staging", eligible=False, candidate=True)
    assert count_independent_exit_paths([nl]) == 0
    assert is_independent_exit(nl) is False
    assert is_independent_exit_candidate(nl) is True


def test_non_compliant_exit_not_counted():
    bad = _exit("x", arch="non_compliant")
    assert count_independent_exit_paths([bad]) == 0
    assert is_independent_exit(bad) is False


def test_active_eligible_compliant_exit_is_independent():
    assert is_independent_exit(_exit("lv-exit-1")) is True
