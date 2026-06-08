# BenderVPN Master Backlog

**Status:** canonical · **Created:** 2026-06-09
**Branch:** `product-referral-cabinet-ui-v1`
**Purpose:** single source of truth for product, technical, audit, UX, ops, and deferred decisions — nothing lost between sessions.

**Related docs:**

| Document | Role |
|----------|------|
| [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) | Accepted owner decisions (policy v1) |
| [`BENDERVPN-PRODUCT-QUALITY-PLAN.md`](BENDERVPN-PRODUCT-QUALITY-PLAN.md) | Portal UX execution log (Batches 1–3 done) |
| [`BENDERVPN-AUDIT-ROADMAP.md`](BENDERVPN-AUDIT-ROADMAP.md) | Ordered audit sequence |
| [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md) | Linear ops Q001+ queue (infra phases closed) |
| [`BACKLOG-MAP.md`](BACKLOG-MAP.md) | Legacy doc hierarchy map |
| [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md) | VPN infra backlog (gen/sub/routing) |
| [`VPN-INCIDENT-LESSONS-2026-05-25.md`](VPN-INCIDENT-LESSONS-2026-05-25.md) | Hotfix guardrails |

---

## 1. Executive summary

### Current product state

| Layer | State |
|-------|-------|
| **Portal client journey** | **Good enough for pilot** — two-path landing (TG 90d + email 1d), legal 90d/1d distinction, capacity badge hidden, status/setup/errors aligned |
| **Product policy** | **Locked** — `BENDERVPN-PRODUCT-POLICY.md` v1 (2026-06-09) |
| **Backend vs policy** | **Misaligned** — invite gate, capacity cap, device limit, web referral attribution, cabinet API fields |
| **VPN reliability** | **User reports unstable connection / reconnect loops** — needs read-only diagnostic before any routing patch |
| **Admin/reporting** | **Incomplete** — referral ledger, user lookup, funnel metrics missing |
| **Ops queue (Q001+)** | **Phases 1–17 closed** — infra scale/monetize/VPN node resilience done; product-logic track is separate |

### What is already done

- Portal UX Batches 1–3 (`7ffe7c5`, `a54f7a2`, `19678fa`, `3a9fa73`) — cabinet fallback, legal terms, onboarding copy, guide nav, a11y, two-path CTA
- UX-201–207 — status visual language, capacity counter hidden, support `/id`
- Product Policy v1 + Decision Workshop (`81db9a2`)
- VPN infra: xhttp Happ trim (Q-VPN-STAB-005), sub HA, transport mux, commerce go-live (per `BACKLOG-QUEUE.md`)

### Biggest remaining risks

| Risk | Severity | Why |
|------|----------|-----|
| **VPN reconnect instability** | P0/P1 | Direct user pain; may be routing/sub/Happ — patch without audit risks repeat of gen-13→20 incidents |
| **Web referral attribution drop** | P0/P1 | Product promise breach; growth data wrong |
| **Policy vs code gaps** | P1 | Invite-only, 30k cap, one-device are copy-only |
| **No admin visibility** | P1/P2 | Cannot scale invites, detect fraud, or hit 300-config threshold safely |
| **REG-001 not designed** | P2 | Recovery, fraud, legal reconciliation deferred |
| **Legal/privacy final review** | P2 | REG-001 and support visibility not reconciled |

### Next recommended work order

1. **AUDIT-001** — VPN reliability diagnostic (read-only) — see [`BENDERVPN-AUDIT-ROADMAP.md`](BENDERVPN-AUDIT-ROADMAP.md)
2. **AUDIT-002** — VPN architecture map (read-only, parallel OK)
3. **AUDIT-003** — Product policy implementation audit → unlocks Phase 1
4. **Phase 1 implementation** — web ref fix, bot labels, admin ledger/lookup (no schema-heavy REG-001, no hard gate)
5. **AUDIT-007, AUDIT-008** — billing clarity + bot live flow
6. **Phase 2** — REG-001, trial 90→30 switch prep, metrics (before 300 active configs)

---

## 2. Backlog principles

