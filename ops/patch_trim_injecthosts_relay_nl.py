#!/usr/bin/env python3
"""Remove RELAY→NL :9443 hosts from injectHosts (proxy-12..14).

Symptom: access_log ~22% traffic on proxy-12..14; LV probe :9443 timeout.
Balancers already exclude these tags but Happ still exposes 14 outbounds in sub.

Usage:
    python ops/patch_trim_injecthosts_relay_nl.py
    python ops/patch_trim_injecthosts_relay_nl.py --apply
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
RELAY_IP = site_urls.RU_RELAY_HOST
RELAY_NL_PORT = 9443


def is_relay_nl_host(host: dict) -> bool:
    remark = str(host.get("remark") or "").lower()
    if "9443" in remark or "relay" in remark and "nl" in remark:
        return True
    port = host.get("port") or host.get("inboundPort")
    try:
        if int(port) == RELAY_NL_PORT:
            return True
    except (TypeError, ValueError):
        pass
    addr = str(host.get("address") or host.get("host") or "")
    if addr == RELAY_IP and "9443" in remark:
        return True
    return False


def relay_nl_uuids(c: PanelClient, template_uuid: str) -> list[tuple[str, str]]:
    tpl = c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]
    inject_vals = set(
        tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"].get("values") or []
    )
    hosts = c.get_or_raise("/api/hosts")["response"]
    out: list[tuple[str, str]] = []
    for h in hosts:
        uid = str(h.get("uuid") or "")
        if uid not in inject_vals:
            continue
        if is_relay_nl_host(h):
            out.append((uid, str(h.get("remark") or uid)))
    return out


def trim_injecthosts(doc: dict, drop: set[str]) -> tuple[int, int, list[str]]:
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = [str(x) for x in (sel.get("values") or [])]
    after = [x for x in before if x not in drop]
    sel["values"] = after
    removed = [x for x in before if x in drop]
    return len(before), len(after), removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    drop_list = relay_nl_uuids(c, args.template_uuid)
    drop = {uid for uid, _ in drop_list}
    if not drop_list:
        print("OK: no RELAY→NL :9443 hosts in injectHosts")
        return 0

    print("RELAY→NL hosts to remove:")
    for uid, remark in drop_list:
        print(f"  {uid}  {remark}")

    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])
    n_before, n_after, removed = trim_injecthosts(doc, drop)
    print(f"injectHosts: {n_before} -> {n_after} (drop {len(removed)})")
    if n_after == n_before:
        print("Nothing to change")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_trim_injecthosts_relay_nl.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-trim-relay-nl-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_trim_injecthosts_relay_nl")
    print("Applied trim RELAY→NL injectHosts (gen+1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
