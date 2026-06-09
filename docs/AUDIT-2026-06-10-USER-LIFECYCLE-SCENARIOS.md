# AUDIT — User Lifecycle Scenarios & Monetization Gates

**ID:** USER-LIFECYCLE-001  
**Date:** 2026-06-10  
**Mode:** audit only · no deploy · no prod mutation · no implementation  
**Branch:** `product-referral-cabinet-ui-v1`  
**Repo HEAD:** `c5f5062` (synced with `origin`)  
**Parent:** [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md)  
**Related:** [`AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md`](AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md), [`AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md`](AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md), [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md), [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md)

**Evidence method:** code + docs + postdeploy records only. No live Telegram session, no payment mutation, no reconcile `--apply`. Status per finding: **CONFIRMED** / **PARTIAL** / **BLOCKED** / **UNKNOWN**.

---

## 1. Executive summary

BenderVPN has **two parallel acquisition paths** with different rules:

| Path | Trial | PII collected | Post-trial model |
|------|-------|---------------|------------------|
| **Telegram bot** | 90 days (`REMNA_TRIAL_DAYS`) | Telegram ID + username only | Wallet 6,67 ₽/day after top-up |
| **Web/email fallback** | 1 day (`WEB_TRIAL_DAYS`) | Email required; phone optional | Bind TG → wallet; else expire |

**Monetization readiness:** architecture is sound; **live money-path proof, TG bind migration, copy truth, and support tooling** block paid/open/referral launches.

| Launch type | Verdict | Lifecycle basis |
|-------------|---------|-----------------|
| Internal / F&F | **GO** | Manual support; disclose limits |
| Closed soft launch | **SOFT-LAUNCH ONLY** | Happ mobile-first; no email-growth push; ghost copy fix recommended |
| Paid commercial pilot | **NO-GO** | BILL-SMOKE missing; autopay UI unwired; admin lookup missing |
| Open commercial launch | **NO-GO** | G1/G4/G8/G9/G12/G14 open |
| Referral-driven growth | **NO-GO** | G4 bind BLOCKED; bonus not implemented; hidden +3d code risk |

**BILL-FIX-001** deployed — reconcile idempotency `yk:{payment_id}` aligned. **Do not run reconcile `--apply`** without separate owner approval.

---

## 2. Canonical lifecycle states (Phase 2)

| State | DB truth | Bot truth | Cabinet truth | Remna/key truth | Launch-ready |
|-------|----------|-----------|---------------|-----------------|--------------|
| **S0** Unknown visitor | — | — | Portal static | — | N/A |
| **S1** New TG user, no key | `users` row (`telegram_id`, `username`) | Terms gate; main menu | N/A until Mini App open | No `vpn_keys` | **PARTIAL** — ghost copy in errors |
| **S2** TG trial 90d | `trial_used=1`, `vpn_keys` `-trial@` | `get_trial` → `provision_key` | `billing_profile=trial` | Panel `expireAt` ~90d | **CONFIRMED** |
| **S3** Web/email 1d | `web_trial_claims.contact_email` | N/A (web only) | Grace/setup pages | 1d key | **CONFIRMED** |
| **S4** Web user → TG bind | `web_trial_claims.telegram_id`, `bound_at` | `/start bind_*` → `merge_web_user_to_telegram` | `bind_url` in setup/cabinet | `sync_panel_telegram_id` | **BLOCKED** — live bind FAIL |
| **S5** Wallet, balance ≥ 6,67 | `users.balance` | Top-up + daily debit path | `billing_profile=wallet` | `expireAt` from balance | **PARTIAL** — no live debit smoke |
| **S6** Wallet, low balance | Same; `balance < 6.67` | Scheduler 7/3/1d warnings | `cabinet-balance--low` CSS | `expireAt` shrinking | **PARTIAL** |
| **S7** Expired / stopped paying | `balance` depleted or trial ended | «Пополнить баланс» prompts | `billing_profile=expired` | Panel past `expireAt` | **PARTIAL** — recovery smoke missing |
| **S8** Legacy/manual | Keys with expiry >400d or ≥2030 | No daily debit | `billing_profile=legacy` | Long `expireAt` | **CONFIRMED** (P1-CAB smoke) |
| **S9** Active single config | `vpn_keys` active=1 | `menu_get_setup` reuses URL | `active_config_count=1` | One sub URL | **CONFIRMED** |
| **S10** Multi-config anomaly | `vpn_keys` active>1 | No auto-fix | `multiple_configs_anomaly` flag | Multiple subs | **PARTIAL** — support-only |
| **S11** Referral-linked | `referred_by`, `referrals` table | `ref_*` / web `ref_code` | `referral_preserve_note` copy | N/A | **PARTIAL** — bind migration unproven |
| **S12** Device replacement needed | Same key row | `menu_get_setup` = same URL | `btn-new-device` → bot | No new key issued | **BLOCKED** — see [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) — target **MODEL A** |

