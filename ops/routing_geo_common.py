"""Shared private-network CIDRs for routing (no geoip.dat PRIVATE section required)."""
from __future__ import annotations

# Same list as Happ routing profile (generate_happ_routing_link / happ_routing_profile_ru.json).
PRIVATE_IP_CIDRS: tuple[str, ...] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "224.0.0.0/4",
    "255.255.255.255",
)


def expand_geoip_private(ip_list: list[str] | None) -> tuple[list[str], bool]:
    """Replace ``geoip:private`` with explicit CIDRs. Returns (new_list, changed)."""
    if not ip_list:
        return [], False
    if "geoip:private" not in ip_list:
        return list(ip_list), False
    out: list[str] = []
    for item in ip_list:
        if item == "geoip:private":
            out.extend(PRIVATE_IP_CIDRS)
        else:
            out.append(item)
    # preserve order, drop duplicate CIDRs
    seen: set[str] = set()
    deduped: list[str] = []
    for c in out:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return deduped, True


def routing_rules_use_geoip_private(rules: list[dict]) -> bool:
    for r in rules:
        ips = r.get("ip") or []
        if "geoip:private" in ips:
            return True
    return False
