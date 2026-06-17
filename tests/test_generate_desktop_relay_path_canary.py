"""Tests for ops/generate_desktop_relay_path_canary.py — owner/staging only, redacted."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import RELAY1_SELECTOR, RELAY2_SELECTOR  # noqa: E402
from generate_desktop_relay_path_canary import (  # noqa: E402
    build_canary_plan,
    format_markdown,
)
from vpn_node_selector import load_validated_registry  # noqa: E402


def _plan():
    return build_canary_plan(load_validated_registry())


def test_canary_excludes_bad_keeps_healthy():
    plan = _plan()
    assert plan["bad_path"]["endpoint_token"] == "ep_20e413bd:443"
    assert plan["healthy_path"]["endpoint_token"] == "ep_d1a601f6:443"
    assert plan["bad_path"]["exclude_outbounds"] == list(RELAY1_SELECTOR)
    assert plan["healthy_path"]["keep_outbounds"] == list(RELAY2_SELECTOR)
    # excluded and kept outbound sets must not overlap
    assert not set(plan["bad_path"]["exclude_outbounds"]) & set(
        plan["healthy_path"]["keep_outbounds"]
    )


def test_canary_does_not_change_production_default():
    plan = _plan()
    assert plan["production_default_changed"] is False
    assert plan["owner_only"] is True
    assert plan["do_not_refresh"] is True


def test_canary_reflects_registry_incident_state():
    plan = _plan()
    assert plan["bad_path"]["node_id"] == "ru-relay-1"
    assert plan["bad_path"]["registry_incident"] is True
    assert plan["bad_path"]["exclude_from_desktop_canary"] is True
    assert plan["healthy_path"]["node_id"] == "ru-relay-2"
    assert plan["healthy_path"]["desktop_canary_path"] is True


def test_canary_pins_both_balancers_and_has_rollback():
    plan = _plan()
    assert "Intl_Direct" in plan["pin_balancers"]
    assert "Intl_Stealth" in plan["pin_balancers"]
    assert plan["rollback_instructions"]
    assert plan["build_tool"] == "ops/generate_happ_relay2_lab_profile.py"


def test_markdown_has_no_raw_ip_and_uses_tokens():
    md = format_markdown(_plan())
    assert "ep_20e413bd:443" in md
    assert "ep_d1a601f6:443" in md
    # crude raw-IPv4 leak check (token hashes contain no dotted-quad)
    import re

    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", md)
