"""Tests for ops/nl_canary_route_classes.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from balancer_selectors import INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG  # noqa: E402
from nl_canary_profile_builder import (  # noqa: E402
    build_nl_direct_basic_profile,
    build_nl_split_stealth_profile,
)
from nl_canary_route_classes import (  # noqa: E402
    ROUTE_CLASS_DIRECT_BYPASS,
    resolve_marker_route,
    validate_route_classes,
)
from relay_latency_probe import RELAY2_IP  # noqa: E402
from subscription_fetch import NL_IP  # noqa: E402
from validate_happ_importable_profile import validate_nl_canary_variant  # noqa: E402


def _vless(tag: str, addr: str) -> dict:
    return {
        "protocol": "vless",
        "tag": tag,
        "settings": {"vnext": [{"address": addr, "port": 443, "users": [{"id": "00000000-0000-0000-0000-000000000010"}]}]},
        "streamSettings": {"network": "tcp"},
    }


def _source() -> dict:
    return {
        "outbounds": [
            _vless("proxy-7", NL_IP),
            _vless("proxy-8", NL_IP),
            _vless("proxy-4", RELAY2_IP),
            _vless("proxy-5", RELAY2_IP),
            {"protocol": "freedom", "tag": "direct"},
        ],
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy-7", "proxy-8"]},
                {"tag": "Intl_Stealth", "selector": ["proxy-4", "proxy-5"]},
            ],
            "rules": [
                {"domain": ["yandex.ru", "vk.com"], "outboundTag": "direct"},
                {"ip": ["geoip:ru"], "outboundTag": "direct"},
            ],
        },
    }


def test_direct_basic_google_routes_nl():
    profile = build_nl_direct_basic_profile(_source())
    assert resolve_marker_route(profile, "geosite:google") == INTL_BALANCER_TAG
    assert resolve_marker_route(profile, "yandex.ru") == "direct"
    assert validate_route_classes(profile, variant="direct_basic") == []
    assert validate_nl_canary_variant(profile, "direct_basic").ok is True


def test_split_stealth_explicit_nl_validation_rule():
    profile = build_nl_split_stealth_profile(_source())
    assert resolve_marker_route(profile, "geosite:google") == INTL_BALANCER_TAG
    assert resolve_marker_route(profile, "x.com") == INTL_BALANCER_TAG
    assert resolve_marker_route(profile, "geosite:telegram") == INTL_STEALTH_BALANCER_TAG
    assert resolve_marker_route(profile, "yandex.ru") == "direct"
    assert validate_route_classes(profile, variant="split_stealth") == []
    assert validate_nl_canary_variant(profile, "split_stealth").ok is True


def test_split_stealth_fails_without_explicit_nl_rule():
    bad = build_nl_split_stealth_profile(_source())
    rules = bad["routing"]["rules"]
    bad["routing"]["rules"] = [r for r in rules if "geosite:google" not in str(r.get("domain"))]
    errors = validate_route_classes(bad, variant="split_stealth")
    assert any("explicit NL_DIRECT_VALIDATION" in e for e in errors)


def test_direct_bypass_not_nl_proof_marker():
    from nl_canary_route_classes import expected_route_class  # noqa: E402

    assert expected_route_class("yandex.ru") == ROUTE_CLASS_DIRECT_BYPASS
    assert expected_route_class("google.com") is not ROUTE_CLASS_DIRECT_BYPASS
