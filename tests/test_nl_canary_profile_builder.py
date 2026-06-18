"""Tests for ops/nl_canary_profile_builder.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

from nl_canary_profile_builder import (  # noqa: E402
    build_nl_direct_basic_profile,
    build_nl_split_stealth_profile,
    google_routes_via_stealth,
    reality_fragment_outbounds,
    relay1_proxy_tags,
)
from validate_happ_importable_profile import validate_nl_canary_variant  # noqa: E402
from subscription_fetch import NL_IP  # noqa: E402
from relay_latency_probe import RELAY1_IP, RELAY2_IP  # noqa: E402


def _vless(tag: str, addr: str) -> dict:
    return {
        "protocol": "vless",
        "tag": tag,
        "settings": {
            "vnext": [
                {
                    "address": addr,
                    "port": 443,
                    "users": [{"id": "00000000-0000-0000-0000-000000000010"}],
                }
            ]
        },
        "streamSettings": {"network": "tcp"},
    }


def _vless_reality_fragment(tag: str, addr: str) -> dict:
    """NL direct REALITY+vision outbound carrying the breaking sockopt.fragment."""
    ob = _vless(tag, addr)
    ob["settings"]["vnext"][0]["users"][0]["flow"] = "xtls-rprx-vision"
    ob["streamSettings"] = {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "serverName": "www.yandex.ru",
            "publicKey": "PK",
            "shortId": "0011",
            "fingerprint": "chrome",
        },
        "sockopt": {
            "fragment": {"length": "50-100", "packets": "1-3", "interval": "10-20"},
            "tcpNoDelay": True,
        },
    }
    return ob


def _source() -> dict:
    return {
        "outbounds": [
            _vless("proxy-7", NL_IP),
            _vless("proxy-8", NL_IP),
            _vless("proxy-4", RELAY2_IP),
            _vless("proxy-5", RELAY2_IP),
            _vless("proxy-99", RELAY1_IP),
            {"protocol": "freedom", "tag": "direct"},
        ],
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy-99"]},
                {"tag": "Intl_Stealth", "selector": ["proxy-99"]},
            ],
            "rules": [],
        },
    }


def test_direct_basic_filters_relay_outbounds():
    profile = build_nl_direct_basic_profile(_source())
    tags = {o["tag"] for o in profile["outbounds"] if o.get("protocol") == "vless"}
    assert tags == {"proxy-7", "proxy-8"}
    assert relay1_proxy_tags(profile) == []
    assert validate_nl_canary_variant(profile, "direct_basic").ok is True


def test_split_stealth_keeps_relay2_not_relay1():
    profile = build_nl_split_stealth_profile(_source())
    tags = {o["tag"] for o in profile["outbounds"] if o.get("protocol") == "vless"}
    assert tags == {"proxy-4", "proxy-5", "proxy-7", "proxy-8"}
    assert relay1_proxy_tags(profile) == []
    assert google_routes_via_stealth(profile) is False
    assert validate_nl_canary_variant(profile, "split_stealth").ok is True


def _reality_source() -> dict:
    return {
        "outbounds": [
            _vless_reality_fragment("proxy-7", NL_IP),
            _vless_reality_fragment("proxy-8", NL_IP),
            {"protocol": "freedom", "tag": "direct"},
        ],
        "routing": {
            "balancers": [{"tag": "Intl_Direct", "selector": ["proxy-7", "proxy-8"]}],
            "rules": [],
        },
    }


def test_builder_strips_reality_fragment_direct_basic():
    """report(13) root cause: sockopt.fragment on REALITY breaks the NL direct
    handshake. The builder must drop it so the direct exit handshake survives."""
    profile = build_nl_direct_basic_profile(_reality_source())
    assert reality_fragment_outbounds(profile) == []
    for ob in profile["outbounds"]:
        ss = ob.get("streamSettings") or {}
        if ss.get("security") == "reality":
            assert "fragment" not in (ss.get("sockopt") or {})
            assert (ss.get("sockopt") or {}).get("tcpNoDelay") is True
    assert validate_nl_canary_variant(profile, "direct_basic").ok is True


def test_validator_rejects_reality_fragment():
    """A profile that still carries fragment on a REALITY outbound must FAIL."""
    bad = build_nl_direct_basic_profile(_reality_source())
    bad["outbounds"][0]["streamSettings"].setdefault("sockopt", {})["fragment"] = {
        "length": "50-100"
    }
    res = validate_nl_canary_variant(bad, "direct_basic")
    assert res.ok is False
    assert any("fragment" in e.lower() for e in res.errors)
