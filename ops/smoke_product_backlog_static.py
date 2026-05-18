#!/usr/bin/env python3
"""Static smokes for product Q052-Q062 (repo artifacts)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHECKS = [
    ("V2RAYN_CLIENT_OK", ["docs/CLIENT-V2RAYN.md"], lambda: "v2rayN" in (ROOT / "web/portal/content/ru.json").read_text(encoding="utf-8")),
    ("TSPU_VLESS_PLAYBOOK_OK", ["docs/RUNBOOK-TSPU-VLESS-INCIDENT.md"], None),
    ("TSPU_BLOCK_PROBE_OK", ["ops/tspu_block_probe.py"], None),
    ("VPN_INBOUND_PORT_OK", ["docs/RUNBOOK-VPN-INBOUND-PORT.md"], None),
    ("SELFSTEAL_REVIEW_OK", [], lambda: "Q057" in (ROOT / "docs/TSPU-OBSERVATIONS.md").read_text(encoding="utf-8")),
    ("SNI_ROTATE_OK", [], lambda: "www.yandex.ru" in (ROOT / "ops/site.env.example").read_text(encoding="utf-8")),
    ("TSPU_THREAT_MODEL_OK", ["docs/TSPU-THREAT-MODEL.md"], None),
    ("P4_RF_EGRESS_POC_OK", ["docs/P4-DNS-RF-EGRESS-POC.md"], None),
    ("NODE_DNS_RESOLVER_OK", ["docs/RUNBOOK-NODE-DNS-RESOLVER.md"], None),
    ("SUB_TIER_PROFILES_OK", [], lambda: "tier_profiles" in json.loads((ROOT / "web/portal/content/ru.json").read_text(encoding="utf-8"))),
]


def main() -> int:
    failed = 0
    for label, files, extra in CHECKS:
        for f in files:
            if not (ROOT / f).is_file():
                print(f"{label}_FAIL: missing {f}", file=sys.stderr)
                failed += 1
                break
        else:
            if extra is not None and not extra():
                print(f"{label}_FAIL: extra check", file=sys.stderr)
                failed += 1
            else:
                print(label)
    if failed:
        return 1
    print("PRODUCT_BACKLOG_STATIC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
