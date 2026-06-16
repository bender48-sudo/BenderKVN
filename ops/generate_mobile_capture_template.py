#!/usr/bin/env python3
"""Generate owner daily capture notes template (CLIENT-MOBILE-DAILY-CAPTURE-001).

Local only — writes to .local/ by default. No secrets, no network calls.

Usage:
    python ops/generate_mobile_capture_template.py
    python ops/generate_mobile_capture_template.py --write .local/mobile_capture_notes_2026-06-16.md
    python ops/generate_mobile_capture_template.py --date 2026-06-16 --stdout
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

TEMPLATE = """# Mobile capture notes — {day}

**Task:** CLIENT-MOBILE-DAILY-CAPTURE-001  
**Generated:** {generated_at}  
**Runbook:** docs/CLIENT-MOBILE-OBSERVABILITY-PLAN.md §9

> Keep in `.local/` only. Do not commit. No subscription URLs, QR, tokens, or UUIDs.

---

## Device

| Field | Your answer |
|-------|-------------|
| Phone model | |
| OS + version | |
| Happ version | |
| Profile name | BenderVPN Auto |
| Routing profile active | BenderVPN RU — Y / N |

---

## Instability event

| Field | Your answer |
|-------|-------------|
| Start time (local) | HH:MM |
| End time or «still bad» | HH:MM / ongoing |
| Network | Wi‑Fi / LTE / switched |
| Phone state | active use / after sleep-unlock / other |
| Apps affected | Telegram / Instagram / browser / all |
| Happ showed | connected / disconnected / unknown |
| Manual reconnect helped? | Y / N / not tried |
| One-line symptom | |

---

## Exports (fill after copying files to PC)

| File | Exported? | Local path under `.secrets/diagnostics/` |
|------|-----------|------------------------------------------|
| access_log (after bad period) | Y / N | |
| subscription_log (after bad period) | Y / N | |
| access_log (end of day) | Y / N | |
| subscription_log (end of day) | Y / N | |
| core / app log (if offered) | Y / N | |

**Suggested names:**

- `access_log_{day_compact}_HHMM_after_bad_period.txt`
- `subscription_log_{day_compact}_HHMM_after_bad_period.txt`
- `notes_{day}.md` (this file)

---

## Timeline notes (no secrets)

Add lines as events happen:

```
{day} HH:MM — symptom started (app, network)
{day} HH:MM — locked phone
{day} HH:MM — unlocked, waited ~Xs until usable
{day} HH:MM — exported Happ logs
```

---

## For PC analysis (after export)

```powershell
cd D:\\Va\\projects\\VPN
python ops/generate_mobile_capture_template.py --date {day}
python ops/analyze_mobile_logs.py --fullday --validate-coverage --correlate --day {day} `
  --access .secrets/diagnostics/access_log_{day_compact}_HHMM_after_bad_period.txt `
  --subscription .secrets/diagnostics/subscription_log_{day_compact}_HHMM_after_bad_period.txt `
  --owner-note "{day} HH:MM unstable started" `
  --out .local/mobile_observability_report_{day}.md
```

Check `access_percent_day` in report. **≥50%** or **two exports same day** helps diagnosis.

---

## Do not send

- Screenshots with subscription QR or link
- Subscription URL / token / UUID
- Raw logs in public chat (use `.secrets/diagnostics/` on your PC only)
"""


def render_template(*, day: str | None = None) -> str:
    d = day or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        raise ValueError(f"invalid date: {d!r}, expected YYYY-MM-DD")
    day_compact = d.replace("-", "")
    return TEMPLATE.format(
        day=d,
        day_compact=day_compact,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def default_output_path(day: str | None = None) -> Path:
    d = day or date.today().isoformat()
    return Path(f".local/mobile_capture_notes_{d}.md")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="Target day YYYY-MM-DD (default: today)")
    ap.add_argument(
        "--write",
        type=Path,
        nargs="?",
        const=None,
        help="Write template (default path: .local/mobile_capture_notes_DATE.md)",
    )
    ap.add_argument("--stdout", action="store_true", help="Print to stdout instead of file")
    args = ap.parse_args()

    text = render_template(day=args.date)
    if args.stdout:
        sys.stdout.write(text)
    else:
        out = args.write if args.write is not None else default_output_path(args.date)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote: {out}")
    print("MOBILE_CAPTURE_TEMPLATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
