# Mini App — staging deploy checklist (PLAN ONLY, not applied)

**Status:** plan only. **Nothing applied. Prod untouched.** All money/mutation gates stay **OFF**.
Branch: `product-referral-cabinet-ui-v1`. Apply on staging first; prod alongside the old cabinet
with a one-flip rollback. Basis: `MINI-APP-BALANCE-DEPLOY-WIRING.md` (same proxy pattern).

Request path (unchanged): `browser /setup/api/<x>` → Caddy LV `handle /setup/api/*` strip-prefix
→ `setup_verify_service.py` (:8871, **explicit allowlist**) → `_ams_portal_post("/portal-<x>")`
(SSH curl to AMS bot :1488, injects `X-Portal-Web-Trial-Key`) → bot webhook `/portal-<x>`.

---

## 1. Proxy allowlist — add new paths to `ops/setup_verify_service.py` (`do_POST`)

Today the proxy forwards only: `/funnel-event /telegram-setup /cabinet /web-trial /web-trial-recover`.
**Every new Mini App endpoint needs an allowlist block** (mirror the existing `/cabinet` block:
read JSON body → `_ams_portal_post("/portal-<x>", body)` → relay status). All are POST; identity is
in the body (telegram_id / customer_id / email), same as `/cabinet`.

| Proxy path (`/setup/api/…`) | → AMS bot route | Body | Notes |
|---|---|---|---|
| `/tariff` | `/portal-tariff` | `{}` | balance (was documented, never applied) |
| `/transactions` | `/portal-transactions` | id | balance |
| `/create-payment` | `/portal-create-payment` | id+amount_rub | balance |
| `/referral` | `/portal-referral` | id | |
| `/home` | `/portal-home` | id | |
| `/tickets` | `/portal-tickets` | id | |
| `/ticket` | `/portal-ticket` | id+subject+text | |
| `/ticket-get` | `/portal-ticket-get` | id+ticket_id | |
| `/ticket-message` | `/portal-ticket-message` | id+ticket_id+text | |
| `/unread` | `/portal-unread` | id | |
| `/fortune` | `/portal-fortune` | id | |
| `/fortune-spin` | `/portal-fortune-spin` | id | |

- **`/cabinet` already forwarded — no proxy change.** The Access GAP fields are **already coded**
  (Cursor, 20 tests): `bot_src/portal_cabinet.py` now returns `subscription_url`, `last_client`,
  `last_client_os`, `last_client_version`, `last_fetch_at_iso` per `configurations[]` (+ its DB
  layer). **Deploy `portal_cabinet.py` (+ database/subscription_profile) in THIS pass** → the Access
  screen lights up immediately (real «Последний клиент» tags + per-config sub-link), no null-fallback.
  The deploy script's file list already includes `$PortalCabinet`, `$Database`, `$SubscriptionProfile`.
- Map error→HTTP codes already handled bot-side; the proxy just relays status.
- After editing: redeploy the unit (`ops/install-setup-verify-lv.sh` copies + restarts
  `bvpn-setup-verify.service`). **Staging box first.**

## 2. Migrations v8 / v9 / v10 (additive — CREATE only, reversible)

- v8 `balance_ledger` · v9 `tickets` + `ticket_messages` · v10 `fortune_spins`.
- Auto-apply on bot start (`initialize_db` → `run_schema_migrations`). **Back up the staging DB
  first** (`data/shop_bot.db`).
- Verify after restart: `schema_version = 10`; tables `balance_ledger, tickets, ticket_messages,
  fortune_spins` exist; no migration error in logs.

## 3. transactions → ledger switch + backfill  ⚠️ needs a small code change first

- **Backfill (ready):** `ops/backfill_balance_ledger.py` (idempotent) on the **staging** DB:
  `--dry-run` → review → apply. Populates `balance_ledger` from `user_actions` (topups/daily).
- **Source switch (NOT yet coded):** `portal_balance.build_transactions` still reads
  `get_balance_ledger` (= `user_actions`, Phase A). Switching `/portal-transactions` to the ledger
  needs a 1-function change (`build_transactions` → `get_ledger_entries`, map kinds incl.
  `fortune`/`referral_reward`). **Order: backfill → code change → deploy → verify**, else history
  shows empty.
- **Recommendation:** ship the app on **Phase A** first (works today); do the ledger switch as a
  follow-up once backfill is verified on staging. Mark this row **deferred** unless owner wants it now.

