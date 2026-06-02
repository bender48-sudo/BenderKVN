"""VPN-AUD-230: split DNS config for Xray subscription template.

RU domains → system DNS (localhost). Intl → DoH (Google + Cloudflare).

Happ/sing-box: **NO geosite:** matchers in dns.servers — bundled geosite.dat
often lacks RU/geolocation categories → core fails to start. Use regexp + FQDN only.

Does NOT use routing port-53→direct (gen=30 regression).
"""
from __future__ import annotations

from typing import Any

# regexp only — safe without geosite.dat RU section (Happ crash gen=39).
RU_DNS_DOMAIN_MATCHERS: list[str] = [
    "regexp:.*\\.ru$",
    "regexp:.*\\.xn--p1ai$",
    "regexp:.*\\.xn--p1acf$",
    "regexp:.*\\.xn--p1ag$",
]

# High-traffic .com RU services (same as routing EXTRA_DIRECT_DOMAINS subset).
RU_DNS_EXTRA_FQDN: list[str] = [
    "vk.com",
    "yandex.com",
    "yandex.net",
    "sberbank.com",
    "tinkoff.com",
    "tbank.com",
    "gosuslugi.com",
    "ozon.com",
    "avito.com",
]

INTL_DOH_DOMAINS: list[str] = [
    "domain:telegram.org",
    "domain:instagram.com",
    "domain:facebook.com",
    "domain:twitter.com",
    "domain:x.com",
    "domain:youtube.com",
    "domain:google.com",
    "domain:googleapis.com",
    "domain:gstatic.com",
    "domain:whatsapp.com",
    "domain:openai.com",
]

INTL_DOH_SERVERS: list[dict[str, Any]] = [
    {
        "address": "https://dns.google/dns-query",
        "domains": list(INTL_DOH_DOMAINS),
        "skipFallback": True,
    },
    {
        "address": "https://cloudflare-dns.com/dns-query",
        "domains": list(INTL_DOH_DOMAINS),
        "skipFallback": True,
    },
]

RU_LOCALHOST_SERVER: dict[str, Any] = {
    "address": "localhost",
    "domains": list(RU_DNS_DOMAIN_MATCHERS) + list(RU_DNS_EXTRA_FQDN),
    "skipFallback": True,
}


def build_split_dns_config() -> dict[str, Any]:
    """Canonical split DNS block for templateJson.dns (Happ-safe, no geosite)."""
    return {
        "servers": INTL_DOH_SERVERS + [RU_LOCALHOST_SERVER, "localhost"],
        "queryStrategy": "UseIP",
        "disableCache": False,
        "tag": "dns-split",
    }


def _has_geosite_in_dns(dns: dict) -> bool:
    for s in dns.get("servers") or []:
        if not isinstance(s, dict):
            continue
        for d in s.get("domains") or []:
            if isinstance(d, str) and d.startswith("geosite:"):
                return True
    return False


def verify_dns_split_config(doc: dict) -> list[str]:
    """Return human-readable errors; empty = OK."""
    errors: list[str] = []
    dns = doc.get("dns")
    if not dns:
        return errors  # absent = OK (Super catch-all)
    if _has_geosite_in_dns(dns):
        errors.append("dns.servers uses geosite: — Happ may fail (missing RU in geosite.dat)")
    if dns.get("queryStrategy") != "UseIP":
        errors.append(f"dns.queryStrategy={dns.get('queryStrategy')!r} want UseIP")
    servers = dns.get("servers") or []
    doh_addrs = [
        str(s.get("address"))
        for s in servers
        if isinstance(s, dict) and str(s.get("address", "")).startswith("https://")
    ]
    if len(doh_addrs) < 1:
        errors.append("dns.servers missing DoH entry (https://…)")
    ru_local = [
        s
        for s in servers
        if isinstance(s, dict)
        and s.get("address") == "localhost"
        and any("regexp:" in str(d) for d in (s.get("domains") or []))
    ]
    if not ru_local:
        errors.append("dns.servers missing localhost+regexp.ru entry for RU split")
    return errors
