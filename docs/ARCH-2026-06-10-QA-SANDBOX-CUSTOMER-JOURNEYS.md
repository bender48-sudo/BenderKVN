# ARCH — QA Sandbox for Customer Journey Scenarios

**ID:** QA-SANDBOX-001  
**Date:** 2026-06-10  
**Mode:** architecture + implementation plan · **no implementation** in this pass  
**Branch:** `product-referral-cabinet-ui-v1`  
**Parent:** [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md), [`ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md`](ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md)  
**Skill:** `.cursor/skills/bendervpn-journey-qa/SKILL.md` (manual Playwright checklist — not a sandbox)

**Parity principle:** Sandbox must exercise **the same application code paths** as production. Mocks sit only at **integration boundaries** (YooKassa writes, Remna provision, real subscription URLs). A passing sandbox run must mean high confidence post-deploy — not a toy environment with different business logic.

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **Problem** | Owner has one Telegram account on **prod bot** → always «existing user»; cannot safely exercise new-user, referral, trial-cap, temp, paid, expired journeys |
| **MVP recommendation** | **E — combination:** isolated **staging/local DB** + **real handlers/portal** + **boundary dry-runs** + **seed fixtures** + **Playwright/API matrix** |
| **Not acceptable** | Fake bot flows, fake portal screens, hardcoded trial UI unrelated to gate API |
| **Existing partial harness** | `admin_flow_test.py` (prod read-only + copy preview), `ops/test_web_referral_attribution.py` (temp DB + mock Remna), `.playwright-review/serve_portal.py` (static portal :8765) |
| **Staging bot** | Separate `@BotFather` token + `BVPN_ENV=staging` + isolated DB — **recommended** for owner E2E |
| **QA-GUARD-001** | **IMPLEMENTED** (repo) — `bot_src/runtime_env.py`; boundary guards in Remna/YooKassa |
| **Implementation** | **PARTIAL** — guards, seed, bot harness, portal fixtures, **scenario matrix** (repo); staging E2E + owner preview OPEN |

---

## 2. Current state (what exists)

| Artifact | What it does | Parity | Gap |
|----------|--------------|--------|-----|
| `bot_src/admin_flow_test.py` | Infra smoke, existing-user checks, newbie **logic** checks (no DB write) | Uses **real** DB read, real `cabinet_snapshot`, real Remna probe | Runs on **prod**; owner = one user; no synthetic states |
| `bot_src/admin_flow_guide.py` | Admin **copy/menu preview** for newbie/existing/web | Real keyboards/messages | **Not** state simulation; no referral/temp/paid matrix |
| `ops/test_web_referral_attribution.py` | Temp SQLite, real `link_referral` / `issue_web_trial`, mock `provision_key` | **Real** attribution handlers | No TG; no payment; single scenario |
| `.playwright-review/serve_portal.py` | Static portal on `127.0.0.1:8765` | **Real** `web/portal` files | No bot API; no dynamic gates/slots |
| `bendervpn-journey-qa` skill | Manual Playwright MCP scenarios | Live URL when used | Not automated; prod risk if misused |
| `tests/test_portal_cabinet_billing.py` | Cabinet API field unit tests | Real `portal_cabinet.py` | Fixture users only; no full journey |
| `ops/reconcile_yookassa_topups_ams.py` | Dry-run default | Prod read risk | Not a journey harness |

**Verdict:** Repo has **safe local-only patterns** (temp DB + mock Remna) worth extending — but **no** unified sandbox. **Do not implement** until owner approves QA-* backlog items.

---

## 3. Recommended sandbox architecture (MVP)

### 3.1 Option analysis

| Option | Description | Verdict |
|--------|-------------|---------|
| **A** | Staging bot token + staging DB | **Required** for owner Telegram E2E without prod mutation |
| **B** | Local dev + fake Telegram identities | **Required** for automated matrix (CLI injects `user_id` into real handlers) |
| **C** | Admin scenario switcher (non-prod only) | **Useful** owner preview layer on staging — must call real gates/APIs |
| **D** | Seeded fixtures + Playwright/API | **Required** for regression matrix |
| **E** | **Combination of A+B+C+D** | **MVP recommendation** |

### 3.2 Three-layer model

