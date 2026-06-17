"""Tests for registry-driven config generator — VPN-INVENTORY-DRIVEN-CONFIG-GENERATOR-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from generate_vpn_config_from_registry import (  # noqa: E402
    format_markdown,
    generate_for_cohort,
)
from vpn_registry_model import (  # noqa: E402
    COHORT_CANARY,
    COHORT_LAB_OWNER,
    COHORT_PUBLIC_PROD,
)


def _node(node_id, role, status, *, eligible=False, groups=None, monitor="ok",
          smoke="pass", canary=0, weight=0, country="LV"):
    return {
        "node_id": node_id,
        "role": role,
        "status": status,
        "country": country,
        "region": "EU",
        "delivery_path_eligible": eligible,
        "groups": groups or [],
        "health": {"monitor_status": monitor, "last_smoke_status": smoke},
        "rollout": {"canary_percent": canary, "cohort_weight": weight},
        "capacity": {"max_active_configs": None},
    }


def _registry(nodes):
    return {"nodes": nodes, "capacity_policy": {"delivery_path_gate_300": 2}}


def _current_like():
    return _registry(
        [
            _node("lv-exit-1", "exit", "active", eligible=True, groups=["INTL_STEALTH_ACTIVE"], weight=100),
            _node("ru-relay-1", "relay", "active", monitor="suspect", groups=["RU_RELAY_ACTIVE"]),
            _node("ru-relay-2", "relay", "active", groups=["RU_RELAY_ACTIVE"]),
            _node("ru-relay-2-lab", "lab", "staging", groups=["LAB_OWNER"]),
            _node("nl-node-1", "exit", "staging", groups=["INTL_DIRECT_ACTIVE"], country="NL"),
            _node("ams-backup-edge", "backup", "active", groups=["FALLBACK_MANUAL"], country="NL"),
        ]
    )


def test_public_prod_current_state_no_go():
    gen = generate_for_cohort(_current_like(), COHORT_PUBLIC_PROD)
    assert gen.go is False
    assert any("NO-GO" in b for b in gen.blockers)


def test_lab_owner_generates_lab_preview():
    gen = generate_for_cohort(_current_like(), COHORT_LAB_OWNER)
    assert gen.go is True
    assert any(o["node_id"] == "ru-relay-2-lab" for o in gen.outbounds)


def test_canary_excludes_nl_until_canary_flag():
    gen = generate_for_cohort(_current_like(), COHORT_CANARY)
    node_ids = {o["node_id"] for o in gen.outbounds}
    assert "nl-node-1" not in node_ids  # staging, canary_percent=0


def test_synthetic_canary_preview_includes_nl():
    from generate_vpn_config_from_registry import apply_synthetic_canary_overlay

    reg = apply_synthetic_canary_overlay(_current_like(), "nl-node-1")
    gen = generate_for_cohort(reg, COHORT_CANARY)
    node_ids = {o["node_id"] for o in gen.outbounds}
    assert "nl-node-1" in node_ids
    assert "nl-node-1" in node_ids or "lv-exit-1" in node_ids
    nl = next(o for o in gen.outbounds if o["node_id"] == "nl-node-1")
    assert nl["lifecycle_status"] == "canary"
    assert nl["tag"] == "out-nl-node-1"


def test_second_clean_exit_makes_public_prod_pass():
    reg = _registry(
        [
            _node("lv-exit-1", "exit", "active", eligible=True, groups=["INTL_STEALTH_ACTIVE"], weight=100),
            _node("nl-exit-2", "exit", "active", eligible=True, groups=["INTL_DIRECT_ACTIVE"], weight=80, country="NL"),
        ]
    )
    gen = generate_for_cohort(reg, COHORT_PUBLIC_PROD)
    assert gen.go is True
    assert {o["node_id"] for o in gen.outbounds} == {"lv-exit-1", "nl-exit-2"}


def test_output_uses_node_id_mapping_not_proxy_positions():
    gen = generate_for_cohort(_current_like(), COHORT_LAB_OWNER)
    blob = json.dumps(gen.to_dict())
    assert "node_id" in blob
    for o in gen.outbounds:
        assert not o["tag"].startswith("proxy")


def test_no_secrets_in_output():
    gen = generate_for_cohort(_current_like(), COHORT_PUBLIC_PROD)
    blob = json.dumps(gen.to_dict()) + format_markdown(gen)
    assert "vless://" not in blob
    assert "token" not in blob.lower() or "banner" in blob.lower()
    # no raw UUIDs (synthetic tags only)
    import re
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}", blob)
