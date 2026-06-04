"""Shared balancer selector lists for subscription template patches (Q132-safe).

Do NOT use ``["proxy"]`` on catch-all — random across all 14 injectHosts (~×3 ping).
Do NOT use relay-only ``proxy-5..7`` — three inbounds on one IP (72.56.0.145), no failover.
Exclude ``proxy-12..14`` (RELAY→NL :9443) from default pools — DPI / TG slowness history.
"""

from __future__ import annotations

# injectHosts: proxy..4 LV :443, 5..7 RELAY→LV, 8..11 NL :443, 12..14 RELAY→NL :9443
RU_MULTIPATH_SELECTOR: list[str] = [
    "proxy",
    "proxy-2",
    "proxy-3",
    "proxy-4",
    "proxy-5",
    "proxy-6",
    "proxy-7",
    "proxy-8",
    "proxy-9",
    "proxy-10",
    "proxy-11",
]

RELAY_LV_ONLY_SELECTOR: list[str] = ["proxy-5", "proxy-6", "proxy-7"]

# Q120 / VPN-AUD-201: second RU relay IP (injectHosts proxy-12..14 → relay#2 LV).
RELAY2_OUTBOUND_TAGS: list[str] = ["proxy-12", "proxy-13", "proxy-14"]

# Intl TG/IG/Meta from RU: relay paths only (no LV direct, no NL).
INTL_RELAY_ONLY_SELECTOR: list[str] = RELAY_LV_ONLY_SELECTOR + RELAY2_OUTBOUND_TAGS

# Temporary RU incident profile: LV direct + both relays; NL direct excluded (patch_nl_exclude_temp).
LV_RELAY_SELECTOR: list[str] = [
    "proxy",
    "proxy-2",
    "proxy-3",
    "proxy-4",
    "proxy-5",
    "proxy-6",
    "proxy-7",
    "proxy-12",
    "proxy-13",
    "proxy-14",
]

# Failover when RU relay unreachable (VPN-AUD-202): LV direct only, no relay SPOF paths.
LV_DIRECT_ONLY_SELECTOR: list[str] = [
    "proxy",
    "proxy-2",
    "proxy-3",
    "proxy-4",
]

# Catch-all / DNS / Happ ping: LV direct only (relay blocks outbound :53).
SUPER_LV_DIRECT_SELECTOR: list[str] = list(LV_DIRECT_ONLY_SELECTOR)

RELAY_OUTBOUND_TAGS: list[str] = ["proxy-5", "proxy-6", "proxy-7"] + RELAY2_OUTBOUND_TAGS

# After injectHosts trim to relay-only (gen>=47): tags proxy..proxy-6, all relay.
RELAY6_SELECTOR: list[str] = ["proxy", "proxy-2", "proxy-3", "proxy-4", "proxy-5", "proxy-6"]
RELAY1_SELECTOR: list[str] = ["proxy", "proxy-2", "proxy-3"]
RELAY2_SELECTOR: list[str] = ["proxy-4", "proxy-5", "proxy-6"]

# NL direct :443 (injectHosts positions 7–10 after relay×6).
NL_DIRECT_SELECTOR: list[str] = ["proxy-7", "proxy-8", "proxy-9", "proxy-10"]

# VPN-AUD-220: Intl = relay×6 + NL×4 (NL gated by RU probe; never Super catch-all LV).
INTL_RELAY_NL_SELECTOR: list[str] = RELAY6_SELECTOR + NL_DIRECT_SELECTOR

# VPN-AUD-279: after relay-NL :443 hosts in inject (positions 11–16); Stealth stays relay×6 only.
RELAY_NL443_SELECTOR: list[str] = [
    "proxy-11",
    "proxy-12",
    "proxy-13",
    "proxy-14",
    "proxy-15",
    "proxy-16",
]
INTL_RELAY_NL_443_SELECTOR: list[str] = RELAY6_SELECTOR + NL_DIRECT_SELECTOR + RELAY_NL443_SELECTOR


def relay_n_selector(n: int) -> list[str]:
    if n <= 0:
        return []
    tags = ["proxy"]
    for i in range(2, n + 1):
        tags.append(f"proxy-{i}")
    return tags


DNS_RELAY_BALANCER_TAG = "RELAY_DNS"
INTL_BALANCER_TAG = "Intl_Direct"
INTL_STEALTH_BALANCER_TAG = "Intl_Stealth"
DNS_LV_BALANCER_TAG = "DNS_LV"

POLICY_UPLINK_ONLY = 30
POLICY_DOWNLINK_ONLY = 30


def allowed_relay_only_selectors() -> tuple[list[str], ...]:
    return (RELAY6_SELECTOR, RELAY1_SELECTOR, RELAY2_SELECTOR)


def allowed_intl_relay_selectors() -> tuple[list[str], ...]:
    return allowed_relay_only_selectors() + (INTL_RELAY_NL_SELECTOR, INTL_RELAY_NL_443_SELECTOR)


