"""Quick read of the most recent panel snapshot.

Usage:
    python ops/inspect_snapshot.py                # summary
    python ops/inspect_snapshot.py host UUID      # show one host body
    python ops/inspect_snapshot.py lv-hosts       # hosts on Latvia-Node uuid
    python ops/inspect_snapshot.py inject-uuids   # list injectHosts UUIDs
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / ".secrets" / "snapshots"


def latest() -> dict:
    files = sorted(SNAP_DIR.glob("panel-*.json"))
    if not files:
        sys.exit("no snapshots")
    return json.loads(files[-1].read_text(encoding="utf-8"))


def summary(snap: dict) -> None:
    nodes = snap["nodes"]["data"]["response"]
    hosts = snap["hosts"]["data"]["response"]
    tpl = snap["template"]["data"]["response"]
    inj = tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"]["values"]
    print(f"nodes={len(nodes)}, hosts={len(hosts)}, inject={len(inj)}")
    for n in nodes:
        print("  node:", n["name"], n["address"], "uuid=", n["uuid"], "connected=", n["isConnected"])
    by_node: dict[str, list[dict]] = {}
    for h in hosts:
        for nid in (h.get("nodes") or []):
            by_node.setdefault(nid, []).append(h)
    for nid, hs in by_node.items():
        print(f"  hosts_for_node[{nid}]={len(hs)}")
        for h in hs:
            print(
                "    -",
                h.get("uuid"),
                h.get("remark"),
                "|",
                h.get("address") + ":" + str(h.get("port")),
                "| sni=" + str(h.get("sni")),
                "| inj?=" + ("Y" if h.get("uuid") in inj else "N"),
            )


def show_host(snap: dict, uid: str) -> None:
    for h in snap["hosts"]["data"]["response"]:
        if h.get("uuid") == uid:
            print(json.dumps(h, ensure_ascii=False, indent=2))
            return
    sys.exit(f"host {uid} not found")


def lv_hosts(snap: dict) -> None:
    nodes = snap["nodes"]["data"]["response"]
    lv = next((n for n in nodes if "Latvia" in n["name"]), None)
    if not lv:
        sys.exit("no Latvia node")
    print(f"# Hosts attached to {lv['name']} ({lv['address']}, uuid={lv['uuid']})")
    for h in snap["hosts"]["data"]["response"]:
        if lv["uuid"] in (h.get("nodes") or []):
            print(json.dumps(h, ensure_ascii=False, indent=2))


def inject_uuids(snap: dict) -> None:
    tpl = snap["template"]["data"]["response"]
    inj = tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"]["values"]
    for u in inj:
        print(u)


def main() -> None:
    snap = latest()
    if len(sys.argv) < 2:
        summary(snap)
        return
    cmd = sys.argv[1]
    if cmd == "host" and len(sys.argv) >= 3:
        show_host(snap, sys.argv[2])
    elif cmd == "lv-hosts":
        lv_hosts(snap)
    elif cmd == "inject-uuids":
        inject_uuids(snap)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
