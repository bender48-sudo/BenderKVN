# CODERABBIT-AUDIT-TRIAGE-001 — Commercial launch audit triage

**Date:** 2026-06-15  
**Branch:** `product-referral-cabinet-ui-v1`  
**HEAD (verified):** `4fdf06c` — repeat relay2 soak PASS docs  
**Mode:** read-only triage · **no prod mutation** · **no deploy** · **no fixes in this task**  
**Input:** Owner-provided CodeRabbit commercial launch audit (verdict **CONDITIONAL GO**) — raw text **not** committed (may contain env-specific detail).  
**Canonical cross-check:** [`COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md`](COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md) · [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) · [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md)

**Worktree note:** Unrelated dirty files (`.cursor/`, `ops/happ_routing_profile_ru.json`, checkpoint monitoring) **left untouched**.

---

## 1. Executive summary

### What CodeRabbit got right

| Area | Rabbit claim (summary) | Repo verification |
|------|------------------------|-------------------|
| **Terms enforcement gap** | Inline callbacks can bypass terms gate | **Confirmed** — `_ensure_terms_or_prompt` only on `main_menu_handler`; most `@user_router.callback_query` handlers skip it |
| **Trial flag ordering** | `trial_used` set before key exists | **Confirmed** — `set_trial_used` before `provision_key`; reset only on exception/failed provision |
| **Float daily rate** | 200 ₽ → 29 days not 30 | **Confirmed** — `DAILY_RATE=6.67`, `int(balance/6.67)` |
| **Payment/billing test gap** | Weak offline billing coverage | **Confirmed** — BILL-UT-001/002 still OPEN; limited pytest on debit/idempotency |
| **Legacy plan flow** | Old `buy_*_month` path still wired | **Confirmed** — handlers at `handlers.py` ~1649+ |
| **Webhook idempotency race** | `claim_webhook_delivery` TOCTOU | **Confirmed** — SELECT-then-INSERT; on `sqlite3.Error` returns `"new"` |
| **`show_qr` silent failure** | User gets no feedback on some paths | **Confirmed** — bare `return` when inbound/URI missing |
| **`subscription_resolve` timezone** | Naive `datetime.now()` vs ISO expiry | **Confirmed** — line 72–76; risk if expiry strings are tz-aware |
| **G4 / acquisition gaps** | Web→TG bind not proven live | **Confirmed** — handoff UX fixed in repo (`ed8b563`); **live bind still unproven** |
| **Launch not fully ready** | Not open commercial GO | **Aligned** with canonical checkpoint — **NO-GO** for referral/public/300-cap |

### Outdated / incorrect / conflicts with canonical docs

| Rabbit claim | Triage |
|--------------|--------|
| **“Only 2 tests in repo”** | **REJECTED / OUTDATED** — **72** pytest cases collected (`tests/` + selected `ops/test_*.py`); **26** `test_*.py` files; plus **50+** `ops/smoke_*.py` scripts |
| **Capacity PASS — LV + NL sufficient for 300** | **REJECTED** — canonical policy: NL **not** normal Auto delivery capacity; **`delivery_path_nodes < 2`**; [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) § capacity |
| **CONDITIONAL GO = safe for referral/public acquisition** | **REJECTED** — Rabbit **CONDITIONAL GO** ≈ canonical **F&F / manual paid beta only**; referral/public/300-cap remain **NO-GO** |
| **No autopay guard at all** | **PARTIAL** — `run_yookassa_autopay_batch` lacks internal guard, but **`scheduler.start_subscription_monitor` only starts `_yookassa_autopay_loop` when `BOT_PAYMENTS_LIVE`** (`scheduler.py` ~559–560) |
| **Repeat relay2 soak PENDING** | **OUTDATED** — **PASS** recorded report(8) · commit `4fdf06c` |
| **“Safe to merge = safe to accept real payments”** | **REJECTED** — merge safety ≠ commercial payment/acquisition readiness |

### Must fix before paid beta (automated or manual at scale)

