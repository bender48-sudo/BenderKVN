# AUDIT CLOSEOUT — Launch Backlog Freeze

**ID:** AUDIT-CLOSEOUT-001  
**Date:** 2026-06-10  
**Branch:** `product-referral-cabinet-ui-v1`  
**Repo HEAD:** `08bf3f6` (closeout); see FINAL-AUDIT-COMPLETE-001 for push state
**Final audit phase:** **COMPLETE** after SUPPORT-AI-ARCH-001 (FINAL-AUDIT-COMPLETE-001)
**Mode:** final audit consolidation + backlog freeze · **no implementation** · **no prod mutation**

**Purpose:** Close the 2026-06-10 audit wave; freeze implementation-ready backlog; define tomorrow's work queue.

---

## 1. Executive summary

The **2026-06-10 commercial launch audit wave is complete** for architecture and decision design. Remaining work is **implementation, smoke, owner proof, or owner decision** — not new broad audits.

| Launch type | Verdict | Basis |
|-------------|---------|-------|
| **F&F** | **GO** | Manual support; disclose known limits |
| **Closed soft launch** | **SOFT-LAUNCH ONLY** | Happ mobile-first; L2 device minimum; copy fixes pending |
| **Paid pilot** | **NO-GO** | G6 smokes; G7 DEVICE-ENFORCE-001; G8 admin; G4 bind |
| **Open launch** | **NO-GO** | G1 desktop/SaaS; G9 monitoring; G11 CI; L3/L4 enforce |
| **Referral growth** | **NO-GO** | G4 bind BLOCKED; REF-ADMIN-001; DEVICE-ENFORCE-001 at scale |

**Owner clarification incorporated:** MODEL A (one tracked config per device) is **not commercially complete** without **DEVICE-ENFORCE-001** — detection of same active subscription URL reused on another physical device. L2 = soft-launch minimum only; paid/open requires **L3/L4**.

**Implementation may start tomorrow** on **TRACK 0** (copy/UX hygiene) without new audits.

---

## 2. Audit inventory

| Audit ID | Status | What it closed | What remains | Next artifact | Remaining type |
|----------|--------|----------------|--------------|---------------|----------------|
| **COMMERCIAL-LAUNCH-READINESS** | **CLOSED** | G1–G15 matrix; launch verdicts A–E | Implementation per gates | This doc §4 | Implementation |
| **BILL-001 / LAUNCH-003** | **CLOSED** | Money-path map; idempotency risks | BILL-SMOKE-001..004 live proof | `POSTDEPLOY-BILL-FIX-001` | Smoke |
| **BILL-FIX-001** | **CLOSED + DEPLOYED** | `yk:{payment_id}` reconcile alignment | No `--apply` without owner; smokes | AMS postdeploy | Smoke |
| **USER-LIFECYCLE-001** | **CLOSED** | S0–S12; scenarios A–H; go/no-go | REG-001, PAY-001 implementation | Lifecycle doc | Implementation |
| **DEVICE-ARCH-001** | **CLOSED** | MODEL A target; billing × N; L0–L5 | Owner approve MODEL A; DEVICE-* impl | `ARCH-MULTI-DEVICE` §14 | Owner + Implementation |
| **DEVICE-ENFORCE-001** | **CLOSED (design)** | Reuse detection architecture §14 | DEVICE-SMOKE proof + implementation | `ARCH-MULTI-DEVICE` §14 | Smoke + Implementation |
| **REFERRAL-ARCH-001** | **CLOSED** | OPTION 3 hybrid; REF-* gates | Owner approve OPTION 3; REF-* impl | `ARCH-REFERRAL` | Owner + Implementation |
| **INCIDENT-001** | **MONITORING** | Prod stability read-only audit | Extended owner soak | Stability prod audit | Owner proof |
| **INCIDENT-002** | **MONITORING** | Interim stable after fresh import | Extended soak | Active failure capture | Owner proof |
| **INCIDENT-003** | **PARTIAL** | Sleep/resume diagnostic protocol | Owner route/DNS matrix | Laptop sleep doc | Owner proof |
| **INCIDENT-004** | **PARTIAL** | SaaS long-session hypothesis | 20–30 min soak | Browser long-session doc | Owner proof |
| **P1-CAB-001** | **CLOSED + DEPLOYED** | `billing_profile` cabinet API | — | Postdeploy CAB | — |
| **P1-DEV-001** | **CLOSED + DEPLOYED** | Config count/list read-only | DEVICE-ADMIN revoke | Postdeploy DEV | Implementation |
| **P1-REF-001** | **CLOSED + DEPLOYED** | Web `ref_code` attribution PASS | TG bind migration FAIL | Postdeploy REF | Smoke (bind) |
| **DEVELOPMENT-READINESS-GATES** | **CLOSED** | G0–G5 hierarchy | Per-gate implementation | Gates doc | Implementation |
| **VPN-REL-001 / VPN-ARCH-001** | **SUPERSEDED** | Candidate D applied | INCIDENT-003/004 desktop | Incident docs | Owner proof |
| **SUPPORT-AI-ARCH-001** | **CLOSED** | AI triage bot architecture; L0–L4 permissions | SUPPORT-TICKET/DIAG impl | [`ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md`](ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md) | Implementation |

