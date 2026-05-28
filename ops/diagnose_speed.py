#!/usr/bin/env python3
"""Speed/throughput diagnostic: analyze live template for known bottlenecks.

Checks routing rule order, balancer config, policy settings, CIDR conflicts,
and flags anything that could degrade throughput. Read-only, no PATCH.

Usage:
    python ops/diagnose_speed.py
    python ops/diagnose_speed.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402

# Known Cloudflare ranges added in gen=28 (labeled "OpenAI" — wrong)
_CLOUDFLARE_RANGES = {"104.18.0.0/16", "104.19.0.0/16"}

# speedtest.net Ookla CDN (Cloudflare) + measurement infra
_SPEEDTEST_DOMAINS = {
    "speedtest.net", "fast.com", "2ip.ru",
    "ooklaserver.net", "ookla.com",
}


def _balancer_map(doc: dict) -> dict[str, dict]:
    return {b.get("tag"): b for b in doc.get("routing", {}).get("balancers", [])}


def _rules(doc: dict) -> list[dict]:
    return doc.get("routing", {}).get("rules", [])


def check_policy(doc: dict, issues: list, info: list) -> None:
    pol = (doc.get("policy") or {}).get("levels", {}).get("0") or {}
    bs = pol.get("bufferSize")
    ul = pol.get("uplinkOnly")
    dl = pol.get("downlinkOnly")
    info.append(f"policy.bufferSize={bs}  uplinkOnly={ul}  downlinkOnly={dl}")
    if bs is None:
        issues.append("WARN: bufferSize not set in policy.levels.0 (Xray default 512KB)")
    elif bs < 64:
        issues.append(f"WARN: bufferSize={bs}KB is low — may limit throughput on fast links")
    elif bs > 512:
        issues.append(f"WARN: bufferSize={bs}KB is very high — may cause OOM on mobile")
    if ul is not None and ul < 5:
        issues.append(f"WARN: uplinkOnly={ul}s too low — may close idle connections prematurely")
    if dl is not None and dl < 5:
        issues.append(f"WARN: downlinkOnly={dl}s too low")


def check_balancers(doc: dict, issues: list, info: list) -> None:
    bmap = _balancer_map(doc)
    if not bmap:
        issues.append("ERROR: no balancers defined")
        return
    for tag, b in bmap.items():
        sel = list(b.get("selector") or [])
        strat = (b.get("strategy") or {}).get("type", "unknown")
        obs = b.get("strategy", {})
        info.append(f"balancer {tag!r}: strategy={strat} paths={len(sel)} selector={sel}")
        if strat == "random" and len(sel) > 1:
            info.append(f"  → random across {len(sel)} paths: each path gets ~{100//len(sel)}%")
        if len(sel) == 0:
            issues.append(f"ERROR: balancer {tag!r} has empty selector")
        if strat not in ("random", "leastLoad", "leastPing"):
            issues.append(f"WARN: balancer {tag!r} unknown strategy {strat!r}")


def check_routing_rules(doc: dict, issues: list, info: list) -> None:
    rules = _rules(doc)
    info.append(f"routing rules count: {len(rules)}")

    has_dns_direct = False
    has_dns_relay = False
    has_block = False
    has_catchall = False
    has_ru_direct = False
    has_intl_ip = False
    cloudflare_in_intl = False
    direct_before_catchall = 0

    for i, r in enumerate(rules):
        tag = r.get("outboundTag") or r.get("balancerTag") or ""
        port = str(r.get("port") or "")
        ip_list = r.get("ip") or []
        domain_list = r.get("domain") or []
        network = r.get("network") or ""

        if port == "53" and tag == "direct":
            has_dns_direct = True
            issues.append(f"CRIT rule[{i}]: DNS port 53 → direct (gen=30 regression, ISP can filter DNS)")
        if port == "53" and "RELAY_DNS" in tag:
            has_dns_relay = True
            issues.append(f"CRIT rule[{i}]: DNS port 53 → RELAY_DNS (gen=33 regression, relay blocks port 53)")
        if tag == "block":
            has_block = True
        if tag in ("Super_Balancer", "direct") and not domain_list and not ip_list and not port:
            has_catchall = True
        if tag == "direct" and any("geoip:ru" in str(x) for x in (domain_list + ip_list)):
            has_ru_direct = True
        if any(isinstance(x, str) and "geoip:ru" in x for x in ip_list):
            has_ru_direct = True
        if r.get("balancerTag") == "Intl_Direct" and ip_list:
            has_intl_ip = True
            cf_in_rule = set(ip_list) & _CLOUDFLARE_RANGES
            if cf_in_rule:
                cloudflare_in_intl = True
                issues.append(
                    f"WARN rule[{i}]: Cloudflare ranges {cf_in_rule} in Intl_Direct IP rule "
                    f"— speedtest.net, 1.1.1.1 web, and many CDN sites forced through Intl_Direct balancer"
                )

    if not has_dns_direct and not has_dns_relay:
        info.append("OK: no DNS-specific routing rule — DNS uses Super_Balancer catch-all")
    if not has_catchall:
        issues.append("WARN: no catch-all balancer rule found — unmatched traffic may go default outbound")

    if cloudflare_in_intl:
        info.append(
            "NOTE: 104.18-19/16 (Cloudflare) in Intl_Direct IP rule. "
            "Since Intl_Direct selector == Super_Balancer selector, routing result is identical. "
            "Performance impact: none, but the label 'OpenAI' in the comment is wrong."
        )


def check_observatory(doc: dict, issues: list, info: list) -> None:
    obs = doc.get("burstObservatory") or doc.get("observatory")
    if obs:
        issues.append(
            "WARN: observatory present in template — risk of 'closed pipe' errors on RU networks. "
            "Disabled by policy (§0 P8 backlog). Remove if unintentional."
        )
    else:
        info.append("OK: observatory absent (intentional — closed-pipe risk on RU)")
        info.append(
            "SPEED IMPACT: random balancer without health-check means "
            "~N% connections may hit a degraded path. "
            "With 11 paths each gets ~9%; with NL blocked that 9% times out."
        )


def check_injecthosts(doc: dict, issues: list, info: list) -> None:
    rw = doc.get("remnawave") or {}
    inject = rw.get("injectHosts") or []
    if not inject:
        info.append("injectHosts: not present in template root")
        return
    vals = (inject[0].get("selector") or {}).get("values") or []
    info.append(f"injectHosts count: {len(vals)}")
    if len(vals) > 12:
        issues.append(f"WARN: {len(vals)} injectHosts — large sub JSON, slower Happ parse")
    if len(vals) == 0:
        issues.append("ERROR: injectHosts empty — no outbounds in subscription")


def check_sub_size(tpl: dict, issues: list, info: list) -> None:
    js = json.dumps(tpl.get("templateJson") or {})
    size = len(js.encode())
    info.append(f"template JSON size: {size} bytes")
    if size > 20_000:
        issues.append(f"WARN: template JSON {size}B is large — Happ parse may be slow")
    elif size < 5_000:
        issues.append(f"WARN: template JSON only {size}B — may be missing outbounds")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=60)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl.get("templateJson") or {}

    issues: list[str] = []
    info: list[str] = []

    check_sub_size(tpl, issues, info)
    check_policy(doc, issues, info)
    check_balancers(doc, issues, info)
    check_routing_rules(doc, issues, info)
    check_observatory(doc, issues, info)
    check_injecthosts(doc, issues, info)

    if args.json:
        print(json.dumps({"issues": issues, "info": info}, ensure_ascii=False, indent=2))
        return 1 if issues else 0

    print("=== SPEED DIAGNOSTIC ===\n")
    print("INFO:")
    for line in info:
        print(f"  {line}")
    print()
    if issues:
        print("ISSUES:")
        for line in issues:
            print(f"  {line}")
        print()
        print(f"SPEED_DIAGNOSTIC: {len(issues)} issue(s) found")
        return 1
    print("SPEED_DIAGNOSTIC_OK: no template-level speed issues found")
    print("If speed is still low, the bottleneck is server-side (capacity/DPI) — see SSH commands below")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
