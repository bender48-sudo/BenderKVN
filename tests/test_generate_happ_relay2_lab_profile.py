"""Tests for ops/generate_happ_relay2_lab_profile.py (owner-only lab, no prod)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_OPS = ROOT / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG, RELAY2_SELECTOR  # noqa: E402
from generate_happ_relay2_lab_profile import (  # noqa: E402
    build_relay2_lab_profile,
    validate_relay2_lab_profile,
)
from relay_latency_probe import RELAY1_IP, RELAY2_IP  # noqa: E402


def _vless(tag: str, addr: str, port: int = 443) -> dict:
    return {
        "tag": tag,
        "protocol": "vless",
        "settings": {"vnext": [{"address": addr, "port": port, "users": [{"id": "00000000-0000-0000-0000-000000000001"}]}]},
        "streamSettings": {"network": "tcp", "security": "reality"},
    }


def _candidate_d_fixture(*, stealth_split: bool = False) -> dict:
    outbounds = [
        _vless("proxy", RELAY1_IP, 443),
        _vless("proxy-2", RELAY1_IP, 8443),
        _vless("proxy-3", RELAY1_IP, 9443),
        _vless("proxy-4", RELAY2_IP, 443),
        _vless("proxy-5", RELAY2_IP, 8443),
        _vless("proxy-6", RELAY2_IP, 9443),
        _vless("proxy-7", "91.90.192.17", 443),
        {"tag": "direct", "protocol": "freedom"},
        {"tag": "block", "protocol": "blackhole"},
    ]
    intl_sel = ["proxy", "proxy-2", "proxy-3", "proxy-4", "proxy-5", "proxy-6", "proxy-7"] if stealth_split else [
        "proxy",
        "proxy-2",
        "proxy-3",
        "proxy-4",
        "proxy-5",
        "proxy-6",
    ]
    rules = [
        {"type": "field", "ip": ["149.154.0.0/16"], "balancerTag": INTL_STEALTH_BALANCER_TAG},
        {"type": "field", "domain": ["geosite:telegram"], "balancerTag": INTL_STEALTH_BALANCER_TAG},
        {"type": "field", "network": "tcp,udp", "balancerTag": INTL_BALANCER_TAG},
        {"type": "field", "ip": [f"{RELAY1_IP}/32", f"{RELAY2_IP}/32"], "outboundTag": "direct"},
    ]
    return {
        "remarks": "BenderVPN Auto",
        "outbounds": outbounds,
        "routing": {
            "balancers": [
                {
                    "tag": INTL_STEALTH_BALANCER_TAG,
                    "selector": ["proxy", "proxy-2", "proxy-3", "proxy-4", "proxy-5", "proxy-6"],
                    "strategy": {"type": "random"},
                },
                {
                    "tag": INTL_BALANCER_TAG,
                    "selector": intl_sel,
                    "strategy": {"type": "random"},
                },
            ],
            "rules": rules,
        },
        "policy": {"levels": {"0": {"uplinkOnly": 30, "downlinkOnly": 30}}},
    }


def test_build_relay2_lab_strips_relay1_and_nl():
    lab = build_relay2_lab_profile(_candidate_d_fixture(stealth_split=True))
    tags = [o["tag"] for o in lab["outbounds"] if o.get("protocol") == "vless"]
    assert tags == list(RELAY2_SELECTOR)
    assert validate_relay2_lab_profile(lab) == []
    for ob in lab["outbounds"]:
        if ob.get("protocol") != "vless":
            continue
        addr = ob["settings"]["vnext"][0]["address"]
        assert addr == RELAY2_IP
        assert addr != RELAY1_IP


def test_build_relay2_lab_pins_both_balancers():
    lab = build_relay2_lab_profile(_candidate_d_fixture())
    bal = {b["tag"]: b for b in lab["routing"]["balancers"]}
    assert list(bal[INTL_BALANCER_TAG]["selector"]) == list(RELAY2_SELECTOR)
    assert list(bal[INTL_STEALTH_BALANCER_TAG]["selector"]) == list(RELAY2_SELECTOR)


def test_build_relay2_lab_single_outbound():
    lab = build_relay2_lab_profile(_candidate_d_fixture(), single=True)
    assert validate_relay2_lab_profile(lab, single=True) == []
    proxy_tags = [o["tag"] for o in lab["outbounds"] if o.get("protocol") == "vless"]
    assert proxy_tags == ["proxy-4"]


def test_relay2_lab_removes_relay1_direct_rule():
    lab = build_relay2_lab_profile(_candidate_d_fixture())
    direct_rules = [
        r for r in lab["routing"]["rules"] if r.get("outboundTag") == "direct" and r.get("ip")
    ]
    assert direct_rules
    joined = " ".join(str(ip) for r in direct_rules for ip in r["ip"])
    assert RELAY2_IP in joined
    assert RELAY1_IP not in joined


def test_stealth_rules_preserved():
    lab = build_relay2_lab_profile(_candidate_d_fixture())
    stealth = [r for r in lab["routing"]["rules"] if r.get("balancerTag") == INTL_STEALTH_BALANCER_TAG]
    assert len(stealth) >= 2