**Audit-complete definition:** Architecture, gates, risks, and ordered surfaces are documented. **Not** audit-complete: live smokes, Remna HWID proof, bind retest, billing `--apply`, enforcement PATCH.

---

## 3. Final gate board

Legend: **DONE** = audit/impl complete · **PARTIAL** · **BLOCKED** · **MONITORING** · **OWNER_DECISION** · **READY_FOR_IMPLEMENTATION**

### A. VPN stability

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| G1 mobile Happ | **MONITORING** | No | Partial | Partial | **Yes** | No | INCIDENT-002 soak |
| G1 desktop sleep | **PARTIAL** | No | **Yes** | **Yes** | **Yes** | No | LAUNCH-001 / INCIDENT-003 |
| G1 browser SaaS | **PARTIAL** | No | **Yes** | **Yes** | **Yes** | No | INCIDENT-004 soak |
| G2 client apps | **PARTIAL** | No | No | Partial | **Yes** | No | Happ primary only |

### B. Billing / payment

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| BILL-001 audit | **DONE** | — | — | — | — | — | — |
| BILL-FIX-001 deploy | **DONE** | — | — | — | — | — | — |
| BILL-UT-001/002 | **READY_FOR_IMPLEMENTATION** | No | No | Partial | Partial | No | Unit tests CI |
| BILL-SMOKE-001..004 | **NOT_STARTED** | No | No | **BLOCKER** | **BLOCKER** | No | `ops/smoke_billing_*` |
| PAY-AUTO-001 | **PARTIAL** | No | No | **Yes** | **Yes** | No | Wire autopay UI |
| G6 overall | **PARTIAL** | Manual OK | Manual OK | **BLOCKER** | **BLOCKER** | No | Smokes + owner |

### C. User lifecycle

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| USER-LIFECYCLE-001 | **DONE** | — | — | — | — | — | — |
| G4 TG bind | **BLOCKED** | No | Partial | **Yes** | **Yes** | **Yes** | G4-BIND-RETEST |
| REG-001 | **OWNER_DECISION** | No | No | Partial | Partial | No | Design deferred Phase 2 |

### D. Device architecture / enforcement

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| DEVICE-ARCH-001 | **DONE** | — | — | — | — | — | Owner approve MODEL A |
| DEVICE-ENFORCE-001 | **READY_FOR_PROOF** | No | Partial | **BLOCKER** | **BLOCKER** | Partial | DEVICE-SMOKE-001 |
| P1-DEV-001 | **DONE** | — | — | — | — | — | — |
| DEVICE-COPY-001 | **READY_FOR_IMPLEMENTATION** | No | **Yes** | **Yes** | **Yes** | No | `ru.json` deploy |
| DEVICE-ADMIN-001 | **NOT_STARTED** | No | **Yes** | **Yes** | **Yes** | No | Admin revoke |
| DEVICE-BILL-001 | **BLOCKED** | No | No | **Yes** | **Yes** | No | After BILL-SMOKE |
| L2 enforce | **PARTIAL** | OK | **Min** | No | No | No | Support revoke |
| L3/L4 enforce | **NOT_STARTED** | No | No | **BLOCKER** | **BLOCKER** | At scale | DEVICE-ENFORCE-001 |

