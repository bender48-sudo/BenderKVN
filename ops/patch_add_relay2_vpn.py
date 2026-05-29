#!/usr/bin/env python3
"""VPN-AUD-201: relay#2 panel hosts + injectHosts + balancer selectors.

Creates 3 LV relay hosts on RELAY2_IP:443 (mirror relay#1 SNIs), appends to
injectHosts (proxy-12..14), sets Super_Balancer + Intl_Direct to LV_RELAY_SELECTOR.

Usage:
    python ops/patch_add_relay2_vpn.py
    python ops/patch_add_relay2_vpn.py --apply
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

from balancer_selectors import LV_RELAY_SELECTOR  # noqa: E402
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

RELAY1_IP = site_urls.RU_RELAY_HOST
RELAY2_IP = "46.173.28.252"
RELAY2_PORT = 443
RELAY1_PORT = 443

SUPER_TAG = "Super_Balancer"
INTL_TAG = "Intl_Direct"


def relay1_lv_hosts(hosts: list[dict]) -> list[dict]:
    out = [
        h
        for h in hosts
        if h.get("address") == RELAY1_IP
        and int(h.get("port") or 0) == RELAY1_PORT
        and "Relay" in (h.get("remark") or "")
    ]
    out.sort(key=lambda x: x.get("remark") or "")
    return out


def create_relay2_host(c: PanelClient, src: dict) -> str:
    remark = (src.get("remark") or "").replace("Relay LV", "Relay2 LV")
    if "Relay2" not in remark:
        remark = remark.replace("Relay ", "Relay2 ", 1)
    body = {
        "remark": remark,
        "address": RELAY2_IP,
        "port": RELAY2_PORT,
        "sni": src.get("sni"),
        "fingerprint": src.get("fingerprint") or "chrome",
        "isDisabled": False,
        "isHidden": True,
        "inbound": copy.deepcopy(src.get("inbound") or {}),
        "nodes": list(src.get("nodes") or []),
        "sockoptParams": copy.deepcopy(src.get("sockoptParams") or {}),
    }
    code, resp = c.post("/api/hosts", body=body)
    if code not in (200, 201):
        raise RuntimeError(f"POST host HTTP {code}: {resp!s}"[:300])
    uuid = resp["response"]["uuid"]
    print(f"created host {uuid} | {remark} | {RELAY2_IP}:{RELAY2_PORT}")
    return uuid


def apply_balancers(doc: dict) -> list[str]:
    log: list[str] = []
    want = list(LV_RELAY_SELECTOR)
    for tag in (SUPER_TAG, INTL_TAG):
        for b in doc.get("routing", {}).get("balancers", []):
            if b.get("tag") != tag:
                continue
            old = list(b.get("selector") or [])
            if old != want:
                b["selector"] = want
                log.append(f"{tag}: {len(old)} -> {len(want)} paths")
            else:
                log.append(f"OK: {tag} already {len(want)} paths")
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    all_hosts = c.get_or_raise("/api/hosts")["response"]
    src_hosts = relay1_lv_hosts(all_hosts)
    if len(src_hosts) != 3:
        print(f"FAIL: expected 3 relay#1 LV hosts, got {len(src_hosts)}", file=sys.stderr)
        return 1

    existing_r2 = [
        h
        for h in all_hosts
        if h.get("address") == RELAY2_IP and int(h.get("port") or 0) == RELAY2_PORT
    ]
    existing_r2.sort(key=lambda x: x.get("remark") or "")

    if len(existing_r2) >= 3:
        new_uuids = [h["uuid"] for h in existing_r2[:3]]
        print(f"reuse {len(new_uuids)} existing relay#2 hosts")
    else:
        new_uuids = [h["uuid"] for h in existing_r2]
        have_sni = {h.get("sni") for h in existing_r2}
        for src in src_hosts:
            if src.get("sni") in have_sni:
                continue
            if not args.apply:
                print(f"dry-run create: {src.get('remark')} -> {RELAY2_IP}:{RELAY2_PORT}")
                new_uuids.append(f"dry-run-{src['uuid'][:8]}")
            else:
                new_uuids.append(create_relay2_host(c, src))
        new_uuids.sort()
        # stable order: match relay1 sort by remark via re-fetch
        if args.apply:
            refetched = [
                h
                for h in c.get_or_raise("/api/hosts")["response"]
                if h.get("address") == RELAY2_IP and int(h.get("port") or 0) == RELAY2_PORT
            ]
            refetched.sort(key=lambda x: x.get("remark") or "")
            new_uuids = [h["uuid"] for h in refetched[:3]]
            print(f"relay#2 host UUIDs ({len(new_uuids)}): ready for inject")

    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = list(sel.get("values") or [])
    print(f"injectHosts before: {len(before)}")

    if args.apply:
        seen = set(before)
        # Ensure all relay2 UUIDs present at tail (proxy-12..14)
        r2_set = set(new_uuids)
        without_r2 = [u for u in before if u not in r2_set]
        after = without_r2 + new_uuids
        sel["values"] = after
        print(f"injectHosts after: {len(after)} (relay2 tail {len(new_uuids)})")
    else:
        print(f"injectHosts after (dry): {len(before) + len(new_uuids)}")

    for line in apply_balancers(doc):
        print(line)

    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_add_relay2_vpn.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-relay2-vpn-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_add_relay2_vpn")
    print("Applied: relay#2 VPN hosts + injectHosts + balancers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
