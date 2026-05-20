#!/usr/bin/env python3
"""Repo check: web email trial is 1 day, bot trial stays 90."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cfg = (ROOT / "bot_src" / "config.py").read_text(encoding="utf-8")
    trial_py = (ROOT / "bot_src" / "portal_web_trial.py").read_text(encoding="utf-8")
    tmpl = (ROOT / "compose" / "ams" / "remna-shop" / "bot.env.tmpl").read_text(encoding="utf-8")

    if 'WEB_TRIAL_DAYS = int(os.getenv("WEB_TRIAL_DAYS", "1"))' not in cfg:
        print("FAIL: WEB_TRIAL_DAYS default 1 missing in config.py", file=sys.stderr)
        return 1
    if "days=WEB_TRIAL_DAYS" not in trial_py:
        print("FAIL: portal_web_trial must use WEB_TRIAL_DAYS", file=sys.stderr)
        return 1
    if "days=REMNA_TRIAL_DAYS" in trial_py:
        print("FAIL: portal_web_trial still uses REMNA_TRIAL_DAYS", file=sys.stderr)
        return 1
    if "trial_expired" not in trial_py:
        print("FAIL: recover must return trial_expired", file=sys.stderr)
        return 1
    if not re.search(r"^WEB_TRIAL_DAYS=1\s*$", tmpl, re.M):
        print("FAIL: bot.env.tmpl WEB_TRIAL_DAYS=1", file=sys.stderr)
        return 1
    print("WEB_TRIAL_DAYS_CONFIG_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