1. **BILL-SMOKE-001..004** live/idempotency proof (canonical P0)  
2. **Terms callback guard** (CB-1) — legal/compliance on all money/trial paths  
3. **Trial grant atomicity** (CB-2) — avoid stuck `trial_used` on crash  
4. **Balance kopeks / Decimal** (CB-4) — honest “~30 days for 200 ₽”  
5. **BILL-UT-001/002** offline tests in CI  
6. Owner manual reconciliation process if automated smokes not PASS  

### Must fix before referral / public acquisition

Everything in paid beta **plus**:

1. **G4-TG-BIND-RETEST-001** — live `funnel_bot_start bind:*` ≥ 1  
2. **Desktop Happ launch gate** — sleep/wake (CLIENT-SMOKE-001); normal Bender long-session  
3. **CLIENT-STABILITY-MOBILE-SMOKE-001**  
4. **Capacity ≥2 verified delivery-path nodes** — NL A2/A4 only after owner approval  
5. **REF-ADMIN-001**, anti-abuse, admin user lookup  
6. No referral bonus promises until ledger implemented  

---

## 2. Finding classification table

| Rabbit finding | Rabbit sev | Verified sev | Evidence | Backlog ID | Action | Owner? |
|----------------|------------|--------------|----------|------------|--------|--------|
| **CB-1** Terms bypass on callbacks | Critical | **P0** | `handlers.py` `_ensure_terms_or_prompt` only L529–564, used L569; callbacks `get_trial`, `connect_vpn`, `show_topup`, `pay_*` skip check | **BILL-TERMS-GUARD-001** (proposed) · related **LEGAL-001** | Shared `_ensure_terms_callback(callback, state)` + tests on trial/topup/pay | **Yes** — legal priority |
| **CB-2** Trial flag before key | Critical | **P1** | `handlers.py` L946 before L952 `provision_key`; reset L956/L988 only in-process | **TRIAL-GRANT-ATOMIC-001** (proposed) | Set `trial_used` only after successful `add_new_key`; or transactional outbox + reconcile job | No |
| **CB-3** No `BOT_PAYMENTS_LIVE` in autopay batch | Critical | **P2** (defense) | `yookassa_autopay_scheduler.py` L19 — no guard; **caller guarded** `scheduler.py` L559–560 | **BILL-AUTOPAY-LIVE-GUARD-001** (proposed) · **PAY-AUTO-001** | Add assert at top of `run_yookassa_autopay_batch`; unit test | No |
| **CB-4** Float `DAILY_RATE` 6.67 | High | **P1** | `config.py` L66, L84–88; 200/6.67→**29** days | **BILL-BALANCE-KOPEKS-001** (proposed) · **BILL-UT-001** | Kopeks int internally; update labels/tests | No |
| Webhook `claim_webhook_delivery` TOCTOU | High | **P1** | `database.py` L883–918; duplicate INSERT → error → returns `"new"` | **BILL-001** follow-up | `INSERT OR IGNORE` + return duplicate; or immediate transaction | No |
| No migration rollback | Medium | **P2** | `schema_migrations.py` forward-only by design | **P2-OPS-DB-MIGRATE-01** | Document; backup-before-migrate runbook (exists) | No |
| Low payment/billing offline tests | High | **P0** | 72 pytest total; **no** `test_balance_billing.py`; BILL-UT OPEN | **BILL-UT-001/002** | Implement per BILL-001 audit | No |
| `user_actions` unbounded growth | Medium | **P2** | `database.py` L82+, append-only | **BILL-MON-001** / ops | Retention job or archive policy | **Yes** — retention window |
| `show_qr_handler` silent return | Medium | **P2** | `handlers.py` L1459–1468 | **BOT-001** | User-visible error on all exit paths | No |
| Legacy `buy_*_month` flow active | Medium | **P2** | `handlers.py` L1649+; `PLANS` in `config.py` | **BILL-001** / product | Deprecate UI entry; document wallet-only path | **Yes** — sunset plan |
| `subscription_resolve` naive datetime | Medium | **P2** | `subscription_resolve.py` L72–76 | **P1-CAB-001** follow-up | UTC-aware compare | No |
| Secrets in compose/templates | High | **P1** | Placeholders in `compose/**/*.tmpl`; guardrails forbid live secrets in git | **SEC-001** | Keep sanitize/drift-check; no live `.env` commit | No |
| Capacity LV+NL = OK for 300 | High | **REJECT** | Master backlog § capacity; NL not Auto delivery | **VPN-ARCH-001** · **ACQ-TRIAL-CAP-001** | Do not accept; A2/A4 smoke after gates | **Yes** |
| Test count “2 only” | Info | **REJECT** | 72 pytest collected; 26 test files | — | Ignore Rabbit metric | No |
| G4 web→TG bind broken | High | **PARTIAL** | Audit FAIL live; handoff fix `ed8b563` not deployed | **G4-TG-BIND-RETEST-001** | Owner live retest after deploy | **Yes** |
| Referral attribution | Medium | **PARTIAL** | P1-REF-001 PASS code; bind blocks TG side | **G4-TG-BIND-RETEST-001** | Retest bind funnel | **Yes** |
| Happ client stability | High | **PARTIAL** | report(7)+(8) relay2 active PASS; sleep/wake OPEN | **CLIENT-SMOKE-001** · **CLIENT-STABILITY-001** | No prod selector without owner approval | **Yes** |
| Rabbit CONDITIONAL GO overall | — | **PARTIAL** | Matches **F&F / manual paid beta** only | Checkpoint doc | Do not upgrade to referral/public GO | **Yes** |