1. **Product truth first, implementation second** — policy v1 and PT-01…PT-12 before code changes.
2. **No false promises** — no live capacity counter, referral bonus, device enforcement, or invite gate in copy until implemented.
3. **No fake capacity counter** — badge «Доступ по приглашению · лимит 30 000» only until stable read-only API.
4. **No Semgrep dependency** — security audits use Trivy, Gitleaks, Bandit, pip-audit, etc.; not Semgrep.
5. **No VPN/prod mutation without explicit approval** — one probe → smoke → commit; see `VPN-INCIDENT-LESSONS`.
6. **One surface per commit** — portal, bot copy, ops, docs — not mixed.
7. **Audit before patch** — especially VPN routing, template PATCH, billing.
8. **Live verification before push** — scoped deploy smoke on LV/AMS for touched surface.

---

## 3. Severity definitions

| Severity | Definition | Examples |
|----------|------------|----------|
| **P0** | Blocks access, security-critical, data/payment loss, active product-promise breach | VPN down/reconnect loop; web ref drop; secrets exposed |
| **P1** | Breaks core model: onboarding, invite/referral, account, support trust, billing clarity | Ghost bot labels; invite policy mismatch; cabinet API gaps |
| **P2** | Important before scale: fraud, admin, UX clarity, observability, REG-001 | Waitlist design; capacity dashboard; fraud signals |
| **P3** | Polish, future scale, nice-to-have | Referral bonus; public capacity API; UX-209 footer ref |
| **P4** | Later ideas / post-scale | Partner automation; calendar subscription; HWID at signup |

---

## 4. Master backlog table

**Legend:** Decision = Accepted / Deferred / N/A · Phase = Policy §12 phase · Status = OPEN / IN_PROGRESS / DONE / DEFERRED / BLOCKED

### 4.1 Product policy & access

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| DEC-IMPL-001 | P1 | Product policy | Policy v1 sign-off | Informal truths scattered | **Accepted** | — | Canonical rules | Workshop 2026-06-09 | `BENDERVPN-PRODUCT-POLICY.md` | Doc published; team uses PT-01…12 | — | No | Done | — | **DONE** |
| PROD-001 | P1 | Invite-only / waitlist | Invite-only not enforced | Copy says invite-only; `/start` allows organic 90d trial | **Accepted:** soft pilot; waitlist after 300 active configs | 4 | Trust + growth control | Full Product Audit | `handlers.py`, portal copy | Organic flagged; no hard gate until Phase 4 | Manual review flag spec | No | No | DEC-IMPL-008 | OPEN |
| PROD-002 | P2 | Capacity / 30k | 30k cap not enforced | Positioning only; no counter or stop | **Accepted:** active configs; grandfather; waitlist at cap | 4 | Overload risk | Audit; UX-207 | `capacity_snapshot.py`, bot | Internal count matches policy §3.4 | ops snapshot | No | Yes at cap | DEC-IMPL-009 | OPEN |
| DEC-IMPL-008 | P2 | Invite-only / waitlist | Waitlist flow | No waitlist UX or data model | **Accepted** Phase 4 | 4 | Controlled growth | Policy §3.3 | portal, bot, DB (later) | No-ref after 300 → waitlist state | UX + admin | Yes | Yes | 300 config metric | DEFERRED |
| DEC-IMPL-009 | P2 | Capacity / 30k | Internal capacity dashboard | No admin view of active configs | **Accepted** | 4 | Threshold decisions | Policy §10.4 | ops, admin | Dashboard shows active configs vs 30k | ops snapshot | No | No | — | OPEN |
| DEC-IMPL-015 | P2 | Invite-only / waitlist | Invite gate enforcement | Hard gate not built | **Deferred** post-300 | 4 | Organic block | Policy §3.3 | `handlers.py` | No-ref blocked after threshold | E2E bot | Yes | Yes | DEC-IMPL-008, 300 configs | DEFERRED |
| DEC-IMPL-020 | P3 | Capacity / 30k | Public capacity API | No stable read-only source | **Deferred** OD-06 | 4 | Transparency | UX-207 audit | portal, setup API | Optional public counter; no fake numbers | API smoke | Yes | Yes | OD-06 | DEFERRED |
| DEC-IMPL-022 | P2 | Capacity / 30k | Hard 30k stop + waitlist drain | No issuance stop at cap | **Accepted** Phase 4 | 5 | Capacity promise | Policy §3.4 | bot, panel | New trials/keys blocked at 30k | admin + bot | Yes | **Yes** | DEC-IMPL-009 | DEFERRED |