### E. Referral acquisition / analytics

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| REFERRAL-ARCH-001 | **DONE** | — | — | — | — | — | Owner approve OPTION 3 |
| P1-REF-001 web attr | **DONE** | — | — | — | — | — | — |
| REF-BIND-001 | **BLOCKED** | No | Partial | **Yes** | **Yes** | **Yes** | G4-BIND-RETEST |
| REF-COPY-001 / P1-REF-002 | **READY_FOR_IMPLEMENTATION** | No | **Yes** | **Yes** | **Yes** | No | Gate +3d; soften note |
| REF-PORTAL-001 | **OWNER_DECISION** | No | Partial | Partial | Partial | **Yes** | Portal share URL |
| REF-ADMIN-001 | **NOT_STARTED** | No | Partial | **Yes** | **Yes** | **BLOCKER** | Admin ledger |

### F. Copy / UX truth

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| COPY-TRUTH-001 | **IMPLEMENTED** (repo) | No | **Yes** deploy | **Yes** deploy | **Yes** deploy | No | Bot ghost labels fixed; LV deploy pending |
| G10 device_rule / MODEL A cabinet | **IMPLEMENTED** (repo) | No | **Yes** deploy | **Yes** deploy | **Yes** deploy | No | `COMMERCIAL-UX-DEVICE-MVP-001` — gated add/replace CTAs |
| Setup link-first UX | **IMPLEMENTED** (repo) | No | Partial deploy | Partial deploy | Partial deploy | No | Link primary, QR secondary (`setup.html/js` v30) |
| Cabinet typography | **IMPLEMENTED** (repo) | No | Partial deploy | No | No | No | Balance amount/days split |
| COMMERCIAL-UX-DEVICE-MVP-001 | **IMPLEMENTED** (repo) | No | Deploy LV portal | Deploy | Deploy | No | MODEL A UX; backend add/replace/billing still gated |

### G. Admin / support

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| P1-ADM-001 lookup | **NOT_STARTED** | No | **Yes** | **Yes** | **Yes** | Partial | `admin_handlers.py` |
| P1-ADM-003 payment lookup | **NOT_STARTED** | No | No | **Yes** | **Yes** | No | Admin billing query |
| LAUNCH-004 runbooks | **NOT_STARTED** | No | **Yes** | **Yes** | **Yes** | No | docs runbook pack |

### H. Monitoring / CI

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| G9 monitoring | **NOT_STARTED** | OK | Partial | **Yes** | **BLOCKER** | No | Profile alert cron |
| G11 CI gitleaks | **NOT_STARTED** | OK | Partial | **Yes** | **BLOCKER** | No | P2-CI-001 |
| BILL-MON-001 | **NOT_STARTED** | No | No | **Yes** | **Yes** | No | Billing job alert |

### I. Commercial policy / legal

| Gate | Status | F&F | Soft | Paid | Open | Referral | Next surface |
|------|--------|-----|------|------|------|----------|--------------|
| G12 policy enforce | **NOT_STARTED** | OK | OK | Risk | **Yes** | No | Phase 4 gates |
| G14 reporting | **NOT_STARTED** | No | No | **Yes** | **Yes** | **Yes** | REF-ADMIN + reconcile view |
| Product Policy v1 | **DONE** | — | — | — | — | — | Pending notes only |

---

## 4. Final blockers by launch type

### F&F — none hard (manual support)

- Disclose: bind unproven, desktop sleep/SaaS open, no HWID enforce, referral bot-only share.

### Soft launch

1. **COPY-TRUTH-001** / **DEVICE-COPY-001** — `device_rule`, ghost labels, NL/LV help
2. **REF-COPY-001** — soften `referral_preserve_note`; gate hidden +3d
3. **LAUNCH-004** — support runbook draft
4. Desktop sleep/SaaS — position as known limitation

### Paid pilot

1. **BILL-SMOKE-001..004** — live money-path proof
2. **DEVICE-ENFORCE-001** — L3/L4 reuse detection or written waiver
3. **G4 bind** — retest or disable email growth path
4. **P1-ADM-001** + **DEVICE-ADMIN-001** — lookup + tracked revoke
5. **PAY-AUTO-001** — autopay UI wired (if selling automated topup)

### Open launch

All paid pilot blockers plus:

