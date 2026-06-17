"""Tests for ops/generate_independent_exit_canary.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from generate_independent_exit_canary import (  # noqa: E402
    TASK_ID,
    build_artifact,
)
from vpn_node_selector import load_validated_registry  # noqa: E402


def test_build_artifact_includes_traffic_smoke_runbook():
    registry = load_validated_registry()
    artifact = build_artifact(registry, "nl-node-1")
    assert artifact["task"] == TASK_ID
    assert artifact["traffic_smoke_status"] == "WAITING_FOR_OWNER_TRAFFIC_SMOKE"
    assert artifact["candidate_counts_as_capacity"] is False
    assert artifact["independent_exit_paths_now"] == 1
    assert "import_instructions" in artifact
    assert "record_template" in artifact
    assert "pass_criteria" in artifact
    assert "promotion_on_pass" in artifact
    assert artifact["node_current"]["acceptance_status"] == "pending_traffic_smoke"


def test_artifact_json_serializable():
    registry = load_validated_registry()
    artifact = build_artifact(registry, "nl-node-1")
    raw = json.dumps(artifact, ensure_ascii=False)
    assert "WAITING_FOR_OWNER_TRAFFIC_SMOKE" in raw
    assert "vless://" not in raw.lower()