### 4.2 Referral & anti-fraud

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| PROD-003 | P0 | Referral | Web `ref_code` dropped | Email fallback loses referral before `issue_web_trial` | **Accepted:** fix end-to-end | 1 | Attribution integrity | Full Product Audit | `portal_web_trial.py`, `portal.js` | Web signup records `referred_by` | py_compile; manual ref test | Yes | No | — | OPEN |
| DEC-IMPL-002 | P0 | Referral | Web referral attribution fix | Same as PROD-003 | **Accepted** | 1 | Growth data | Policy §5.1 | `portal_web_trial.py`, `database.py` | `ref_code` preserved through chain | integration test | Yes | No | — | OPEN |
| DEC-IMPL-006 | P1 | Admin/reporting | Referral ledger | No who→whom report | **Accepted** | 1 | Invite scale | Policy §10.1 | admin, DB queries | Export/list inviter→invitee | manual admin | No | No | — | OPEN |
| DEC-IMPL-017 | P3 | Referral | Referral bonus later | No reward implemented | **Deferred** OD-02 | 3 | Economics | Policy §5.3 | bot, billing | Small time credit after active/paid only | fraud review | Yes | **Yes** | OD-02 | DEFERRED |
| AF-001 | P2 | Anti-fraud | Fraud signals baseline | No IP/email cluster detection | **Accepted** Phase 2 | 2 | Abuse before scale | Policy §10.2 | admin, logs | Same-IP/email flags visible | audit | No | No | DEC-IMPL-006 | OPEN |
| AF-002 | P2 | Anti-fraud | Referral attribution completeness metric | Unknown % with `referred_by` | **Accepted** | 2 | Growth quality | Policy §10.2 | admin | Dashboard % attributed | SQL report | No | No | DEC-IMPL-006 | OPEN |
| DEC-IMPL-018 | P3 | Anti-fraud | Email verification | Not at MVP | **Deferred** OD-04 | 3 | Abuse reduction | Policy §4.1 | web trial | Codes only if abuse threshold | — | Yes | Yes | OD-04 | DEFERRED |
| DEC-IMPL-019 | P3 | Partner channel | Partner ref codes + payout ledger | No partner separation | **Deferred** OD-01 | 5 | Partner scale | Policy §10.3 | admin, ref codes | Partner tag ≠ user ref | manual ledger | No | **Yes** | OD-01 | DEFERRED |
| PARTNER-001 | P3 | Partner channel | Partner seller growth audit | CAC, payout, fraud undefined | **Deferred** OD-01 | 5 | Commercial channel | GTM wiki | docs | Audit report before partner launch | AUDIT-014 | No | **Yes** | OD-01 | OPEN |

### 4.3 Registration (REG-001)

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| REG-001 | P2 | Registration | REG-001 design | TG path collects no phone/email | **Accepted:** soft ask; no block at pilot | 2 | Recovery + fraud | Policy §4; Audit | bot onboarding | Design doc: fields, consent, storage | AUDIT-004 | No | No | — | OPEN |
| DEC-IMPL-011 | P2 | Registration | Optional phone/email in bot onboarding | Not implemented | **Accepted** | 2 | Contact capture | Policy §4.1 | `handlers.py`, keyboards | Contact share + optional email; no trial block | py_compile; UX | Yes | No | REG-001 design | DEFERRED |
| DEC-IMPL-012 | P2 | Registration | Phone/email uniqueness if collected | No UNIQUE on phone | **Accepted** | 2 | Dedup | Policy §4.2 | `database.py` | UNIQUE when field populated | migration review | Yes | **Yes** | OD-09 | DEFERRED |
| DEC-IMPL-016 | P2 | Legal/privacy | Privacy/terms update for REG-001 | Minimization doc conflicts | **Deferred** OD-09 | 2 | Legal compliance | `DATA-MINIMIZATION-POLICY.md` | legal/, privacy | Terms match collection | AUDIT-011 | Yes | **Yes** | OD-09 | OPEN |
| OD-05 | P2 | Registration | Mandatory phone before topup | Not decided | **Deferred** | 2 | Payment fraud | Policy OD-05 | bot, billing | Owner decision recorded | — | — | **Yes** | — | BLOCKED |

