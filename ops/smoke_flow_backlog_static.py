#!/usr/bin/env python3
"""Static smokes for flow Q044-Q050."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ru = json.loads((ROOT / "web/portal/content/ru.json").read_text(encoding="utf-8"))
    portal_js = (ROOT / "web/portal/assets/portal.js").read_text(encoding="utf-8")
    index = (ROOT / "web/portal/index.html").read_text(encoding="utf-8")
    css = (ROOT / "web/portal/assets/portal.css").read_text(encoding="utf-8")
    setup_svc = (ROOT / "ops/setup_verify_service.py").read_text(encoding="utf-8")
    handlers = (ROOT / "bot_src/handlers.py").read_text(encoding="utf-8")

    devices = ru.get("devices") or []
    if len(devices) < 4:
        print("PORTAL_DEVICE_BRANCHES_FAIL: need 4 devices", file=sys.stderr)
        return 1
    for d in devices:
        n = len(d.get("install_steps") or []) + len((ru.get("steps") or {}).get("after_device") or [])
        if n > 5:
            print(f"PORTAL_DEVICE_BRANCHES_FAIL: {d['id']} has {n} steps", file=sys.stderr)
            return 1
    if "trackFunnel" not in portal_js or "#device=" not in portal_js:
        print("PORTAL_DEVICE_BRANCHES_FAIL: portal.js routing", file=sys.stderr)
        return 1
    print("PORTAL_DEVICE_BRANCHES_OK")

    if "skip-link" not in index or "focus-visible" not in css or 'font-size: 18px' not in css:
        print("PORTAL_A11Y_FAIL", file=sys.stderr)
        return 1
    print("PORTAL_A11Y_OK")

    if "/funnel-event" not in setup_svc or "funnel_bot_start" not in handlers:
        print("FUNNEL_METRICS_FAIL", file=sys.stderr)
        return 1
    if not (ROOT / "docs/FUNNEL-METRICS.md").is_file():
        print("FUNNEL_METRICS_FAIL: missing wiki", file=sys.stderr)
        return 1
    print("FUNNEL_METRICS_OK")

    if not (ROOT / "docs/RUNBOOK-BACKUP-BOOTSTRAP-DOMAIN.md").is_file():
        print("BACKUP_BOOTSTRAP_DOMAIN_FAIL", file=sys.stderr)
        return 1
    print("BACKUP_BOOTSTRAP_DOMAIN_OK")

    if "portal_cabinet" not in (ROOT / "bot_src/webhook_server/app.py").read_text(encoding="utf-8"):
        print("PORTAL_CABINET_BALANCE_FAIL: route", file=sys.stderr)
        return 1
    if "/cabinet" not in setup_svc or "loadCabinetBalance" not in portal_js:
        print("PORTAL_CABINET_BALANCE_FAIL: wiring", file=sys.stderr)
        return 1
    print("PORTAL_CABINET_BALANCE_OK")

    if not (ROOT / "bot_src/web_tg_bind.py").is_file():
        print("WEB_TG_BIND_FAIL", file=sys.stderr)
        return 1
    print("WEB_TG_BIND_OK")

    if "cabinet-web-notify" not in index or "portal_view_home" not in portal_js:
        print("WEB_NOTIFY_CHANNEL_FAIL", file=sys.stderr)
        return 1
    print("WEB_NOTIFY_CHANNEL_OK")

    print("FLOW_BACKLOG_STATIC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