```text
┌─────────────────────────────────────────────────────────────┐
│ Layer 3 — Owner preview (staging admin / QA-OWNER-PREVIEW)   │
│   «Show me as trial user» → seeds + opens portal/bot URLs    │
├─────────────────────────────────────────────────────────────┤
│ Layer 2 — Staging Telegram bot (QA staging env)              │
│   Same bot image · BVPN_ENV=staging · staging DB · dry-run   │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 — Local CI matrix (QA-DB-SEED + pytest + Playwright) │
│   Temp/staging DB · synthetic tg_ids · mock YK/Remna edges   │
└─────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
    PRODUCTION-IDENTICAL: handlers, portal_cabinet, portal_web_trial,
    web_referral, config flags, DB schema, ru.json, routing
         ▼                    ▼                    ▼
    MOCKED BOUNDARIES ONLY: remnawave_api.provision_key (dry-run),
    YooKassa Payment.create / webhooks, real sub URLs, prod messaging
```

### 3.3 Environment model (QA-GUARD-001 implemented)

| Variable | Values | Rule |
|----------|--------|------|
| `BVPN_ENV` | `production` (default) \| `staging` \| `local` \| `test` | Unset = **production** — prod deploys unchanged |
| `BVPN_QA_DRY_RUN_REMNA` | `1` in staging/local | Required for `provision_key` / `add_extra_traffic` in non-prod |
| `BVPN_QA_DRY_RUN_PAYMENTS` | `1` in staging/local | Required for `payment_create` in non-prod |
| `BVPN_QA_TOOLS_ENABLED` | `1` | Required for QA seed/matrix ops scripts |
| `BVPN_PROD_DB_PATH` | Absolute path | QA tools reject this path in non-prod |
| `SHOP_BOT_DB_PATH` / `BVPN_QA_DB_PATH` | Staging/local DB file | Isolated DB; same schema as prod |
| `BVPN_QA_ALLOW_BROADCAST` | `1` optional | Override broadcast guard in staging only |
| `TELEGRAM_BOT_TOKEN` | Staging bot token | **Never** prod token in staging harness |
| `PUBLIC_PORTAL_ORIGIN` | Staging portal URL or `http://127.0.0.1:8765` | Same portal **build**, different origin |

**Guard module:** `shop_bot.runtime_env` — `get_bvpn_env()`, `require_non_production()`, `require_qa_tooling_enabled()`, `assert_remna_mutation_allowed()`, `assert_yookassa_write_allowed()`, `assert_broadcast_allowed()`, `assert_db_path_allowed_for_qa()`.

**Wired boundaries (repo):**

- `remnawave_api.provision_key`, `add_extra_traffic` → `assert_remna_mutation_allowed`
- `yookassa_payment.payment_create` → `assert_yookassa_write_allowed` (used by `handlers.py`, `yookassa_autopay.py`)

**Remna dry-run (QA-REMNA-DRYRUN-001 — implemented):**

- Module: `shop_bot.remna_dryrun`
- Enable: `BVPN_ENV=staging|local|test` + `BVPN_QA_DRY_RUN_REMNA=1`
- Never active when `BVPN_ENV=production` (even if flag set)
- Returns same tuple shape as `provision_key`: dummy `vless://…@sandbox.invalid`, `https://sandbox.invalid/sub/qa-{id}`, synthetic `expire_iso`, deterministic `vless_uuid`
- `add_extra_traffic` → `True`; `set_user_access_days` → synthetic `expireAt`
- **Not verified without real Remna:** routing, HWID, panel PATCH semantics, Happ import

**Payment dry-run (QA-PAYMENT-DRYRUN-001 — implemented):**

- Module: `shop_bot.yookassa_dryrun`
- Enable: `BVPN_ENV=staging|local|test` + `BVPN_QA_DRY_RUN_PAYMENTS=1`
- Never active when `BVPN_ENV=production` (even if flag set)
- Wired at `yookassa_payment.payment_create` only (handlers top-up/plan, `yookassa_autopay` bind/charge)
- Returns `DryRunPayment` with `.id` (`qa-pay-{hash}`), `.status` (`pending`), `.amount`, `.confirmation.confirmation_url` (`https://sandbox.invalid/pay/{id}`) for redirect flows; no confirmation for recurring/off-session charges
- Idempotency: same `idempotency_key` → same synthetic `payment_id`
- **Does not mutate balances** — `process_topup_payment` / webhook success path still requires separate fixture or simulator (QA-PAYMENT-WEBHOOK-001)
- **Not verified without real YooKassa:** capture/void/refund, `Payment.find_one` in webhook verify, shop credentials, production callback signatures

**DB seed/reset (QA-DB-SEED-001 — implemented):**

