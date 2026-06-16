#!/usr/bin/env python3
"""CLI alias for mobile log analysis (smoke + full-day deep-dive).

See ops/analyze_mobile_smoke_logs.py and ops/mobile_log_fullday.py.
"""
from analyze_mobile_smoke_logs import main

if __name__ == "__main__":
    raise SystemExit(main())
