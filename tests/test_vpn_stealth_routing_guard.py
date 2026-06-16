"""Tests for stealth/routing guardrails — VPN-STEALTH-ROUTING-GUARDRAILS-001."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
_ROOT = Path(__file__).resolve().parent.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
)
from happ_routing_directip_guard import scan_happ_routing_profile  # noqa: E402
from vpn_stealth_routing_guard import scan_stealth_routing  # noqa: E402


def _good_doc():
    return {
        "routing": {
            "balancers": [
                {"tag": INTL_STEALTH_BALANCER_TAG, "selector": ["proxy"]},
                {"tag": INTL_BALANCER_TAG, "selector": ["proxy", "proxy-2"]},
            ],
            "rules": [
                {"network": "tcp,udp", "balancerTag": INTL_BALANCER_TAG},
                {"balancerTag": INTL_STEALTH_BALANCER_TAG, "ip": ["geoip:telegram"]},
                {"balancerTag": INTL_STEALTH_BALANCER_TAG, "domain": ["geosite:meta", "geosite:instagram"]},
            ],
        }
    }


def test_good_doc_passes():
    assert scan_stealth_routing(_good_doc()) == []


def test_route_groups_present():
    doc = _good_doc()
    tags = {b["tag"] for b in doc["routing"]["balancers"]}
    assert INTL_STEALTH_BALANCER_TAG in tags and INTL_BALANCER_TAG in tags


def test_stealth_marker_routed_to_general_fails():
    doc = _good_doc()
    doc["routing"]["rules"].append(
        {"balancerTag": INTL_BALANCER_TAG, "domain": ["geosite:telegram"]}
    )
    bad = scan_stealth_routing(doc)
    assert any("telegram" in v and "general" in v for v in bad)


def test_missing_stealth_ip_rule_fails():
    doc = _good_doc()
    doc["routing"]["rules"] = [
        r for r in doc["routing"]["rules"]
        if not (r.get("balancerTag") == INTL_STEALTH_BALANCER_TAG and r.get("ip"))
    ]
    bad = scan_stealth_routing(doc)
    assert any("IP-CIDR" in v for v in bad)


def test_super_balancer_catchall_flagged():
    doc = _good_doc()
    doc["routing"]["balancers"].append({"tag": "Super_Balancer", "selector": ["proxy"]})
    bad = scan_stealth_routing(doc)
    assert any("Super_Balancer" in v for v in bad)


def test_missing_stealth_balancer_fails():
    doc = _good_doc()
    doc["routing"]["balancers"] = [
        b for b in doc["routing"]["balancers"] if b["tag"] != INTL_STEALTH_BALANCER_TAG
    ]
    bad = scan_stealth_routing(doc)
    assert any("missing stealth balancer" in v for v in bad)


def test_real_happ_profile_has_no_geoip_ru_directip_regression():
    """Regression guard on the committed Happ RU routing profile."""
    profile_path = _ROOT / "ops" / "happ_routing_profile_ru.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    bad = scan_happ_routing_profile(profile)
    # The committed profile may legitimately lack some ProxySite markers depending
    # on build, but it must NEVER contain geoip:ru DirectIp or a relay-direct leak.
    leak = [v for v in bad if "geoip:ru" in v or "infra endpoint" in v or "FallbackTag=direct" in v]
    assert leak == [], leak