**Transitions (confirmed in code):**

- S1 → S2: `trial_period_handler` (`handlers.py`)
- S1 → S5: `process_topup_payment` after trial or direct top-up
- S3 → S4: `bind_web_account_by_token` (`web_tg_bind.py`)
- S4 → S5/S7: merge preserves `referred_by`; wallet after top-up
- S2 → S7: trial `expireAt` passes; no re-trial (`trial_used`)
- S5 → S7: daily debit depletes balance (`balance_billing.py`)
- S7 → S5: top-up + `sync_panel_access_from_balance`

---

## 3. Scenario matrix A–H

### A — New Telegram user

| ID | User action | Expected product | Actual code | Deployed evidence | Data collected | Launch | Blocker | Action |
|----|-------------|------------------|-------------|-------------------|----------------|--------|---------|--------|
| A1 | `/start` no ref | Register + terms + menu | `start_handler` → `register_user_if_not_exists` | G3 DONE | TG ID, username | **DONE** | — | — |
| A2 | `/start ref_*` | Attribution, no bonus | `link_referral` + `referrals` insert | Web ref PASS; TG code exists | + `referred_by` | **PARTIAL** | Bonus copy absent OK; ledger admin missing | P1-ADM-002 |
| A3 | «Получить доступ» | Owner term — not in bot | **0 matches** in `bot_src/` | — | — | **PARTIAL** | Label mismatch | Map to «Получить настройку» (COPY) |
| A4 | Trial 90d | New key, Happ steps | `get_trial` → `provision_key(REMNA_TRIAL_DAYS)` | Policy PT-01 | None beyond TG | **CONFIRMED** | — | — |
| A5 | Setup link | Reuse sub URL | `menu_get_setup` → `_wizard_setup_url` | INCIDENT-002 stable interim | — | **CONFIRMED** | — | — |
| A6 | Opens cabinet | `billing_profile` trial | `portal_cabinet.build_billing_fields` | P1-CAB legacy/trial PASS | — | **PARTIAL** | Mini App visual not owner-verified | Owner spot-check |
| A7 | Email asked? | Policy: soft ask | **Not implemented** | — | **none** | **PARTIAL** | REG-001 deferred | Owner: REG timing |
| A8 | Phone asked? | Policy: soft ask | **Not implemented** | — | **none** | **PARTIAL** | REG-001 deferred | Owner: REG timing |
| A9 | Card/autopay asked? | Optional post-setup | Handler exists; **no menu button** | Autopay not smoked | **none** | **BLOCKED** for paid | UI unwired | PAY-AUTO-001 |
| A10 | Day 1/7/end | Warnings + top-up CTA | `scheduler.py` EXPIRY_NOTIFY_DAYS | Code only | — | **PARTIAL** | Live delivery UNKNOWN | Scheduler spot-check |

### B — New user via web/email

| ID | User action | Expected | Actual | Evidence | Data | Launch | Blocker | Action |
|----|-------------|----------|--------|----------|------|--------|---------|--------|
| B1 | Lands setup | Email path visible | `setup.html` + `setup.js` | Static 200 | — | **CONFIRMED** | — | — |
| B2 | Enters email | Required | `issue_web_trial` rejects invalid | POSTDEPLOY days:1 | email | **CONFIRMED** | — | — |
| B3 | Gets 1d | 1 day key | `WEB_TRIAL_DAYS=1` | POSTDEPLOY §3 | — | **CONFIRMED** | — | — |
| B4 | Setup link | QR + Happ deep link | `showSetupResult` | Code | — | **CONFIRMED** | — | — |
| B5 | TG instruction | Step 3 bind panel | `renderBindTelegram` | Code | — | **CONFIRMED** | — | — |
| B6 | Bind TG | Merge web→TG | `bind_web_account_by_token` | **FAIL** — 0 `bind:*` funnel | TG ID on merge | **BLOCKED** | Link not opened in TG app | Owner retest G4 |
| B7 | Referral preserved | `referred_by` migrates | `merge_web_user_to_telegram` L73-82 | Web signup PASS; bind migration **not observed** | ref at signup | **PARTIAL** | G4 | Retest bind |
| B8 | After 1 day | Expire, bind+top-up CTA | `recover_web_trial` → `trial_expired` | Code | — | **CONFIRMED** | — | — |
| B9 | Email/phone/card | Email req; phone opt; no card | Matches code | — | email, phone? | **CONFIRMED** | Card N/A on web trial | — |
| B10 | Next step | Bind TG or pay | Copy `signup_error_expired` | `ru.json` | — | **PARTIAL** | Bind BLOCKED | Fix G4 or disable email campaigns |

