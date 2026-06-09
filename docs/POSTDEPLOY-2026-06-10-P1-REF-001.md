# POSTDEPLOY — P1-REF-001 Web email referral attribution

**Date:** 2026-06-09 ~13:25 UTC (backup suffix `20260609-132523`)  
**Target:** AMS `168.100.11.140` · container **`remna-shop-bot`**  
**Approval:** `G1 Candidate D soak PASS. approve AMS deploy P1-REF-001`  
**Command:** `pwsh -File ops/deploy-portal-web-trial-ams.ps1` → **`DEPLOY_PORTAL_WEB_TRIAL_AMS_OK`**  
**Rollback:** Not used (backups available)  
**Related:** [`DEPLOY-P1-REF-001.md`](DEPLOY-P1-REF-001.md), commits `62aea49`, `efa2f07`

---

## 1. Deploy scope (actual)

| File | Pre-deploy | Post-deploy |
|------|------------|-------------|
| `web_referral.py` | **Absent** | **Present** (new) |
| `portal_web_trial.py` | Present | Updated (`apply_web_referral`) |
| `web_tg_bind.py` | Present | Updated (referral merge on bind) |
| `web_trial_db.py` | Present | Updated (batch unchanged functionally) |
| `webhook_server/app.py` | `ref_code` **0** matches | `ref_code` **2** matches |

**Not touched:** Remna template, Caddy, broadcast, mass-refresh, portal/guide/Karing.

---

## 2. Backups / rollback

Host backups created by deploy script:

- `/opt/remna-shop/src/shop_bot/*.before-web-trial-20260609-132523`
- `/opt/remna-shop/src/shop_bot/webhook_server/app.py.before-web-trial-20260609-132523`

Rollback procedure: [`DEPLOY-P1-REF-001.md`](DEPLOY-P1-REF-001.md) §4.

---

## 3. Container / env

| Check | Result |
|-------|--------|
| Container restart | **Success** — `remna-shop-bot` Up after deploy |
| Startup logs | Flask :1488, polling started; **no import errors** |
| `WEB_TRIAL_DAYS` | **1** (redacted in logs) |
| `REMNA_TRIAL_DAYS` | **90** (unchanged) |
| Referral bonus | **Not granted** |

**Unrelated:** Remna API timeout warnings in monitor logs (pre-existing).

---

## 4. Smoke (immediate)

| Test | Result |
|------|--------|
| Invalid email → `/portal-web-trial` | **HTTP 400** `invalid_email` (not 500) |
| `web_referral.py` in container | **Present** |
| `py_compile` deployed modules | **OK** |
| Deploy script health curl | **409** for `healthcheck@example.invalid` (already claimed; non-fatal) |

Repeatable AMS host check: `python3 ops/smoke_p1_ref_deploy_ams.py` (run **on AMS** only; creates test emails).

---

## 5. Live verification (controlled)

Run on AMS after deploy via `ops/smoke_p1_ref_deploy_ams.py`:

| Check | Result |
|-------|--------|
| Valid `ref_code` web trial | **HTTP 200**, `ok: true`, **`referral_linked: true`**, **`days: 1`** |
| DB `users.referred_by` | **Matches referrer ref code string** (not TG id) |
| Invalid `ref_code` | **HTTP 200**, `ok: true`, **`referral_linked: false`** |
| Referral bonus | **None** |
| Logs | **Clean** (no stack traces; no secrets observed) |

**Test artifacts created on prod DB:**

- `p1diag-*@bendervpn-smoke.invalid` — controlled smoke emails (low impact; optional cleanup later)

---

## 6. Remaining verification gaps

| Gap | Status |
|-----|--------|
| **TG bind migration** (web surrogate → TG user, `referrals` row migrate) | **NOT RUN** — preparation complete 2026-06-09; **owner Telegram bind pending** (see §9) |
| **Telegram `/start ref_*` path** | **Not re-tested live** this deploy; code path unchanged. |
| **G1 48h detailed device log** | **Incomplete in repo** — owner verbal PASS at deploy gate; continue 24–48h VPN monitoring. |

---

## 9. TG bind verification (controlled)

**Status:** **NOT RUN** (2026-06-09) — agent cannot complete Telegram UI bind without owner session.

### Preparation (completed)

| Field | Value (redacted) |
|-------|------------------|
| Timestamp | 2026-06-09 ~14:18 UTC (AMS) |
| Test email | `p1bind-****@bendervpn-smoke.invalid` |
| Web surrogate | negative `web_user_id` (smoke) |
| Referrer ref prefix | `jHGK****` |
| Web `referred_by` | **Matches referrer ref code string** before bind |
| Trial API | HTTP 200, `ok: true`, **`referral_linked: true`**, **`days: 1`** |
| `bind_token` | prefix `ef549b****` (full token not stored in repo) |

### Owner action required

1. Use an **owner-controlled Telegram account** with **no existing VPN keys** and **no conflicting `referred_by`** (or accept PARTIAL PASS if guard blocks overwrite).
2. Open the bot bind deep link: `https://t.me/Bender_KVN_bot?start=bind_<token>` (token from AMS prepare output only — not committed).
3. Complete bind in Telegram (`/start bind_*` flow).
4. On AMS, verify DB:
   ```bash
   python3 /tmp/smoke_p1_ref_tg_bind_ams.py verify --email-prefix p1bind-
   ```
   Expect: web surrogate deleted, TG user has `referred_by`, `referrals.referred_user_id` on TG id.

### Expected after successful bind

- Web surrogate user row **removed**
- TG user **`referred_by`** = web ref code string (if TG had none)
- **`referrals.referred_user_id`** migrated web surrogate → TG id
- **No** referral bonus / balance change
- **`REMNA_TRIAL_DAYS=90`**, **`WEB_TRIAL_DAYS=1`** unchanged

### If TG user already has different `referred_by`

Record **PARTIAL PASS** — guard must not overwrite; full migration path not exercised.

---

## 7. Post-deploy soak (24–48h)

Monitor:

- `/portal-web-trial` 5xx rate and webhook errors
- New `referrals` / `referred_by` anomalies vs support tickets
- Candidate D VPN stability (reconnect / refresh / sleep-resume)

No mass user action required.

---

## 8. Outcome

**P1-REF-001 AMS deploy: SUCCESS.** Web email `ref_code` attribution is **live** on AMS.

**TG bind referral migration:** preparation **complete**; **live bind NOT RUN** — owner Telegram session required (POSTDEPLOY §9).
