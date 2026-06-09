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
| **TG bind migration** (web surrogate → TG user, `referrals` row migrate) | **FAIL** — `p1bind2-` retest 2026-06-09; zero `funnel_bot_start bind:*`; see §9 |
| **Telegram `/start ref_*` path** | **Not re-tested live** this deploy; code path unchanged. |
| **G1 48h detailed device log** | **Incomplete in repo** — owner verbal PASS at deploy gate; continue 24–48h VPN monitoring. |

---

## 9. TG bind verification (controlled)

**Status:** **FAIL** (latest AMS read **2026-06-09 post–p1bind2- retest**) — owner reported bind completed for **`p1bind2-`** fresh trial; **DB still does not show bind**; **`funnel_bot_start bind:*` remains 0 (all time)**.

### Preparation (completed)

| Field | Value (redacted) |
|-------|------------------|
| Timestamp | 2026-06-09 ~14:18 UTC (AMS) |
| Test email | `p1bind-1781014699209728980@bendervpn-smoke.invalid` (prefix `p1bind-`) |
| Web surrogate | `web_user_id` negative (smoke) |
| Referrer ref prefix | `jHGK****` |
| Web `referred_by` before bind | **Matched referrer ref code string** |
| Trial API | HTTP 200, `ok: true`, **`referral_linked: true`**, **`days: 1`** |
| `bind_token` | prefix `ef549b****` (full token not stored in repo) |

### Verification attempt (2026-06-09 ~15:25 UTC)

Owner message: *«TG bind completed for p1bind- test. verify AMS bind migration.»*

Command on AMS:

```bash
python3 /tmp/smoke_p1_ref_tg_bind_ams.py verify --email-prefix p1bind-
```

**Result:** `P1_BIND_VERIFY_PENDING` / **NOT_BOUND**

| DB check | Observed |
|----------|----------|
| `web_trial_claims.telegram_id` | **NULL** |
| `web_trial_claims.bound_at` | **NULL** |
| Web surrogate user row | **Still exists** |
| `referrals` migration to TG id | **Not observed** |
| Other `*@bendervpn-smoke.invalid` trials | Also unbound (`p1diag-*`) |
| Container logs (tail) | No stack traces; no import errors; no secrets observed |

**Conclusion:** Web email referral attribution **PASS** remains valid. **TG bind migration path not verified live** — bind either did not persist, used a different token/trial, or failed silently in bot (e.g. `both_have_keys`, `already_bound_other`, invalid token).

### Verification attempt 2 (2026-06-09 ~15:30 UTC)

Owner message: *«TG bind completed for p1bind- test»* (retry after first FAIL).

Command on AMS:

```bash
python3 /tmp/smoke_p1_ref_tg_bind_ams.py verify --email-prefix p1bind-
```

**Result:** `P1_BIND_VERIFY_PENDING` / **NOT_BOUND** (same email as prepare)

| DB check | Observed |
|----------|----------|
| `web_trial_claims.telegram_id` | **NULL** |
| `web_trial_claims.bound_at` | **NULL** |
| Web surrogate user row | **Still exists** |
| `user_actions` `funnel_bot_start` with `bind:*` | **None** (no bind link opened on AMS bot DB) |
| `user_actions` `web_tg_bind` | **None** |
| Container logs (bind-related) | No `merge_web` / bind success lines; scheduler clean |

**Likely causes:** bind URL not opened in `@Bender_KVN_bot` **Telegram app**, wrong/expired token, or bind attempted with Telegram account that already has VPN keys (`both_have_keys` — would still log `funnel_bot_start bind:***` if link opened). **Use a clean test Telegram account** with no existing keys.

**Dedicated bind-flow audit (2026-06-09):** [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) — bind never reached prod `/start bind_*` handler on prior attempts. **Not** a migration-code defect until bot entry is proven.

### Fresh retest — prepare (p1bind2-, 2026-06-09 ~15:46 UTC)

| Field | Value (redacted) |
|-------|------------------|
| Test email | `p1bind2-1781019986458956739@bendervpn-smoke.invalid` (prefix **`p1bind2-`**) |
| Trial API | HTTP 200, `ok: true`, **`referral_linked: true`**, **`days: 1`** |
| Referrer ref prefix | `jHGK****` |
| Web `referred_by` before bind | **Matched referrer ref code string** |
| `bind_token` | prefix `6f90a8****` |
| Token expiry | `2026-06-10T15:46:26Z` (valid at verify time) |
| Bot username in link | `Bender_KVN_bot` |

### Verification attempt 3 — p1bind2- (2026-06-09, after owner «TG bind completed»)

Owner message: *«TG bind completed for p1bind2- test. verify AMS bind migration.»*

Command on AMS:

```bash
python3 /tmp/smoke_p1_ref_tg_bind_ams.py verify --email-prefix p1bind2-
```

**Result:** `P1_BIND_VERIFY_PENDING` / **NOT_BOUND**

| Check | Observed |
|-------|----------|
| `funnel_bot_start` `bind:*` (all time) | **0 rows** — bind `/start` never logged on AMS |
| `funnel_bot_start` after p1bind2 prepare (≥15:46 UTC) | **0 rows** |
| `web_tg_bind` | **0 rows (all time)** |
| `web_trial_claims.telegram_id` | **NULL** |
| `web_trial_claims.bound_at` | **NULL** |
| `bind_token` | **Still present** (prefix `6f90a8****` — not consumed) |
| Web surrogate user row | **Still exists** |
| `referrals.referred_user_id` → TG id | **Not migrated** |
| Referral bonus / balance change | **None** |
| `WEB_TRIAL_DAYS` / `REMNA_TRIAL_DAYS` | **1** / **90** (unchanged) |
| Container logs | Scheduler clean; no bind merge lines; no secrets observed |
| Owner bot response text | **Not provided** — cannot classify conflict/invalid/terms |

**Conclusion:** Third owner bind report; **same failure mode as `p1bind-`** — Telegram deep link did not produce a recorded `/start bind_*` on prod bot. Web email referral attribution **PASS** unchanged. §9 **not closed**.

### Owner retry (required to close §9)

1. Use **dedicated test Telegram account** — no existing VPN keys; no conflicting `referred_by` unless accepting PARTIAL PASS.
2. Open **fresh** bind link from latest `prepare` (prefix **`p1bind2-`** or new `p1bind3-` if token ages out).
3. Open link **inside Telegram app** (not browser preview); tap **Start**; accept terms if prompted.
4. **Send exact bot reply text** (or screenshot) + UTC timestamp to operator before DB verify.
5. Re-run on AMS:
   ```bash
   python3 /tmp/smoke_p1_ref_tg_bind_ams.py verify --email-prefix p1bind2-
   ```
   Expect: **`P1_BIND_VERIFY_OK`** only after step 4 shows success message.

### Expected after successful bind

- Web surrogate user row **removed**
- TG user **`referred_by`** = web ref code string (if TG had none)
- **`referrals.referred_user_id`** migrated web surrogate → TG id
- **No** referral bonus / balance change
- **`REMNA_TRIAL_DAYS=90`**, **`WEB_TRIAL_DAYS=1`** unchanged

### If TG user already has different `referred_by`

Record **PARTIAL PASS** — guard must not overwrite; document limitation.

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

**TG bind referral migration:** **FAIL** on AMS DB after **`p1bind2-` retest** — see POSTDEPLOY §9. Web trial referral attribution remains **PASS**. Device/balance UX audit: [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md).