### C — User on trial

| ID | Action | Expected | Actual | Launch | Blocker |
|----|--------|----------|--------|--------|---------|
| C1 | Cabinet | trial profile + expiry | `billing_profile=trial` | **PARTIAL** | Wallet UI unsmoked |
| C2 | «Получить доступ» | N/A in bot | Use «Получить настройку» | **PARTIAL** | Terminology |
| C3 | «Получить доступ на сутки» | Web only | Portal `action_email_access` | **CONFIRMED** | TG user in browser may see wrong CTA |
| C4 | Refresh setup | Same sub URL | `telegram_setup_for_user` no new trial | **CONFIRMED** | — |
| C5 | Top-up offered | At end + `BOT_PAYMENTS_LIVE` | `show_topup_handler` | **PARTIAL** | Live payments gate UNKNOWN |
| C6 | Card bind offered | Optional | **No menu entry** | **BLOCKED** | PAY-AUTO-001 |
| C7 | End warnings | 7/3/1/0 + 6h | `scheduler.py` | **PARTIAL** | Live UNKNOWN |
| C8 | Convert wallet | Top-up → sync panel | `process_topup_payment` | **PARTIAL** | BILL-SMOKE-001 |

### D — Paying wallet user

| ID | Action | Expected | Actual | Launch | Blocker |
|----|--------|----------|--------|--------|---------|
| D1 | Top-up | YooKassa link | `pay_yookassa_topup_handler` | **PARTIAL** | No live smoke |
| D2 | Payment success | Webhook credit | `payment.succeeded` → queue | **PARTIAL** | BILL-SMOKE-001 |
| D3 | Balance credited | `add_balance` + `yk:` action | `process_topup_payment` | **CONFIRMED** code | Live UNKNOWN |
| D4 | Access extended | `sync_panel_access_from_balance` | `balance_billing.py` | **PARTIAL** | S10 sync-fail runbook |
| D5 | Daily debit | 6,67 once/UTC day | `charge_daily_balance_if_due` | **PARTIAL** | BILL-SMOKE-002 |
| D6 | Duplicate webhook | Single credit | `yk:{id}` + `claim_webhook_delivery` | **CONFIRMED** code; BILL-FIX-001 deployed | BILL-SMOKE-002 |
| D7 | Failed payment | User notified | Non-success webhook **ignored** | **PARTIAL** | Silent fail — support risk |
| D8 | Card autopay | Optional 200₽/30d | Coded; scheduler loop | **UNKNOWN** live | No UI; no smoke |
| D9 | Cabinet | wallet profile + balance | `portal.js` render | **PARTIAL** | Wallet not API-smoked |
| D10 | Active configs | count + list | P1-DEV-001 deployed | **CONFIRMED** postdeploy | — |
| D11 | Support reconcile | Lookup payment | **No admin view** | **BLOCKED** | P1-ADM-003 |

### E — Stopped paying / expired

