#!/usr/bin/env python3
"""Generate empty mobile smoke result template (CLIENT-STABILITY-MOBILE-SMOKE-001).

Writes markdown tables for owner to fill locally. No network, no secrets.

Usage:
    python ops/generate_mobile_smoke_template.py
    python ops/generate_mobile_smoke_template.py --write .local/mobile_smoke_results.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

TEMPLATE = """# Mobile smoke results — owner fill-in (do not commit with secrets)

**Task:** CLIENT-STABILITY-MOBILE-SMOKE-001
**Generated:** {today}
**Runbook:** docs/CLIENT-STABILITY-MOBILE-SMOKE.md

> Do not paste subscription URLs, QR payloads, or tokens into git.

## Device

| Field | Value |
|-------|-------|
| Model | |
| OS | |
| Client | Happ / Karing |
| App version | |
| Routing profile (Happ) | BenderVPN RU Y/N |

## Speed — Wi‑Fi

| Mode | Run 1 ↓/↑/ping | Run 2 | Run 3 | Median ↓ Mbps | ~% loss vs baseline |
|------|----------------|-------|-------|---------------|---------------------|
| No VPN | | | | | — |
| VPN | | | | | |

## Speed — mobile data

| Mode | Run 1 ↓/↑/ping | Run 2 | Run 3 | Median ↓ Mbps | ~% loss vs baseline |
|------|----------------|-------|-------|---------------|---------------------|
| No VPN | | | | | — |
| VPN | | | | | |

## Sites (Y/N/P)

| Check | Wi‑Fi | Mobile data | Notes |
|-------|-------|-------------|-------|
| Connect time (sec) | | | |
| google.com | | | |
| Gmail | | | |
| Google Docs | | | |
| Telegram | | | |
| Instagram/Meta | | | |
| ya.ru | | | |
| vk.com | | | |
| Bank / .ru site | | | |
| ipinfo.io | | | |

## Stability

| Phase | Result | Notes |
|-------|--------|-------|
| 15 min active | | |
| 30 min lock | | |
| After unlock | | |
| Wi‑Fi → mobile data | | |
| Mobile data → Wi‑Fi | | |
| Airplane toggle | | |

## Verdict

| Overall | PASS / SOFT PASS / FAIL |
|---------|-------------------------|
| Speed | |
| Stability | |
| Setup friction | |

## Caveats

-

"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", type=Path, help="write template to path (e.g. .local/mobile_smoke_results.md)")
    args = ap.parse_args()
    text = TEMPLATE.format(today=date.today().isoformat())
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(text, encoding="utf-8")
        print(f"Wrote: {args.write}")
    else:
        sys.stdout.write(text)
    print("MOBILE_SMOKE_TEMPLATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
