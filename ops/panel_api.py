"""Tiny helper: call Remnawave panel API from local PC using cached token.

Usage:
    python ops/panel_api.py snapshot          # save nodes/hosts/template snapshot
    python ops/panel_api.py nodes             # list nodes (name, address, isConnected)
    python ops/panel_api.py inject-count      # how many UUIDs in injectHosts now
    python ops/panel_api.py inject-list       # full list of injectHosts UUIDs
    python ops/panel_api.py hosts-by-node UUID # list hosts attached to given node UUID
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import site_urls  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRET_DIR = REPO_ROOT / ".secrets"
TOKEN_FILE = SECRET_DIR / "panel-token.txt"
SNAPSHOT_DIR = REPO_ROOT / ".secrets" / "snapshots"
PANEL_URL = site_urls.PANEL_URL
TEMPLATE_UUID = os.environ.get(
    "REMNA_TEMPLATE_UUID", site_urls.REMNA_TEMPLATE_UUID
)


def token() -> str:
    return TOKEN_FILE.read_text(encoding="ascii").strip()


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def api(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    url = PANEL_URL.rstrip("/") + path
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    if body is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", errors="replace") or "{}")


def cmd_nodes() -> None:
    code, data = api("GET", "/api/nodes")
    if code != 200:
        sys.exit(f"nodes HTTP {code}: {data}")
    for n in data.get("response", []):
        print(
            n.get("name"),
            "|",
            n.get("address"),
            "|",
            f"connected={n.get('isConnected')}",
            f"disabled={n.get('isDisabled')}",
            f"uuid={n.get('uuid')}",
        )


def cmd_inject_count() -> None:
    code, data = api("GET", f"/api/subscription-templates/{TEMPLATE_UUID}")
    if code != 200:
        sys.exit(f"template HTTP {code}: {data}")
    doc = data["response"]["templateJson"]
    vals = doc["remnawave"]["injectHosts"][0]["selector"]["values"]
    print(len(vals))


def cmd_inject_list() -> None:
    code, data = api("GET", f"/api/subscription-templates/{TEMPLATE_UUID}")
    if code != 200:
        sys.exit(f"template HTTP {code}: {data}")
    doc = data["response"]["templateJson"]
    vals = doc["remnawave"]["injectHosts"][0]["selector"]["values"]
    for v in vals:
        print(v)


def cmd_hosts_by_node(node_uuid: str) -> None:
    code, data = api("GET", "/api/hosts")
    if code != 200:
        sys.exit(f"hosts HTTP {code}: {data}")
    for h in data.get("response", []):
        nodes = h.get("nodes") or []
        if node_uuid in nodes:
            print(h.get("uuid"), "|", h.get("remark"), "|", h.get("address"), ":", h.get("port"))


def cmd_snapshot() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    out: dict[str, Any] = {"ts": ts, "panelUrl": PANEL_URL}
    for label, path in (
        ("nodes", "/api/nodes"),
        ("hosts", "/api/hosts"),
        ("template", f"/api/subscription-templates/{TEMPLATE_UUID}"),
    ):
        code, data = api("GET", path)
        out[label] = {"http": code, "data": data}

    snap_path = SNAPSHOT_DIR / f"panel-{ts}.json"
    snap_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot={snap_path}")

    nodes_raw = out["nodes"]["data"].get("response", [])
    hosts_raw = out["hosts"]["data"].get("response", [])
    tpl = out["template"]["data"].get("response", {})
    inj = tpl.get("templateJson", {}).get("remnawave", {}).get("injectHosts", [{}])
    inj_vals = (inj[0].get("selector") or {}).get("values") or []
    print(f"nodes_count={len(nodes_raw)}")
    print(f"hosts_count={len(hosts_raw)}")
    print(f"inject_count={len(inj_vals)}")
    for n in nodes_raw:
        print(
            "node:",
            n.get("name"),
            "|",
            n.get("address"),
            "|",
            f"connected={n.get('isConnected')}",
            f"uuid={n.get('uuid')}",
        )


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    fns = {
        "snapshot": lambda: cmd_snapshot(),
        "nodes": lambda: cmd_nodes(),
        "inject-count": lambda: cmd_inject_count(),
        "inject-list": lambda: cmd_inject_list(),
        "hosts-by-node": lambda: cmd_hosts_by_node(*rest),
    }
    fn = fns.get(cmd)
    if not fn:
        print(__doc__)
        sys.exit(f"unknown command: {cmd}")
    fn()


if __name__ == "__main__":
    main()