1. **G1** desktop INCIDENT-003/004 closed or waived
2. **G9/G11** monitoring + CI
3. **G12/G14** policy enforcement + reporting
4. **DEVICE-BILL-001** if multi-device SKU enabled

### Referral growth

1. **G4 bind PASS**
2. **REF-ADMIN-001** ledger
3. **REF-PORTAL-001** (owner approve OPTION 3)
4. **DEVICE-ENFORCE-001** at campaign scale
5. No bonus copy (REF-BONUS-001 deferred)

---

## 5. Backlog tracks (frozen)

### TRACK 0 — Immediate hygiene / soft-launch blockers (tomorrow first)

| ID | P | Status | Blocker | Owner? | Summary |
|----|---|--------|---------|--------|---------|
| **COMMERCIAL-UX-DEVICE-MVP-001** | P0 | **DONE** (repo) | MODEL A UX | No | Portal cabinet/setup; gated add/replace; no billing/enforce |
| **COPY-TRUTH-001** | P0 | **DONE** (repo) | Soft+paid copy deploy | No | Ghost bot labels; NL/LV removal — deploy pending |
| **DEVICE-COPY-001** | P0 | **DONE** (repo) | G10 deploy | No | Merged into COMMERCIAL-UX-DEVICE-MVP-001 |
| **REF-COPY-001** / **P1-REF-002** | P0 | OPEN | Soft+referral | No | Gate hidden +3d; soften preserve note |
| **SETUP-UX-001** | P1 | **DONE** (repo) | Soft UX deploy | No | Merged into COMMERCIAL-UX-DEVICE-MVP-001 |
| **CABINET-TYPE-001** | P2 | **DONE** (repo) | Polish deploy | No | Merged into COMMERCIAL-UX-DEVICE-MVP-001 |

### TRACK 1 — Bind / referral entrypoint

| ID | P | Status | Blocker | Owner? | Deps |
|----|---|--------|---------|--------|------|
| **G4-BIND-RETEST** | P0 | BLOCKED | Referral+email | Owner in-app | — |
| **REF-PORTAL-001** | P1 | OPEN | Referral growth | **Yes** OPTION 3 | ARCH approved |
| **REF-COUNTER-001** | P1 | OPEN | Referral UX | No | REF-PORTAL-001 |
| **REF-ADMIN-001** | P1 | OPEN | Campaigns | No | — |
| **REF-METRICS-001** | P2 | OPEN | Paid referral | No | REF-ADMIN-001 |
| **REF-ATTR-001** | P1 | OPEN | Bind proof | No | G4 PASS |

### TRACK 2 — Billing / payment proof

| ID | P | Status | Blocker | Owner? | Deps |
|----|---|--------|---------|--------|------|
| **BILL-UT-001/002** | P1 | OPEN | CI confidence | No | — |
| **BILL-SMOKE-001** | P0 | NOT_STARTED | Paid pilot | **Yes** controlled users | BILL-FIX-001 |
| **BILL-SMOKE-002..004** | P0 | NOT_STARTED | Paid pilot | **Yes** | 001 |
| **BILL-RUNBOOK-001** | P1 | OPEN | Support | No | Smokes |
| **P1-ADM-003** | P1 | OPEN | Disputes | No | — |
| **BILL-MON-001** | P2 | OPEN | Open launch | No | — |
| **PAY-AUTO-001** | P1 | OPEN | Automated paid | No | BILL-SMOKE |

### TRACK 3 — Device architecture

| ID | P | Status | Blocker | Owner? | Deps |
|----|---|--------|---------|--------|------|
| **DEVICE-SMOKE-001** | P0 | NOT_STARTED | ENFORCE proof | No | Read-only lab |
| **DEVICE-ENFORCE-001** | P0 | OPEN (design done) | **Paid/open** | **Yes** strictness | SMOKE-001 |
| **DEVICE-DATA-001** | P1 | NOT_STARTED | MODEL A | **Yes** MODEL A | ARCH |
| **DEVICE-ADMIN-001** | P1 | NOT_STARTED | Soft+paid | No | DATA-001 |
| **DEVICE-REPLACE-001** | P1 | NOT_STARTED | S12 | No | ADMIN-001 |
| **DEVICE-REVOKE-001** | P1 | NOT_STARTED | G7 | No | REPLACE |
| **DEVICE-BILL-001** | P0 | BLOCKED | Money | **Yes** coefficient | BILL-SMOKE |
| **DEVICE-ADD-001** | P1 | BLOCKED | Multi-device | **Yes** | BILL-001 |
| **DEVICE-UX-001** | P2 | NOT_STARTED | UX | No | BILL-001 |

