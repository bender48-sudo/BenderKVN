#!/usr/bin/env python3
"""Happ subscription import compatibility diagnostic (Q-VPN-STAB-002/003).

Simulates Happ batch-import heuristics, runs A/B (with vs without xhttp outbounds),
and reports Content-Type + auto-balance sections present in live sub.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import site_urls
from subscription_fetch import (
    HAPP_UA,
    decode_subscription,
    extract_outbounds,
    fetch_url,
    simulate_happ_batch,
    strip_xhttp_outbounds,
    xray_config_root,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
PANEL = site_urls.PANEL_URL
SUB = site_urls.SUB_PUBLIC_ORIGIN


def pick_active_short() -> str:
    resp = fetch_url(
        f"{PANEL}/api/users?limit=20&start=0",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    if resp.status != 200:
        raise SystemExit(f"users HTTP {resp.status}")
    users = json.loads(resp.body).get("response", {}).get("users") or []
    for u in users:
        if u.get("status") in ("ACTIVE", "active"):
            short = u.get("shortUuid") or u.get("subscriptionUuid")
            if short:
                return short
    if users:
        u0 = users[0]
        short = u0.get("shortUuid") or u0.get("subscriptionUuid")
        if short:
            return short
    raise SystemExit("no user with shortUuid")


def print_batch_report(label: str, outbounds: list[dict]) -> dict:
    sim = simulate_happ_batch(outbounds)
    print(f"\n=== {label} ===")
    print(f"outbounds={sim['total']} parseable={sim['parseable']} failed={sim['failed']} xhttp={sim['xhttp_count']}")
    print(f"batch_risk={sim['batch_risk']} (proxy-like tags={sim['proxy_tags']})")
    for row in sim["rows"]:
        if row["protocol"] == "vless" and str(row["tag"]).startswith("proxy"):
            status = "OK" if row["parseable"] else f"FAIL {row['error']}"
            print(f"  {row['tag']:10s} {row['network']:6s} {row['node']:12s} {status}")
    return sim


def main() -> int:
    p = argparse.ArgumentParser(description="Happ import compatibility diagnostic")
    p.add_argument("--short", help="subscription shortUuid (default: first active user)")
    p.add_argument("--json", action="store_true", help="machine-readable summary")
    p.add_argument("--write-ab", type=Path, help="write variant B JSON (no xhttp) for manual Happ import")
    args = p.parse_args()

    short = args.short or pick_active_short()
    sub_url = f"{SUB}/api/sub/{short}"
    sub_resp = fetch_url(sub_url, headers={"User-Agent": HAPP_UA})

    if sub_resp.status != 200:
        print(f"FAIL: sub HTTP {sub_resp.status}", file=sys.stderr)
        return 1

    sub = decode_subscription(sub_resp.body)
    root = xray_config_root(sub)
    outbounds_a = extract_outbounds(sub)

    sub_b = strip_xhttp_outbounds(sub)
    outbounds_b = extract_outbounds(sub_b)

    sim_a = simulate_happ_batch(outbounds_a)
    sim_b = simulate_happ_batch(outbounds_b)

    has_obs = "burstObservatory" in root or "observatory" in root
    routing = root.get("routing") or {}
    bal = routing.get("balancers") if isinstance(routing.get("balancers"), list) else []
    has_least_load = any(
        isinstance(b, dict) and (b.get("strategy") or {}).get("type") == "leastLoad" for b in bal
    )

    if args.write_ab:
        args.write_ab.write_text(json.dumps(sub_b, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote variant B (no xhttp): {args.write_ab}")

    if args.json:
        summary = {
            "short": short,
            "sub_url": sub_url,
            "bytes": len(sub_resp.body),
            "content_type": sub_resp.content_type,
            "content_type_ok": sub_resp.content_type_ok,
            "variant_a": {k: sim_a[k] for k in ("total", "parseable", "failed", "xhttp_count", "batch_risk")},
            "variant_b": {k: sim_b[k] for k in ("total", "parseable", "failed", "xhttp_count", "batch_risk")},
            "burst_observatory": has_obs,
            "least_load_balancer": has_least_load,
            "recommendation": "",
        }
        if sim_a["batch_risk"] == "HIGH" and sim_b["batch_risk"] == "LOW":
            summary["recommendation"] = "Deploy Happ-only xhttp filter (Q-VPN-STAB-005); xhttp likely causes batch failure"
        elif not sub_resp.content_type_ok:
            summary["recommendation"] = "Fix Content-Type header (Q-VPN-STAB-006) before template changes"
        else:
            summary["recommendation"] = "Investigate non-xhttp batch failure causes"
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if sim_a["batch_risk"] == "HIGH" else 0

    print(f"sub_url: {sub_url}")
    print(f"Happ GET HTTP {sub_resp.status}, {len(sub_resp.body)} bytes")
    print(f"Content-Type: {sub_resp.content_type or '(missing)'}")
    if not sub_resp.content_type_ok:
        print("WARN: Content-Type is not application/json")
    print(f"remarks: {root.get('remarks')!r}")
    print(f"burstObservatory: {'yes' if has_obs else 'NO'}")
    print(f"leastLoad balancer: {'yes' if has_least_load else 'NO'}")

    print_batch_report("Variant A (live sub)", outbounds_a)
    print_batch_report("Variant B (no xhttp outbounds)", outbounds_b)

    print("\n=== A/B verdict ===")
    if sim_a["batch_risk"] == "HIGH" and sim_b["batch_risk"] == "LOW":
        print("LIKELY ROOT CAUSE: xhttp outbounds break Happ batch-import.")
        print("Product fix: Q-VPN-STAB-005 (Happ UA filter), NOT full template removal.")
        print(f"Expected Happ batch count after fix: ~{sim_b['parseable']} parseable proxy outbounds")
    elif not sub_resp.content_type_ok:
        print("Content-Type may contribute; fix Q-VPN-STAB-006 first.")
    else:
        print("xhttp alone does not explain batch risk — check Happ version / JSON shape.")

    return 1 if sim_a["batch_risk"] == "HIGH" else 0


if __name__ == "__main__":
    raise SystemExit(main())
