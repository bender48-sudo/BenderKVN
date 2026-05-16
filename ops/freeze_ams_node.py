#!/usr/bin/env python3
"""P1-ARCH-AMS-DECOM step 1: freeze growth on the AMS node.

What it does (default = dry-run):
  1. Resolve the AMS node UUID by its address (default 168.100.11.140).
  2. List all /api/hosts attached to that node (membership in `nodes` array
     OR same `address`).
  3. Show which of those host UUIDs are still present in
     subscription-templates[].templateJson.remnawave.injectHosts[0].selector.values.
  4. Plan:
       a) PATCH /api/subscription-templates — trim those UUIDs out.
       b) PATCH each /api/hosts with {"uuid":..., "isHidden":true} — so even
          if someone re-adds them to the template, they won't ship.
       c) (--disable) PATCH each /api/hosts with isDisabled=true. This makes
          ru-monitor.py stop probing them (it filters by isDisabled), and is
          a stronger statement of intent than isHidden alone.

Pass --apply to actually mutate. Without --apply prints the plan only.

Safety:
  - Always reads & saves a snapshot of the template before mutating
    (.secrets/snapshots/template-before-freeze-<ts>.json).
  - Verifies inject-count and isHidden=true after each PATCH.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from panel_client import PanelClient  # type: ignore

import site_urls  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_NODE_ADDR = "168.100.11.140"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID


def resolve_node_uuid(c: PanelClient, address: str) -> tuple[str, str]:
    nodes = c.get_or_raise("/api/nodes")["response"]
    for n in nodes:
        if n.get("address") == address:
            return n["uuid"], n.get("name", "?")
    raise SystemExit(f"no node found with address {address}")


def list_hosts_on_node(c: PanelClient, node_uuid: str, node_address: str) -> list[dict]:
    hosts = c.get_or_raise("/api/hosts")["response"]
    out = []
    for h in hosts:
        attached = False
        nodes_field = h.get("nodes") or []
        if isinstance(nodes_field, list) and node_uuid in nodes_field:
            attached = True
        if h.get("address") == node_address:
            attached = True
        if attached:
            out.append(h)
    return out


def get_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def inject_values(tpl: dict) -> list[str]:
    doc = tpl["templateJson"]
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    return [str(x) for x in (sel.get("values") or [])]


def patch_template_trim(c: PanelClient, template_uuid: str, full_tpl: dict,
                        drop: set[str]) -> tuple[int, int]:
    """Returns (before, after) count of injectHosts.values."""
    doc = full_tpl["templateJson"]
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = [str(x) for x in (sel.get("values") or [])]
    after = [v for v in before if v not in drop]
    sel["values"] = after

    minimal = {
        "uuid": full_tpl.get("uuid") or template_uuid,
        "templateJson": doc,
        "viewPosition": full_tpl.get("viewPosition"),
        "templateType": full_tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        sys.exit(f"PATCH template HTTP {code}: {str(body)[:500]}")
    return len(before), len(after)


def hide_host(c: PanelClient, host_uuid: str) -> bool:
    code, body = c.patch("/api/hosts", body={"uuid": host_uuid, "isHidden": True})
    if code not in (200, 201, 204):
        print(f"  PATCH host {host_uuid} HTTP {code}: {str(body)[:300]}")
        return False
    # Verify.
    code, body = c.get(f"/api/hosts/{host_uuid}")
    if code != 200:
        print(f"  GET-back host {host_uuid} HTTP {code}")
        return False
    return bool(body.get("response", {}).get("isHidden"))


def disable_host(c: PanelClient, host_uuid: str) -> bool:
    code, body = c.patch("/api/hosts", body={"uuid": host_uuid, "isDisabled": True})
    if code not in (200, 201, 204):
        print(f"  PATCH host {host_uuid} HTTP {code}: {str(body)[:300]}")
        return False
    code, body = c.get(f"/api/hosts/{host_uuid}")
    if code != 200:
        print(f"  GET-back host {host_uuid} HTTP {code}")
        return False
    return bool(body.get("response", {}).get("isDisabled"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--node-address", default=DEFAULT_NODE_ADDR)
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    ap.add_argument("--apply", action="store_true",
                    help="actually mutate (default: dry-run)")
    ap.add_argument("--disable", action="store_true",
                    help="also set isDisabled=true (stops ru-monitor probing)")
    args = ap.parse_args()

    c = PanelClient()
    node_uuid, node_name = resolve_node_uuid(c, args.node_address)
    print(f"target node : {node_name} | {args.node_address} | uuid={node_uuid}")

    hosts = list_hosts_on_node(c, node_uuid, args.node_address)
    print(f"hosts on node: {len(hosts)}")
    for h in hosts:
        print(f"  - {h.get('uuid')} | hidden={h.get('isHidden')} | "
              f"port={h.get('port')} | addr={h.get('address')!r} | "
              f"remark={h.get('remark')!r}")

    if not hosts:
        print("nothing to freeze; bye.")
        return

    tpl = get_template(c, args.template_uuid)
    inject = set(inject_values(tpl))
    print(f"injectHosts.values: {len(inject)} UUIDs total")

    host_uuids = {h["uuid"] for h in hosts}
    will_trim = host_uuids & inject
    will_hide = {h["uuid"] for h in hosts if not h.get("isHidden")}
    will_disable: set[str] = set()
    if args.disable:
        will_disable = {h["uuid"] for h in hosts if not h.get("isDisabled")}

    print(f"would TRIM from injectHosts.values: {len(will_trim)} UUID(s)")
    for u in sorted(will_trim):
        print(f"  - trim  {u}")
    print(f"would HIDE (isHidden=true): {len(will_hide)} host(s)")
    for u in sorted(will_hide):
        print(f"  - hide  {u}")
    if args.disable:
        print(f"would DISABLE (isDisabled=true): {len(will_disable)} host(s)")
        for u in sorted(will_disable):
            print(f"  - disable {u}")

    if not args.apply:
        print("\n[dry-run] re-run with --apply to mutate.")
        return

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = SNAPSHOT_DIR / f"template-before-freeze-{ts}.json"
    backup_path.write_text(json.dumps({"response": tpl}, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"\n[backup] template -> {backup_path}")

    if will_trim:
        before, after = patch_template_trim(c, args.template_uuid, tpl, will_trim)
        print(f"[trim] injectHosts.values: {before} -> {after}")
        verify = inject_values(get_template(c, args.template_uuid))
        assert len(verify) == after, f"verify failed: re-fetch shows {len(verify)} != {after}"
        print(f"[verify] re-fetched inject-count = {len(verify)}  OK")
    else:
        print("[trim] nothing to trim (UUIDs already absent from injectHosts)")

    if will_hide:
        ok = 0
        for u in sorted(will_hide):
            if hide_host(c, u):
                ok += 1
                print(f"[hide] {u}  OK")
            else:
                print(f"[hide] {u}  FAIL")
        print(f"[hide] {ok}/{len(will_hide)} hosts now isHidden=true")
    else:
        print("[hide] all target hosts already isHidden=true")

    if args.disable:
        if will_disable:
            ok = 0
            for u in sorted(will_disable):
                if disable_host(c, u):
                    ok += 1
                    print(f"[disable] {u}  OK")
                else:
                    print(f"[disable] {u}  FAIL")
            print(f"[disable] {ok}/{len(will_disable)} hosts now isDisabled=true")
        else:
            print("[disable] all target hosts already isDisabled=true")

    print("\nDONE")


if __name__ == "__main__":
    main()
