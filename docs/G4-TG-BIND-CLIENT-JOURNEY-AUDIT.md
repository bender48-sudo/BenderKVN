# G4-TG-BIND-CLIENT-JOURNEY-AUDIT-001 — Web→Telegram bind & acquisition identity

**Date:** 2026-06-15  
**Branch:** `product-referral-cabinet-ui-v1`  
**HEAD (committed):** `7120823` — commercial readiness checkpoint  
**Mode:** read-only audit · **no prod mutation** · **no deploy** · **no implementation**  
**Parent:** [`COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md`](COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md) · [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) · [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md)

**Naming note:** In [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) **G4 = web/email fallback + TG bind**. In [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md) the same bind proof is **G2-A**. This doc uses **G4 (launch)** unless stated otherwise.

**Parallel work:** `CLIENT-STABILITY-HAPP-RELAY2-REPEAT-SOAK-001` may run on owner laptop — not interrupted by this audit.

**Follow-up implementation:** [`G4-TG-BIND-HANDOFF-FIX-001`](#11-g4-tg-bind-handoff-fix-001-handoff-ux-only) — portal bind handoff UX + telemetry (does **not** close G4 until owner retest).

---

## 1. Executive verdict

### Answers to audit questions

| # | Question | Verdict | Summary |
|---|----------|---------|---------|
| 1 | Can a portal lead be reliably connected to a Telegram user? | **FAIL** (live) / **PARTIAL** (code) | Merge code exists; **prod never recorded** `/start bind_*` entry (`funnel_bot_start bind:*` = 0). |
| 2 | Can phone/email/referral survive portal→bot transition? | **PARTIAL** | Email + `ref_code` on web surrogate **PASS** in code/POSTDEPLOY; **lost on TG** until bind; phone optional, not used for match. |
| 3 | Can 1-day temp access convert to paid without unrelated config? | **FAIL** | No portal paid path; wallet/top-up is **Telegram-only**; without bind, user risks **second config** (`both_have_keys`). |
| 4 | Can referral attribution be preserved without abuse? | **PARTIAL** | `link_referral` idempotent if `referred_by IS NULL`; **no admin ledger, hold window, or bonus controls**. |
| 5 | What exactly is failing under G4 TG bind? | See §4 | **Bind deep link never reached bot** on AMS — not proven migration bug. |
| 6 | What must ship before referral/public acquisition? | See §7–§8 | **G4-BIND-RETEST PASS**, portal-first share, `acquisition_leads` model, REF-ADMIN, capacity ≥2 nodes, client stability gates. |

### Component verdicts

| Component | Verdict | Evidence |
|-----------|---------|----------|
| Portal lead creation | **PARTIAL** | `issue_web_trial` + `web_trial_claims` — no unified `acquisition_leads` |
| Phone/email capture | **PARTIAL** | Email required; phone optional (`setup.js`, `portal_web_trial.py`) |
| Referral attribution | **PARTIAL** | Web `ref_code` **PASS** (P1-REF-001); TG `ref_*` code **CONFIRMED**; bind migration **FAIL** live |
| Telegram handoff | **PARTIAL** | `bind_url` generated; UI in `setup.js` |
| Bind confidence | **FAIL** | AMS: `NOT_BOUND`, token unconsumed, zero bind funnel rows |
| Temporary access linkage | **PARTIAL** | One key per email/web_uid; orphan if user opens TG trial separately |
| Paid conversion linkage | **FAIL** | No web checkout; extend-via-bind only in code paths |
| Anti-abuse / idempotency | **PARTIAL** | One trial/email; no ref overwrite; no fraud/hold |
| Support / admin visibility | **PARTIAL** | SQL infer only; **REF-ADMIN-001** missing |

**Commercial acquisition verdict:** **NO-GO** for referral growth and portal-first campaigns until G4 bind is **proven PASS** and acquisition identity model is implemented.

---

## 2. Current client journey

| Step | User action | Status | Evidence | Missing / failure mode |
|------|-------------|--------|----------|------------------------|
| 1. Portal visit | `/portal/` or `/portal/?ref=CODE` | **DONE** | `web/portal/index.html`, `portal.js` | No server-side lead row |
| 2. Referral capture | `?ref=` → `localStorage.bvpn_ref_code` | **PARTIAL** | `setup.js` L818 | Lost on new device/incognito; no cookie/API |
| 3. Path choice | TG 90d vs email 1d | **DONE** | Landing + setup UX | No capacity/trial-cap gates |
| 4. Email signup | POST `/setup/api/web-trial` | **DONE** | `setup.js` → proxy → Flask `/portal-web-trial` | Secret header only; localhost proxy |
| 5. Phone capture | Optional field on signup | **PARTIAL** | `setup.html`, stored in `web_trial_claims.contact_phone` | Not required; not used for identity match |
| 6. Web identity created | Negative `web_user_id` from email hash | **DONE** | `web_trial_db.web_user_id_from_email` | Surrogate id opaque to user |
| 7. Referral link (web) | `apply_web_referral(ref_code, web_uid)` | **PASS** (code) | `portal_web_trial.py`, `web_referral.py`, POSTDEPLOY P1-REF-001 | On web uid only until bind |
| 8. Config issued | `provision_key` 1 day | **DONE** | `WEB_TRIAL_DAYS`, `portal_web_trial.py` | Panel email `web{uid}-key…`; `telegram_id=None` |
| 9. Bind URL shown | `bind_url` in API response | **DONE** | `telegram_bind_url()`, `renderBindTelegram()` | Copy says open in TG — not enforced |
| 10. Telegram open | `/start bind_<token>` | **FAIL** (live) | `handlers.start_handler` | **Zero** `funnel_bot_start bind:*` on AMS |
| 11. Terms gate | New TG user accepts terms | **DONE** | `pending_web_bind` in FSM → `_apply_web_bind` after agree | User may skip bind UI |
| 12. Merge | `merge_web_user_to_telegram` | **UNKNOWN** (live) | `web_tg_bind.py` | Unit test PASS; prod never entered |
| 13. TG trial (parallel path) | User opens bot without bind | **DONE** | `trial_period_handler` | **Conflict:** `both_have_keys` if web key exists |
| 14. Cabinet / recover | Email lookup | **PARTIAL** | `portal_cabinet.py`, recover API | Bind state in claim row |
| 15. Payment / top-up | YooKassa in bot | **DONE** (code) | `handlers.py`, webhook queue | **Requires real `telegram_id`** — web surrogate cannot pay in TG |
| 16. Paid wallet sync | `sync_panel_from_balance` | **DONE** (code) | BILL-001 audit | Primary key row only; post-bind tg id |
| 17. Referral invite (inviter) | Bot «Пригласить» | **DONE** | `referral_invite_payload` | **Bot-only URL** — not portal-first |

---

## 3. Identity model

### Current identifiers

| Identifier | Where stored | Role |
|------------|--------------|------|
| `telegram_id` | `users.telegram_id` PK | Real TG user; positive int |
| `web_user_id` | Negative int derived from email | Web-only surrogate before bind |
| `contact_email` | `web_trial_claims.contact_email` PK | Web trial anchor |
| `contact_phone` | `web_trial_claims.contact_phone` | Optional; not verified |
| `customer_id` / `customer_seq` | `format_customer_id(web_uid)` | User-facing web customer label |
| `ref_code` | `users.ref_code` per inviter | Share token |
| `referred_by` | `users.referred_by` | **Inviter's ref_code string**, not TG id |
| `referrals.referred_user_id` | FK to `users.telegram_id` | Counts invitees (web uid until bind) |
| `panel_email` | `vpn_keys.email`, Remna | Remna user; may lack `telegramId` until bind sync |
| `bind_token` | `web_trial_claims` | One-time TG handoff; 24h expiry |
| YooKassa idempotency | `user_actions` `yk:{payment_id}` | Payment dedup |

### Where identity splits or is lost

| Risk | Mechanism | Severity |
|------|-----------|----------|
| **Web vs TG duplicate user** | User completes web trial then `/start` trial in bot without bind | **High** — `both_have_keys` blocks bind |
| **Referral invisible in TG** | `referred_by` on negative web uid until merge | **High** for referral reporting |
| **Referrals row stuck on web uid** | `referrals.referred_user_id` not migrated until bind | **High** — breaks inviter counts for email path |
| **localStorage ref loss** | `bvpn_ref_code` client-only | **Medium** — attribution miss if signup without ref in POST |
| **Second browser signup** | `trial_already_claimed` per email | **Low** — intentional |
| **Panel TG id stale** | `sync_panel_telegram_id` only on bind success | **Medium** — support confusion |
| **Orphan config after abandon** | Web trial provisioned; never bound | **Medium** — capacity noise |
| **No lead UUID** | No cross-channel primary key | **High** for portal-first architecture |

---

## 4. G4 bind failure analysis

### What “G4 TG bind FAIL” means

| Layer | Finding |
|-------|---------|
| **Launch gate G4** | Web→Telegram identity merge **not verified** on production |
| **Dev gate G2-A** | Same: E2E web trial attribution **PASS**; TG bind **FAIL** |
| **Exact failing check** | After controlled prepare (`p1bind-`, `p1bind2-`): `web_trial_claims.telegram_id IS NULL`, `bound_at IS NULL`, bind token **still present** |
| **Instrumentation** | `SELECT COUNT(*) FROM user_actions WHERE action='funnel_bot_start' AND meta LIKE 'bind:%'` → **0** (all time on AMS shop DB) |
| **Migration code** | **Not exercised** — failure is **before** `bind_web_account_by_token()` |

### Most likely cause (documented)

**Bind URL not opened inside Telegram app** (browser preview, wrong link, or step skipped) — confidence **high**. See [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) §6.

**Not supported as primary cause:** migration bug, wrong bot username, expired token (at audit time), polling down (ref funnels logged same day).

### Impacted flows if ignored

| Flow | Impact |
|------|--------|
| Email 1d → Telegram account | User stays on web surrogate; cannot use bot wallet cleanly |
| Referral via email path | Inviter credit / future +1 month reward **unverifiable** after TG signup |
| Portal-first acquisition | Leads do not merge; campaigns create **split identities** |
| Support | Two customer IDs, two configs, manual reconciliation |
| Copy claiming “ref preserved through email→TG” | **Misleading** (G2-F / REF-COPY-001) |

### Risk if ignored

- Referral and email acquisition **NO-GO** per [`COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md`](COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md)
- Paid conversion from temp access **requires** bind or manual ops
- Fraud/disputes **unresolvable** without admin ledger

---

## 5. Required target model

Aligned with [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md) — **TARGET, not implemented**.

| Principle | Requirement |
|-----------|-------------|
| **One acquisition identity** | Single `acquisition_lead_id` (or equivalent) spanning portal, web trial, TG user, payment |
| **Contact capture** | Phone + email collected **before** temp/paid issuance where policy requires |
| **Confident TG bind** | `/start bind_*` proven; status `bound` / `failed` / `pending` stored |
| **Referral preserved** | `ref_code` on lead at creation; migrates to TG `referred_by` + `referrals` on bind |
| **Temp → paid** | Extend **same** Remna user / config where possible; no orphan second key |
| **Idempotent conversion** | Top-up and trial claim deduped by lead id + payment id |
| **Anti-abuse** | Hold window before referrer reward; velocity limits; admin review flags |
| **Portal-first share** | Default `{portal}/portal/?ref={code}`; bot link secondary |

---

## 6. Commercial risk

| Blocked outcome | Why G4 / identity blocks it |
|---------------|----------------------------|
| **Referral growth** | Email-path invitees may never bind; attribution breaks; bonus not implementable safely |
| **Portal-first acquisition** | No lead model; share URL still bot-first; no gate API |
| **Paid-from-day-one after ~300 users** | No portal checkout; temp path dead-ends without bind |
| **1-day temp → paid conversion** | Wallet path is TG; web uid cannot top up in bot without merge |
| **Support reconciliation** | Duplicate configs, split balances, `referred_by` on wrong uid |
| **Public acquisition / 300 configs** | Also blocked by **capacity < 2 delivery nodes** and **client stability** — independent of but compounded by G4 |

---

## 7. Acceptance criteria (future implementation)

### Data / DB

- [ ] `acquisition_leads` (or extend `web_trial_claims`) with: `lead_id`, email, phone, `ref_code`, `source`, `status`, `web_user_id`, `telegram_id`, `bind_status`, timestamps
- [ ] `bind_attempts` log: token prefix hash, result, error class, TG id
- [ ] Referral events table or extend `user_actions` with structured bind/referral funnel
- [ ] Unique constraint: one active temp config per lead unless explicit replace

### Portal

- [ ] Portal-first invite URL from bot + cabinet (`ACQ-PORTAL-001` / `REF-PORTAL-001`)
- [ ] Server-side ref capture (cookie or lead API) — not localStorage-only
- [ ] Required phone + email on temp/paid forms when policy says so
- [ ] Bind panel copy: **open in Telegram app** + QR; show bind expiry
- [ ] Post-signup: show `customer_id`, bind state, recover path

### Bot

- [ ] **G4-BIND-RETEST PASS:** `funnel_bot_start bind:*` ≥ 1, `web_tg_bind` row, surrogate deleted
- [ ] Handle `both_have_keys` with support message + runbook (or block TG trial if web claim open)
- [ ] `pending_web_bind` survives bot restart (optional persist by token)
- [ ] Portal-first `ref_*` and bind on same `/start` if ever combined

### Referral

- [ ] Inviter resolved from `ref_code` in admin views
- [ ] REF-ADMIN-001: ledger export, bind_pending list
- [ ] REF-BONUS-001 gated: +1 month only after paid conversion + hold window
- [ ] REF-COPY-001: no “ref preserved” until G2-A/G4 PASS

### Payment conversion

- [ ] Documented path: temp web user → bind → top-up → `sync_panel_from_balance` on **same** key
- [ ] BILL-SMOKE includes **bound web-origin user** recovery scenario
- [ ] Future: portal paid start attaches to lead id (ACQUISITION-JOURNEY-001)

### Tests (minimum)

| Scenario | Expected |
|----------|----------|
| Portal signup with `ref_code` | `referred_by` on web uid; `referrals` row |
| Open bind in TG (clean account) | Merge; `web_tg_bind`; referrals migrated |
| Bind with existing TG keys | `both_have_keys`; funnel row still logged |
| Expired token | `invalid_token`; no merge |
| Duplicate webhook top-up after bind | Single credit (`yk:` idempotency) |
| TG trial without bind when web key exists | Block or clear user messaging |

Existing unit coverage: `ops/test_web_referral_attribution.py` (merge path) — **repo only**.

---

## 8. Backlog mapping

| ID | Sev | Scope | Status | Notes |
|----|-----|-------|--------|-------|
| **G4-BIND-RETEST** | **P0** | Owner prove bind entry in TG app | **OPEN** | No code until entry proven or new failure class |
| **ACQ-BOT-BIND-001** | **P0** | G4 bind + portal lead merge | **OPEN** | Implementation umbrella |
| **G2-A** (dev gates) | **P0** | Same as G4 bind proof | **FAIL** | Launch audit G4 |
| **REF-BIND-001** | P0 | Bind migration verification | **BLOCKED** | On G4-BIND-RETEST |
| **ACQ-PORTAL-001** | P1 | Portal referral landing + gate API | **OPEN** | Portal-first share |
| **REF-PORTAL-001** | P1 | Portal-first share URL in bot/cabinet | **OPEN** | Depends on owner approve OPTION 3 |
| **REF-ADMIN-001** | P0 | Referral ledger / admin | **NOT STARTED** | Before campaigns |
| **REF-ATTR-001** | P1 | Attribution spec + bind migration test | **PARTIAL** | Tests exist locally |
| **REF-COPY-001** | P2 | Soften `referral_preserve_note` | **OPEN** | Until G4 PASS |
| **REF-BONUS-001** | P2 | +1 month referrer reward | **DEFERRED** | After bind + paid proof |
| **ACQUISITION-JOURNEY-001** | P1 | Full portal-first architecture | **NOT IMPLEMENTED** | Docs only |
| **BILL-SMOKE-001..004** | P0 | Paid path proof | **PENDING** | Includes post-bind wallet |
| **CLIENT-STABILITY-*** | P0 | Client gates | **OPEN** | Blocks acquisition regardless |

**P0 before public acquisition:** G4-BIND-RETEST PASS, ACQ-BOT-BIND-001, REF-ADMIN-001, capacity ≥2 nodes, mobile/desktop stability gates.

**P1 before paid beta (conditional):** BILL-SMOKE, REF-PORTAL-001, bind UX copy fixes.

---

## 9. Recommended next implementation task

**Title:** `G4-TG-BIND-RETEST-001` (owner) → then **`G4-TG-BIND-IMPLEMENTATION-001`** (code)

**Do not start implementation until retest classifies failure.**

### Phase A — Owner (reuse **G4-BIND-RETEST**)

1. Prepare fresh trial via `ops/smoke_p1_ref_tg_bind_ams.py prepare` (or portal signup on smoke email prefix).
2. Use **clean Telegram account** (no existing VPN keys).
3. Open `bind_url` **inside Telegram app** (not browser-only).
4. Accept terms if prompted; capture **exact bot reply**.
5. Verify AMS: `funnel_bot_start bind:*` ≥ 1; `web_tg_bind` row; `telegram_id` set.

Follow [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) §7.

### Phase B — Implementation (only if A fails with proven bot entry, or UX gaps)

Reuse backlog ID **ACQ-BOT-BIND-001**:

- Bind UX copy + QR in `setup.js` / `ru.json`
- Verifier status codes in `smoke_p1_ref_tg_bind_ams.py`
- Optional: block or warn TG trial when open web claim exists
- If migration bug proven: patch `web_tg_bind.py` / `handlers.py` in isolated commit

**Do not** bundle with referral portal-first or billing schema in one commit.

---

## 11. G4-TG-BIND-HANDOFF-FIX-001 (handoff UX only)

**Scope:** Fix portal → Telegram bind **handoff** so users reliably reach `/start bind_<token>` inside Telegram, with fallback copy/retry and safe funnel events. **No** migration logic changes unless a local bug is proven by tests.

| Item | Status |
|------|--------|
| Primary CTA | `Открыть в Telegram` → `https://t.me/<bot>?start=bind_<token>` (+ mobile `tg://resolve?…`) |
| Instruction | Visible `/start bind_…` preview (truncated in UI; full command on copy) |
| Fallback | Copy `/start bind_…` + copy t.me link + retry (refresh via recover API when email stored) |
| Browser preview warning | Copy explains browser-only preview does not bind |
| Telemetry | `web_tg_bind_rendered`, `web_tg_bind_open_clicked`, `web_tg_bind_copy_clicked`, `web_tg_bind_retry_clicked` — event names only, no raw token in POST body |
| Files | `web/portal/assets/bind-handoff.js`, `setup.js`, `setup.html`, `content/ru.json`, `ops/test_web_tg_bind_handoff.py` |

**G4 commercial verdict after this fix:** still **NOT PASS** until owner retest (**G4-TG-BIND-RETEST-001**) proves:

- `funnel_bot_start` where `meta LIKE 'bind:%'` ≥ 1 on AMS
- bind migration completes (`web_tg_bind` row / `telegram_bound` on claim)

**Next task:** **G4-TG-BIND-RETEST-001** (owner, live Telegram app, clean account).

---

## 10. Safety

| Check | Result |
|-------|--------|
| Prod mutation | **None** |
| Deploy | **None** |
| Secrets printed | **None** |
| Skills/rules applied | `bendervpn-guardrails.mdc`, journey-qa (code inspection), repo workflow, sequential-backlog (single doc) |
| Repeat-soak dirty files | **Left untouched** |

---

## References

| Artifact | Role |
|----------|------|
| `7120823` | Commercial readiness checkpoint |
| `2e2bca9` | Relay2 lab evidence |
| POSTDEPLOY P1-REF-001 | Web `ref_code` PASS |
| [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) | Bind failure analysis |
| [`ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md`](ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md) | Referral portal hybrid |
| `bot_src/portal_web_trial.py`, `web_tg_bind.py`, `web_referral.py` | Implementation |
| `web/portal/assets/setup.js` | Portal signup + bind UI |
| `ops/test_web_referral_attribution.py` | Repo tests for merge |