def is_relay_only_profile(doc: dict) -> bool:
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    intl_b = balancers.get(INTL_BALANCER_TAG)
    if not intl_b or balancers.get("Super_Balancer") or balancers.get(DNS_LV_BALANCER_TAG):
        return False
    intl_sel = list(intl_b.get("selector") or [])
    if intl_sel not in allowed_relay_only_selectors():
        return False
    catch_intl = any(
        r.get("network") == "tcp,udp"
        and r.get("balancerTag") == INTL_BALANCER_TAG
        and not r.get("port")
        for r in (doc.get("routing") or {}).get("rules") or []
    )
    return catch_intl and len(intl_sel) >= 3


def is_stealth_split_relay_nl_443_profile(doc: dict) -> bool:
    if not is_stealth_split_profile(doc):
        return False
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    intl_b = balancers.get(INTL_BALANCER_TAG)
    if not intl_b:
        return False
    return list(intl_b.get("selector") or []) == INTL_RELAY_NL_443_SELECTOR


def is_relay_nl_intl_profile(doc: dict) -> bool:
    if is_stealth_split_profile(doc):
        return False
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    intl_b = balancers.get(INTL_BALANCER_TAG)
    if not intl_b or balancers.get("Super_Balancer") or balancers.get(DNS_LV_BALANCER_TAG):
        return False
    intl_sel = list(intl_b.get("selector") or [])
    if intl_sel != INTL_RELAY_NL_SELECTOR:
        return False
    catch_intl = any(
        r.get("network") == "tcp,udp"
        and r.get("balancerTag") == INTL_BALANCER_TAG
        and not r.get("port")
        for r in (doc.get("routing") or {}).get("rules") or []
    )
    return catch_intl


def _intl_media_rules_use_stealth(rules: list[dict]) -> bool:
    """TG/Meta IP-CIDR + geosite rules must point at Intl_Stealth."""
    ip_ok = domain_ok = False
    for r in rules:
        tag = r.get("balancerTag")
        if tag != INTL_STEALTH_BALANCER_TAG:
            continue
        if r.get("ip"):
            ip_ok = True
        if r.get("domain"):
            domain_ok = True
    return ip_ok and domain_ok


def is_stealth_split_profile(doc: dict) -> bool:
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    stealth_b = balancers.get(INTL_STEALTH_BALANCER_TAG)
    intl_b = balancers.get(INTL_BALANCER_TAG)
    if not stealth_b or not intl_b:
        return False
    if balancers.get("Super_Balancer") or balancers.get(DNS_LV_BALANCER_TAG):
        return False
    stealth_sel = list(stealth_b.get("selector") or [])
    intl_sel = list(intl_b.get("selector") or [])
    if stealth_sel not in allowed_relay_only_selectors():
        return False
    if intl_sel not in allowed_intl_relay_selectors():
        return False
    # VPN-AUD-279: Intl may be relay×6+NL×4+relay-NL×6; Stealth must stay relay-only.
    rules = (doc.get("routing") or {}).get("rules") or []
    catch_fast = any(
        r.get("network") == "tcp,udp"
        and r.get("balancerTag") == INTL_BALANCER_TAG
        and not r.get("port")
        for r in rules
    )
    return catch_fast and _intl_media_rules_use_stealth(rules)


def _accepted_traffic_selectors() -> tuple[list[str], ...]:
    return (
        RU_MULTIPATH_SELECTOR,
        LV_RELAY_SELECTOR,
        INTL_RELAY_ONLY_SELECTOR,
        SUPER_LV_DIRECT_SELECTOR,
        RELAY6_SELECTOR,
        INTL_RELAY_NL_SELECTOR,
        INTL_RELAY_NL_443_SELECTOR,
    )