---

## 3. Critical blockers verification

### CB-1 — Terms gate bypass on callback handlers

**Status:** **ACCEPTED (P0)**

| Check | Result |
|-------|--------|
| `_ensure_terms_or_prompt` coverage | `/start` shows terms (L452–484); `main_menu_handler` L569 only **message** path |
| `@user_router.callback_query` handlers | **40+** handlers; examples without terms: `get_trial` L936, `connect_vpn` L580, `show_topup` L1508, `pay_yookassa_topup_*` L1569+ |
| Direct inline bypass | User with stale keyboard / forwarded message can hit trial/pay before `agreed_to_terms` |
| `agree_to_terms` | Works L486+; does not retroactively block already-clicked actions |

**Minimal fix task (proposed):** **BILL-TERMS-GUARD-001** — `async def _ensure_terms_callback(callback, state) -> bool` mirroring message guard; call at top of trial, topup, pay, wizard entry; pytest on blocked/allowed paths.

**Owner decision:** Legal/compliance priority for any paid beta.

---

### CB-2 — Trial flag set before key creation

**Status:** **ACCEPTED (P1)**

| Check | Result |
|-------|--------|
| Flow | L946 `set_trial_used` → L952 `provision_key` → L962 `add_new_key` |
| Reset reliability | L956 if provision returns empty; L988 on exception — **not** on SIGKILL/OOM between L946–962 |
| Double-trial window | Crash after L946 leaves `trial_used=1` without key — user blocked from retry |

**Minimal fix task (proposed):** **TRIAL-GRANT-ATOMIC-001** — move `set_trial_used` after successful `add_new_key`; add idempotent “trial in progress” or reconcile admin tool.

---

### CB-3 — No `BOT_PAYMENTS_LIVE` guard in `run_yookassa_autopay_batch`

**Status:** **PARTIAL — downgrade from critical blocker**

| Check | Result |
|-------|--------|
| `run_yookassa_autopay_batch` | No `BOT_PAYMENTS_LIVE` check (`yookassa_autopay_scheduler.py`) |
| Scheduler wiring | `_yookassa_autopay_loop` started **only if** `BOT_PAYMENTS_LIVE` (`scheduler.py` L559–560) |
| `create_recurring_charge` | Uses `assert_yookassa_write_allowed` (non-prod guard), not live flag |
| Residual risk | Direct call to batch in future code/tests could charge if credentials present |