- Script: `ops/qa_seed_scenarios.py`
- Enable: `BVPN_ENV=staging|local|test` + `BVPN_QA_TOOLS_ENABLED=1`
- Target DB: `SHOP_BOT_DB_PATH` or `BVPN_QA_DB_PATH` (default repo: `data/shop_bot_qa.db`)
- Guards: `require_non_production`, `require_qa_tooling_enabled`, `assert_db_path_allowed_for_qa`
- Prints target DB path before any write; rejects `BVPN_PROD_DB_PATH` and known prod paths
- Synthetic identities: `telegram_id` 900000001+, `qa_*` usernames, `qa+{scenario}@sandbox.invalid`, `QA_REF_*` ref codes
- CLI: `--reset`, `--seed-all`, `--seed NAME`, `--list`
- Manifest: `ops/qa_scenario_manifest.json` (no secrets, no real URLs)
- Reset scope: QA synthetic users only — does not delete arbitrary non-QA rows

**Scenario support (repo today):**

| Support | Scenarios |
|---------|-----------|
| **full** (16) | `new_no_referral`, `new_from_referral`, `existing_tg_user`, `web_lead_without_tg_bind`, `temporary_1d_active`, `temporary_1d_expired`, `paid_wallet_user`, `insufficient_balance_user`, `expired_stopped_user`, `legacy_manual_user`, `user_without_config`, `user_one_active_config`, `user_multiple_device_configs`, `referral_inviter_view`, `referral_invitee_view`, `referrer_reward_not_live` |
| **partial** | `trial_eligible_before_cap` (no trial-cap DB), `temporary_converted_to_paid` (wallet seeded directly — webhook simulator OPEN) |
| **blocked** | `after_trial_cap` (ACQ-TRIAL-CAP-001), `slots_counter_states` (QA-PORTAL-FIXTURES-001) |

**Owner preview (one Telegram account):** seed scenario → open portal/cabinet with `?tid={seed_id}` or email from manifest; bot menus for synthetic id via harness below or QA-OWNER-PREVIEW-001 / second TG account.

**Fake Telegram harness (QA-BOT-FAKE-TG-001 — implemented):**

- Script: `ops/qa_bot_fake_tg.py`
- Enable: `BVPN_ENV=staging|local|test` + `BVPN_QA_TOOLS_ENABLED=1` + isolated `SHOP_BOT_DB_PATH`
- Invokes **real** handlers (`start_handler`, `main_menu_handler`, `menu_get_setup_handler`, `show_topup_handler`, `my_account_handler`, …)
- **Capture-only** `CapturingBot` — no `api.telegram.org` calls; stdout and optional `--out` markdown transcript
- CLI: `--list`, `--list-actions`, `--scenario NAME --action ACTION`, `--tg-id 900000010 --action menu`, `--fresh-start` (delete QA row before `/start`)
- Covered scenarios (13): `new_no_referral`, `new_from_referral`, `existing_tg_user`, `trial_eligible_before_cap`, `paid_wallet_user`, `insufficient_balance_user`, `expired_stopped_user`, `legacy_manual_user`, `user_without_config`, `user_one_active_config`, `referral_inviter_view`, `referral_invitee_view`, `referrer_reward_not_live`
- Actions: `start`, `start_with_ref`, `menu`, `get_setup`, `topup`, `cabinet`, `cabinet_link`, `help`, `status`, `invite`
- **DB mode:** seeded row by default (`new_no_referral` = row exists, `agreed_to_terms=0` → terms screen on `/start`); `--fresh-start` simulates first `/start` without row
- Subscription resolve mocked to `sandbox.invalid` at harness boundary; setup URL still from `portal_links` config
- **Still needs real staging bot / 2nd TG:** inline button taps in real Telegram, Mini App WebView chrome, payment 3DS, bind flow UX

**Portal/cabinet fixtures (QA-PORTAL-FIXTURES-001 — implemented):**

