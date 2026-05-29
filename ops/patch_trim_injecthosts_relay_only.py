#!/usr/bin/env python3
"""Trim injectHosts to relay-only (6) so Happ ping matches real traffic path.

Symptom: speedtest ~77ms via relay catch-all, but Happ shows 400–988ms because
it TCP-pings every outbound in the sub — including LV direct (×4) and NL (×4)
that are not used for catch-all/TG anymore.

After patch (gen+1):
  - injectHosts: 6 relay hosts only (relay#1 ×3 + relay#2 ×3)
  - Intl_Direct + catch-all: proxy..proxy-6 (all relay)
  - Remove DNS_LV / Super_Balancer / port-53 rule (Happ uses DoH; relay blocks :53)

Usage:
    python ops/patch_trim_injecthosts_relay_only.py
    python ops/patch_trim_injecthosts_relay_only.py --apply
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import time
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

RELAY1_IP = site_urls.RU_RELAY_HOST
RELAY2_IP = "46.173.28.252"
RELAY_LV_PORT = 443
INTL_TAG = "Intl_Direct"
DROP_BALANCERS = ("Super_Balancer", "DNS_LV")


def relay_only_selector(n: int) -> list[str]:
    if n <= 0:
        return []
    tags = ["proxy"]
    for i in range(2, n + 1):
        tags.append(f"proxy-{i}")
    return tags


def is_relay_lv_host(host: dict) -> bool:
    addr = str(host.get("address") or host.get("host") or "")
    try:
        port = int(host.get("port") or host.get("inboundPort") or 0)
    except (TypeError, ValueError):
        return False
    if port != RELAY_LV_PORT:
        return False
    if addr not in (RELAY1_IP, RELAY2_IP):
        return False
    remark = str(host.get("remark") or "").lower()
    if "nl" in remark and "9443" in remark:
        return False
    if port == 9443:
        return False
    return "relay" in remark or addr in (RELAY1_IP, RELAY2_IP)


def pick_relay_uuids(c: PanelClient, inject_vals: list[str]) -> list[str]:
    by_uuid = {str(h.get("uuid") or ""): h for h in c.get_or_raise("/api/hosts")["response"]}
    relay1: list[tuple[str, str]] = []
    relay2: list[tuple[str, str]] = []
    for uid in inject_vals:
        h = by_uuid.get(uid)
        if not h or not is_relay_lv_host(h):
            continue
        addr = str(h.get("address") or "")
        item = (uid, str(h.get("remark") or uid))
        if addr == RELAY1_IP:
            relay1.append(item)
        elif addr == RELAY2_IP:
            relay2.append(item)
    relay1.sort(key=lambda x: x[1])
    relay2.sort(key=lambda x: x[1])
    picked = [uid for uid, _ in relay1] + [uid for uid, _ in relay2]
    return picked


def apply_patch(doc: dict, relay_uuids: list[str]) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = [str(x) for x in (sel.get("values") or [])]
    after = list(relay_uuids)
    if before != after:
        sel["values"] = after
        log.append(f"injectHosts {len(before)} -> {len(after)} (relay-only)")
        changed = True

    routing = doc.setdefault("routing", {})
    balancers: list[dict] = routing.setdefault("balancers", [])
    relay_sel = relay_only_selector(len(after))
    if not relay_sel:
        log.append("ERROR: no relay hosts to keep")
        return False, log

    new_balancers: list[dict] = []
    for b in balancers:
        if b.get("tag") in DROP_BALANCERS:
            log.append(f"removed balancer {b.get('tag')}")
            changed = True
            continue
        if b.get("tag") == INTL_TAG:
            old = list(b.get("selector") or [])
            if old != relay_sel:
                b["selector"] = list(relay_sel)
                log.append(f"{INTL_TAG}: {len(old)} -> {len(relay_sel)} relay tags")
                changed = True
        new_balancers.append(b)
    routing["balancers"] = new_balancers

    if not any(b.get("tag") == INTL_TAG for b in new_balancers):
        new_balancers.append(
            {"tag": INTL_TAG, "selector": list(relay_sel), "strategy": {"type": "random"}}
        )
        log.append(f"added {INTL_TAG} relay×{len(relay_sel)}")
        changed = True

    rules: list[dict] = routing.setdefault("rules", [])
    new_rules: list[dict] = []
    for r in rules:
        if r.get("balancerTag") in DROP_BALANCERS:
            log.append(f"removed rule → {r.get('balancerTag')}")
            changed = True
            continue
        if r.get("balancerTag") == "DNS_LV" or (
            str(r.get("port") or "") == "53" and r.get("balancerTag")
        ):
            log.append("removed DNS :53 rule (DoH; relay-only sub)")
            changed = True
            continue
        new_rules.append(r)
    routing["rules"] = new_rules

    catch_idx = next(
        (i for i, r in enumerate(new_rules) if r.get("network") == "tcp,udp" and r.get("balancerTag")),
        None,
    )
    if catch_idx is not None:
        if new_rules[catch_idx].get("balancerTag") != INTL_TAG:
            new_rules[catch_idx]["balancerTag"] = INTL_TAG
            log.append(f"catch-all → {INTL_TAG}")
            changed = True
        if list(new_balancers[[b.get("tag") for b in new_balancers].index(INTL_TAG)].get("selector") or []) != relay_sel:
            pass  # already set above
    else:
        new_rules.append({"type": "field", "network": "tcp,udp", "balancerTag": INTL_TAG})
        log.append("appended catch-all → Intl_Direct")
        changed = True

    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    inject_vals = [
        str(x) for x in tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"].get("values") or []
    ]
    relay_uuids = pick_relay_uuids(c, inject_vals)
    if len(relay_uuids) < 6:
        print(f"WARN: expected 6 relay UUIDs, got {len(relay_uuids)}", file=sys.stderr)
    print(f"relay-only injectHosts ({len(relay_uuids)}):")
    by_uuid = {str(h.get("uuid") or ""): h for h in c.get_or_raise("/api/hosts")["response"]}
    for uid in relay_uuids:
        h = by_uuid.get(uid, {})
        print(f"  {uid}  {h.get('remark')}  {h.get('address')}:{h.get('port')}")

    doc = copy.deepcopy(tpl["templateJson"])
    changed, log = apply_patch(doc, relay_uuids)
    for line in log:
        print(line)
    if not changed:
        print("OK: already relay-only injectHosts")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_trim_injecthosts_relay_only.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-relay-only-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    tpl["templateJson"] = doc
    minimal = {
        "uuid": tpl.get("uuid") or args.template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}: {body!s}"[:400], file=sys.stderr)
        return 1
    after_template_patch("patch_trim_injecthosts_relay_only")
    print("Applied relay-only injectHosts. Refresh Happ sub — ping should ~relay RTT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