### 4.4 Device / config / trial

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| PROD-004 | P1 | Device/config | One device not enforced | Multiple `vpn_keys` allowed | **Accepted:** 1 active config; support for new device | 1 policy / 3 enforce | Fairness + capacity | Audit | panel, `database.py` | Policy documented; no false HWID claim | AUDIT-006 | No | No | — | OPEN |
| DEC-IMPL-014 | P2 | Device/config | Device enforcement design | No deviceLimit/HWID | **Accepted** evaluate Phase 3 | 3 | Link sharing abuse | Policy §6.3 | panel, Remna | Design doc; no prod PATCH in audit | AUDIT-006 | No | **Yes** | OD-03 | OPEN |
| PROD-007 | P1 | Trial policy | Post-trial invite copy alignment | Post-trial text may not match §3 | **Accepted** | 1 | Policy consistency | Audit | `handlers.py`, `ru.json` | Copy matches soft invite-first | forbidden-copy rg | Yes | No | — | OPEN |
| DEC-IMPL-010 | P2 | Trial policy | Trial 90d→30d after 300 active configs | Code still 90d only | **Accepted** | 4 | Economics | Policy §7; `config.py` | `REMNA_TRIAL_DAYS`, bot | New trials 30d; grandfather 90d | env + announce | Yes | **Yes** | 300 configs | DEFERRED |
| OD-03 | P3 | Device/config | Second device paid SKU | Not decided | **Deferred** | 3+ | Revenue | Policy OD-03 | billing, bot | Owner decision | — | — | **Yes** | — | BLOCKED |

### 4.5 Billing / cabinet / bot UX

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| BILL-001 | P1 | Billing/topup | Billing clarity audit | Trial vs wallet; 200₽ vs 6.67₽/day confusion | **Accepted** communicate 6.67₽/day | 1 | Payment trust | Policy §8; Audit | bot, cabinet, terms | Audit report; no logic change unless gap found | AUDIT-007 | No | No | — | OPEN |
| DEC-IMPL-013 | P1 | Cabinet/account | Cabinet API `billing_profile` / trial-wallet | `portal_cabinet.py` missing fields `portal.js` expects | **Accepted** | 1 | Cabinet truth | Full Product Audit | `portal_cabinet.py`, `portal.js` | API returns trial/wallet state | py_compile; cabinet smoke | Yes | No | — | OPEN |
| PROD-005 | P1 | Bot UX/copy | Ghost button labels | «Начать бесплатно», «Мой VPN» in errors | **Accepted** | 1 | Onboarding confusion | Audit | `subscription_resolve.py`, `portal_cabinet.py` | Labels match live menu | py_compile | Yes | No | — | OPEN |
| DEC-IMPL-003 | P1 | Bot UX/copy | Bot/API label alignment | Same as PROD-005 | **Accepted** | 1 | Support load | Policy Phase 1 | bot handlers | All user strings match keyboards | grep labels | Yes | No | — | OPEN |
| PROD-006 | P1 | Bot UX/copy | NL/Latvia in user help | `msg_help_connect` exposes infra names | **Accepted** | 1 | Policy breach PT-11 | Audit | `user_messages.py` | No NL/LV/9443 in user copy | forbidden-copy rg | Yes | No | — | OPEN |
| DEC-IMPL-004 | P1 | Bot UX/copy | Remove infra names from help | Same as PROD-006 | **Accepted** | 1 | Trust | Policy Phase 1 | bot copy | BenderVPN Auto only | rg | Yes | No | — | OPEN |
| DEC-IMPL-005 | P1 | Bot UX/copy | Post-trial invite copy | Same as PROD-007 | **Accepted** | 1 | Growth messaging | Policy §3 | `handlers.py` | Matches soft invite-first | copy review | Yes | No | — | OPEN |
| BOT-001 | P1 | Bot UX/copy | Live bot flow audit | Real TG flow not re-verified post-copy fixes | N/A | 1 | End-to-end truth | Audit need | bot, Mini App | Audit report with safe test user | AUDIT-008 | No | No | — | OPEN |
| OD-10 | P4 | Billing/topup | Wallet-only vs calendar subscription | Not decided | **Deferred** | Future | Billing model | Policy OD-10 | billing | Owner decision | — | — | **Yes** | — | BLOCKED |

