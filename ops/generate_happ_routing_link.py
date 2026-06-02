#!/usr/bin/env python3
"""Build Happ routing profile + happ:// deeplink for BenderVPN RU split.

Windows Happ ignores subscription embedded routing until a **routing profile**
exists (Settings → Routing). Geofiles in core/ alone are not enough.

Usage:
    python ops/generate_happ_routing_link.py
    python ops/generate_happ_routing_link.py --write-json
    python ops/generate_happ_routing_link.py --open   # Windows: launch deeplink
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from patch_routing_category_ru_leak import PROXY_EXTRA_DOMAINS, PROXY_GEOSITES  # noqa: E402
from ru_bypass_routing import EXTRA_DIRECT_DOMAINS  # noqa: E402

PROFILE_PATH = _OPS / "happ_routing_profile_ru.json"
GEOIP_LOYAL = (
    "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat"
)
GEOSITE_LOYAL = (
    "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"
)

RU_REGEXP_DIRECT = [
    "regexp:.*\\.ru$",
    "regexp:.*\\.xn--p1ai$",
    "regexp:.*\\.xn--p1acf$",
    "regexp:.*\\.xn--p1ag$",
]

PRIVATE_IP_DIRECT = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "224.0.0.0/4",
    "255.255.255.255",
]


def _domain_entries(fqdns: list[str]) -> list[str]:
    out: list[str] = []
    for d in fqdns:
        d = d.strip()
        if not d:
            continue
        out.append(d if d.startswith(("domain:", "regexp:", "geosite:", "full:")) else f"domain:{d}")
    return out


def build_profile(*, use_bundled_geofiles: bool = True) -> dict:
    direct_sites = list(RU_REGEXP_DIRECT) + _domain_entries(list(EXTRA_DIRECT_DOMAINS))
    proxy_sites = list(PROXY_GEOSITES) + _domain_entries(list(PROXY_EXTRA_DOMAINS))
    direct_ip = ["geoip:ru", *PRIVATE_IP_DIRECT]

    base = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    base["DirectSites"] = direct_sites
    base["DirectIp"] = direct_ip
    base["ProxySites"] = proxy_sites
    base["LastUpdated"] = str(int(time.time()))
    # DoU 127.0.0.1 only works inside Xray on the server; on Windows Happ it breaks DNS
    # when no local resolver listens. Use DoH for domestic too (routing still sends RU direct).
    base["DomesticDNSType"] = "DoH"
    base["DomesticDNSDomain"] = "https://dns.google/dns-query"
    base["DomesticDNSIP"] = "8.8.8.8"
    if use_bundled_geofiles:
        base["Geoipurl"] = ""
        base["Geositeurl"] = ""
    else:
        base["Geoipurl"] = GEOIP_LOYAL
        base["Geositeurl"] = GEOSITE_LOYAL
    return base


def profile_to_deeplink(profile: dict, *, activate: bool = True) -> str:
    payload = base64.b64encode(
        json.dumps(profile, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    action = "onadd" if activate else "add"
    return f"happ://routing/{action}/{payload}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-json", action="store_true", help="Refresh happ_routing_profile_ru.json")
    ap.add_argument("--open", action="store_true", help="Open happ:// deeplink (Windows)")
    ap.add_argument(
        "--remote-geofiles",
        action="store_true",
        help="Use Loyalsoldier URLs instead of bundled core geofiles",
    )
    args = ap.parse_args()

    profile = build_profile(use_bundled_geofiles=not args.remote_geofiles)
    link = profile_to_deeplink(profile)

    if args.write_json:
        PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {PROFILE_PATH}")

    print(link)
    print(f"\nDirectSites: {len(profile['DirectSites'])}  ProxySites: {len(profile['ProxySites'])}")

    if args.open:
        subprocess.run(["cmd", "/c", "start", "", link], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
