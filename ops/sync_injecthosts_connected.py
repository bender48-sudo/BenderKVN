#!/usr/bin/env python3
"""P1-PRO-SUB-DEAD-OUTBOUND-01: keep injectHosts aligned with connected panel nodes.

Removes host UUIDs tied to disconnected/disabled nodes so Happ sub stops advertising
dead LV/NL paths. Does not change routing rules or balancers (E8).

Usage:
    python ops/sync_injecthosts_connected.py              # dry-run
    python ops/sync_injecthosts_connected.py --apply     # PATCH if diff
    python ops/sync_injecthosts_connected.py --gate --apply
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parent.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402
from trim_injecthosts_no_xhttp import is_xhttp_host  # noqa: E402
from vpn_apply_guard import print_guardrail_banner  # noqa: E402

SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
MIN_INJECT = int(__import__("os").environ.get("SYNC_INJECTHOSTS_MIN", "3"))


def host_node_connected(host: dict, nodes_by_uuid: dict[str, dict]) -> tuple[bool, str]:
    if is_xhttp_host(host):
        return False, "xhttp"
    node_ids = host.get("nodes") or []
    if not node_ids:
        return False, "no node"
    node = nodes_by_uuid.get(str(node_ids[0]), {})
    if node.get("isDisabled"):
        return False, "node disabled"
    if not node.get("isConnected"):
        return False, f"node down ({node.get('name') or '?'})"
    return True, "ok"


def compute_connected_inject(
    hosts: list[dict], nodes: list[dict], current: list[str]
) -> tuple[list[str], list[str]]:
    nodes_by_uuid = {n["uuid"]: n for n in nodes}
    host_by_uuid = {str(h.get("uuid")): h for h in hosts if h.get("uuid")}
    log: list[str] = []
    new_vals: list[str] = []
    for uid in current:
        h = host_by_uuid.get(uid)
        if not h:
            log.append(f"  drop {uid[:8]}… (host missing in panel)")
            continue
        ok, reason = host_node_connected(h, nodes_by_uuid)
        if ok:
            new_vals.append(uid)
        else:
            log.append(f"  drop {uid[:8]}… ({reason})")
    return new_vals, log


def gate_baseline() -> int:
    py = sys.executable
    for script, label in (
        ("verify_vpn_balancer_profile.py", "verify_vpn_balancer_profile"),
        ("probe_subscription.py", "probe_subscription"),
    ):
        p = _OPS / script
        if not p.is_file():
            continue
        print(f"\n--- gate: {label} ---")
        r = subprocess.run([py, str(p)], cwd=ROOT)
        if r.returncode != 0 and script == "verify_vpn_balancer_profile.py":
            return 1
    print("\nGATE_INJECTHOSTS_SYNC_OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    print_guardrail_banner(
        "sync_injecthosts_connected", capacity_reducing=True, cron_managed=True
    )

    c = PanelClient(timeout=120)
    nodes = c.get_or_raise("/api/nodes")["response"]
    hosts = c.get_or_raise("/api/hosts")["response"]
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]
    cur = list(doc["remnawave"]["injectHosts"][0]["selector"].get("values") or [])
    new_vals, log = compute_connected_inject(hosts, nodes, cur)

    print(f"injectHosts: {len(cur)} -> {len(new_vals)}")
    for ln in log:
        print(ln)

    if new_vals == cur:
        print("no change")
        if args.gate:
            return gate_baseline()
        return 0

    if len(new_vals) < MIN_INJECT:
        print(
            f"ABORT: would leave {len(new_vals)} injectHosts (min {MIN_INJECT}) — "
            "use lv_node_down_nl_failover for full LV outage",
            file=sys.stderr,
        )
        return 1

    if not args.apply:
        print("dry-run. Apply: --apply")
        return 0

    if args.gate:
        rc = gate_baseline()
        if rc != 0:
            print("ABORT: pre-apply gate failed", file=sys.stderr)
            return 1

    doc2 = copy.deepcopy(doc)
    doc2["remnawave"]["injectHosts"][0]["selector"]["values"] = new_vals
    snap = SNAPSHOT_DIR / f"template-before-inject-sync-{time.strftime('%Y%m%d_%H%M%S')}.json"
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    tpl["templateJson"] = doc2
    minimal: dict[str, Any] = {
        "uuid": tpl.get("uuid") or args.template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}: {str(body)[:500]}", file=sys.stderr)
        return 1

    after_template_patch("sync_injecthosts_connected", push_ams=True)
    print("Applied injectHosts sync (gen+1).")
    if args.gate:
        return gate_baseline()
    print("INJECTHOSTS_CONNECTED_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