| ID | Action | Expected | Actual | Launch | Blocker |
|----|--------|----------|--------|--------|---------|
| E1 | Balance < 6,67 | No debit; panel shrinks | `try_deduct_balance` fail | **CONFIRMED** code | Live UNKNOWN |
| E2 | Access expires | Panel `expireAt` past | `sync_panel_from_balance` | **PARTIAL** | — |
| E3 | Opens bot | «Пополнить» CTA | `my_account_handler` / scheduler | **PARTIAL** | «Мой VPN» ghost label |
| E4 | Opens cabinet | expired profile | `billing_profile=expired` | **PARTIAL** | Not API-smoked |
| E5 | «Получить доступ» | Top-up path | Ghost labels in `subscription_resolve` | **PARTIAL** | PROD-005 |
| E6 | «Пополнить» | Top-up flow | Main menu button exists | **CONFIRMED** | — |
| E7 | Pay after expiry | Restore access | top-up + sync | **PARTIAL** | BILL-SMOKE-003 |
| E8 | Config reuse | Same key | No auto new key | **CONFIRMED** | Device replace = support |
| E9 | Support flow | Runbook | **Missing** BILL-RUNBOOK-001 | **BLOCKED** | Write runbook |
| E10 | Notifications | «Доступ приостановлен» | `scheduler.py` notify_mark=0 | **CONFIRMED** code | Live UNKNOWN |

### F — Legacy/manual user

| ID | Action | Expected | Actual | Launch | Blocker |
|----|--------|----------|--------|--------|---------|
| F1 | Cabinet | legacy profile | P1-CAB smoke **PASS** | **CONFIRMED** | — |
| F2 | Balance shown | Yes, not draining | `legacy_manual_access` | **CONFIRMED** | — |
| F3 | No drain | Skip wallet debit | `access_profile=legacy` | **CONFIRMED** | — |
| F4 | Setup/access | Same as others | Reuse URL | **CONFIRMED** | — |
| F5 | Payment prompts | May top-up voluntarily | Top-up in menu | **CONFIRMED** | — |
| F6 | Support class | Long expiry flag | `subscription_profile.is_legacy_manual_panel` | **CONFIRMED** | Admin lookup missing |

### G — Device/config lifecycle

| ID | Topic | Expected | Actual | Launch | Blocker |
|----|-------|----------|--------|--------|---------|
| G1 | One active config | 1 device | Usually 1 key; no hard cap | **PARTIAL** | No enforcement |
| G2 | Multi-config | Support flag | `multiple_configs_anomaly` | **CONFIRMED** | P1-ADM revoke |
| G3 | New device | Support-only | `btn-new-device` → bot; no new key | **CONFIRMED** | Runbook missing |
| G4 | Copy promise | Support-only honest | `setup.device_rule` over-promises | **BLOCKED** soft+ | LAUNCH-005 |
| G5 | Support revoke | Documented | Manual Remna panel only | **BLOCKED** paid | P1-DEV-002 |
| G6 | Billing clarity | Per account/day | `DAILY_RATE` once regardless of keys | **CONFIRMED** | Copy mixed |

### H — Referral user

| ID | Path | Expected | Actual | Launch | Blocker |
|----|------|----------|--------|--------|---------|
| H1 | TG `ref_*` | Attribute only | `link_referral` | **CONFIRMED** | — |
| H2 | Web `ref_code` | Attribute at signup | `apply_web_referral` | **CONFIRMED** POSTDEPLOY | — |
| H3 | Web→TG bind | Migrate `referred_by` | Code in `merge_web_user_to_telegram` | **BLOCKED** live | G4 retest |
| H4 | Bonus copy | None promised | `msg_referral_invite` — link only | **CONFIRMED** | Hidden +3d in legacy purchase |
| H5 | Admin visibility | Query referrals | Manual SQL only | **BLOCKED** | P1-ADM-002 |

---

## 4. Email and phone registration audit (Phase 4)

### Current behavior (code-confirmed)

| Path | Email | Phone | Mandatory? |
|------|-------|-------|------------|
| **Telegram `/start`** | **Not collected** | **Not collected** | N/A |
| **Web 1d trial** | **Required** (`contact_email` PK) | **Optional** (`contact_phone`) | Email yes; phone no |
| **`users` table** | **No column** | **No column** | — |

**REG-001 status:** **Policy only** (`BENDERVPN-PRODUCT-POLICY.md` §4). TG soft ask **not implemented** (`DEC-IMPL-011` DEFERRED). **OD-05** (mandatory phone before top-up) **BLOCKED** — owner undecided.

### Product purpose matrix

| Purpose | TG today | Web today | Gap |
|---------|----------|-----------|-----|
| Recovery without TG | No contact | Email only | TG users unrecoverable without support |
| Payment receipts | N/A | Email stored | TG wallet users — no receipt email |
| Support | TG chat only | Email in `web_trial_claims` | Fragmented identity |
| Anti-abuse | TG ID only | Email uniqueness | Trial abuse via new TG accounts |
| Referral attribution | `ref_*` | `ref_code` | OK at signup; bind migration unproven |
| Legal/accounting | Minimal | Email for 1d | REG-001 Phase 2 |