### TRACK 4 — VPN stability / client

| ID | P | Status | Blocker | Owner? |
|----|---|--------|---------|--------|
| **INCIDENT-003** diagnostics | P0 | PARTIAL | Desktop | Owner |
| **INCIDENT-004** SaaS soak | P0 | PARTIAL | Desktop SaaS | Owner |
| **Hiddify A/B** | P2 | OPEN | G2 decision | **Yes** |
| **VLESS functional probe** | P2 | OPEN | G9 | No |

### TRACK 5 — Monitoring / CI / ops

| ID | P | Status | Blocker |
|----|---|--------|---------|
| **P2-CI-001/002** | P1 | NOT_STARTED | Open launch |
| **Profile integrity alert** | P1 | NOT_STARTED | G9 |
| **Payment callback monitor** | P1 | NOT_STARTED | G9 |
| **LAUNCH-004 runbooks** | P1 | NOT_STARTED | Soft+paid |
| **LAUNCH-015 checklist** | P2 | PARTIAL | Open launch |

### TRACK 6 — Support AI / technical triage

| ID | P | Status | Blocker | Notes |
|----|---|--------|---------|-------|
| **SUPPORT-AI-ARCH-001** | P1 | **DONE** (arch) | — | Not F&F blocker |
| **SUPPORT-TICKET-001** | P1 | NOT_STARTED | Paid partial | Ticket schema |
| **SUPPORT-DIAG-001** | P1 | NOT_STARTED | Paid partial | Needs P1-ADM read-only |
| **SUPPORT-CURSOR-HANDOFF-001** | P1 | NOT_STARTED | Paid partial | Cursor escalation |
| **SUPPORT-REPLY-001** | P1 | NOT_STARTED | Paid partial | Reply drafts |
| **SUPPORT-SECURITY-001** | P1 | NOT_STARTED | Paid partial | Redaction ACL |
| **SUPPORT-RAG-001** | P2 | NOT_STARTED | Open | Docs index |
| **SUPPORT-ADMIN-001** | P2 | NOT_STARTED | Open | Operator queue |
| **SUPPORT-SMOKE-001** | P2 | NOT_STARTED | Auto gate | Simulated cases |
| **SUPPORT-AUTO-001** | P2 | NOT_STARTED | User bot | After smokes |

**TRACK 6 rules:** Internal copilot **recommended** before paid/open scale; **not** prerequisite for tomorrow TRACK 0. AI must **not** bypass missing P1-ADM / LAUNCH-004 runbooks.

---

## 6. Tomorrow implementation plan (2026-06-11)

**Rules:** one surface per commit · one deploy at a time · no billing/Remna mutation without approval · postdeploy doc for every deploy.

### Task 1 — Portal copy truth (commit 1)

| Field | Value |
|-------|-------|
| **ID** | DEVICE-COPY-001 + REF-COPY note (portal half) |
| **Objective** | Fix `setup.device_rule`, `referral_preserve_note`, `home.devices_note` |
| **Allowed** | `web/portal/content/ru.json`, `web/portal/setup.html` copy strings only |
| **Forbidden** | Bot, billing, Remna, referral URL behavior |
| **Tests** | `python -m json.tool web/portal/content/ru.json`; forbidden-copy rg |
| **Deploy** | Yes — portal LV |
| **Approval** | `approve deploy COPY-TRUTH-001 portal` |
| **Rollback** | LV portal backup per runbook |
| **Output** | Postdeploy note or quality-plan tick |

### Task 2 — Bot copy truth (commit 2)

| Field | Value |
|-------|-------|
| **ID** | COPY-TRUTH-001 bot |
| **Objective** | Remove ghost labels; strip NL/LV from `msg_help_connect` |
| **Allowed** | `bot_src/subscription_resolve.py`, `bot_src/user_messages.py`, `bot_src/portal_cabinet.py` (label strings) |
| **Forbidden** | Handlers logic, billing, +3d (separate commit) |
| **Tests** | `py_compile`; forbidden-copy rg |
| **Deploy** | Yes — AMS bot |
| **Approval** | `approve deploy COPY-TRUTH-001 bot` |