def verify_ru_multipath_profile(doc: dict) -> list[str]:
    """Return human-readable errors for live/template JSON root."""
    errors: list[str] = []
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    accepted = _accepted_traffic_selectors()
    using_lv_relay_only = False

    super_b = balancers.get("Super_Balancer")
    intl_b = balancers.get("Intl_Direct")
    if not intl_b:
        errors.append("missing balancer Intl_Direct")

    # Relay-only injectHosts (gen>=47): Happ ping = relay RTT only.
    relay_only_ok = False
    relay_nl_ok = False
    stealth_split_ok = False
    if intl_b and not super_b:
        intl_sel = list(intl_b.get("selector") or [])
        catch_intl = any(
            r.get("network") == "tcp,udp"
            and r.get("balancerTag") == INTL_BALANCER_TAG
            and not r.get("port")
            for r in (doc.get("routing") or {}).get("rules") or []
        )
        if (
            intl_sel in allowed_relay_only_selectors()
            and len(intl_sel) >= 3
            and catch_intl
            and not balancers.get(DNS_LV_BALANCER_TAG)
        ):
            relay_only_ok = True
        if is_relay_nl_intl_profile(doc):
            relay_nl_ok = True
        if is_stealth_split_profile(doc) or is_stealth_split_relay_nl_443_profile(doc):
            stealth_split_ok = True

    if not super_b and not relay_only_ok and not relay_nl_ok and not stealth_split_ok:
        errors.append("missing balancer Super_Balancer")

    # Split profile (gen>=45): Super=LV direct (DNS); Intl=relay×2 (TG/IG).
    # Split profile (gen>=46): catch-all→Intl (ping); DNS:53→DNS_LV.
    split_ok = relay_only_ok or relay_nl_ok or stealth_split_ok
    if super_b and intl_b:
        super_sel = list(super_b.get("selector") or [])
        intl_sel = list(intl_b.get("selector") or [])
        dns_b = balancers.get("DNS_LV")
        catch_intl = any(
            r.get("network") == "tcp,udp"
            and r.get("balancerTag") == INTL_BALANCER_TAG
            and not r.get("port")
            for r in (doc.get("routing") or {}).get("rules") or []
        )
        if (
            super_sel == SUPER_LV_DIRECT_SELECTOR
            and intl_sel == INTL_RELAY_ONLY_SELECTOR
            and dns_b
            and list(dns_b.get("selector") or []) == SUPER_LV_DIRECT_SELECTOR
            and catch_intl
        ):
            split_ok = True
        elif super_sel == SUPER_LV_DIRECT_SELECTOR and intl_sel == INTL_RELAY_ONLY_SELECTOR:
            split_ok = True
        elif super_sel == LV_RELAY_SELECTOR and intl_sel == RU_MULTIPATH_SELECTOR:
            split_ok = True
        elif super_sel == intl_sel:
            pass  # uniform profile below
        else:
            errors.append(
                f"split selector mismatch: Super={len(super_sel)} Intl={len(intl_sel)} "
                f"(want Super={len(SUPER_LV_DIRECT_SELECTOR)} Intl={len(INTL_RELAY_ONLY_SELECTOR)})"
            )

    if not split_ok:
        for tag in ("Super_Balancer", "Intl_Direct"):
            b = balancers.get(tag)
            if not b:
                continue
            sel = list(b.get("selector") or [])
            if sel not in accepted:
                errors.append(
                    f"{tag} selector len={len(sel)} want {len(RU_MULTIPATH_SELECTOR)} "
                    f"or {len(LV_RELAY_SELECTOR)} (NL-excluded incident mode)"
                )
            if sel == RELAY_LV_ONLY_SELECTOR:
                errors.append(f"{tag} still relay-only SPOF")
            if sel == LV_RELAY_SELECTOR:
                using_lv_relay_only = True
            strat = (b.get("strategy") or {}).get("type")
            if strat != "random":
                errors.append(f"{tag} strategy={strat!r} want random")
    else:
        using_lv_relay_only = split_ok or any(
            list(balancers.get(t, {}).get("selector") or []) == LV_RELAY_SELECTOR
            for t in ("Super_Balancer", "Intl_Direct")
            if balancers.get(t)
        )
        for tag in ("Super_Balancer", "Intl_Direct"):
            b = balancers.get(tag)
            if b and (b.get("strategy") or {}).get("type") != "random":
                errors.append(f"{tag} strategy must be random")

    rules = (doc.get("routing") or {}).get("rules") or []
    dns_direct = any(
        r.get("outboundTag") == "direct" and str(r.get("port") or "") == "53" for r in rules
    )
    dns_relay = any(
        r.get("balancerTag") == DNS_RELAY_BALANCER_TAG and str(r.get("port") or "") == "53"
        for r in rules
    )
    if dns_direct:
        errors.append("DNS port 53 still routes direct (RU ISP leak)")
    if balancers.get(DNS_RELAY_BALANCER_TAG):
        errors.append(f"{DNS_RELAY_BALANCER_TAG} balancer present (relay blocks outbound :53)")
    if dns_relay:
        errors.append(f"DNS port 53 still uses {DNS_RELAY_BALANCER_TAG} (relay blocks outbound :53)")
    if using_lv_relay_only and not dns_direct and not dns_relay:
        pass  # DNS via Super_Balancer catch-all — expected after patch_remove_dns_relay_rule

    lv0 = (doc.get("policy") or {}).get("levels", {}).get("0") or {}
    if lv0.get("uplinkOnly") != POLICY_UPLINK_ONLY:
        errors.append(f"uplinkOnly={lv0.get('uplinkOnly')}")
    if lv0.get("downlinkOnly") != POLICY_DOWNLINK_ONLY:
        errors.append(f"downlinkOnly={lv0.get('downlinkOnly')}")

    if doc.get("burstObservatory") or doc.get("observatory"):
        errors.append("observatory present (deferred — closed-pipe risk on RU)")

    return errors
