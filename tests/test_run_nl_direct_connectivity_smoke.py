"""Tests for ops/run_nl_direct_connectivity_smoke.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from run_nl_direct_connectivity_smoke import (  # noqa: E402
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_PARTIAL,
    classify_curl_failure,
    classify_overall_verdict,
    nl_direct_connectivity_targets,
)


def test_nl_targets_exclude_ru_proof_sites():
    targets = nl_direct_connectivity_targets()
    proof = [t for t in targets if t.counts_as_nl_proof]
    control = [t for t in targets if not t.counts_as_nl_proof]
    assert len(proof) >= 4
    assert any(t.target_id == "google_generate_204" for t in proof)
    assert any(t.target_id == "yandex_ru_control" for t in control)


def test_classify_curl_failure_reset():
    assert classify_curl_failure("Connection was reset", "") == "connection_reset"


def test_classify_overall_pass_majority():
    v, bucket = classify_overall_verdict(nl_pass=4, nl_total=5, core_ok=True, reset_errors=0)
    assert v == VERDICT_PASS
    assert bucket is None


def test_classify_overall_partial_some_pass():
    v, bucket = classify_overall_verdict(nl_pass=2, nl_total=5, core_ok=True, reset_errors=3)
    assert v == VERDICT_PARTIAL
    assert bucket is not None


def test_classify_overall_fail_all_reset():
    v, bucket = classify_overall_verdict(nl_pass=0, nl_total=5, core_ok=True, reset_errors=4)
    assert v == VERDICT_FAIL
    assert bucket is not None