- Resolver: `ops/qa_portal_fixtures.py`
- Local preview server: `ops/qa_serve_portal_preview.py` (static `web/portal` + `/setup/api/cabinet|capacity|telegram-setup` stubs)
- Enable: `BVPN_ENV` non-prod + `BVPN_QA_TOOLS_ENABLED=1` + seeded `SHOP_BOT_DB_PATH`
- CLI: `--list`, `--scenario NAME --print-urls`, `--seed-preview-index`
- URLs use `?tid=`, `?ref=`, `?qa_scenario=`, `?qa_capacity_fixture=` (localhost slots preview)
- Cabinet data: real `portal_cabinet.cabinet_snapshot` shape from QA DB — no subscription URLs/tokens in payload
- Localhost hooks in `portal.js` / `setup.js`: autoload cabinet/setup when `tid` present; slots card via `qa_capacity_fixture`
- **Partial/blocked:** `after_trial_cap` (ACQ-TRIAL-CAP-001 placeholder), `slots_counter_states` (fixture param only until gate API ships)
- Preview index: `ops/qa_portal_preview_index.json` (generated; not committed by default)

**Scenario matrix runner (QA-SCENARIO-MATRIX-001 — implemented):**

- Script: `ops/qa_scenario_matrix.py`
- Chains: DB seed/reset → portal/cabinet/setup URLs → fake-TG harness (where applicable) → runnable classification → production-parity drift report
- Enable: `BVPN_ENV=staging|local|test` + `BVPN_QA_TOOLS_ENABLED=1` + isolated `SHOP_BOT_DB_PATH`
- CLI:
  - `python ops/qa_scenario_matrix.py --list`
  - `python ops/qa_scenario_matrix.py --run-all`
  - `python ops/qa_scenario_matrix.py --scenario paid_wallet_user`
  - `python ops/qa_scenario_matrix.py --run-all --out screenshots/qa-preview/matrix-report.md --json-out screenshots/qa-preview/matrix-report.json`
- **Runnable status:** `full` = seed + cabinet checks (+ bot harness when applicable) passed; `partial` = testable subset with documented blocker; `blocked` = not faked as passed (`after_trial_cap`, `slots_counter_states`)
- **Drift report buckets:** `production_identical` (handlers, cabinet schema, DB seed, portal JS); `dry_run_mocked` (TG capture, YooKassa/Remna dry-run, sandbox URLs); `not_verified_without_staging_or_prod` (real Mini App, 3DS, RU ISP, Caddy edge)
- **Feeds QA-OWNER-PREVIEW-001:** matrix markdown/JSON is the pre-flight checklist before owner visual walkthrough on staging
- Generated reports/transcripts go to user-provided paths (e.g. `screenshots/qa-preview/`); **not committed by default**

**Workflow:**
```text
python ops/qa_scenario_matrix.py --run-all --out screenshots/qa-preview/matrix-report.md
python ops/qa_serve_portal_preview.py
# open portal/cabinet URLs printed in matrix report
```

**Tests:** `ops/test_runtime_env_guards.py`, `ops/test_remna_dryrun.py`, `ops/test_yookassa_dryrun.py`, `ops/test_qa_seed_scenarios.py`, `ops/test_qa_bot_fake_tg.py`, `ops/test_qa_portal_fixtures.py`, `ops/test_qa_scenario_matrix.py`, `ops/test_qa_owner_preview.py`

---

## 4. One Telegram account — how to test multiple users

Telegram always sends the **real** `from.id`. Production bot cannot impersonate another user through Telegram UI.

| Approach | Safe? | Parity | Use for |
|----------|-------|--------|---------|
| **Second Telegram account** (recommended for bot E2E) | Yes on staging bot | Full real TG UX | New user, referral `/start ref_*`, bind |
| **Synthetic `telegram_id` via handler harness** (CLI/tests) | Yes local/staging DB | **Real handlers** with injected `types.User` | Automated matrix scenarios 1–16 |
| **DB seed users `900000001+`** + cabinet `?tid=` deep link | Yes staging | Real `cabinet_snapshot(telegram_id=…)` | Cabinet/setup without second phone |
| **Admin preview (staging)** | Yes if non-prod only | Real menus **for seeded id** via API preview | Owner quick look |
| **Prod admin_flow_guide** | Read-only / copy | Partial | Infra smoke only — **not** new-user state |

**MVP path for owner:**

1. Create **staging bot** (@BenderVPN_staging_bot or similar).
2. Run `ops/qa_seed_scenarios.py --env staging --scenario trial_new` (QA-DB-SEED-001) before each preview.
3. Owner uses **second TG account** OR **portal/cabinet URLs with `?tid={seed_id}`** for non-bot surfaces.
4. For bot menus of synthetic users: staging admin command ` /qa_preview trial_new` renders **real** keyboard builder output for seeded id (QA-OWNER-PREVIEW-001).

---

## 5. Portal scenario testing

### 5.1 Production-identical

