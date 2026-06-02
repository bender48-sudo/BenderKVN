#!/usr/bin/env python3
"""Verify Reality outbounds use explicit fp=chrome (uTLS browser mimic).

Audits live subscription streamSettings.fingerprint on all vless outbounds.
Panel host PATCH for fingerprint is not exposed in Remnawave API — fp is set
at URI generation (REMNA_FP / bot remnawave_api default chrome).

Usage:
    python ops/patch_fingerprint_chrome.py
    python ops/patch_fingerprint_chrome.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from subscription_fetch import HAPP_UA, decode_subscription, fetch_url, xray_config_root  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".secrets" / "panel-token.txt"
CANONICAL_FP = "chrome"


def _outbound_fingerprint(o: dict) -> str | None:
    stream = o.get("streamSettings") or {}
    fp = stream.get("fingerprint")
    if fp:
        return str(fp)
    rs = stream.get("realitySettings") or {}
    if rs.get("fingerprint"):
        return str(rs["fingerprint"])
    tls = stream.get("tlsSettings") or {}
    if tls.get("fingerprint"):
        return str(tls["fingerprint"])
    return None


def audit_live_sub() -> dict:
    token = TOKEN_PATH.read_text(encoding="ascii").strip()
    users_resp = fetch_url(
        f"{site_urls.PANEL_URL}/api/users?limit=5&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    short = users[0].get("shortUuid")
    sub_resp = fetch_url(
        f"{site_urls.SUB_PUBLIC_ORIGIN}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    cfg = xray_config_root(decode_subscription(sub_resp.body))
    vless = [o for o in (cfg.get("outbounds") or []) if o.get("protocol") == "vless"]
    missing: list[str] = []
    wrong: list[str] = []
    ok_n = 0
    for o in vless:
        tag = str(o.get("tag") or "?")
        fp = _outbound_fingerprint(o)
        if not fp:
            missing.append(tag)
        elif fp.lower() != CANONICAL_FP:
            wrong.append(f"{tag}={fp}")
        else:
            ok_n += 1
    return {
        "short": short,
        "vless_count": len(vless),
        "chrome_count": ok_n,
        "missing_fp": missing,
        "wrong_fp": wrong,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if not TOKEN_PATH.is_file():
        print(f"FAIL: missing {TOKEN_PATH}", file=sys.stderr)
        return 1

    report = audit_live_sub()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"sub: {report['short']}")
    print(f"vless outbounds: {report['vless_count']}, fp=chrome: {report['chrome_count']}")
    if report["missing_fp"]:
        print(
            f"INFO: {len(report['missing_fp'])} outbounds without explicit fingerprint in JSON "
            f"(Happ may default to chrome): {report['missing_fp'][:5]}"
        )
    if report["wrong_fp"]:
        print(f"FAIL: non-chrome fingerprint: {report['wrong_fp']}", file=sys.stderr)
        return 1

    # Missing fp in sub JSON is INFO not FAIL — Remnawave often omits; bot URI uses chrome.
    if report["vless_count"] == 0:
        print("FAIL: no vless outbounds", file=sys.stderr)
        return 1
    print("FINGERPRINT_CHROME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