### 4.6 Portal UX (quality plan — mostly done)

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| SEM-001 / P1-1 | P1 | Portal UX | Browser cabinet false balance promise | Grace hides data | N/A | — | Trust | Quality plan | `ru.json`, `portal.js` | Browser subline honest | live smoke | Yes | No | — | **DONE** |
| SEM-002 / P1-2 | P1 | Portal UX | Legal 90d vs 1d | Ambiguous terms | N/A | — | Legal clarity | Quality plan | `terms.html` | TG 90d vs email 1d stated | read terms | Yes | No | — | **DONE** |
| SEM-003–008 | P2 | Portal UX | Landing length, tg-blocked CTA, FAQ /id, etc. | Conversion polish | N/A | — | Conversion | Quality plan | portal | Batches 2–3 acceptance | semantic audit | Yes | No | — | **DONE** |
| SEM-009–010, UX-211–212 | P3 | Portal UX | English trial, events-card, guide nav, a11y | Polish | N/A | — | Polish | Quality plan | portal | Batch 3 done | audit | Yes | No | — | **DONE** |
| UX-209 | P3 | Portal UX | Referral on support/footer TG links | Minor IA | N/A | — | Discovery | Quality plan | `ru.json` | Ref preserved in footer links | — | Yes | No | — | OPEN |

### 4.7 Support / admin / legal / ops

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| DEC-IMPL-007 | P1 | Admin/reporting | Admin user lookup | No TG/email/customer ID lookup | **Accepted** | 1 | Support + ops | Policy §10.1 | admin | Single-pane user status | manual test | No | No | — | OPEN |
| ADMIN-001 | P1 | Admin/reporting | Admin/reporting audit | Capabilities unknown vs policy | N/A | 1 | Ops readiness | Policy §10 | admin, bot | Gap report | AUDIT-009 | No | No | — | OPEN |
| DEC-IMPL-021 | P2 | Support/recovery | User-facing support email | TG-only today | **Accepted** before partner scale | 5 | Trust at scale | Policy §9.1 | portal, bot | Email published + SLA | — | Yes | **Yes** | OD-07 | DEFERRED |
| OD-07 | P2 | Support/recovery | Support email address + SLA | Not decided | **Deferred** | 5 | Operations | Policy OD-07 | — | hello@ vs support@ | — | — | **Yes** | — | BLOCKED |
| OD-08 | P2 | Support/recovery | Emergency comms channel | Required before 10k | **Deferred** | 4 | Incident comms | Policy §9.4 | status, email | Channel defined | AUDIT-012 | Yes | **Yes** | — | OPEN |
| RUNBOOK-001 | P2 | Documentation/runbooks | Support/incident runbooks | Support intake not formalized | **Accepted** | 1 | Ops consistency | Policy §9.2 | `docs/` | Runbook: device, /id, screenshot | doc review | No | No | — | OPEN |
| LEGAL-001 | P2 | Legal/privacy | Legal/privacy final review | Draft terms/privacy | N/A | 2 | Compliance | Quality plan §10 | legal/ | Review vs REG-001 | AUDIT-011 | Yes | **Yes** | OD-09 | OPEN |

