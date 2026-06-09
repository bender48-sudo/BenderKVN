#!/usr/bin/env python3
"""AMS host post-deploy smoke for P1-REF-001.

Run on AMS only (SSH to 168.100.11.140):
  python3 ops/smoke_p1_ref_deploy_ams.py

Reads PORTAL_WEB_TRIAL_SECRET from /opt/remna-shop/.env (not from repo).
Creates controlled test emails *@bendervpn-smoke.invalid and issues web trials.
Prints ref_code prefixes redacted. Does not bind Telegram.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request


def _secret() -> str:
    for line in open("/opt/remna-shop/.env", encoding="utf-8", errors="replace"):
        if line.startswith("PORTAL_WEB_TRIAL_SECRET="):
            return line.split("=", 1)[1].strip()
    return ""


def _db_query(sql: str, params: tuple = ()) -> list[str]:
    py = (
        "import sqlite3,sys;"
        f"c=sqlite3.connect('/app/data/shop_bot.db');"
        f"rows=c.execute({sql!r}, {params!r}).fetchall();"
        "[print('\t'.join(str(x) if x is not None else '' for x in r)) for r in rows]"
    )
    out = subprocess.check_output(
        ["docker", "exec", "remna-shop-bot", "python", "-c", py],
        text=True,
    )
    return [ln for ln in out.strip().splitlines() if ln]


def _post(payload: dict) -> tuple[int, dict]:
    secret = _secret()
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:1488/portal-web-trial",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Portal-Web-Trial-Key": secret,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"ok": False, "raw": raw[:200]}


def main() -> int:
    refs = _db_query(
        "SELECT telegram_id, ref_code FROM users WHERE ref_code IS NOT NULL AND ref_code != '' LIMIT 5"
    )
    print("REF_CODES_SAMPLE:")
    for ln in refs:
        parts = ln.split("\t")
        print(f"  tg={parts[0]} ref_prefix={parts[1][:4]}****")

    all_refs = _db_query(
        "SELECT ref_code, telegram_id FROM users WHERE ref_code IS NOT NULL AND ref_code != '' ORDER BY telegram_id DESC LIMIT 1"
    )
    if not all_refs:
        print("NO_REFERRER")
        return 1
    ref, tg = all_refs[0].split("\t", 1)
    print(f"CONTROLLED_REF_PREFIX={ref[:4]}**** tg={tg}")

    em = f"p1diag-{time.time_ns()}@bendervpn-smoke.invalid"
    code, doc = _post({"email": em, "ref_code": "bad code!"})
    print(f"INVALID_REF http={code} ok={doc.get('ok')} referral_linked={doc.get('referral_linked')} error={doc.get('error')}")
    if code == 500:
        return 1
    if doc.get("ok") and doc.get("referral_linked") is not False:
        print("INVALID_REF_EXPECTED_FALSE")
        return 1

    em2 = f"p1diag-ok-{time.time_ns()}@bendervpn-smoke.invalid"
    code2, doc2 = _post({"email": em2, "ref_code": ref})
    print(f"VALID_REF http={code2} ok={doc2.get('ok')} referral_linked={doc2.get('referral_linked')} days={doc2.get('days')}")
    if not doc2.get("ok") or doc2.get("referral_linked") is not True:
        print("VALID_REF_FAIL")
        return 1
    if int(doc2.get("days") or 0) != 1:
        print("DAYS_NOT_1")
        return 1

    rows = _db_query(
        "SELECT web_user_id FROM web_trial_claims WHERE contact_email=? LIMIT 1",
        (em2,),
    )
    if not rows:
        print("NO_CLAIM_ROW")
        return 1
    web_uid = rows[0]
    rb_rows = _db_query(
        "SELECT referred_by FROM users WHERE telegram_id=?",
        (int(web_uid),),
    )
    rb = rb_rows[0] if rb_rows else ""
    print(f"DB web_uid={web_uid} referred_by_prefix={rb[:4]}**** match={rb == ref}")
    if rb != ref:
        return 1

    subprocess.run(
        ["grep", "-E", "^(WEB_TRIAL_DAYS|REMNA_TRIAL_DAYS)=", "/opt/remna-shop/.env"],
        check=False,
    )
    print("P1_REF_DIAG_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