## 4. Flags — ALL OFF on staging (and prod)

| Env flag | Value | Gated behavior (expected) |
|---|---|---|
| `MINIAPP_PAYMENTS_LIVE` | unset/0 | `/create-payment` → `payments_disabled` |
| `REFERRAL_REWARDS_ACTIVE` | unset/0 | referral `earned_rub` 0, per-invitee `reward_rub` null |
| `SUPPORT_TICKETS_LIVE` | unset/0 | `/tickets` `support_live:false`, `/ticket` `support_disabled`, `/unread` 0; legacy DM bridge intact |
| `FORTUNE_LIVE` | unset/0 | `/fortune` `fortune_live:false`, `/fortune-spin` `fortune_disabled` |

Flipping any flag live = a **separate owner OK** per its gate (honest-gate / ledger / etc.).

## 5. Entry point — bot opens the new app, old cabinet = fallback

- Today: bot Mini App button → `config.telegram_cabinet_webapp_url()` → `/portal/cabinet.html` (old).
- **Change (make env-driven):** introduce `MINIAPP_ENTRY_PAGE` (default `cabinet.html`); set
  `home.html` on **staging**. Prod stays `cabinet.html` until verified, then flip.
- **Fallback:** `cabinet.html` stays deployed and functional; the new pages already link back to it
  on error states. The legacy web funnel (`setup.html`) and per-user DM support bridge are untouched.

## 6. Order of operations

**Bot host = AMS3 `168.100.11.52`** (not legacy `.140`). `ops/deploy-bot-handlers-ams.ps1` already
defaults to `.52` (override only via `BVPN_AMS_HOST`); container `remna-shop-bot`, webhook `:1488`,
DB `/app/data/shop_bot.db`, env `/opt/remna-shop/.env`.

1. **Staging:** back up DB → deploy bot (AMS `.52`, migrations apply) → apply proxy allowlist + restart
   `bvpn-setup-verify` (LV) → set `MINIAPP_ENTRY_PAGE=home.html` on staging.
2. **Verify on staging** (§7).
3. **Prod (alongside old, rollback-ready):** deploy bot + proxy, keep entry on `cabinet.html`, smoke
   the gated endpoints, then flip `MINIAPP_ENTRY_PAGE=home.html`. Migrations are additive (no data
   move) so a code rollback leaves the unused tables harmlessly.

## 7. Verification (staging) — must all pass before prod

- [ ] Bot restarts clean; `schema_version=10`; 4 new tables present; no migration error.
- [ ] App opens from the bot (home.html); home/balance/referral/access/support/fortune all render,
      0 console errors.
- [ ] Each endpoint via `/setup/api/<x>` returns the **gated** expectation from §4 (create-payment
      `payments_disabled`; referral earned 0; tickets `support_live:false` + `unread` 0; ticket create
      `support_disabled`; fortune `fortune_live:false`; fortune-spin `fortune_disabled`; home `unread:0`).
- [ ] **Old cabinet intact:** `cabinet.html` + `/setup/api/cabinet` + `/telegram-setup` still work;
      legacy support DM bridge still relays (SUPPORT_TICKETS_LIVE off).
- [ ] Access detail shows **real** GAP data — «Последний клиент: {app} · {os}» tags + per-config
      sub-link (Cursor's fields deployed); honest null-fallback only where a device truly has no fetch.
- [ ] (If §3 applied) `/transactions` shows backfilled history; otherwise Phase A history intact.
- [ ] Smoke scripts pass (mirror `ops/smoke_p1_*` per endpoint).

## 8. Rollback

- **Instant:** set `MINIAPP_ENTRY_PAGE=cabinet.html` (bot reopens the old cabinet).
- Proxy allowlist additions are additive/harmless; revert the file + restart if needed.
- Bot redeploy: revert to the previous image/commit. **DB migrations are additive — leave them**
  (unused tables are inert). No data is destroyed at any step.

## Out of scope (separate owner OK / other party)

- Flipping any gate flag live (real money / referral accrual / live tickets / wheel payouts).
- Email transport for the first-ticket-reply duplicate (stub hook today).
- `/transactions` → ledger source switch code change (DEFERRED — ship on Phase A; ledger switch is a
  separate step after backfill is verified on staging).

_(Access GAP fields are now IN scope — see §1.)_
```
