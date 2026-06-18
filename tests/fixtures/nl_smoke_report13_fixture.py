"""Synthetic report(13)-class NL smoke zip for tests.

Mirrors owner report(13): active profile = NL Split Stealth Canary, Happ
external routing overlay (BenderVPN RU) still enabled, TUN healthy, DNS set,
Telegram/relay2 stealth path alive, but NL DIRECT exit endpoint reset storm.
Used to lock in that this is NOT a clean NL acceptance smoke.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

PROFILE_LABEL_SPLIT_STEALTH = "BenderVPN NL Split Stealth Canary — owner only"

# RFC 5737 / RFC 3849 documentation addresses — never real production endpoints.
NL_DIRECT_IP = "203.0.113.17"
RELAY2_IP = "198.51.100.252"


def _split_stealth_cfg() -> dict:
    outbounds = []
    for tag in ("proxy-7", "proxy-8", "proxy-9", "proxy-10"):
        outbounds.append(
            {"tag": tag, "protocol": "vless", "settings": {"vnext": [{"address": NL_DIRECT_IP, "port": 443}]}}
        )
    for tag in ("proxy-4", "proxy-5", "proxy-6"):
        outbounds.append(
            {"tag": tag, "protocol": "vless", "settings": {"vnext": [{"address": RELAY2_IP, "port": 9443}]}}
        )
    outbounds += [{"tag": "direct", "protocol": "freedom"}, {"tag": "block", "protocol": "blackhole"}]
    return {
        "remarks": PROFILE_LABEL_SPLIT_STEALTH,
        "outbounds": outbounds,
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy-7", "proxy-8", "proxy-9", "proxy-10"], "strategy": {"type": "random"}},
                {"tag": "Intl_Stealth", "selector": ["proxy-4", "proxy-5", "proxy-6"], "strategy": {"type": "random"}},
            ],
            "rules": [
                {"ip": ["geoip:telegram"], "balancerTag": "Intl_Stealth"},
                {"domain": ["geosite:telegram"], "balancerTag": "Intl_Stealth"},
                {"balancerTag": "Intl_Direct", "network": "tcp,udp"},
            ],
        },
        "dns": {"servers": ["1.1.1.1"], "queryStrategy": "UseIP"},
        "inbounds": [{"protocol": "socks", "port": 10808, "listen": "127.0.0.1"}],
    }


def _nl_direct_reset_storm(lines: int = 800) -> str:
    rows = [
        "[01.06 12:00:01] INFO Tun started up in 1500ms",
        "[01.06 12:00:02] INFO DNS 1.1.1.1 set successfully",
        "[01.06 12:00:03] INFO interface UP after 1200ms",
        "[01.06 12:00:30] INFO opening connection to telegram.org via Intl_Stealth",
    ]
    for i in range(lines):
        rows.append(
            f"[01.06 12:0{i % 10}:00] ERROR connection download closed: "
            f"raw-read tcp 172.16.0.2:26531->{NL_DIRECT_IP}:443: "
            "connection reset by peer"
        )
    return "\n".join(rows)


def build_report13_zip() -> bytes:
    cfg = _split_stealth_cfg()
    sel = json.dumps({"selected": {"name": PROFILE_LABEL_SPLIT_STEALTH, "type": "tun", "config": cfg}})
    settings = json.dumps(
        {
            "Preferences": {
                "AdvancedSettings": {"tun": "true", "systemProxy": "false"},
                "TunnelSettings": {
                    "Routing": {"selectedRoutingRule": "BenderVPN RU", "useRouting": "true"},
                },
            },
        }
    )
    routing = json.dumps(
        {"routingEnabled": True, "activeProfile": {"name": "BenderVPN RU", "directIp": ["10.0.0.0/8"]}}
    )
    app_log = "\n".join(
        [
            "[01.06 12:00:00] INFO Connecting BenderVPN",
            "[01.06 12:00:45] INFO Telegram loading chats (stealth alive)",
            "[01.06 12:01:10] ERROR google.com site did not load (NL direct reset)",
        ]
    )
    files = {
        "report/versions.txt": "Happ test fixture report13",
        "report/settings.json": settings,
        "report/routing.json": routing,
        "report/selected_server.json": sel,
        "report/application_log.txt": app_log,
        "report/tun_log.txt": _nl_direct_reset_storm(),
        "report/happd.log": "DNS set successfully\ninterface UP\n",
        "report/tasklist.txt": "Telegram.exe\nHapp.exe\n",
        "report/ipconfig all.txt": "happ-tun adapter",
        "report/route print.txt": "0.0.0.0",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def write_report13_fixture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_report13_zip())
    return path