- Same `web/portal/` static build (or LV staging deploy of same commit).
- Same `ru.json` content loader.
- Portal calls **real** staging webhook `GET /api/acquisition/gates` (when ACQ-PORTAL-001 exists) — not hardcoded HTML.

### 5.2 Fixture injection (staging/local)

| Mechanism | Purpose |
|-----------|---------|
| URL `?ref=TESTREF01` | Referral welcome block |
| URL `?qa_fixture=trial_cap_reached` | **Staging-only** — API reads fixture override table, still uses real gate function with injected count |
| Seeded emails `qa+{scenario}@bendervpn.test` | Temp access / lead dedup |
| Seeded phones `+7900000{scenario_id}` | Identity match tests |
| `localStorage` clear script in Playwright | Clean vs returning visitor |
| Slot counter fixtures | Seed `active_config_count` in QA table → gates API returns many / near / zero slots |

**Bad:** HTML mock page showing fake «90 дней» without calling gate API.  
**Good:** Playwright opens real `/portal/?ref=X`; asserts on API-driven CTA visibility.

### 5.3 Local portal serve

Use `ops/qa_serve_portal_preview.py` for local portal + `/setup/api/*` cabinet fixtures (QA-PORTAL-FIXTURES-001). Staging may proxy to bot webhook separately.

---

## 6. Bot scenario testing

### 6.1 Production-identical

- Same `handlers.py`, `keyboards.py`, `user_messages.py`.
- Same `process_successful_payment`, `issue_web_trial`, `link_referral`.
- Feature flags from same `config.py` (+ documented overrides).

### 6.2 Synthetic identity harness (QA-BOT-FAKE-TG-001)

```text
qa_invoke_handler(handler_name, synthetic_telegram_id, payload)
  → loads user from seeded DB
  → builds aiogram Update with User(id=synthetic_telegram_id, ...)
  → calls REAL handler coroutine
  → captures outbound messages / DB diffs
  → NEVER calls Telegram send API in local mode (capture-only)
```

Staging mode may send to **allowlisted** chat ids only.

### 6.3 Allowlisted test IDs (staging)

| ID range | Purpose |
|----------|---------|
| `900000001–900000099` | Synthetic journey users (seed-owned) |
| Owner real id | «Existing prod-like» scenario on staging after seed clone |
| Prod owner id on prod bot | **Existing user only** — document as limitation |

---

## 7. Integration boundary mocks (allowed)

| Integration | Mock strategy | Production-identical core |
|-------------|---------------|---------------------------|
| **Remna** `provision_key` | QA-REMNA-DRYRUN-001: return dummy `expire_iso`, fake `vless://…@sandbox.invalid/...`, fake `sub_url` https://sandbox.invalid/sub/{uuid} | Still writes `vpn_keys`, runs expiry logic, scheduler hooks |
| **YooKassa** | QA-PAYMENT-DRYRUN-001: stub `payment_create` → `sandbox.invalid` URL + `qa-pay-*` id; webhook simulator (QA-PAYMENT-WEBHOOK-001) still OPEN | Real `process_successful_payment`, idempotency, `first_purchase` |
| **Balance debit** | Allowed **only** on test DB | Real `charge_daily_balance_if_due` code path |
| **Telegram send** | Capture-only local; allowlist staging | Real message **text** from templates |
| **Subscription resolve** | Return seeded dummy URL from DB row | Real `resolve_subscription_url` lookup order |

**Forbidden:** alternate trial duration logic in test-only module; parallel referral attribution function.

---

## 8. Safety guards (hard requirements)

| Guard | Implementation target |
|-------|----------------------|
| Isolated DB | `data/shop_bot_staging.db` or Docker volume — never prod path |
| `BVPN_ENV` check | Abort if staging uses prod `REMNA_BASE_URL` without `BVPN_QA_DRY_RUN_REMNA=1` |
| No prod credentials in QA docs/scripts | Templates only; redacted examples |
| No real subscription URLs in fixtures | `*.invalid` or `sandbox.bendervpn.test` |
| No prod payment callbacks | Webhook simulator bound to `127.0.0.1` or staging host |
| No billing scheduler on test DB pointing at prod Remna | Disable scheduler in local QA profile |
| Seed reset | `qa_reset_staging_db.sh` — documented; never targets prod |
| Drift report | Every QA run emits §10 parity report |

---

## 9. Customer journey scenario matrix

Status key: **T** = testable today (partial) · **S** = needs staging sandbox · **L** = local matrix only · **B** = blocked on missing feature