### Task 3 — Hidden +3d gate (commit 3)

| Field | Value |
|-------|-------|
| **ID** | P1-REF-002 / REF-COPY-001 |
| **Objective** | Remove or gate `days_to_add += 3` on first purchase |
| **Allowed** | `bot_src/handlers.py` (legacy purchase path only) |
| **Forbidden** | Bonus engine, referral rewards |
| **Tests** | `py_compile`; grep `ref_bonus_received` |
| **Deploy** | Yes — AMS bot (can combine with Task 2 **only if** owner accepts one bot deploy) |
| **Approval** | `approve REF-COPY-001` |

**Split rule:** Tasks 2 and 3 may ship in **one bot deploy** but prefer **two commits** (copy vs logic).

### Task 4 — Setup page UX (commit 4)

| Field | Value |
|-------|-------|
| **ID** | SETUP-UX-001 |
| **Objective** | Link-first CTA, QR secondary, fix broken mobile layout if present |
| **Allowed** | `web/portal/setup.html`, `web/portal/assets/setup.js`, portal CSS |
| **Forbidden** | Trial API, billing |
| **Tests** | `node --check`; manual mobile viewport |
| **Deploy** | Yes — portal LV |
| **Approval** | `approve deploy SETUP-UX-001` |

### Task 5 — Cabinet typography (commit 5, if time)

| Field | Value |
|-------|-------|
| **ID** | CABINET-TYPE-001 |
| **Objective** | Balance/heading typography polish |
| **Allowed** | `web/portal/assets/portal.css`, `portal.js` display only |
| **Forbidden** | Cabinet API, billing fields |
| **Deploy** | Yes — portal LV |
| **Approval** | `approve deploy CABINET-TYPE-001` |

### Task 6 — G4 bind retest (owner-led, no code unless fix found)

| Field | Value |
|-------|-------|
| **ID** | G4-BIND-RETEST / REF-BIND-001 |
| **Objective** | Prove web→TG bind + referral migration on AMS |
| **Allowed** | `ops/smoke_p1_ref_tg_bind_ams.py` read-only on AMS |
| **Forbidden** | Prod DB mutation except controlled smoke emails |
| **Tests** | `P1_BIND_VERIFY_PASS` + `funnel_bot_start bind:*` > 0 |
| **Deploy** | No (unless bug fix discovered) |
| **Approval** | Owner opens bind link **in Telegram app** |

### Task 7 — Billing unit tests (commit 6, parallel-safe)

| Field | Value |
|-------|-------|
| **ID** | BILL-UT-001/002 |
| **Objective** | CI tests for daily debit + topup idempotency |
| **Allowed** | `tests/`, `bot_src/balance_billing.py`, `payment_idempotency.py` test imports only |
| **Forbidden** | Live YooKassa, reconcile `--apply` |
| **Deploy** | No |
| **Approval** | None (repo-only) |

### Task 8 — BILL-SMOKE prep only (no live money)

| Field | Value |
|-------|-------|
| **ID** | BILL-SMOKE-001 prep |
| **Objective** | Draft/finish `ops/smoke_billing_commercial_ams.py` skeleton |
| **Allowed** | `ops/` new script, docs |
| **Forbidden** | Live topup, webhook replay, `--apply` |
| **Approval** | `approve BILL-SMOKE-001 prep` — **not** live smoke |

### Task 9 — Support runbook or P1-ADM-003 (if time)

| Field | Value |
|-------|-------|
| **ID** | LAUNCH-004 **or** P1-ADM-003 |
| **Objective** | Payment-not-applied runbook **or** admin topup lookup |
| **Allowed** | `docs/` **or** `admin_handlers.py` read-only queries |
| **Forbidden** | Balance changes |
| **Deploy** | AMS if admin code |

---

## 7. Owner decisions required before implementation

