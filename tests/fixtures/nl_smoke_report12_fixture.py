"""Synthetic report(12)-class invalid NL Direct Basic smoke zip for tests."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

PROFILE_LABEL_LEGACY = "BenderVPN NL Independent Exit Canary — owner only"


def _legacy_split_stealth_cfg() -> dict:
    proxies = [f"proxy-{i}" if i > 1 else "proxy" for i in range(1, 7)]
    outbounds = []
    for i, tag in enumerate(proxies, start=1):
        addr = "203.0.113.20" if i >= 4 else "203.0.113.10"
        outbounds.append(
            {
                "tag": tag,
                "protocol": "vless",
                "settings": {"vnext": [{"address": addr, "port": 443}]},
            }
        )
    outbounds += [{"tag": "direct", "protocol": "freedom"}, {"tag": "block", "protocol": "blackhole"}]
    return {
        "remarks": PROFILE_LABEL_LEGACY,
        "outbounds": outbounds,
        "routing": {
            "balancers": [
                {"tag": "Intl_Direct", "selector": ["proxy"], "strategy": {"type": "random"}},
                {"tag": "Intl_Stealth", "selector": ["proxy-4", "proxy-5", "proxy-6"], "strategy": {"type": "random"}},
            ],
            "rules": [
                {"domain": ["geosite:google"], "balancerTag": "Intl_Stealth"},
                {"domain": ["geosite:telegram"], "balancerTag": "Intl_Stealth"},
                {"balancerTag": "Intl_Direct", "network": "tcp,udp"},
            ],
        },
        "dns": {"servers": ["1.1.1.1"], "queryStrategy": "UseIP"},
        "inbounds": [{"protocol": "socks", "port": 10808, "listen": "127.0.0.1"}],
    }


def _error_tun_log(lines: int = 700) -> str:
    rows = [
        "[01.06 12:00:01] INFO Tun started up in 1500ms",
        "[01.06 12:00:02] INFO DNS 1.1.1.1 set successfully",
        "[01.06 12:00:03] INFO interface UP after 1200ms",
    ]
    for i in range(lines):
        rows.append(
            f"[01.06 12:0{i % 10}:00] ERROR connection download closed: "
            f"raw-read tcp 172.16.0.2:26531->203.0.113.20:443: forcibly closed by the remote host"
        )
    rows.append("[01.06 12:01:30] INFO opening connection to telegram.org via outbound")
    return "\n".join(rows)


def build_report12_invalid_zip() -> bytes:
    cfg = _legacy_split_stealth_cfg()
    sel = json.dumps({"selected": {"name": PROFILE_LABEL_LEGACY, "type": "tun", "config": cfg}})
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
        {
            "routingEnabled": True,
            "activeProfile": {"name": "BenderVPN RU", "directIp": ["10.0.0.0/8"]},
        }
    )
    app_log = "\n".join(
        [
            "[01.06 12:00:00] INFO Connecting BenderVPN",
            "[01.06 12:00:01] INFO Tun started up in 1500ms",
            "[01.06 12:00:45] INFO User opened Telegram — loading chats",
            "[01.06 12:01:00] ERROR Telegram connection stalled",
        ]
    )
    files = {
        "report/versions.txt": "Happ test fixture report12-invalid",
        "report/settings.json": settings,
        "report/routing.json": routing,
        "report/selected_server.json": sel,
        "report/application_log.txt": app_log,
        "report/tun_log.txt": _error_tun_log(),
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


def write_report12_fixture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_report12_invalid_zip())
    return path
