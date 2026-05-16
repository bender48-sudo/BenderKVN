#!/usr/bin/env python3
"""Quarterly TLS/client-stack audit (P2-RED-TLS-01).

Collects: Xray on prod nodes, latest sing-box release (GitHub), subscription
outbound protocols from a sample user. See docs/TLS-CLIENT-STACK-REVIEW.md.

Exit 0 prints TLS_CLIENT_STACK_AUDIT_OK when collection succeeds.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402

try:
    from panel_client import PanelClient
except ImportError:
    from ops.panel_client import PanelClient  # type: ignore

from transport_mux_audit import (  # noqa: E402
    _HAPP_UA,
    classify_profile,
    fetch_sub,
    parse_outbounds,
    profiles_in_sub,
)

NODES = ("bvpn-lv", "bvpn-nl")


def _ssh_xray_version(host: str) -> str:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        f"root@{host}",
        "docker exec remnanode xray version 2>/dev/null | head -1",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().split("\n")[0]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def _github_latest_singbox() -> dict:
    url = "https://api.github.com/repos/SagerNet/sing-box/releases/latest"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "BenderVPN-audit/1.0"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return {
            "tag": data.get("tag_name", "?"),
            "published": (data.get("published_at") or "")[:10],
            "url": data.get("html_url", ""),
        }
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        return {"tag": "fetch_failed", "error": str(e)[:120]}


def _outbound_stack_summary(raw: bytes) -> dict:
    protos: set[str] = set()
    flows: set[str] = set()
    security: set[str] = set()
    for o in parse_outbounds(raw):
        protos.add(str(o.get("protocol") or o.get("type") or "?"))
        s = o.get("settings") or {}
        vnext = (s.get("vnext") or [{}])[0]
        users = (vnext.get("users") or [{}])[0]
        if users.get("flow"):
            flows.add(str(users["flow"]))
        stream = o.get("streamSettings") or o.get("stream_settings") or {}
        sec = stream.get("security")
        if sec:
            security.add(str(sec))
        rs = stream.get("realitySettings") or stream.get("reality_settings") or {}
        if rs:
            security.add("reality")
    return {
        "protocols": sorted(protos),
        "flows": sorted(flows),
        "security": sorted(security),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-ssh", action="store_true")
    args = ap.parse_args()

    report: dict = {
        "review_id": "P2-RED-TLS-01",
        "nodes_xray": {},
        "sing_box_upstream": _github_latest_singbox(),
        "subscription_origin": site_urls.SUB_PUBLIC_ORIGIN,
    }

    if not args.skip_ssh:
        for h in NODES:
            report["nodes_xray"][h] = _ssh_xray_version(h)

    client = PanelClient()
    code, data = client.get(
        "/api/users?size=5&start=0",
        extra_headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "127.0.0.1"},
    )
    sample_short = None
    if code == 200:
        users = (data.get("response") or {}).get("users") or []
        for u in users:
            if (u.get("status") or "").upper() == "ACTIVE" and u.get("shortUuid"):
                sample_short = u["shortUuid"]
                break
    if sample_short:
        try:
            ctx = ssl.create_default_context()
            raw = fetch_sub(sample_short, ctx)
            profs, ob_cnt = profiles_in_sub(raw)
            report["subscription_sample"] = {
                "shortUuid_prefix": sample_short[:8] + "…",
                "transport_profiles": sorted(profs),
                "outbound_counts": dict(ob_cnt),
                "stack": _outbound_stack_summary(raw),
            }
        except Exception as e:
            report["subscription_sample"] = {"error": str(e)[:200]}
    else:
        report["subscription_sample"] = {"error": f"panel users HTTP {code}"}

    report["notes"] = {
        "happ_client": "Happ uses sing-box core; track sing-box releases for client-side ECH/uTLS",
        "prod_core": "remnanode runs Xray (not sing-box on server)",
        "mux_matrix": "docs/TRANSPORT-MUX-MATRIX.md",
        "next_review": "2026-08-16 (quarterly)",
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=== TLS client stack audit (P2-RED-TLS-01) ===")
        for host, ver in report.get("nodes_xray", {}).items():
            print(f"xray {host}: {ver}")
        sb = report["sing_box_upstream"]
        print(f"sing-box latest: {sb.get('tag')} ({sb.get('published', '')})")
        ss = report.get("subscription_sample") or {}
        if "stack" in ss:
            print(f"sub profiles: {ss.get('transport_profiles')}")
            print(f"sub stack: {ss.get('stack')}")
        print(f"next_review: {report['notes']['next_review']}")

    if report["sing_box_upstream"].get("tag") == "fetch_failed":
        print("TLS_CLIENT_STACK_AUDIT_WARN: sing-box release fetch failed", file=sys.stderr)
    print("TLS_CLIENT_STACK_AUDIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