### Risks

| Risk | Not collecting early | Collecting too early |
|------|---------------------|----------------------|
| F&F | Low — manual support | Friction unnecessary |
| Soft launch | Medium — recovery harder | Conversion drop on trial |
| Paid pilot | **High** — disputes/chargebacks | Privacy/terms update required (OD-09) |
| Open launch | **High** | Compliance/storage obligation |

### Email/phone collection matrix

| Launch type | Email (TG path) | Phone (TG path) | Mandatory? | Timing | Why | Blocker? |
|-------------|-----------------|-----------------|------------|--------|-----|----------|
| F&F | Skip | Skip | No | — | TG ID sufficient with manual support | No |
| Soft launch | Optional soft ask | Optional soft ask | **No** | After setup success or before first top-up | Recovery; not blocking trial | **NEEDS_OWNER_DECISION** |
| Paid pilot | **Recommend optional** | **Recommend optional** | No before top-up | Before first paid top-up or support escalation | Disputes; OD-05 undecided | **Yes** until OD-05 + privacy |
| Open launch | Soft → stronger nudge | Consider before top-up | TBD | Phase 2 REG-001 | Fraud/recovery | **Yes** — REG-001 + OD-09 |

### Owner decisions required

1. **OD-05:** Mandatory phone before first top-up? (BLOCKED in backlog)
2. **REG-001 timing:** Implement soft ask in Phase 2 or waive until 300 configs?
3. **OD-09:** Privacy/terms update before any bot PII collection?

**Recommendation:** Do **not** implement collection in this audit. **Do not** block F&F or soft launch on REG-001. **Do** require owner decision before automated paid pilot.

---

## 5. Card binding / autopay timing audit (Phase 5)

### Current implementation

| Capability | Code | User-visible | Live |
|------------|------|--------------|------|
| YooKassa save card (`save_payment_method`) | `yookassa_autopay.create_bind_payment` | `msg_autopay_bind_offer` | **UNKNOWN** |
| Recurring charge 200₽/30d | `create_recurring_charge` + scheduler | Generic topup msg on success | **UNKNOWN** |
| Toggle autopay | `toggle_autorenew_handler` | **No menu button** — keyboard unwired | **No** |
| DB fields | `yookassa_payment_method_id`, `yookassa_autopay_*` | — | Migrated |

**Messaging mismatch:** Daily wallet model = **6,67 ₽/day**; autopay default = **200 ₽ / 30 days** — different UX story.

### Card/autopay decision matrix

| Option | UX timing | Technical readiness | Money risk | F&F | Soft | Paid | Open | Verdict |
|--------|-----------|---------------------|------------|-----|------|------|------|---------|
| **A** Trial start | High friction | UI missing | High — unaudited | No | No | No | No | **Reject** |
| **B** After setup, optional | Low friction | UI missing | Medium | Optional copy only | **Best candidate** | After smokes | After smokes | **Defer** until PAY-AUTO-001 |
| **C** After successful VPN use | Trust-building | No telemetry hook | Medium | No | Maybe | After smokes | Yes | **Defer** — needs product metric |
| **D** 3 days before trial end | Good conversion moment | Scheduler could target | Medium | No | **Consider** | After smokes | Yes | **Defer** — wire UI first |
| **E** Balance low | Aligns wallet model | Partial — low balance notify exists | Lower | No | Yes | Yes | Yes | **Best for paid** after BILL-SMOKE |
| **F** After first manual top-up | Proven payer | Top-up path exists | Lower | No | Yes | **Recommended first paid** | Yes | **Recommended** |
| **G** Not until BILL-SMOKE pass | Safest | Current state | Lowest | **Yes** | **Yes** | **Required** | **Required** | **CONFIRMED policy** |

### Recommendation

- **F&F / soft launch:** Do **not** surface card binding. Manual top-up only.
- **Paid pilot:** Option **F** then **E** — optional «автопродление» after first successful top-up; never forced.
- **Before any primary autopay CTA:** BILL-SMOKE-001..004 + PAY-AUTO-001 audit + wire `create_autorenew_toggle_keyboard` into menu.
- **Do not run** reconcile `--apply` or enable forced autopay until owner explicitly approves.