| # | Scenario | Seed profile | Primary surface | TG accounts needed | Parity notes | Today |
|---|----------|--------------|-----------------|-------------------|--------------|-------|
| 1 | New user, no referral | `new_plain` | Bot `/start` | 2nd TG on staging | Real handlers | **S** |
| 2 | New user from referral | `new_referred` + `?ref=` | Portal → bot `ref_*` | 2nd TG | Real `link_referral` | **S** / portal **L** |
| 3 | Existing Telegram user | `existing_active` | Bot menu | Owner on staging clone | Clone owner state to staging | **T** partial prod |
| 4 | Web lead, no TG bind | `web_lead_unbound` | Portal setup | None | Real `web_trial_claims` | **L** |
| 5 | Trial-eligible before cap | `trial_open` + cap fixture low | Portal + bot | 2nd TG | Real `trial_used=0`, gate open | **B** cap N/I |
| 6 | After trial cap | `trial_cap_closed` | Portal + bot | 2nd TG | Real gate API | **B** ACQ-TRIAL-CAP-001 |
| 7 | Temp 1d access active | `temp_active` | Portal setup | None | Real `WEB_TRIAL_DAYS` | **L** |
| 8 | Temp expired | `temp_expired` | Portal cabinet | None | Real expiry in DB | **L** |
| 9 | Temp → paid | `temp_converted` | Portal pay | None | Real payment dry-run | **B** ACQ-PAID-CONVERT-001 |
| 10 | Paid wallet user | `wallet_ok` | Bot + cabinet | Seed id / 2nd TG | Real balance fields | **L** |
| 11 | Insufficient balance | `wallet_low` | Bot + cabinet | Seed id | Real `charge_daily` logic | **L** |
| 12 | Expired/stopped | `expired` | Bot + cabinet | Seed id | Real expiry dates past | **L** |
| 13 | Legacy/manual user | `legacy_manual` | Cabinet | Seed id | Frozen balance display | **L** |
| 14 | No config | `no_config` | Bot + cabinet | 2nd TG | Real empty `vpn_keys` | **S** |
| 15 | One active config | `one_config` | Setup + cabinet | Seed id | P1-DEV-001 fields | **L** |
| 16 | Multiple configs | `multi_config` | Cabinet anomaly | Seed id | `multiple_configs_anomaly` | **L** |
| 17 | Referral inviter view | `inviter` | Bot invite + cabinet | Owner seed | Real `count_referrals` | **T** partial |
| 18 | Referral invitee view | `invitee_referred` | Portal `?ref=` | 2nd TG | Real `referred_by` | **L** / **S** |
| 19 | Referrer reward not live | any | Admin/docs | None | Flags OFF; no bonus copy | **T** |
| 20a | Slots: many free | `slots_high` fixture | Portal landing | None | Gate API + fixture count | **B** |
| 20b | Slots: near capacity | `slots_low` fixture | Portal landing | None | Same | **B** |
| 20c | Slots: none | `slots_zero` fixture | Portal landing | None | Hard stop gate | **B** |

---

## 10. Production parity checks (required before deploy)

Every sandbox run (CI or owner preview) should append a **drift report**:

| Check | Method | Pass criteria |
|-------|--------|---------------|
| **Schema parity** | `qa_schema_parity.py` — compare migration version staging vs prod read-only | Same `schema_migrations` version |
| **Config parity** | Diff `config.py` flags + env tmpl staging vs prod | Document intentional diffs only (e.g. `BVPN_QA_DRY_RUN_*`) |
| **Route/API parity** | Same commit SHA deployed staging vs prod target | `git rev-parse HEAD` match in report |
| **Copy parity** | Hash `web/portal/content/ru.json` + bot message modules | Identical unless testing feature branch |
| **Scenario parity** | Matrix §9 — % runnable | Paid/open: ≥90% **L** green; referral: bind scenarios **S** green |
| **Deploy parity** | Staging uses `deploy-portal-web-trial-ams.ps1` equivalent on staging hosts | Same compose tmpl family |
| **Unverified list** | Manual items | e.g. real Happ import, real TG Mini App chrome, real YooKassa 3DS |

### 10.1 What is production-identical

- Bot handlers, portal JS/CSS, `portal_cabinet.py`, `portal_web_trial.py`, `web_referral.py`, `web_tg_bind.py`
- DB schema + migrations
- User lifecycle state machine (trial_used, balance, vpn_keys, referrals)
- Feature flag **names** and gate **functions** (overrides logged, not forked logic)
- Copy sources (`ru.json`, `user_messages.py`)

