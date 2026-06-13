"""Tests for ops/probe_fallback_client_sub.py (no live network)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from probe_fallback_client_sub import (  # noqa: E402
    summarize_happ_cfg,
    summarize_karing_cfg,
    summarize_v2rayn_body,
)


def test_summarize_happ_candidate_d_shape():
    cfg = {
        "outbounds": [{"tag": f"proxy{'-' + str(i) if i else ''}"} for i in range(6)],
        "routing": {
            "balancers": [{"tag": "Intl_Direct"}, {"tag": "Intl_Stealth"}],
            "rules": [
                {"balancerTag": "Intl_Stealth", "domain": ["geosite:telegram"]},
                {"network": "tcp,udp", "balancerTag": "Intl_Direct"},
            ],
        },
    }
    s = summarize_happ_cfg(cfg)
    assert s["proxy_count"] == 6
    assert s["auto_equivalent"] is True
    assert s["candidate_d_shape"] is True
    assert s["fallback_tag_direct"] is False


def test_summarize_karing_stripped():
    cfg = {
        "outbounds": [{"type": "vless", "server": "176.126.162.158", "server_port": 443}],
        "route": {"rules": [{"outbound": "proxy"}]},
    }
    s = summarize_karing_cfg(cfg)
    assert s["proxy_count"] == 1
    assert s["auto_equivalent"] is False
    assert s["endpoints"] == ["LV:443"]


def test_summarize_v2rayn_vless_link_without_secrets():
    body = b"vless://REDACTED-UUID@176.126.162.158:443?type=tcp#node"
    s = summarize_v2rayn_body(body)
    assert s["format"] == "vless_link"
    assert s["proxy_count"] == 1
    assert "176.126.162.158" not in json.dumps(s)
