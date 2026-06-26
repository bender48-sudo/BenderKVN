#!/usr/bin/env python3
"""One-pass GATED post-deploy smoke for the Mini App endpoints on AMS (read-only).

Run ON the AMS3 host (168.100.11.52) after deploying the bot. Hits each new /portal-* route on the
localhost webhook (:1488) with the portal secret and asserts the **gated-off** contract:
no real money / no accruals / no tickets / no spins — exactly what we expect before any flag flip.

It does NOT flip flags, create real payments, or write anything user-visible (a ticket create is
expected to be refused with support_disabled while SUPPORT_TICKETS_LIVE is off). Idempotent.

Usage (on AMS):  python3 smoke_miniapp_gated_ams.py [--tid <telegram_id>]
Exit code 0 = all checks pass; non-zero = at least one mismatch.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

WEBHOOK = "http://127.0.0.1:1488"
ENV_PATH = "/opt/remna-shop/.env"
CONTAINER = "remna-shop-bot"
DB = "/app/data/shop_bot.db"


def _secret() -> str:
    try:
        for line in open(ENV_PATH, encoding="utf-8", errors="replace"):
            if line.startswith("PORTAL_WEB_TRIAL_SECRET="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _sample_tid() -> int:
    """Pick an existing terms-agreed user so identity resolves for create/ticket paths."""
    py = (
        "import sqlite3;c=sqlite3.connect('%s');"
        "r=c.execute(\"SELECT telegram_id FROM users WHERE agreed_to_terms=1 AND telegram_id>0 LIMIT 1\").fetchone();"
        "print(r[0] if r else 0)" % DB
    )
    try:
        out = subprocess.check_output(["docker", "exec", CONTAINER, "python", "-c", py], text=True)
        return int(out.strip() or "0")
    except Exception:
        return 0


def _post(path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        WEBHOOK + path,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-Portal-Web-Trial-Key": _secret()},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"ok": False, "raw": raw[:200]}
    except Exception as e:  # connection refused etc.
        return 0, {"ok": False, "error": f"request_failed:{e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tid", type=int, default=0)
    args = ap.parse_args()
    tid = args.tid or _sample_tid()
    if not tid:
        print("NO_SAMPLE_USER_IN_DB — pass --tid <telegram_id>")
        return 1
    print(f"=== Mini App gated smoke · AMS · tid={tid} ===")

    ID = {"telegram_id": tid}
    # (name, path, body, expected_status, predicate(doc)->bool, human note)
    checks = [
        ("home", "/portal-home", ID, 200,
         lambda d: d.get("ok") and d.get("unread") == 0 and "access" in d and "banners" in d,
         "ok, unread=0, has access/banners"),
        ("tariff", "/portal-tariff", {}, 200,
         lambda d: d.get("ok") and d.get("payments_live") is False,
         "payments_live=false"),
        ("transactions", "/portal-transactions", ID, 200,
         lambda d: d.get("ok") is True,
         "ok (Phase A history)"),
        ("create-payment(gated)", "/portal-create-payment", {**ID, "amount_rub": 600}, 403,
         lambda d: d.get("error") == "payments_disabled",
         "payments_disabled"),
        ("referral", "/portal-referral", ID, 200,
         lambda d: d.get("ok") and d.get("earned_rub") == 0
                   and (d.get("program") or {}).get("rewards_active") is False,
         "earned 0, rewards_active=false"),
        ("cabinet(GAP keys)", "/portal-cabinet", ID, 200,
         lambda d: d.get("ok") and _cfg_has_gap_keys(d),
         "configurations[] carry last_client/subscription_url keys"),
        ("tickets(gated)", "/portal-tickets", ID, 200,
         lambda d: d.get("ok") and d.get("support_live") is False and d.get("tickets") == [],
         "support_live=false, empty"),
        ("unread", "/portal-unread", ID, 200,
         lambda d: d.get("ok") and d.get("count") == 0,
         "count=0"),
        ("ticket-create(gated)", "/portal-ticket", {**ID, "subject": "connection", "text": "smoke"}, 403,
         lambda d: d.get("error") == "support_disabled",
         "support_disabled"),
        ("ticket-get(gated)", "/portal-ticket-get", {**ID, "ticket_id": 1}, 403,
         lambda d: d.get("error") == "support_disabled",
         "support_disabled"),
        ("ticket-message(gated)", "/portal-ticket-message", {**ID, "ticket_id": 1, "text": "x"}, 403,
         lambda d: d.get("error") == "support_disabled",
         "support_disabled"),
        ("fortune", "/portal-fortune", ID, 200,
         lambda d: d.get("ok") and d.get("fortune_live") is False,
         "fortune_live=false"),
        ("fortune-spin(gated)", "/portal-fortune-spin", ID, 403,
         lambda d: d.get("error") == "fortune_disabled",
         "fortune_disabled"),
    ]

    failed = 0
    for name, path, body, exp_status, pred, note in checks:
        status, doc = _post(path, body)
        ok_status = status == exp_status
        ok_pred = False
        try:
            ok_pred = bool(pred(doc))
        except Exception:
            ok_pred = False
        ok = ok_status and ok_pred
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{flag}] {name:24s} http={status}(exp {exp_status}) · {note}")
        if not ok:
            print(f"        got: {json.dumps(doc, ensure_ascii=False)[:240]}")

    print(f"=== {'ALL GATED CHECKS PASS' if not failed else f'{failed} CHECK(S) FAILED'} ===")
    return 0 if failed == 0 else 2


def _cfg_has_gap_keys(doc: dict) -> bool:
    cfgs = doc.get("configurations") or []
    if not cfgs:
        return True  # no devices → nothing to assert (still a pass)
    c = cfgs[0]
    return all(k in c for k in ("last_client", "last_client_os", "last_fetch_at_iso", "subscription_url"))


if __name__ == "__main__":
    sys.exit(main())