### 10.2 What is mocked / dry-run

- Remna panel create/extend/revoke
- YooKassa payment create/capture
- Real `subscriptionUrl` values (dummy hosts)
- Telegram message delivery (local capture mode)
- Outbound broadcasts

### 10.3 What cannot be validated without prod approval

- Real Remna routing under RU ISP conditions
- Real YooKassa production merchant callbacks
- Telegram Mini App WebView quirks on owner device
- LV/AMS Caddy edge behavior
- HWID / device enforcement (DEVICE-ENFORCE-001)

---

## 11. Owner preview workflow (implemented)

**QA-OWNER-PREVIEW-001** — local/staging HTML index (`ops/qa_owner_preview.py`):

```text
1. BVPN_ENV=local  BVPN_QA_TOOLS_ENABLED=1  SHOP_BOT_DB_PATH=/path/to/isolated/qa.db
2. python ops/qa_seed_scenarios.py --reset --seed-all
3. python ops/qa_serve_portal_preview.py          # keep running
4. python ops/qa_owner_preview.py --build --out screenshots/qa-preview/index.html
5. Open screenshots/qa-preview/index.html in browser
6. Click Portal / Cabinet / Setup per scenario; open **Bot Visual Preview** (Step 2) where harness output exists; raw markdown under collapsible technical details
```

CLI:

- `python ops/qa_owner_preview.py --open-instructions` — print workflow
- `python ops/qa_owner_preview.py --build` — run matrix + write HTML/MD index (default `screenshots/qa-preview/index.html`)
- `python ops/qa_owner_preview.py --scenario paid_wallet_user` — single-scenario build + stdout detail
- `python ops/qa_owner_preview.py --build --reuse-matrix screenshots/qa-preview/matrix-report.json` — skip matrix re-run

Index groups **20 scenarios** by runnable status: **full** / **partial** / **blocked** (labeled **Owner: visually reviewable / limited / blocked** — same counts as matrix JSON). Each card has an ordered **Journey walkthrough** (Step 1 Portal → Step 2 Bot transcript → Step 3 Cabinet → Step 4 Setup → Step 5 Final state), **CTA transition map**, and collapsible technical details.

**QA-OWNER-PREVIEW-FIX-001:** Bot transcript links fixed; **Start here** section; journey walkthrough Step 1–5.

**QA-OWNER-PREVIEW-FIX-002:** Step 2 links to Telegram-like **bot visual preview** HTML (`screenshots/qa-preview/bot/{scenario}-{action}.html`); raw markdown in collapsible details. Cabinet `#cabinet-actions` hidden for new browser users when `#cabinet-grace` shows acquisition CTAs; utility actions only after identity/config.

**PORTAL-LANDING-CTA-DEDUP-001 (done):** Browser landing shows hero + `#landing-paths` (primary/secondary CTAs with after-click copy) + journey steps + existing-user entry; `#home-cta` hidden; `#events-card` hidden until incident; account-fold bot/setup hidden for new browser users. Rebuild preview: `python ops/qa_owner_preview.py --build` → inspect `new_no_referral` / `new_from_referral`.

| Visually reviewable now (full) | Portal landing, cabinet/setup states, wallet/expired/legacy, referral views, multi-config read path |
| Partial | `trial_eligible_before_cap`, `temporary_converted_to_paid` — UI subset; backend gate/webhook OPEN |
| Blocked | `after_trial_cap`, `slots_counter_states` — fixture URLs only until ACQ APIs ship |

**Still requires staging / second TG / Playwright / prod approval:**

- Real Telegram inline buttons and Mini App WebView
- Staging bot E2E (QA-STAGING-BOT-001)
- Playwright portal smokes (QA-E2E-001)
- Real YooKassa 3DS, Remna RU ISP routing, Caddy edge

Generated `screenshots/qa-preview/`, transcripts, and matrix JSON are **gitignored** — not committed by default.

**Never on production.**

---

## 12. Implementation backlog