---

## 6. Lifecycle notifications audit (Phase 6)

| Event | Implemented | Copy | Timing | Support risk | Launch blocker |
|-------|-------------|------|--------|--------------|----------------|
| Trial started | **CONFIRMED** | `trial_period_handler` success msg | Immediate | Low | No |
| Trial midway | **PARTIAL** | Generic menu hint | Passive only | Low | No |
| Trial ending soon | **CONFIRMED** code | 7/3/1d + 6h (`scheduler.py`) | Scheduled | Medium if payments off | Soft: partial |
| Trial ended | **CONFIRMED** code | «Пробный период завершился» | `notify_mark=0` | Medium — ghost «Мой VPN» | **PARTIAL** |
| Balance low | **CONFIRMED** code | Days-left + balance in notify | 7/3/1d | Medium | Paid: yes until smoke |
| Daily debit | **CONFIRMED** code | Silent (no user msg) | UTC daily | Low | No |
| Payment success | **CONFIRMED** code | `process_topup_payment` notify | Webhook | Low | Paid: smoke needed |
| Payment failed | **PARTIAL** | Webhook ignores non-success | — | **High** — silent | Paid: yes |
| Access restored | **CONFIRMED** code | Top-up success msg | After credit | Medium if sync fails | BILL-RUNBOOK-001 |
| Access expired | **CONFIRMED** code | «Доступ приостановлен» | Wallet 0 days | Medium | Partial |
| Card bind success/fail | **PARTIAL** | Bind offer + fail msg; no menu | On toggle only | High if unwired | Paid |
| Device/config warning | **CONFIRMED** | `configs_multi_anomaly` | Cabinet load | Medium | Soft: copy fix |
| Support contact | **CONFIRMED** | «Написать нам» in menu | Always | Low | No |
| Web 1d expiry | **CONFIRMED** | `signup_error_expired` | On recover | Medium | G4 |

---

## 7. User-visible screens/buttons audit (Phase 7)

| Issue | File/key | Current | Why wrong | Fix before | Direction |
|-------|----------|---------|-----------|------------|-----------|
| Ghost «Мой VPN» | `subscription_resolve.py` L91-110 | Error paths reference removed menu | User cannot find CTA | **Soft launch** | «Пополнить баланс» / «Личный кабинет» |
| Ghost «Начать бесплатно» | `subscription_resolve.py` L66,105 | Points to non-existent button | Dead-end errors | **Soft launch** | «Начать бесплатный период» / «Получить настройку» |
| «Получить доступ» absent in bot | — | Owner term unmapped | Support confusion | Soft | Glossary in COPY-TRUTH-001 |
| `setup.device_rule` false promise | `ru.json` L448 | «выпусти новую настройку в кабинете» | No self-service new key | **Soft+paid** | «Напишите в поддержку для нового устройства» |
| `home.devices_note` | `ru.json` L18 | «выпусти отдельную конфигурацию в боте» | Same | Soft+paid | Align with FAQ |
| NL/Latvia in help | `user_messages.py` L275 | Mentions NL/Latvia | PT-11 breach | Paid | BenderVPN Auto only |
| Trial hint mismatch | `MSG_MAIN_MENU_TRIAL_HINT` | «активируется при первой настройке» | Trial needs explicit click | Soft | Match `menu_get_setup` gate |
| Invitation after trial | `my_account_handler` | «нужно приглашение» | No invite gate in code | Soft | Remove or implement gate |
| Autopay 200₽/30d vs 6,67/day | `msg_autopay_bind_offer` | Calendar autopay copy | Wallet model confusion | Paid | Unify messaging |
| `referral_preserve_note` | `ru.json` L29 | Implies bind preserves ref | G4 bind FAIL | Referral growth | Soften until bind PASS |
| Web «1 сутки» for TG users | `ru.json` grace CTAs | Email trial CTA in browser | Wrong path for bound TG | Soft | Hide when TG session detected |
| Hidden +3d referral bonus | `handlers.py` L1983-1989 | Code only | PT-07 violation | Paid | P1-REF-002 gate/remove |

---

## 8. Launch gate matrix (Phase 8)

