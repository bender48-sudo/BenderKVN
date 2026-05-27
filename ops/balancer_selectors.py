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

POLICY_UPLINK_ONLY = 30
POLICY_DOWNLINK_ONLY = 30


def verify_ru_multipath_profile(doc: dict) -> list[str]:
    """Return human-readable errors for live/template JSON root."""
    errors: list[str] = []
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}

    for tag in ("Super_Balancer", "Intl_Direct"):
        b = balancers.get(tag)
        if not b:
            errors.append(f"missing balancer {tag}")
            continue
        sel = list(b.get("selector") or [])
        if sel != RU_MULTIPATH_SELECTOR:
            errors.append(f"{tag} selector len={len(sel)} want {len(RU_MULTIPATH_SELECTOR)}")
        if sel == RELAY_LV_ONLY_SELECTOR:
            errors.append(f"{tag} still relay-only SPOF")
        strat = (b.get("strategy") or {}).get("type")
        if strat != "random":
            errors.append(f"{tag} strategy={strat!r} want random")

    lv0 = (doc.get("policy") or {}).get("levels", {}).get("0") or {}
    if lv0.get("uplinkOnly") != POLICY_UPLINK_ONLY:
        errors.append(f"uplinkOnly={lv0.get('uplinkOnly')}")
    if lv0.get("downlinkOnly") != POLICY_DOWNLINK_ONLY:
        errors.append(f"downlinkOnly={lv0.get('downlinkOnly')}")

    if doc.get("burstObservatory") or doc.get("observatory"):
        errors.append("observatory present (deferred — closed-pipe risk on RU)")

    return errors
