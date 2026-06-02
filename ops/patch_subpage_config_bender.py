#!/usr/bin/env python3
"""Restore subscription-page UI copy from Remnawave default + BenderVPN branding.

Symptom: browser sub page shows ????? for labels — `subscription-page-config`
in panel has corrupted localized strings (778+ fields), not UTF-8 transport.
List endpoint may show `config: null`; GET by uuid returns the broken blob.

Source of truth: `ops/assets/remnawave-default-subpage-config.json`
(regenerate: `node ops/extract_default_subpage.mjs`).

Also ensure `subscription-settings.isProfileWebpageUrlEnabled=true` (SRR gate).

Usage:
    python ops/patch_subpage_config_bender.py              # dry-run
    python ops/patch_subpage_config_bender.py --apply
    python ops/patch_subpage_config_bender.py --apply --restart-ams
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

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON = _OPS / "assets" / "remnawave-default-subpage-config.json"
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
CONFIG_UUID = "00000000-0000-0000-0000-000000000000"

SUPPORT_URL = "https://t.me/Bender_KVN_bot"


def load_default_config() -> dict:
    if not DEFAULT_JSON.is_file():
        raise SystemExit(
            f"missing {DEFAULT_JSON}; run: node ops/extract_default_subpage.mjs"
        )
    return json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))


def bender_branding(cfg: dict) -> dict:
    out = copy.deepcopy(cfg)
    out.setdefault("brandingSettings", {})
    out["brandingSettings"]["title"] = "BenderVPN"
    out["brandingSettings"]["supportUrl"] = SUPPORT_URL
    # Keep Remnawave logo unless we host our own asset later.
    out["brandingSettings"].setdefault("logoUrl", "https://docs.rw/img/logo.svg")
    bs = out.setdefault("baseSettings", {})
    bs["metaTitle"] = "BenderVPN"
    bs["metaDescription"] = "Подписка BenderVPN — установка и обновление"
    return out


def suspicious_strings(obj: object) -> int:
    n = 0
    if isinstance(obj, dict):
        for v in obj.values():
            n += suspicious_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            n += suspicious_strings(v)
    elif isinstance(obj, str):
        q = obj.count("?")
        if q >= 3 and q / max(len(obj), 1) > 0.35:
            n += 1
    return n


def ensure_webpage_enabled(c: PanelClient, apply: bool) -> None:
    settings = c.get_or_raise("/api/subscription-settings")["response"]
    enabled = settings.get("isProfileWebpageUrlEnabled")
    print(f"isProfileWebpageUrlEnabled: {enabled}")
    if enabled:
        return
    if not apply:
        print("dry-run: would set isProfileWebpageUrlEnabled=true")
        return
    payload = copy.deepcopy(settings)
    payload["isProfileWebpageUrlEnabled"] = True
    code, _ = c.patch("/api/subscription-settings", body=payload)
    if code not in (200, 201):
        raise SystemExit(f"subscription-settings PATCH HTTP {code}")
    print("OK: isProfileWebpageUrlEnabled=true")


def restart_sub_page_ams() -> None:
    cmd = (
        "cd /opt/remnawave/sub && "
        "docker compose restart remnawave-subscription-page "
        "remnawave-subscription-page-b"
    )
    subprocess.run(["ssh", "bvpn-ams", cmd], check=True, timeout=120)
    print("OK: subscription-page containers restarted on AMS")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument(
        "--restart-ams",
        action="store_true",
        help="after PATCH, restart sub-page containers on AMS",
    )
    args = ap.parse_args()

    c = PanelClient()
    target = bender_branding(load_default_config())

    current = c.get_or_raise(f"/api/subscription-page-configs/{CONFIG_UUID}")["response"]
    cur_cfg = current.get("config") or {}
    print(f"current suspicious strings: {suspicious_strings(cur_cfg)}")
    print(f"target suspicious strings: {suspicious_strings(target)}")
    print(f"target installationGuideHeader.ru: {target['baseTranslations']['installationGuideHeader']['ru']!r}")

    ensure_webpage_enabled(c, args.apply)

    if cur_cfg == target:
        print("OK: subpage config already matches Bender default")
        return 0

    if not args.apply:
        print("dry-run: pass --apply to PATCH /api/subscription-page-configs")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"subpage-config-before-bender-{ts}.json"
    snap.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    code, body = c.patch(
        "/api/subscription-page-configs",
        body={"uuid": CONFIG_UUID, "name": current.get("name") or "Default", "config": target},
    )
    if code not in (200, 201):
        raise SystemExit(f"PATCH failed HTTP {code}: {body!s}"[:500])

    got = c.get_or_raise(f"/api/subscription-page-configs/{CONFIG_UUID}")["response"]["config"]
    if suspicious_strings(got):
        raise SystemExit("verify failed: config still has corrupted ?-strings")
    print("OK: subpage config restored (Remnawave default + BenderVPN branding)")

    if args.restart_ams:
        restart_sub_page_ams()
    else:
        print("note: restart subscription-page on AMS to reload config (or --restart-ams)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
