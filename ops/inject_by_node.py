"""Break down injectHosts list by node and confirm AMS is excluded."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
snap = sorted((ROOT / ".secrets" / "snapshots").glob("panel-*.json"))[-1]
print(f"# {snap.name}")
data = json.loads(snap.read_text(encoding="utf-8"))

hosts = {h["uuid"]: h for h in data["hosts"]["data"]["response"]}
nodes_by_uuid = {n["uuid"]: n["name"] for n in data["nodes"]["data"]["response"]}
profile_inbound_to_node = {}
for n in data["nodes"]["data"]["response"]:
    cp = (n.get("configProfile") or {})
    for inb in cp.get("activeInbounds") or []:
        profile_inbound_to_node[inb.get("uuid")] = n["name"]

# inbound -> node mapping is hard since we don't have profile->node. Use host.inbound.tag pattern by sni/address
# Use host.address to map: 176.126.162.158=LV, 168.100.11.140=AMS, 91.90.192.17=NL
addr_to_node = {
    "176.126.162.158": "Latvia",
    "168.100.11.140": "Amsterdam",
    "91.90.192.17": "Netherlands",
}

doc = data["template"]["data"]["response"]["templateJson"]
# Real shape: templateJson.remnawave.injectHosts[0].selector.values
inj = doc.get("remnawave", {}).get("injectHosts") or [{}]
inject = (inj[0].get("selector") or {}).get("values") or []
print(f"# injectHosts count: {len(inject)}")
by_node = {}
unknown = 0
for uuid in inject:
    h = hosts.get(uuid)
    if not h:
        unknown += 1
        continue
    node = addr_to_node.get(h.get("address"), f"other:{h.get('address')}")
    by_node.setdefault(node, []).append((uuid, h.get("remark")))

for node, items in sorted(by_node.items()):
    print(f"\n## {node} — {len(items)} hosts")
    for uuid, rem in items:
        print(f"  {uuid} | {rem!r}")
if unknown:
    print(f"\n!! unknown UUIDs in injectHosts: {unknown}")

print("\n## All non-hidden hosts (visible in subscriptions outside injectHosts):")
visible = [h for h in hosts.values() if not h.get("isHidden")]
for h in visible:
    node = addr_to_node.get(h.get("address"), f"other:{h.get('address')}")
    print(f"  {h['uuid']} | {node:12} | {h.get('remark')!r}")