| Gate | Scenario(s) | Status | Evidence | Blocker | Action | Owner decision |
|------|-------------|--------|----------|---------|--------|----------------|
| **REG-001** | A7-A8, B9 | **NEEDS_OWNER_DECISION** | Policy §4; code absent TG | OD-05, OD-09 | REG-001 design | Phone before top-up? |
| **PAY-001** | A9, C6, D8 | **BLOCKED** | Autopay coded; UI unwired; no smoke | BILL-SMOKE | PAY-AUTO-001 | When to offer bind? |
| **TRIAL-001** | A10, C7-C8 | **PARTIAL** | Notifications coded; conversion unsmoked | BILL-SMOKE-001 | Trial→wallet smoke | — |
| **EXPIRE-001** | E1-E10 | **PARTIAL** | Recovery coded; ghost copy; no smoke | BILL-SMOKE-003, PROD-005 | Expired recovery smoke | — |
| **WEB-001** | B6-B7, H3 | **BLOCKED** | POSTDEPLOY bind FAIL | G4 | Owner in-app bind retest | Waive email growth? |
| **DEVICE-001** | G1-G6 | **PARTIAL** | Read-only deployed; no revoke | P1-DEV-002, LAUNCH-005 | Support runbook | Option A vs B |
| **REF-001** | H1-H5 | **PARTIAL** | Attribution yes; bind migration no | G4, P1-REF-002 | Fix bind; remove hidden +3d | Referral campaigns? |

### Gate status summary (unchanged from commercial audit unless noted)

| Gate | Status | USER-LIFECYCLE note |
|------|--------|---------------------|
| G1 VPN stability | PARTIAL | INCIDENT-003/004 — desktop/browser |
| G2 Client apps | PARTIAL | Happ primary |
| G3 TG 90d | DONE | S2 confirmed |
| G4 Web/TG bind | **BLOCKED** | S4 transition unproven live |
| G5 Referral | PARTIAL | S11 partial |
| G6 Billing | **PARTIAL** | BILL-FIX-001 deployed; smokes open |
| G7 Device | PARTIAL | S12 support-only |
| G8 Admin | PARTIAL | No lookup |
| G9 Monitoring | PARTIAL | — |
| G10 Copy | PARTIAL | §7 issues |
| G11 Security | PARTIAL | — |
| G12 Enforcement | NOT_STARTED | — |
| G13 Deploy | DONE | — |
| G14 Reporting | NOT_STARTED | — |
| G15 Launch ops | PARTIAL | — |

---

## 9. Owner decisions required

| # | Decision | Options | Default if no answer |
|---|----------|---------|----------------------|
| 1 | **G4 bind waiver** | Retest in-app bind vs disable email growth campaigns | Keep email path **internal only** |
| 2 | **OD-05 phone before top-up** | Mandatory vs soft vs never | Soft optional at first top-up |
| 3 | **REG-001 timing** | Phase 2 vs waive until 300 configs | Defer (current backlog) |
| 4 | **PAY-001 autopay timing** | Options B/D/E/F from §5 | **G** — not until BILL-SMOKE |
| 5 | **Referral campaigns** | Allow tracking-only vs block until bind PASS | Block growth campaigns |
| 6 | **Device policy** | Strict one-device enforce vs support-only (current) | Support-only (Option A MVP) |
| 7 | **Manual paid pilot waiver** | Whitelist ≤10 users with manual verification | Required for any paid traffic |
| 8 | **Desktop/SaaS positioning** | Sell Happ mobile-only vs support desktop | SOFT-LAUNCH ONLY mobile-first |

---

## 10. Recommended next surfaces (Phase 9)

Ordered — **one surface per commit**; prod/money mutations need explicit approval phrases.