**Minimal fix task (proposed):** **BILL-AUTOPAY-LIVE-GUARD-001** — early return in batch if not `BOT_PAYMENTS_LIVE`; test.

---

### CB-4 — Float balance / day-rate

**Status:** **ACCEPTED (P1)**

| Check | Result |
|-------|--------|
| `DAILY_RATE` | `6.67` float (`config.py` L66) |
| `balance_to_days(200)` | `int(200/6.67)` = **29** days |
| UI | `topup_button_label` shows `~29 дн.` for 200 ₽ preset — consistent but **not** “30 days” marketing expectation |

**Minimal fix task (proposed):** **BILL-BALANCE-KOPEKS-001** — store/compute in kopeks; preset copy alignment; BILL-UT tests.

---

## 4. High-risk findings verification

| Finding | Status | Notes |
|---------|--------|-------|
| **`claim_webhook_delivery` TOCTOU** | **ACCEPTED** | Concurrent workers can both get `"new"` on PK conflict; needs atomic claim |
| **No migration rollback** | **ACCEPTED (by design)** | Forward migrations only; mitigate with backup runbooks |
| **Zero/low billing offline tests** | **ACCEPTED** | BILL-UT-001/002 OPEN; `test_yookassa_topup_idempotency.py` + `test_portal_cabinet_billing.py` exist but narrow |
| **`user_actions` growth** | **ACCEPTED** | No TTL/prune; long-run DB size risk |
| **`show_qr_handler` silent return** | **ACCEPTED** | L1459, L1466, L1468 — no user message |
| **Legacy `buy_*_month` active** | **ACCEPTED** | Parallel to wallet model; `process_successful_payment` non-topup path still in money map (BILL-001 §3) |
| **`subscription_resolve` timezone** | **ACCEPTED** | `datetime.now()` naive vs `fromisoformat` expiry — edge case / Py version dependent |

---

## 5. Conflicts with canonical state

### Capacity (Rabbit vs Bender)

| | CodeRabbit (typical) | Canonical Bender |
|--|---------------------|------------------|
| NL in Auto delivery | Implied active | **Not** in normal user sub path |
| 300 configs | Sufficient on LV+NL | **NO-GO** until ≥2 **verified** delivery-path nodes + acceptance checklist |
| **Triage** | **REJECTED** | Treat as **NEEDS VERIFICATION** only via controlled A2/A4 smoke + owner sign-off |

### Test coverage

| Metric | Rabbit | Repo (2026-06-15) |
|--------|--------|-------------------|
| Total pytest | “~2” | **72 collected** |
| Bot/payment/billing | Missing | **Gap remains** — BILL-UT not implemented |
| Ops smokes | — | **50+** scripts (many AMS/LV SSH — not CI unit tests) |
| **Triage** | Overall count **OUTDATED** | Payment/billing unit gap **ACCEPTED** |

### Launch verdict

| Mode | CodeRabbit (inferred) | After triage (canonical) |
|------|----------------------|---------------------------|
| Internal testing | CONDITIONAL GO | **GO** |
| F&F beta | CONDITIONAL GO | **CONDITIONAL GO** |
| Small paid beta | CONDITIONAL GO | **CONDITIONAL GO** (manual reconciliation; BILL-SMOKE not PASS) |
| Automated paid pilot | — | **NO-GO** |
| Referral growth | — | **NO-GO** |
| Public acquisition | — | **NO-GO** |
| 300 active configs | Rabbit may imply OK | **NO-GO** |

---

## 6. Recommended remediation order