| # | Decision | Blocks |
|---|----------|--------|
| 1 | Approve **MODEL A** device architecture | DEVICE-DATA-001, DEVICE-BILL-001 |
| 2 | Approve **OPTION 3** referral entrypoint | REF-PORTAL-001 |
| 3 | **DEVICE-ENFORCE-001** strictness or paid/open waiver | Paid/open launch |
| 4 | **G4 bind** retest participation (real TG app) | Referral + email growth |
| 5 | **BILL-SMOKE** controlled test users on AMS | Automated paid pilot |
| 6 | Combine bot copy + P1-REF-002 in one deploy vs two | Tomorrow sequencing |
| 7 | **OD-02** referral bonus | Deferred — do not implement |
| 8 | **OD-03** second device pricing | DEVICE-BILL-001 |

---

## 8. Approval phrases registry

| Phrase | Permits |
|--------|---------|
| `approve deploy COPY-TRUTH-001 portal` | LV portal copy deploy |
| `approve deploy COPY-TRUTH-001 bot` | AMS bot copy deploy |
| `approve REF-COPY-001` | Gate/remove hidden +3d |
| `approve deploy SETUP-UX-001` | Setup page deploy |
| `approve DEVICE-SMOKE-001 lab` | Read-only Remna HWID lab |
| `approve DEVICE-ENFORCE-001` | Enforcement design → implementation |
| `approve MODEL A target` | Multi-device schema/billing track |
| `approve OPTION 3` | Portal-first referral share |
| `approve BILL-SMOKE-001` | Live controlled topup smoke on AMS |
| `approve reconcile --apply` | Balance mutation via reconcile |
| `approve DEVICE-BILL-001 coefficient` | Per-device daily debit live |
| `approve REF-PORTAL-001` | Change public share URL behavior |
| `approve AMS deploy P1-*` | Scoped AMS bot deploy |

---

## 9. Explicit NO-GO list

- New broad audits (this wave is **closed**)
- Paid/open launch without BILL-SMOKE + DEVICE-ENFORCE-001 (or waiver)
- Referral campaigns while G4 bind BLOCKED
- Bonus/reward copy without REF-BONUS-001
- Claim HWID enforcement in UI before DEVICE-ENFORCE-001 PASS
- `reconcile --apply` without explicit approval
- Remna template PATCH / HWID settings PATCH without DEVICE-SMOKE proof
- Multi-device self-service before DEVICE-BILL-001
- Semgrep / `SEMGREP_APP_TOKEN`

---

## 10. What remains (not audit)

| Category | Examples |
|----------|----------|
| **Implementation** | COPY-TRUTH, REF-PORTAL, DEVICE-ADMIN, PAY-AUTO |
| **Smoke / proof** | BILL-SMOKE, DEVICE-SMOKE, G4 bind retest |
| **Owner proof** | INCIDENT-003/004 diagnostics, G1 soak logs |
| **Owner decision** | MODEL A, OPTION 3, OD-02/03, enforce waiver |
| **Deploy** | Portal LV, bot AMS per task |
| **Monitoring** | G9 alerts, CI gitleaks |

---

## 11. References

| Doc | Role |
|-----|------|
| [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) | Master launch gates |
| [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) | MODEL A + §14 DEVICE-ENFORCE-001 |
| [`ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md`](ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md) | Referral OPTION 3 |
| [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) | Frozen tracks §1.1 |
| [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md) | G0–G5 |
| [`ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md`](ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md) | SUPPORT-AI-ARCH-001 |

---

## 12. Final audit phase registry (FINAL-AUDIT-COMPLETE-001)

| Phase | ID | Status |
|-------|-----|--------|
| Commercial launch | COMMERCIAL-LAUNCH-READINESS | **CLOSED** |
| Billing | BILL-001 | **CLOSED** |
| Lifecycle | USER-LIFECYCLE-001 | **CLOSED** |
| Device | DEVICE-ARCH-001 + DEVICE-ENFORCE-001 design | **CLOSED** |
| Referral | REFERRAL-ARCH-001 | **CLOSED** |
| Support AI | SUPPORT-AI-ARCH-001 | **CLOSED** |
| Backlog freeze | AUDIT-CLOSEOUT-001 | **CLOSED** |

**Remaining broad audits:** **none identified** (scan 2026-06-10).

**Remaining work types:** implementation (TRACK 0–6) · smoke/proof · owner decisions · documentation cleanup (e.g. «Получить доступ» glossary → COPY-TRUTH).

---

**AUDIT-CLOSEOUT-001 complete.** Audit phase **closed**. Implementation may begin TRACK 0.