| Order | ID | Why | Files likely | Tests | Deploy? | Prod risk | Prerequisite | Approval phrase |
|-------|-----|-----|--------------|-------|---------|-----------|--------------|-----------------|
| 0 | **DEVICE-ARCH-001** | Multi-device model decision | [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) | — | No | None | — | owner approve MODEL A |
| 1 | **COPY-TRUTH-001** / **DEVICE-COPY-001** | Ghost labels + `device_rule` | `subscription_resolve.py`, `user_messages.py`, `ru.json` | grep forbidden | Yes LV+bot | Low | DEVICE-ARCH-001 | approve deploy COPY-TRUTH-001 |
| 2 | **G4-BIND-RETEST** | WEB-001 BLOCKED | — (manual) | POSTDEPLOY §9 checklist | No | None | Owner clean TG account | owner retest bind in Telegram app |
| 3 | **BILL-SMOKE-001** | Paid gate G6 | `ops/smoke_billing_commercial_ams.py` | controlled user | AMS exec | **Money** | BILL-FIX-001 deployed | approve BILL-SMOKE-001 controlled top-up |
| 4 | **BILL-SMOKE-002** | Duplicate credit proof | same | webhook replay read-only | AMS | Medium | 001 | approve BILL-SMOKE-002 |
| 5 | **BILL-SMOKE-003** | EXPIRE-001 | same | expired user | AMS | Medium | 001 | approve BILL-SMOKE-003 |
| 6 | **BILL-RUNBOOK-001** | E9 support | `docs/RUNBOOK-*` | — | No | None | BILL audit | — |
| 7 | **P1-ADM-003** | D11 support lookup | `admin_handlers.py` | py_compile | Yes AMS | Low read-only | — | approve deploy P1-ADM-003 |
| 8 | **P1-REF-002** | Hidden +3d bonus | `handlers.py` | unit test | Yes AMS | Low | — | approve deploy P1-REF-002 |
| 9 | **PAY-AUTO-001** | Autopay decision + wire UI | `keyboards.py`, `handlers.py` | smoke | Yes AMS | **Money** | BILL-SMOKE pass | approve PAY-AUTO-001 optional autopay |
| 10 | **BILL-UT-001/002** | CI debit/idempotency | `tests/test_balance_billing.py` | unittest | No | None | — | — |
| 11 | **DEVICE-RUNBOOK-001** | G3/G5 support path | docs | — | No | None | — | — |
| 12 | **REG-001** | Only if owner approves Phase 2 | `handlers.py`, schema | — | Yes | Medium privacy | OD-09 | approve REG-001 implementation |

**Do not start** in this pass: BILL-UT, BILL-SMOKE execution, reconcile `--apply`, REG-001 implementation.

---

## 11. Go/no-go by launch type

| Launch | Verdict | Must be true |
|--------|---------|--------------|
| **F&F** | **GO** | Manual support; disclose VPN desktop limits + bind unverified |
| **Soft launch** | **SOFT-LAUNCH ONLY** | COPY-TRUTH-001; Happ mobile-first; no email ad campaigns; no referral growth |
| **Paid pilot** | **NO-GO** | BILL-SMOKE-001..004 PASS; P1-ADM-003; BILL-RUNBOOK-001; owner whitelist; OD-05 decided |
| **Open launch** | **NO-GO** | All paid gates + G9 monitoring + G11 CI + G12 enforcement + INCIDENT-003/004 resolved or waived |
| **Referral growth** | **NO-GO** | G4 PASS; P1-REF-002; P1-ADM-002 ledger; no bonus promises |

### Before any paid traffic

1. `BOT_PAYMENTS_LIVE=1` confirmed on AMS (read-only check).
2. BILL-SMOKE-001..004 PASS on controlled users.
3. Owner manual verification per payment (whitelist pilot).
4. No reconcile `--apply` without separate approval.
5. Support runbook for payment-sync failure (BILL-RUNBOOK-001).
6. Ghost copy fixed (PROD-005 / COPY-TRUTH-001).
7. P1-ADM-003 or equivalent manual SQL runbook in hand.

---

## 12. References

| Artifact | Role |
|----------|------|
| `bot_src/handlers.py` | TG lifecycle handlers |
| `bot_src/subscription_profile.py` | State classification |
| `bot_src/portal_cabinet.py` | Cabinet API |
| `bot_src/portal_web_trial.py` | Web 1d trial |
| `bot_src/web_tg_bind.py` | TG bind merge |
| `bot_src/balance_billing.py` | Wallet debit |
| `bot_src/yookassa_autopay.py` | Card bind/charge |
| `web/portal/content/ru.json` | Portal copy |
| `POSTDEPLOY-2026-06-10-P1-CAB-001.md` | billing_profile deploy |
| `POSTDEPLOY-2026-06-10-P1-DEV-001.md` | config list deploy |
| `POSTDEPLOY-2026-06-10-P1-REF-001.md` | web ref + bind FAIL |
| `POSTDEPLOY-2026-06-10-BILL-FIX-001.md` | idempotency deploy |

---

**Audit complete.** No implementation. No prod mutation.
