#!/usr/bin/env python3
"""Q-VPN-STAB-005: remove XHTTP host UUIDs from injectHosts (Happ batch-import fix).

Removes only hosts whose remark contains ``XHTTP`` (LV + NL matrix XHTTP inbounds).
TCP primary/alt outbounds (443, relay) stay — no speed regression for Happ users.

XHTTP inbounds remain on nodes for future recovery sub (Q-VPN-STAB-020).

Usage:
    python ops/trim_injecthosts_no_xhttp.py              # dry-run
    python ops/trim_injecthosts_no_xhttp.py --apply      # PATCH template + notify
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
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID


def is_xhttp_host(host: dict) -> bool:
    remark = str(host.get("remark") or "")
    if "xhttp" in remark.lower():
        return True
    # Fallback: config profile inbound network (when present in API payload)
    for key in ("network", "type"):
        val = str(host.get(key) or "").lower()
        if val == "xhttp":
            return True
    return False


def resolve_xhttp_uuids(c: PanelClient) -> list[tuple[str, str]]:
    hosts = c.get_or_raise("/api/hosts")["response"]
    inject_tpl = c.get_or_raise(f"/api/subscription-templates/{DEFAULT_TEMPLATE_UUID}")["response"]
    inject_vals = set(
        inject_tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"].get("values") or []
    )
    out: list[tuple[str, str]] = []
    for h in hosts:
        uid = str(h.get("uuid") or "")
        if not uid or uid not in inject_vals:
            continue
        if is_xhttp_host(h):
            out.append((uid, str(h.get("remark") or uid)))
    return out


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def trim_injecthosts(doc: dict, drop_uuids: set[str]) -> tuple[int, int]:
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = [str(x) for x in (sel.get("values") or [])]
    after = [x for x in before if x not in drop_uuids]
    sel["values"] = after
    return len(before), len(after)


def patch_template(c: PanelClient, tpl: dict) -> None:
    doc = tpl["templateJson"]
    minimal = {
        "uuid": tpl.get("uuid") or DEFAULT_TEMPLATE_UUID,
        "templateJson": doc,
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201):
        raise RuntimeError(f"PATCH template HTTP {code}: {body!s}"[:500])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="PATCH template (default: dry-run)")
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient()
    xhttp_hosts = resolve_xhttp_uuids(c)
    if not xhttp_hosts:
        print("OK: no XHTTP hosts in injectHosts — nothing to trim")
        return 0

    drop = {uid for uid, _ in xhttp_hosts}
    print(f"XHTTP hosts to remove from injectHosts ({len(xhttp_hosts)}):")
    for uid, remark in xhttp_hosts:
        print(f"  {uid}  {remark!r}")

    tpl = fetch_template(c, args.template_uuid)
    doc = copy.deepcopy(tpl["templateJson"])
    before, after = trim_injecthosts(doc, drop)
    print(f"injectHosts.values: {before} -> {after} (-{before - after})")

    if before == after:
        print("OK: XHTTP UUIDs already absent from injectHosts")
        return 0

    if not args.apply:
        print("dry-run: pass --apply to PATCH template")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"template-before-trim-xhttp-{ts}.json"
    snap.write_text(json.dumps({"response": tpl}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    tpl["templateJson"] = doc
    patch_template(c, tpl)
    print("OK: template PATCH applied (XHTTP removed from injectHosts)")

    try:
        after_template_patch("trim_injecthosts_no_xhttp")
    except Exception as exc:
        print(f"[sub-config] WARN: notify/push failed ({exc})")
        print("[sub-config] Run manually: python ops/push_sub_config_generation_ams.py --generation N")
        print("             or ops/broadcast_refresh_sub.py from AMS/LV with SSH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