### 4.8 VPN reliability & architecture

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| VPN-REL-001 | P0 | VPN reliability | Unstable reconnect loop diagnostic | Users report disconnect/reconnect | N/A | **Now** | Core product value | `AUDIT-2026-06-09-VPN-RELIABILITY.md` | ops probes, panel, Happ | RC-1 relay2-only SPOF; RC-2 random balancer | AUDIT-001 done | No | **Yes** for patch | Owner picks profile target | **AUDIT DONE** |
| VPN-ARCH-001 | P1 | VPN architecture | Full VPN architecture audit | Selector/injectHosts mismatch; stealth split map | N/A | **Now** | Informed restore | `AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md` | ops/, panel | Global apply only; test-user N/A; STOPPED | AUDIT-002 done | No | **Yes** global | VPN-REL-001 | **AWAITING APPROVAL** |
| VPN-STAB-005 | P2 | VPN reliability | xhttp Happ batch risk (historical) | xhttp causes «0 servers» in Happ | Partially done | — | Happ UX | `AUDIT-2026-05-VPN-STABILITY-RESOLUTION` | sub-page, template | batch_risk=LOW on Happ UA | diagnose_happ_import | Yes | No | — | **DONE** |
| VPN-INC-001 | P1 | VPN reliability | Incident guardrails enforcement | Repeat PATCH without probe caused gen 13→20 outages | N/A | ongoing | Prod stability | `VPN-INCIDENT-LESSONS` | ops patches | One PATCH → probe → smoke | verify gate | No | **Yes** | — | OPEN |
| VPN-AUD-210+ | P2 | VPN architecture | Remaining VPN full audit items | geosite, DNS leak, remarks, etc. | Per infra backlog | infra | Routing quality | `BACKLOG-VPN-FULL-AUDIT-2026-05-28` | ops, panel | Per-item verify gate | probe scripts | Yes | **Yes** | VPN-REL-001 | OPEN |

### 4.9 Security / observability / performance / release

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| SEC-001 | P1 | Security | Full security audit | Last audit May 2025; surface grew | N/A | 2 | Breach prevention | `AUDIT-2026-05-SECURITY*.md` | bot, portal, ops | Report: secrets, auth, rate limits | AUDIT-010 | No | No | — | OPEN |
| OBS-001 | P2 | Monitoring/observability | Monitoring audit | Status page exists; user-impact detection weak | N/A | 4 | Incident response | `MONITORING.md` | ops, status | Gap report | AUDIT-012 | No | No | — | OPEN |
| PERF-001 | P3 | Metrics/analytics | Performance/load audit | Portal/bot/web-trial load unknown | N/A | 4 | Scale readiness | — | portal, bot | Approved profile only | AUDIT-013 | No | **Yes** | — | OPEN |
| OPS-001 | P2 | Ops/deploy/release | Deploy/release safety audit | Dirty tree, stale smokes, rollback | N/A | 2 | Safe releases | `RUNBOOK-AMS-SAFE-DEPLOY` | deploy scripts | Audit report | AUDIT-015 | No | No | — | OPEN |

### 4.10 Open decisions (tracking only — not implementation)

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|------------|--------|
| OD-01 | P3 | Partner channel | Partner program structure | Channel vs user referral | **Deferred** | 5 | GTM | Policy §11 | Owner | BLOCKED |
| OD-02 | P3 | Referral | Referral bonus economics | +7d who/when | **Deferred** | 3 | Cost | Policy §11 | Owner | BLOCKED |
| OD-03 | P3 | Device/config | Second device paid SKU | Pricing, self-serve | **Deferred** | 3+ | Revenue | Policy §11 | Owner | BLOCKED |
| OD-04 | P3 | Anti-fraud | Email verification timing | Signup vs topup | **Deferred** | 3 | Abuse | Policy §11 | Owner | BLOCKED |
| OD-05 | P2 | Registration | Mandatory phone before topup | Hard vs soft | **Deferred** | 2 | Fraud | Policy §11 | Owner | BLOCKED |
| OD-06 | P3 | Capacity / 30k | Public capacity API shape | Endpoint design | **Deferred** | 4 | UX | Policy §11 | Owner | BLOCKED |
| OD-07 | P2 | Support/recovery | Support email + SLA | Address, response time | **Deferred** | 5 | Trust | Policy §11 | Owner | BLOCKED |
| OD-08 | P2 | Support/recovery | Emergency comms channel | Status vs email list | **Deferred** | 4 | Incidents | Policy §11 | Owner | BLOCKED |
| OD-09 | P2 | Legal/privacy | Privacy revision for REG-001 | Minimization conflict | **Deferred** | 2 | Legal | Policy §11 | Owner | BLOCKED |
| OD-10 | P4 | Billing/topup | Wallet vs calendar subscription | Product model | **Deferred** | Future | Billing | Policy §11 | Owner | BLOCKED |

### 4.11 Severity summary (open items only)

