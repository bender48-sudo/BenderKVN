"""Tests for Happ routing DirectIp guard — no secrets."""
from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from generate_happ_routing_link import build_profile  # noqa: E402
from happ_routing_directip_guard import (  # noqa: E402
    assert_happ_routing_directip_safe,
    build_safe_direct_ip,
    direct_ip_host_set,
    relay_endpoint_ips,
    scan_happ_routing_profile,
)
from routing_geo_common import PRIVATE_IP_CIDRS  # noqa: E402


def _base_profile(**overrides):
    p = {
        "Name": "BenderVPN RU",
        "DirectIp": list(build_safe_direct_ip()),
        "DirectSites": ["regexp:.*\\.ru$", "domain:ya.ru", "domain:vk.com"],
        "ProxySites": [
            "geosite:instagram",
            "geosite:telegram",
            "geosite:google",
        ],
    }
    p.update(overrides)
    return p


def test_relay1_not_in_direct_ip():
    profile = build_profile()
    overlap = direct_ip_host_set(profile) & relay_endpoint_ips()
    assert not overlap


def test_relay2_not_in_direct_ip():
    profile = build_profile()
    ips = relay_endpoint_ips()
    assert len(ips) >= 2
    assert not (direct_ip_host_set(profile) & ips)


def test_geoip_ru_forbidden_in_direct_ip():
    bad = scan_happ_routing_profile(_base_profile(DirectIp=["geoip:ru", *PRIVATE_IP_CIDRS]))
    assert any("geoip:ru" in v for v in bad)


def test_explicit_relay_ip_forbidden():
    ips = relay_endpoint_ips()
    relay_ip = next(iter(ips))
    bad = scan_happ_routing_profile(_base_profile(DirectIp=[f"{relay_ip}/32", *PRIVATE_IP_CIDRS]))
    assert any("infra endpoint" in v for v in bad)


def test_build_profile_passes_guard():
    profile = build_profile()
    assert_happ_routing_directip_safe(profile)
    assert "geoip:ru" not in profile["DirectIp"]


def test_proxy_sites_include_social_targets():
    profile = build_profile()
    joined = " ".join(profile["ProxySites"]).lower()
    assert "instagram" in joined
    assert "telegram" in joined


def test_direct_sites_include_ru_bypass():
    profile = build_profile()
    joined = " ".join(profile["DirectSites"]).lower()
    assert "ya.ru" in joined
    assert "vk.com" in joined


def test_no_fallback_direct():
    bad = scan_happ_routing_profile(_base_profile(FallbackTag="direct"))
    assert any("FallbackTag" in v for v in bad)