| Order | Task | Surface | Gate |
|-------|------|---------|------|
| **A** | **BILL-TERMS-GUARD-001** — terms on all trial/pay callbacks + tests | `handlers.py` | Before paid beta |
| **B** | **TRIAL-GRANT-ATOMIC-001** — trial flag after key or idempotent grant | `handlers.py` | Before paid beta |
| **C** | **BILL-AUTOPAY-LIVE-GUARD-001** — defense-in-depth in autopay batch | `yookassa_autopay_scheduler.py` | Before enabling autopay UI (**PAY-AUTO-001**) |
| **D** | **BILL-BALANCE-KOPEKS-001** — Decimal/kopeks + preset labels | `config.py`, billing | Before paid marketing copy freeze |
| **E** | **BILL-UT-001/002** + webhook claim hardening | `tests/`, `database.py` | Before automated paid pilot |
| **F** | **G4-TG-BIND-RETEST-001** — deploy handoff fix + live bind proof | owner + AMS | Before referral campaigns |
| **G** | **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** — **eligible**, owner approval only | ops/panel | After repeat soak PASS (`4fdf06c`) — **not auto** |
| **H** | **CLIENT-STABILITY-MOBILE-SMOKE-001** | owner phone | Before mobile acquisition |
| **I** | **VPN-ARCH-001** NL A2/A4 + capacity acceptance | infra | Before 300-cap / public growth |

---

## 7. Backlog mapping

| Proposed ID | Maps to existing | Status |
|-------------|------------------|--------|
| **BILL-TERMS-GUARD-001** | New (compliance); near **LEGAL-001**, **BOT-001** | **Propose add** to master backlog |
| **TRIAL-GRANT-ATOMIC-001** | New; relates **USER-LIFECYCLE-001** | **Propose add** |
| **BILL-AUTOPAY-LIVE-GUARD-001** | **PAY-AUTO-001** (autopay UI/smoke) | Sub-task of PAY-AUTO |
| **BILL-BALANCE-KOPEKS-001** | **BILL-UT-001** scope extension | Can merge into BILL-UT or separate |
| **BILL-UT-001/002** | Already in backlog | **OPEN** |
| **BILL-SMOKE-001..004** | Already in backlog | **OPEN** |
| **G4-TG-BIND-RETEST-001** | G4 audit §11 | **OPEN** |
| **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** | Master backlog | **ELIGIBLE — NOT STARTED** |

**Do not duplicate:** BILL-FIX-001 (**DONE**), P1-REF-001 web attribution (**DONE** code), REPEAT-SOAK-001 (**DONE** PASS).

---

## 8. Merge safety

| Claim | Valid? |
|-------|--------|
| Safe to merge **docs/tooling/analyzer** commits on this branch | **Yes** — recent commits are docs + portal handoff + tests; no prod template drift in those commits |
| Safe to merge = **safe to accept real payments** | **No** — BILL-SMOKE not PASS; terms/trial gaps open |
| Safe to merge = **referral/public acquisition** | **No** — G4 bind unproven live; capacity; client gates OPEN |
| Safe to merge = **prod relay selector change** | **No** — requires **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** owner approval |

**Branch note:** `product-referral-cabinet-ui-v1` mixes portal/referral/cabinet UI with stability docs — review diffs per surface; one-surface-one-commit for future fixes.

---

## 9. Final verdict (after triage)

| Launch mode | Verdict |
|-------------|---------|
| Internal testing | **GO** |
| F&F beta | **CONDITIONAL GO** |
| Small paid beta (manual reconciliation) | **CONDITIONAL GO** |
| Automated paid pilot | **NO-GO** |
| Referral growth | **NO-GO** |
| Public acquisition | **NO-GO** |
| 300 active configs/devices | **NO-GO** |

**CodeRabbit CONDITIONAL GO:** **Partially accepted** — aligns with **internal/F&F/manual paid beta only**, **not** with referral, public acquisition, or 300-cap readiness. Canonical checkpoint unchanged in substance.

---

## References

| Artifact | Role |
|----------|------|
| `4fdf06c` | Repeat relay2 soak PASS |
| `ed8b563` | G4 bind handoff UX (not live-proven) |
| [`COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md`](COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT.md) | Canonical launch modes |
| [`AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md`](AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md) | BILL-001 money map |
| [`G4-TG-BIND-CLIENT-JOURNEY-AUDIT.md`](G4-TG-BIND-CLIENT-JOURNEY-AUDIT.md) | Bind FAIL live |
