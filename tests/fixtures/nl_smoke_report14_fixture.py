"""Synthetic report(14)-class NL smoke zip for tests.

Mirrors owner report(14): active profile = NL Split Stealth Canary, Happ
external routing overlay OFF, TUN healthy, DNS set, no relay1, no fragment,
Telegram/relay2 stealth alive, normal RU/direct-bypass sites OK, blocked
intl sites failed, NL direct endpoint reset storm (~611 errors).
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

PROFILE_LABEL_SPLIT_STEALTH = "BenderVPN NL Split Stealth Canary — owner only"

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
                {"domain": ["geosite:telegram", "geosite:instagram"], "balancerTag": "Intl_Stealth"},
                {
                    "domain": ["geosite:google", "geosite:youtube", "geosite:twitter", "x.com", "openai.com"],
                    "balancerTag": "Intl_Direct",
                },
                {"domain": ["yandex.ru", "vk.com"], "outboundTag": "direct"},
                {"balancerTag": "Intl_Direct", "network": "tcp,udp"},
            ],
        },
        "dns": {"servers": ["1.1.1.1"], "queryStrategy": "UseIP"},
        "inbounds": [{"protocol": "socks", "port": 10808, "listen": "127.0.0.1"}],
    }


def _nl_direct_reset_storm(lines: int = 611) -> str:
    rows = [
        "[01.06 01:04:01] INFO Tun started up in 1450ms",
        "[01.06 01:04:02] INFO DNS 1.1.1.1 set successfully",
        "[01.06 01:04:03] INFO interface UP after 1200ms",
        "[01.06 01:04:30] INFO opening connection to telegram.org via Intl_Stealth",
        "[01.06 01:04:45] INFO Telegram loading chats (stealth alive)",
        "[01.06 01:04:50] INFO yandex.ru loaded ok (direct bypass)",
        "[01.06 01:05:10] ERROR google.com site did not load (blocked NL path)",
        "[01.06 01:05:12] ERROR youtube blocked site fail reset",
    ]
    for i in range(lines):
        rows.append(
            f"[01.06 01:0{i % 10}:00] ERROR connection download closed: "
            f"raw-read tcp 172.16.0.2:26531->{NL_DIRECT_IP}:443: "
            "connection reset by peer"
        )
    return "\n".join(rows)


def build_report14_zip() -> bytes:
    cfg = _split_stealth_cfg()
    sel = json.dumps({"selected": {"name": PROFILE_LABEL_SPLIT_STEALTH, "type": "tun", "config": cfg}})
    settings = json.dumps(
        {
            "Preferences": {
                "AdvancedSettings": {"tun": "true", "systemProxy": "false"},
                "TunnelSettings": {
                    "Routing": {"selectedRoutingRule": "", "useRouting": "false"},
                },
            },
        }
    )
    routing = json.dumps({"routingEnabled": False, "activeProfile": None})
    app_log = "\n".join(
        [
            "[01.06 01:04:00] INFO Connecting BenderVPN NL Split Stealth",
            "[01.06 01:04:45] INFO Telegram loading chats (stealth alive)",
            "[01.06 01:04:50] INFO yandex.ru opened ok",
            "[01.06 01:05:10] ERROR google.com site did not load",
            "[01.06 01:05:12] ERROR blocked site youtube fail",
        ]
    )
    files = {
        "report/versions.txt": "Happ test fixture report14",
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


def write_report14_fixture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_report14_zip())
    return path
