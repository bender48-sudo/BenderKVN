#!/usr/bin/env python3
"""Guardrails for Happ routing profile DirectIp (Windows desktop CLIENT-STABILITY).

Happ routing profile is a **separate layer** from subscription templateJson.routing.
``geoip:ru`` in DirectIp classifies all Russian IP addresses as direct — including
Bender relay endpoints hosted in RU. Xray then opens plain TCP via outbound/direct
to relay IPs instead of VLESS proxy outbounds → timeout/reset storm under TUN.

Canonical: docs/INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md
"""
from __future__ import annotations

import re
from typing import Any

from routing_geo_common import PRIVATE_IP_CIDRS

# geoip:ru in Happ DirectIp expands to RU IPs at runtime (relay #1/#2 included).
FORBIDDEN_DIRECT_IP_MARKERS = frozenset({"geoip:ru"})

# Minimum proxy/intl sites that must stay in ProxySites after profile build.
REQUIRED_PROXY_SITE_MARKERS = (
    "instagram",
    "telegram",
    "google",
)

# Sample RU bypass domains that must remain direct via DirectSites (not DirectIp).
REQUIRED_DIRECT_SITE_MARKERS = (
    "ya.ru",
    "vk.com",
)


def _ops_import_relay_ips() -> frozenset[str]:
    import site_urls
    from relay_latency_probe import RELAY2_IP

    ips = {site_urls.RU_RELAY_HOST, RELAY2_IP}
    try:
        from subscription_fetch import LV_IP, NL_IP

        ips.add(LV_IP)
        ips.add(NL_IP)
    except ImportError:
        pass
    return frozenset(ips)


def relay_endpoint_ips() -> frozenset[str]:
    """Public infra IPs that must never appear in Happ routing DirectIp."""
    return _ops_import_relay_ips()


def build_safe_direct_ip() -> list[str]:
    """DirectIp for Happ profile: RFC1918/link-local only — no geoip:ru."""
    return list(PRIVATE_IP_CIDRS)


def _parse_ip_token(token: str) -> str | None:
    token = token.strip()
    if not token or token in FORBIDDEN_DIRECT_IP_MARKERS:
        return None
    if token.startswith("geoip:"):
        return None
    if "/" in token:
        return token.split("/", 1)[0]
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", token):
        return token
    return None


def direct_ip_host_set(profile: dict[str, Any]) -> set[str]:
    hosts: set[str] = set()
    for entry in profile.get("DirectIp") or profile.get("directIp") or []:
        s = str(entry).strip()
        if s in FORBIDDEN_DIRECT_IP_MARKERS:
            continue
        host = _parse_ip_token(s)
        if host:
            hosts.add(host)
    return hosts


def scan_happ_routing_profile(profile: dict[str, Any]) -> list[str]:
    """Return violations (empty = safe for relay/VLESS under TUN)."""
    found: list[str] = []
    direct_ip = profile.get("DirectIp") or profile.get("directIp") or []

    for entry in direct_ip:
        s = str(entry).strip()
        if s in FORBIDDEN_DIRECT_IP_MARKERS:
            found.append(
                f"DirectIp contains {s} — RU relay endpoints match geoip:ru and route direct"
            )

    overlap = direct_ip_host_set(profile) & relay_endpoint_ips()
    if overlap:
        found.append(
            "DirectIp contains Bender infra endpoint(s) "
            f"(count={len(overlap)}) — must use proxy outbounds only"
        )

    proxy_sites = [str(x).lower() for x in (profile.get("ProxySites") or profile.get("proxySites") or [])]
    for needle in REQUIRED_PROXY_SITE_MARKERS:
        if not any(needle in s for s in proxy_sites):
            found.append(f"ProxySites missing {needle!r} — Intl/proxy path regression")

    direct_sites = [str(x).lower() for x in (profile.get("DirectSites") or profile.get("directSites") or [])]
    for needle in REQUIRED_DIRECT_SITE_MARKERS:
        if not any(needle in s for s in direct_sites):
            found.append(f"DirectSites missing {needle!r} — RU bypass regression")

    if profile.get("FallbackTag") == "direct" or profile.get("fallbackTag") == "direct":
        found.append("FallbackTag=direct — forbidden leak to direct outbound")

    return found


def assert_happ_routing_directip_safe(profile: dict[str, Any]) -> None:
    bad = scan_happ_routing_profile(profile)
    if bad:
        raise ValueError(
            "Happ routing DirectIp guard failed:\n  "
            + "\n  ".join(bad)
            + "\nSee docs/INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md"
        )


def main() -> int:
    import argparse
    import json
    import sys
    from pathlib import Path

    _OPS = Path(__file__).resolve().parent
    if str(_OPS) not in sys.path:
        sys.path.insert(0, str(_OPS))

    from generate_happ_routing_link import PROFILE_PATH, build_profile  # noqa: E402

    ap = argparse.ArgumentParser(description="Scan Happ routing profile for DirectIp relay leak")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--profile", type=Path, default=PROFILE_PATH)
    args = ap.parse_args()

    if args.profile.is_file():
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
    else:
        profile = build_profile()

    bad = scan_happ_routing_profile(profile)
    if args.json:
        import json as _json

        print(_json.dumps({"ok": not bad, "violations": bad}, ensure_ascii=False, indent=2))
        return 0 if not bad else 1

    if bad:
        print("FAIL: HAPP_ROUTING_DIRECTIP_GUARD", file=sys.stderr)
        for v in bad:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("HAPP_ROUTING_DIRECTIP_GUARD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