| ID | P | Surface | Objective | Depends |
|----|---|---------|-----------|---------|
| **QA-SANDBOX-001** | P1 | docs | This architecture | — |
| **QA-GUARD-001** | P0 | bot | `BVPN_ENV` fail-closed guards | QA-SANDBOX-001 — **DONE** repo |
| **QA-DB-SEED-001** | P1 | ops | `qa_seed_scenarios.py` — seed/reset 20 scenarios — **DONE** repo | QA-GUARD-001 |
| **QA-BOT-FAKE-TG-001** | P1 | bot/ops | `qa_bot_fake_tg.py` capture-only handler harness — **DONE** repo | QA-DB-SEED-001 |
| **QA-REMNA-DRYRUN-001** | P1 | bot | Dry-run `provision_key` at boundary | QA-GUARD-001 — **DONE** repo |
| **QA-PAYMENT-DRYRUN-001** | P1 | bot | Dry-run `payment_create` at boundary — **DONE** repo | QA-GUARD-001 |
| **QA-PAYMENT-WEBHOOK-001** | P1 | webhook | Staging-only payment success simulator | QA-PAYMENT-DRYRUN-001 |
| **QA-PORTAL-FIXTURES-001** | P1 | portal/ops | `qa_portal_fixtures.py` + `qa_serve_portal_preview.py` — **DONE** repo | QA-DB-SEED-001 |
| **QA-SCENARIO-MATRIX-001** | P1 | ops | `qa_scenario_matrix.py` — matrix runner + drift report — **DONE** repo | QA-DB-SEED-001 |
| **QA-E2E-001** | P2 | playwright | Portal→API→cabinet smokes on staging | QA-PORTAL-FIXTURES-001 |
| **QA-OWNER-PREVIEW-001** | P2 | ops | `qa_owner_preview.py` — owner HTML preview index — **DONE** repo | QA-SCENARIO-MATRIX-001 |
| **QA-STAGING-BOT-001** | P1 | ops | Staging bot + DB + portal origin setup runbook | Owner BotFather |

**Extend existing (do not replace):**

- `admin_flow_test.py` → staging-only mode; stop calling prod Remna in local
- `test_web_referral_attribution.py` → pattern for QA-DB-SEED-001
- `serve_portal.py` → API proxy for QA-PORTAL-FIXTURES-001

---

## 13. Launch gates — testability requirements

| Launch mode | Scenarios that must be green in sandbox | Blocker if untestable |
|-------------|----------------------------------------|------------------------|
| **F&F** | 1, 3, 7, 14, 15, 17 (partial) | Cannot demo onboarding to helpers |
| **Soft launch** | + 2, 4, 8, 10, 11, 12, 18 | Referral/temp paths unverified |
| **Paid pilot** | + 9, 10, 11, payment dry-run E2E | **BILL-SMOKE** cannot substitute journey matrix |
| **Open commercial** | + 5, 6, 20a–c, 16, multi-device read paths | Capacity/trial cap unverified |
| **Referral growth** | + 2, 4, 9, 18, bind **S**, anti-abuse ledger | G4 bind scenario **S** must pass on staging |

---

## 14. Owner decisions required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 14.1 | Staging bot | New BotFather token vs reuse | **New staging bot** |
| 14.2 | Second Telegram account | Owner buys second SIM / uses family account | **Yes** for true bot E2E |
| 14.3 | Staging host | AMS separate compose vs local-only | **AMS staging** for deploy parity; **local** for CI |
| 14.4 | Prod admin QA menu | Keep read-only smoke vs disable | **Keep** read-only; add **staging** preview |
| 14.5 | Happ real import in QA | Lab only vs skip | **Skip** in automated; manual lab checklist |

---

## 15. Anti-patterns (reject)

| Bad | Why |
|-----|-----|
| Test-only `handlers_qa.py` fork | Divergent business logic |
| Portal mock HTML not from `web/portal/` | Copy/routing drift |
| Hardcoded «trial available» in Playwright | Hides gate bugs |
| Running seed scripts against prod DB | Data corruption |
| Using prod `subscriptionUrl` in fixtures | Leak + accidental use |

---

## 16. References

| Artifact | Role |
|----------|------|
| `bot_src/admin_flow_test.py` | Existing prod smoke (partial) |
| `ops/test_web_referral_attribution.py` | Temp DB + mock Remna pattern |
| `.playwright-review/serve_portal.py` | Local portal static serve |
| [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md) | Scenarios 5–9, 20 |
| [`ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md`](ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md) | Referral scenarios 17–18 |
| [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) | Scenario 16 |
| `docs/RUNBOOK-AMS-SAFE-DEPLOY.md` | Staging deploy parity template |

---

**Document status:** architecture complete · implementation **NOT STARTED** · owner decisions §14 pending