| Severity | Count (approx.) | Examples |
|----------|-----------------|----------|
| **P0** | 3 | VPN-REL-001, PROD-003, DEC-IMPL-002 |
| **P1** | 18 | PROD-001,004,005,006,007; DEC-IMPL-003–007,013; BILL-001; BOT-001; ADMIN-001; VPN-ARCH-001; SEC-001; VPN-INC-001 |
| **P2** | 22 | REG-001; DEC-IMPL-008–012,016,021; PROD-002; AF-*; LEGAL-001; RUNBOOK-001; OD-08; OPS-001; OBS-001; VPN-AUD+ |
| **P3** | 8 | DEC-IMPL-017–020; UX-209; PARTNER-001; PERF-001; OD-01–04,06 |
| **P4** | 1 | OD-10 |
| **DONE** | 12+ | Policy v1, portal batches, SEM/UX items, VPN-STAB-005 |
| **BLOCKED** | 10 | OD-01 … OD-10 (owner decisions) |

---

## 5. Current implementation sequence

### Phase 1 — Product logic alignment (before broader invite rollout)

**Do:** web ref attribution · bot/Mini App labels · remove NL/LV user copy · post-trial invite copy · referral ledger · admin user lookup · cabinet API trial/wallet fields · support runbook draft

**Do not:** schema-heavy REG-001 · hard invite gate · device HWID · capacity enforcement · referral bonus · VPN routing PATCH

**Unlock:** AUDIT-003 product policy implementation audit → then implement

### Phase 2 — Registration / REG-001 / before 300 active configs

**Do:** optional phone/email bot onboarding · legal/privacy update (OD-09) · trial switch policy prep · contact capture metrics · fraud signals · AUDIT-004/005/006

### Phase 3 — Referral / anti-fraud / partner readiness

**Do:** attribution completeness · fraud scoring · device enforcement design · referral bonus if OD-02 approved · email verification if OD-04 approved · partner tagging if OD-01 approved

### Phase 4 — Capacity and 10k readiness

**Do:** internal active config dashboard · waitlist · trial 90→30 switch · invite gate after 300 · emergency comms (OD-08) · observability (AUDIT-012) · support email prep

### Phase 5 — 30k closure & partner scale

**Do:** hard config/trial stop · waitlist drain · capacity expansion decision · user-facing support email · partner ledger · CAC reporting

---

## 6. Do-not-touch list

Without **explicit owner approval**, do not change:

| Category | Items |
|----------|-------|
| **Billing** | Billing logic, daily charge rules, trial skip, balance math |
| **Payments** | YooKassa integration, webhook handlers, real payment tests |
| **VPN core** | Remna provisioning, subscription template PATCH, routing/transport, geo rules |
| **Data** | Database schema migrations, production data mutation |
| **Infra** | Production Caddy, `deploy-node.sh`, emergency/patch/restore scripts |
| **Mass ops** | Mass subscription refresh, broadcast messages to all users |
| **Growth gates** | Referral gate logic (until Phase 4 policy implementation approved) |
| **Repo hygiene** | `git stash` apply, unrelated dirty files in commits, QA artifact commits |

**VPN PATCH rule (from incident lessons):** one change → `probe_subscription.py` → `diagnose_happ_import.py` → smoke → then next change.

---

## 7. Commit / release discipline

| Rule | Detail |
|------|--------|
| One surface per commit | portal · bot copy · ops · docs — not mixed |
| Checks by surface | `json.tool` / `node --check` / `py_compile` / forbidden-copy rg |
| Deploy scoped surface only | portal LV script; bot AMS; legal scp if needed |
| Live smoke before push | touched URLs on `k9x2m1.conntest.xyz:8443` or bot test user |
| No unrelated dirty files | QA screenshots, `.playwright-review/`, skills — exclude unless requested |
| Docs commits | May bundle policy + backlog + roadmap in one `docs(product):` commit |
| No push without ask | Unless owner explicitly requests |

---

## 8. Document maintenance

- **Add new items** to §4 table with ID, severity, source evidence.
- **Mark DONE** when acceptance criteria met + verify recorded in execution log.
- **Do not duplicate** `BACKLOG-QUEUE.md` infra Q items — link to `BACKLOG-VPN-FULL-AUDIT` for VPN infra.
- **Review** at 300 active configs or when policy v2 triggered.

---

**Version:** 1.0 · **Next:** AUDIT-001 VPN reliability diagnostic
