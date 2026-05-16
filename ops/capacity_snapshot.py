#!/usr/bin/env python3
"""Capacity snapshot for P6-SCALE-01 — panel users (paginated), nodes, soft capacity.

Run from repo root with ``.secrets/panel-token.txt`` or ``PANEL_TOKEN`` / ``REMNA_API_TOKEN``.

Uses the same pagination as ``daily-report.sh`` (``/api/users?size=&start=``).

Example::

  python ops/capacity_snapshot.py
  python ops/capacity_snapshot.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

from panel_client import PanelClient  # noqa: E402

# Match balancer.sh default unless overridden (soft cap heuristic only).
USERS_PER_NODE_DEFAULT = 50

# Backlog §10.1 — advisory thresholds (users in DB).
WARN_USERS = 2000
CRITICAL_USERS = 8000


def _fwd() -> dict[str, str]:
    return {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "127.0.0.1",
    }


def fetch_all_users(client: PanelClient) -> list[dict]:
    out: list[dict] = []
    seen: set[str | int] = set()
    start = 0
    size = 100
    while True:
        path = f"/api/users?size={size}&start={start}"
        code, data = client.get(path, extra_headers=_fwd())
        if code != 200:
            raise RuntimeError(f"GET users HTTP {code}: {data!s}"[:500])
        chunk = (data.get("response") or {}).get("users") or []
        if not isinstance(chunk, list):
            chunk = []
        n_new = 0
        for u in chunk:
            uid = u.get("uuid") or u.get("shortUuid") or u.get("email") or id(u)
            if uid in seen:
                continue
            seen.add(str(uid))
            out.append(u)
            n_new += 1
        if len(chunk) < size:
            break
        if n_new == 0:
            break
        start += len(chunk)
        if start > 100_000:
            break
    return out


def fetch_nodes(client: PanelClient) -> list[dict]:
    code, data = client.get("/api/nodes", extra_headers=_fwd())
    if code != 200:
        raise RuntimeError(f"GET nodes HTTP {code}: {data!s}"[:500])
    nodes = data.get("response", data)
    if isinstance(nodes, list):
        return nodes
    for k in ("nodes", "items"):
        if isinstance(nodes, dict) and isinstance(nodes.get(k), list):
            return nodes[k]
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description="Remnawave capacity snapshot")
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    args = ap.parse_args()

    per_node = int(os.environ.get("USERS_PER_NODE", USERS_PER_NODE_DEFAULT))
    client = PanelClient()

    users = fetch_all_users(client)
    active = [u for u in users if u.get("status") == "ACTIVE"]
    nodes = fetch_nodes(client)
    nodes_prod = [n for n in nodes if not n.get("isDisabled")]
    n_active_nodes = len(nodes_prod)
    connected = [n for n in nodes_prod if n.get("isConnected")]
    n_conn = len(connected)

    capacity = n_active_nodes * per_node if n_active_nodes else 0
    load_pct = (len(active) * 100 // capacity) if capacity > 0 else 0

    alerts: list[str] = []
    if len(active) >= CRITICAL_USERS:
        alerts.append(f"users_active>={CRITICAL_USERS} (§10.1: consider panel scale / load test)")
    elif len(active) >= WARN_USERS:
        alerts.append(f"users_active>={WARN_USERS} (§10.1: watch AMS RAM / API)")

    snap = {
        "users_total": len(users),
        "users_active": len(active),
        "nodes_total": len(nodes),
        "nodes_active_not_disabled": n_active_nodes,
        "nodes_connected": n_conn,
        "soft_capacity_users": capacity,
        "users_per_node_assumption": per_node,
        "load_pct_vs_soft_capacity": load_pct,
        "alerts": alerts,
    }

    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return

    print("=== BenderVPN capacity snapshot (panel API) ===")
    print(f"users_total={snap['users_total']}  users_active={snap['users_active']}")
    print(
        f"nodes: total={snap['nodes_total']}  "
        f"active(not disabled)={n_active_nodes}  connected={n_conn}"
    )
    print(
        f"soft_capacity={capacity} (nodes_active×{per_node})  "
        f"load_pct={load_pct}%"
    )
    if alerts:
        for a in alerts:
            print(f"NOTICE: {a}")
    else:
        print("thresholds: OK (see docs/COMMERCIAL-BACKLOG.md §10.1)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
