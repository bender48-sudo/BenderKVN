# DEPLOY — P1-REF-001 Web email referral attribution

**Fix commit:** `62aea49` — `fix(bot): wire web email ref_code to referred_by attribution`
**Deploy target:** AMS **`remna-shop-bot` only** (hot-patch host tree + `docker cp` + restart)
**Script:** `ops/deploy-portal-web-trial-ams.ps1`
**Post-deploy report:** [`POSTDEPLOY-2026-06-10-P1-REF-001.md`](POSTDEPLOY-2026-06-10-P1-REF-001.md) — **deployed 2026-06-09 ~13:25 UTC**
**Gate:** G1 owner-approved PASS (verbal, 2026-06-09) per [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md) §7.

---

## 1. Scope

| In scope | Out of scope |
|----------|--------------|
| `bot_src/web_referral.py` (**new — required**) | Portal / guide / Karing copy |
| `bot_src/portal_web_trial.py` | Remna template PATCH |
| `bot_src/web_tg_bind.py` | Caddy reload |
| `bot_src/webhook_server/app.py` (full app, includes `ref_code` extract) | Broadcast / mass-refresh |
| `bot_src/web_trial_db.py` (existing trial batch) | DB migration |
| | Backfill of existing users |
| | Referral purchase bonus (MVP) |

**No DB migration.** Schema columns `users.referred_by` and table `referrals` already exist.  
**No backfill.** Deploy does not mutate existing user rows.  
**No existing-user mutation on deploy** — only new web trials and explicit TG bind merges at runtime.

---

## 2. Pre-deploy checklist

1. **G1:** Owner Happ soak logged PASS in [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md) §7, or explicit owner risk acceptance.
2. **Push:** Fix + deploy-tooling commits on `origin/product-referral-cabinet-ui-v1`.
3. **Local verify:** `python ops/test_web_referral_attribution.py` → `WEB_REFERRAL_ATTRIBUTION_OK`.
4. **Working tree:** No accidental `.secrets/`, `.cursor/`, or screenshot commits.
5. **Approval phrase:** `approve AMS deploy P1-REF-001`
6. **Snapshot AMS** (before run): host copies get `*.before-web-trial-<ts>` from deploy script for:
   - `portal_web_trial.py`, `web_trial_db.py`, `web_tg_bind.py`, **`web_referral.py`**, `webhook_server/app.py`
7. **Env names only (do not change values):** `PORTAL_WEB_TRIAL_SECRET`, `WEB_TRIAL_DAYS=1`, `REMNA_TRIAL_DAYS=90`.

---

## 3. Deploy command (owner-approved only)

From repo root on admin workstation:

```powershell
pwsh -File ops/deploy-portal-web-trial-ams.ps1
```

Post-run smoke: `python ops/smoke_web_trial_browser.py` (optional). On AMS host: `python3 ops/smoke_p1_ref_deploy_ams.py` (creates `p1diag-*@bendervpn-smoke.invalid` test rows).

Script verifies inside container:

- `/portal-web-trial` route present
- `ref_code` present in webhook `app.py`
- `web_referral.py` file exists

---

## 4. Rollback

Restore from host backups created by script (`*.before-web-trial-<ts>`):

```bash
SB=/opt/remna-shop/src/shop_bot
WH=/opt/remna-shop/src/shop_bot/webhook_server
ts=<timestamp from backup filenames>
cp "$SB/web_referral.py.before-web-trial-$ts" "$SB/web_referral.py"
cp "$SB/portal_web_trial.py.before-web-trial-$ts" "$SB/portal_web_trial.py"
cp "$SB/web_tg_bind.py.before-web-trial-$ts" "$SB/web_tg_bind.py"
cp "$WH/app.py.before-web-trial-$ts" "$WH/app.py"
docker cp "$SB/web_referral.py" remna-shop-bot:/app/src/shop_bot/web_referral.py
docker cp "$SB/portal_web_trial.py" remna-shop-bot:/app/src/shop_bot/portal_web_trial.py
docker cp "$SB/web_tg_bind.py" remna-shop-bot:/app/src/shop_bot/web_tg_bind.py
docker cp "$WH/app.py" remna-shop-bot:/app/src/shop_bot/webhook_server/app.py
docker restart remna-shop-bot
```

If `web_referral.py` did not exist pre-deploy, rollback = remove file from host/container and restore prior `portal_web_trial.py` (no import).

Expected rollback time: ~1–2 minutes.

---

## 5. Live verification (post-deploy)

| # | Check | Pass |
|---|--------|------|
| A | Referrer user with known `ref_code` | Row in `users.ref_code` |
| B | Portal `/setup/?ref=<code>` | `localStorage.bvpn_ref_code` set (browser) |
| C | New test email web trial | HTTP 200, `ok: true` |
| D | Valid `ref_code` | Response `referral_linked: true` |
| E | DB web surrogate | `users.referred_by` = **referrer ref code string** (not TG id) |
| F | Invalid `ref_code` | Trial succeeds; `referral_linked: false`; `referred_by` NULL |
| G | Bind web → Telegram | **FAIL** — two owner bind reports; AMS DB still NOT_BOUND; no `web_tg_bind` actions (POSTDEPLOY §9) |
| H | `referrals` table | **FAIL** — migration not observed; clean-account bind retry required |
| I | Telegram trial path | Still **90d** (`REMNA_TRIAL_DAYS`) |
| J | Email web trial | Still **1d** (`WEB_TRIAL_DAYS`) |
| K | Referral bonus | Not granted or promised |
| L | Logs | No stack traces; no secrets in log lines |

---

## 6. Post-deploy soak (24–48h)

- Webhook error rate on `/portal-web-trial`
- New `referrals` rows vs support tickets
- No mass user action required

---

## 7. Deploy no-go

- G1 not PASS and owner has not accepted risk
- `web_referral.py` missing from deploy batch
- P1 regression tests fail
- Secret scan fails on changed deploy files
- Rollback path unclear
- Scope expands beyond AMS bot/webhook
