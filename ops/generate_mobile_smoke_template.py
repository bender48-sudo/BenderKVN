#!/usr/bin/env python3
"""Generate empty mobile smoke result template (CLIENT-STABILITY-MOBILE-SMOKE-001/002).

Minimal owner fill-in — local only, do not commit with secrets.

Usage:
    python ops/generate_mobile_smoke_template.py
    python ops/generate_mobile_smoke_template.py --write .local/mobile_smoke_results.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Simple sections for owner-assisted collection (COLLECT-001).
TEMPLATE = """# Mobile smoke results — owner fill-in

**Task:** CLIENT-STABILITY-MOBILE-SMOKE-001 / COLLECT-001
**Generated:** {today}
**Runbook:** docs/CLIENT-STABILITY-MOBILE-SMOKE.md §14

> Keep this file in `.local/` only. Do not commit. No subscription URLs or tokens.

---

## Device

| Field | Your answer |
|-------|-------------|
| Device model | |
| OS + version | |
| Client app | Happ / Karing |
| App version | |
| Routing profile (Happ) | BenderVPN RU — Y / N |

---

## Network (note during test)

| Phase | Network |
|-------|---------|
| Phase A | Wi‑Fi |
| Phase B | Wi‑Fi (after lock) |
| Phase C | Mobile data (LTE/5G) |

---

## Connect

| Item | Answer |
|------|--------|
| Connect time (seconds, rough) | |
| Visible errors on connect | none / describe |

---

## Speed (one run each is enough)

| Network | No VPN — download / upload / ping | With VPN — download / upload / ping |
|---------|-----------------------------------|---------------------------------------|
| Wi‑Fi | | |
| Mobile data | | |
| Acceptable for browsing? | Y / N / slow but OK |

---

## Apps & sites (Y = works · N = fail · P = slow/partial)

| Check | Wi‑Fi | Mobile data | Notes |
|-------|-------|-------------|-------|
| Google search | | | |
| Gmail | | | |
| Google Docs | | | |
| Telegram | | | |
| Instagram (optional) | | | |
| ya.ru | | | expect fast / direct |
| vk.com | | | |
| ipinfo.io or ifconfig.me | | | country shown |

---

## Stability

| Check | Result | Notes |
|-------|--------|-------|
| Lock 10–15 min → unlock | VPN still on? Y/N | |
| After unlock: Telegram | Y/N/P | |
| After unlock: Gmail/Docs | Y/N/P | |
| Wi‑Fi → mobile data switch | auto / one tap / broken | |
| Symptoms (reconnects, freezes, «no internet») | | |

---

## Verdict (owner pick one)

| | |
|-|-|
| **Overall** | PASS / SOFT PASS / FAIL |
| One-line why | |
| Date | |

### If SOFT PASS or FAIL — optional note

-

---

## For Cursor (paste chat summary)

Copy filled sections above or write:

```
Device:
Client:
Phase A Wi-Fi: Google/Gmail/Docs/TG =
Speed Wi-Fi VPN:
Lock/unlock:
Phase C mobile data:
Verdict:
```
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--write",
        type=Path,
        default=Path(".local/mobile_smoke_results.md"),
        help="write template (default: .local/mobile_smoke_results.md)",
    )
    ap.add_argument("--stdout", action="store_true", help="print to stdout instead of file")
    args = ap.parse_args()
    text = TEMPLATE.format(today=date.today().isoformat())
    if args.stdout:
        sys.stdout.write(text)
    else:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(text, encoding="utf-8")
        print(f"Wrote: {args.write}")
    print("MOBILE_SMOKE_TEMPLATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
