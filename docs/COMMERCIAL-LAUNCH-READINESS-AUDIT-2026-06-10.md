# COMMERCIAL-LAUNCH-READINESS-AUDIT — BenderVPN

**Date:** 2026-06-10  
**Mode:** audit only · no deploy · no prod mutation · no implementation  
**Branch:** `product-referral-cabinet-ui-v1`  
**Local HEAD:** `928a336` (3 commits ahead of `origin/product-referral-cabinet-ui-v1` @ `cfdd756`)  
**Purpose:** full launch-decision audit for commercial readiness

---

## 1. Executive summary

BenderVPN has **strong infra and profile integrity** post–Candidate D, **partial product-truth improvements** (P1-CAB-001, P1-DEV-001, P1-REF-001 web attribution), and **significant commercial-readiness gaps** in billing assurance, device lifecycle, TG bind, desktop sleep/resume, monitoring automation, admin/support tooling, and copy honesty.

| Launch type | Verdict |
|-------------|---------|
| **A. Internal / friends-and-family** | **GO** — manual support; disclose known limits |
| **B. Closed soft launch** (low volume, manual support) | **SOFT-LAUNCH ONLY** — Happ mobile-first; no web-email growth push |
| **C. Paid commercial pilot** | **NO-GO** — money-flow audit incomplete; support revoke path weak |
| **D. Open commercial launch** | **NO-GO** — monitoring, CI, enforcement, desktop VPN, billing proof missing |
| **E. Referral-driven growth launch** | **NO-GO** — TG bind open; web→TG migration unverified; bonus not implemented |

**Product development remains frozen** until G1 sleep/resume evidence + commercial blockers are addressed or explicitly waived by owner.

---

## 2. Repo state (Step 0)

| Item | Value |
|------|-------|
| Branch | `product-referral-cabinet-ui-v1` |
| Local HEAD | `928a336e500aa9da1e1a6d63444796bd20c89b71` |
| Origin HEAD | `cfdd756daf6308763aa6d610a5aabdc1086101fc` |
| Ahead | **3** commits (all **docs-only**) |
| Behind | **0** |
| Staged | None |
| Deploy in progress | **No** |

### Unpushed commits (docs-only)

| Hash | Message |
|------|---------|
| `928a336` | docs(incident): add laptop sleep resume VPN diagnostics |
| `adfc4ec` | docs(incident): record stable owner VPN soak after fresh import |
| `6b70dbd` | docs(incident): record owner VPN failure watch window |

### Dirty / untracked (not in audit scope)

- Modified: `.cursor/skills/bendervpn-journey-qa/SKILL.md` (do not commit)
- Untracked: screenshots, smoke scripts, `.playwright-*`, `data/`, ops smoke helpers

**Code on origin includes:** P1-CAB-001, P1-DEV-001, P1-REF-001 web referral (`62aea49`), Candidate D apply docs — all deployed per postdeploy records.

---

## 3. Current production state (documented)

| Surface | Status | Evidence |
|---------|--------|----------|
| VPN profile Candidate D | **Active** | INCIDENT-001: 7353 B, 6 VLESS, relay#1×3 + relay#2×3, DoH, selector parity OK |
| Happ UX | **One Auto host** — expected | INCIDENT-001/002; not a regression |
| P1-CAB-001 `billing_profile` | **Deployed** 2026-06-09 | [`POSTDEPLOY-2026-06-10-P1-CAB-001.md`](POSTDEPLOY-2026-06-10-P1-CAB-001.md) |
| P1-DEV-001 active config summary | **Deployed** 2026-06-09 | [`POSTDEPLOY-2026-06-10-P1-DEV-001.md`](POSTDEPLOY-2026-06-10-P1-DEV-001.md) |
| P1-REF-001 web `ref_code` | **Deployed** 2026-06-09 | [`POSTDEPLOY-2026-06-10-P1-REF-001.md`](POSTDEPLOY-2026-06-10-P1-REF-001.md) — web attribution PASS |
| TG bind web→Telegram | **FAIL** | [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) — zero `funnel_bot_start bind:*` |
| VPN owner stability | **Interim stable** (active use); **sleep/resume OPEN** | INCIDENT-002/003 |
| Server regression | **Not confirmed** | INCIDENT-001/002 probes green |
| CI / GitHub Actions | **None** | No `.github/workflows/` |
| Billing commercial audit | **Not done** | BILL-001 OPEN in master backlog |

---

## 4. Audit sources

| Source | Role |
|--------|------|
| [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) | Policy canon PT-01…PT-12 |
| [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) | ID catalog + open items |
| [`AUDIT-2026-06-10-CONSOLIDATED-RISK-MAP.md`](AUDIT-2026-06-10-CONSOLIDATED-RISK-MAP.md) | Risk register |
| [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md) | G0–G5 gates |
| [`INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md`](INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md) | INCIDENT-001 |
| [`INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md`](INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md) | INCIDENT-002 |
| [`INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md`](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md) | INCIDENT-003 |
| [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md) | Client matrix |
| [`AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md`](AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md) | S1–S8 flows |
| [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) | TG bind |
| [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md) | Device/billing UX |
| POSTDEPLOY P1-CAB / P1-DEV / P1-REF | Deploy truth |
| [`COMMERCIAL-BACKLOG.md`](COMMERCIAL-BACKLOG.md) | Ops/commerce baseline |
| [`RUNBOOK-INCIDENT.md`](RUNBOOK-INCIDENT.md) | Incident runbook |
| Code: `balance_billing.py`, `handlers.py`, `web_referral.py`, `portal_cabinet.py` | Static billing/referral/cabinet |
| `.cursor/rules/*`, `.cursor/skills/*` | Guardrails (not committed) |

---

## 5. Launch types defined (Step 2)

### A. Internal owner-only / friends-and-family

| Dimension | Rule |
|-----------|------|
| Audience | Owner + trusted contacts |
| Volume | &lt;20 active users |
| Clients | Happ primary; disclose desktop sleep risk |
| Support | Owner manual |
| Acceptable risks | TG bind unverified; no CI; soft policy enforcement |
| Hard blockers | None for trusted circle |
| Stop criteria | Payment loss; secrets leak; mass VPN down |

### B. Closed soft launch (manual support, low volume)

| Dimension | Rule |
|-----------|------|
| Audience | Invite/referral only; no paid ads |
| Volume | &lt;100 new users; monitor organic |
| Clients | **Happ mobile-first**; desktop with sleep caveat |
| Support | Manual; owner responds |
| Acceptable risks | No hard invite gate; legacy copy gaps; TG bind gap if email path disabled in messaging |
| Hard blockers | Active VPN mass failure; false referral bonus promises |
| Stop criteria | Support overload; &gt;2 unresolved payment disputes/week; VPN incident without runbook |

### C. Paid commercial pilot

| Dimension | Rule |
|-----------|------|
| Audience | Paying users after trial |
| Volume | Low hundreds |
| Clients | Happ only officially |
| Support | Documented revoke/replace; payment reconciliation |
| Acceptable risks | None for money flow — must be audited |
| Hard blockers | Unaudited billing; no payment failure runbook; no admin lookup |
| Stop criteria | Double charge; access not extended after payment; wallet drift |

### D. Open commercial launch / public traffic

| Dimension | Rule |
|-----------|------|
| Audience | Public marketing |
| Volume | Unbounded toward 10k/30k targets |
| Clients | Happ + documented fallback only |
| Support | Runbooks + alerting + on-call |
| Hard blockers | No CI/secret scan; no cap enforcement; desktop sleep unresolved; no VLESS functional monitor |
| Stop criteria | SLO breach; 30k cap exceeded without waitlist; legal/copy false promises |

### E. Referral-driven growth launch

| Dimension | Rule |
|-----------|------|
| Audience | Referral campaigns |
| Volume | Growth via `ref_` / `ref_code` |
| Requirement | End-to-end attribution + web→TG bind + honest copy (no bonus until implemented) |
| Hard blockers | TG bind FAIL; referral migration unproven; false “ref preserved on email→TG” without bind |
| Stop criteria | Attribution &lt;90% on sampled signups; referral disputes |

---

## 6. Gate matrix (Step 14)

| Gate | Area | Status | Evidence | Soft blocker? | Paid blocker? | Open blocker? | Required action | Owner decision |
|------|------|--------|----------|---------------|---------------|---------------|-----------------|----------------|
| **G1** | VPN stability / Happ / sleep-resume | **PARTIAL** | Candidate D active; INCIDENT-002 interim stable; INCIDENT-003 sleep/resume OPEN | Desktop sleep = **yes** for desktop promise | **Yes** if desktop sold | **Yes** | Owner run INCIDENT-003 diagnostics; extended mobile soak | Waive desktop support? |
| **G2** | Client app compatibility | **PARTIAL** | Happ/Hiddify/Streisand = Auto-equivalent; Karing/Clash/v2rayN stripped | Non-Happ clients | Non-Happ for paid | Non-Happ at scale | Happ primary; Hiddify diagnostic only; freeze Karing | Hiddify as official fallback? |
| **G3** | Telegram registration / 90d | **DONE** | Code + policy PT-01; trial provision path | No | No | No | Keep monitoring trial abuse | — |
| **G4** | Web/email fallback / TG bind | **BLOCKED** | Web 1d trial works; **TG bind FAIL** (`funnel_bot_start bind:*` = 0) | **Yes** if email growth pushed | **Yes** | **Yes** | Retest bind per TELEGRAM-BIND-FLOW §9; or disable email path in campaigns | Waive bind or fix first? |
| **G5** | Referral attribution | **PARTIAL** | Web `ref_code` deployed PASS; TG `ref_*` code exists; bind migration FAIL; ledger admin missing | Tracking-only OK | Bonus = no | Growth = yes | P1-ADM-002 ledger; fix bind | Referral campaigns allowed? |
| **G6** | Billing/payment money flow | **NOT_STARTED** | Core code exists (6.67₽/day, YooKassa webhook, autopay); **no commercial audit** | Low $ manual | **Yes** | **Yes** | BILL-001 full audit + wallet/expired smokes | Enable paid pilot when? |
| **G7** | Device/config lifecycle | **PARTIAL** | P1-DEV-001 read-only count/list deployed; **no revoke/replace/enforce** | Support manual OK | Weak | **Yes** | Admin revoke path; copy fix `device_rule` | Option A strict vs B multi-device |
| **G8** | Admin/support operations | **PARTIAL** | Admin flow test exists; **no user lookup by TG/email**; RUNBOOK-001 incomplete | Manual owner OK | **Yes** | **Yes** | P1-ADM-001 lookup; sleep/resume runbook | — |
| **G9** | Monitoring/alerting | **PARTIAL** | Read-only probes + `monitor.sh`; no automated profile alert; no VLESS functional probe; no billing job alert | Acceptable F&F | Partial | **Yes** | Profile integrity cron + alert channel | — |
| **G10** | Legal/copy/FAQ truth | **PARTIAL** | Policy v1 fresh; portal mostly aligned; **setup `device_rule` false promise**; FAQ stale | Minor | **Yes** (device/billing) | **Yes** | Copy sweep; FAQ sync | — |
| **G11** | Security/privacy/secret hygiene | **PARTIAL** | `.secrets/` gitignored; no CI gitleaks; diagnostics gitignored | Internal OK | **Yes** | **Yes** | P2-CI-001/002 | — |
| **G12** | Commercial policy enforcement | **NOT_STARTED** | Invite/30k/one-device = **copy only**; no hard gate | Pilot OK | Risk | **Yes** | DEC-IMPL-008/009 before scale | — |
| **G13** | Deploy/rollback readiness | **DONE** | Candidate D snapshot; APPLY rollback doc; AMS safe deploy runbook | No | No | Partial (no CI gate) | — | — |
| **G14** | Reporting/reconciliation | **NOT_STARTED** | No payment reconciliation view; referral export missing | No | **Yes** | **Yes** | Admin reporting surface | — |
| **G15** | Launch operations checklist | **PARTIAL** | RUNBOOK-INCIDENT exists; sleep/resume + payment runbooks missing | Partial | **Yes** | **Yes** | Commercial launch checklist (§12 below) | — |

### Gate status counts

| Status | Count |
|--------|-------|
| **DONE** | 2 (G3, G13) |
| **PARTIAL** | 9 (G1, G2, G5, G7, G8, G9, G10, G11, G15) |
| **BLOCKED** | 1 (G4) |
| **NOT_STARTED** | 3 (G6, G12, G14) |
| **NEEDS_OWNER_DECISION** | 5 (G1 desktop, G2 Hiddify, G4 bind waiver, G5 campaigns, G7 device policy) |

---

## 7. Done list (launch-relevant)

| Item | Status |
|------|--------|
| Candidate D VPN profile applied + verified | ✅ |
| Portal two-path journey (TG 90d + email 1d) | ✅ |
| P1-CAB-001 cabinet `billing_profile` | ✅ deployed |
| P1-DEV-001 active config count/list (read-only) | ✅ deployed |
| P1-REF-001 web email `ref_code` → `referred_by` | ✅ deployed |
| Product Policy v1 locked | ✅ |
| Happ primary client strategy documented | ✅ |
| Incident read-only probe suite | ✅ |
| INCIDENT-003 sleep/resume diagnostic protocol + script | ✅ |
| Rollback snapshot for Candidate D | ✅ |
| Basic incident runbook | ✅ |
| Unit tests for cabinet billing/config fields | ✅ `tests/test_portal_cabinet_billing.py` |
| Commerce go-live baseline (2026-05-16) | ✅ per COMMERCIAL-BACKLOG |

---

## 8. Open blockers (top 10 by severity)

| # | Severity | Blocker | Blocks |
|---|----------|---------|--------|
| 1 | **P0** | **Billing/payment commercial audit not done** (G6) | Paid pilot, open launch |
| 2 | **P0** | **TG bind FAIL** — web→TG migration unproven (G4) | Email fallback growth, referral migration |
| 3 | **P0** | **Desktop sleep/resume unresolved** (INCIDENT-003, G1) | Desktop commercial support |
| 4 | **P1** | **No admin user lookup / revoke-replace path** (G7, G8) | Commercial support at scale |
| 5 | **P1** | **No automated monitoring/alerting for profile integrity + billing** (G9) | Open launch |
| 6 | **P1** | **Copy false promises** — `device_rule` self-service new config (G10) | External traffic |
| 7 | **P1** | **No CI / secret scanning** (G11) | Multi-contributor / open launch |
| 8 | **P1** | **Policy enforcement gaps** — invite/30k/one-device copy-only (G12) | Public scale |
| 9 | **P2** | **VLESS functional probe gap** — TCP OK ≠ VLESS OK | Open launch confidence |
| 10 | **P2** | **Referral ledger / reconciliation missing** (G14) | Referral growth, paid disputes |

---

## 9. Soft-launch acceptable risks

- Soft invite-only positioning without hard gate (pilot policy)
- 30k cap as badge only without live counter
- One device = policy + support, not HWID enforcement
- Legacy/manual users with frozen balance display
- Happ shows one Auto host (not 6 nodes)
- Interim VPN stability on mobile after fresh import (INCIDENT-002)
- Manual owner support for device change
- Web referral tracking without bonus payout
- No public capacity API

**Not acceptable even for soft launch:**

- Promising referral bonus
- Sending non-Happ users as primary path
- Pushing email 1d path as substitute for 90d without TG bind fix
- Claiming desktop VPN stable without sleep/resume evidence
- Karing as recommended client

---

## 10. Paid / open-launch blockers (hard)

1. G6 billing audit with wallet/trial/expired/payment scenario matrix
2. G4 TG bind verified OR email fallback explicitly disabled in growth
3. G7 support/admin revoke or replace documented and operable
4. G9 profile integrity + payment callback + billing job monitors with alerts
5. G10 copy honesty sweep (device, billing, trial, referral)
6. G11 CI + secret scan minimum
7. G1 desktop sleep/resume resolved or desktop excluded from SLA
8. G14 payment reconciliation / admin reporting
9. G12 capacity dashboard before approaching 300 active configs
10. G2 non-Happ clients excluded from commercial promises

---

## 11. Audit gaps requiring proof

| Gap | Proof needed |
|-----|--------------|
| INCIDENT-003 sleep/resume | BEFORE/AFTER-BROKEN route/DNS snapshots; comparison VPN |
| TG bind | Successful bind with `funnel_bot_start bind:*` &gt; 0 + DB `telegram_id` set |
| Billing | Live smokes: trial→wallet, top-up, insufficient balance, duplicate callback |
| Wallet/expired UI | Mini App spot-check post P1-CAB/DEV |
| Wi‑Fi↔LTE switch | Owner mobile test log |
| VLESS after sleep | `report.zip` or client logs |
| Payment bind failures | AMS log grep + recovery path |
| Multi-key anomaly | Admin handling procedure tested |
| Referral web→TG | Bind success + `referrals` row migrated |

---

## 12. Commercial launch minimum checklist

### Before soft launch (B)

- [ ] Owner INCIDENT-003 sleep/resume test OR waive desktop in all copy
- [ ] Happ mobile soak 30–60 min + sleep test on ≥1 iOS/Android
- [ ] Support intake template: device, OS, Happ version, `/id`, screenshot
- [ ] Disable or caveat email 1d path in referral landing if TG bind still FAIL
- [ ] Confirm no referral bonus in any live copy
- [ ] Manual admin: how to find user, extend access, rotate key via panel

### Before paid pilot (C)

- [ ] All soft-launch items
- [ ] BILL-001 commercial billing audit document + scenario PASS log
- [ ] Wallet/expired/legacy smokes on AMS
- [ ] Payment success + failure runbook
- [ ] Duplicate callback/idempotency verified
- [ ] Admin lookup by Telegram ID (P1-ADM-001)
- [ ] Revoke/replace procedure for lost device

### Before open launch (D)

- [ ] All paid pilot items
- [ ] G9 monitoring + on-call alert path
- [ ] CI + gitleaks (G3)
- [ ] FAQ/ONBOARDING synced to policy v1
- [ ] Capacity internal dashboard (300-config trigger)
- [ ] VLESS functional probe feasibility decision
- [ ] Legal/privacy review (OD-09)
- [ ] Edge HA / sub-page health documented

### Before referral growth (E)

- [ ] TG bind PASS or growth limited to Telegram-only `ref_`
- [ ] Referral ledger admin view (P1-ADM-002)
- [ ] Attribution smoke ≥95% on sample
- [ ] No copy promising email-path referral preservation without bind

---

## 13. Area-by-area analysis

### A. VPN stability and client reliability

| Item | Status | Evidence | Blocker? | Action |
|------|--------|----------|----------|--------|
| Candidate D active | **PASS** | 7353 B, 6 proxy, DoH, parity | No | Continue profile probes |
| INCIDENT-001/002 | **Monitoring** — not closed | Interim stable after fresh import | No for mobile F&F | Extended soak |
| INCIDENT-003 sleep/resume | **OPEN** | Another VPN survives; Happ+BenderVPN fails | **Yes for desktop** | `diagnose_windows_vpn_resume.ps1` |
| Happ primary | **Yes** | Policy PT-05; client audit | No | Keep |
| Hiddify | **Diagnostic fallback** | Same Xray JSON as Happ | No if not promoted | Owner decision |
| Karing | **Frozen / unsupported** | LV-direct strip | Yes if recommended | Do not promote |
| VLESS functional probe | **Gap** | TCP probes only | Open launch | Evaluate feasibility |
| Profile integrity monitoring | **Manual scripts only** | `probe_subscription.py` etc. | Open launch | Cron + alert |

**Classifications:**

| Dimension | Readiness |
|-----------|-----------|
| Mobile (Happ) | **PARTIAL** — interim stable; soak incomplete |
| Desktop (Happ) | **BLOCKED** — sleep/resume |
| Sleep/resume | **BLOCKED** — INCIDENT-003 |
| Wi‑Fi/LTE switch | **UNCONFIRMED** |
| Client cache/import | **Risk** — fresh reimport helped INCIDENT-002 |
| Server rollback | **Ready** — snapshot exists |

### B. Client/app compatibility

| Platform | Happ | Hiddify | Streisand | Karing | Clash | v2rayN |
|----------|------|---------|-----------|--------|-------|--------|
| iOS | **Primary** | Diagnostic | Fallback | Unsupported | Unsupported | Unsupported |
| Android | **Primary** | Diagnostic | — | Unsupported | Unsupported | Unsupported |
| Windows | **Primary*** | Diagnostic | — | Unsupported | Unsupported | Caveat fallback |
| macOS | **Primary*** | Diagnostic | — | Unsupported | Unsupported | Unsupported |

\*Desktop qualified by INCIDENT-003 sleep/resume risk.

**Decisions:**

- **Official primary:** Happ
- **Official fallback:** None publicly; Hiddify/Streisand for power users who already have app
- **Unsupported:** Karing (as Auto), Clash family, v2rayN as Auto, sing-box plain link
- **Disclose:** One visible Auto host; desktop sleep issue until resolved

### C. Registration, trials, access flows

| Scenario | Policy | Deployed | Confirmed | Risk | Blocker |
|----------|--------|----------|-----------|------|---------|
| TG new user `/start` | 90d trial | Yes | **Yes** | Low | No |
| TG trial active | No balance debit | Yes | **Yes** | Low | No |
| Web/email 1d | Fallback only | Yes | **Yes** | Medium if sold as main | Soft |
| Web→TG bind | Merge accounts | Code deployed | **FAIL** | **High** | **G4** |
| Paid wallet user | 6.67₽/day | Code exists | **Unaudited** | **High** | G6 |
| Expired (no balance) | Access ends | Code exists | **Unaudited** | High | G6 |
| Legacy/manual | No drain | Yes | **Partial** — cabinet now shows legacy | Medium | No |
| «Получить доступ» existing user | Reuse same sub | Yes | **Yes** — UX confusing | Medium | Copy |
| «Получить доступ на сутки» | Web only 1d | Yes | **Yes** | Medium | TG bind |
| Referral attribution | TG + web | Web PASS | **Partial** | Medium | G5 |

**30k cap / invite-only:** Policy only — **not enforced** in backend (acceptable pilot; blocker for open launch).

### D. Referral and growth readiness

| Item | Status |
|------|--------|
| TG `ref_*` attribution | Code exists; not re-tested live post-P1-REF |
| Web `ref_code` | **Deployed PASS** |
| Web→TG referral migration | **BLOCKED** by bind FAIL |
| Referral ledger admin | **Missing** |
| Referral bonus promises | **Must not promise** — PT-07; check live copy |
| Commercial campaigns | **Unsafe for bonus**; **tracking-only** OK on TG path |

**Classification:** Safe for **tracking only** on Telegram; **unsafe for bonus**; **unsafe for email-heavy growth** until G4 fixed.

### E. Device/config lifecycle

| Item | Status |
|------|--------|
| `active_config_count` / `configurations[]` | **Deployed** P1-DEV-001 |
| User sees count/list | **Yes** in cabinet |
| Distinguish current config | **Yes** `is_primary` |
| Support revoke/replace | **Manual panel only** — no documented bot admin flow |
| One active config enforced | **No** — multiple `vpn_keys` possible |
| Multi-key anomaly flag | **Yes** `multiple_configs_anomaly` |
| Self-service new device | **Copy claims yes; backend no** |
| Delete/revoke self-service | **No** |
| 6.67 × N billing | **No** |

**Minimum commercial gap:** support must be able to revoke/replace; copy must not promise self-service.

### F. Billing, payments, commercial money flow

| Component | Documented | Audited | Tests |
|-----------|------------|---------|-------|
| `DAILY_RATE = 6.67` | Yes | Partial | Unit cabinet only |
| `charge_daily_balance_if_due` | Yes | No live smoke matrix | No |
| YooKassa webhook + idempotency | Code present | No | No |
| Autopay bind | `yookassa_autopay.py` | No | No |
| Low balance → expire | `sync_panel_from_balance` | No | No |
| Trial → wallet transition | Profile logic | No | No |
| Legacy bypass (≥2030) | Yes | Owner case documented | Partial |
| Reconciliation admin view | **No** | **No** | **No** |

**Money scenarios — all require BILL-001 audit before paid launch:**

| Scenario | Safe for manual pilot? |
|----------|------------------------|
| New paid user top-up | **Unconfirmed** |
| Trial converts to wallet | **Unconfirmed** |
| Insufficient balance | **Unconfirmed** |
| Payment success, access not extended | **Unconfirmed** — high risk |
| Duplicate callback | Code has idempotency — **needs smoke** |
| Refund/manual correction | **No documented path** |

**Verdict:** **Unsafe for open paid launch**; **not audited for paid pilot**.

### G. Admin/support operations

| Capability | Available | Notes |
|------------|-----------|-------|
| Find user by TG ID | **Partial** — DB/panel manual | No bot admin lookup |
| Find by email | **Manual** | |
| See trial/wallet/legacy | **Cabinet API yes** | |
| See balance / expiry | **Yes** | |
| See active configs | **Yes** post P1-DEV-001 | |
| See referral source | **DB manual** | No admin UI |
| Extend access manually | **Panel** | |
| Revoke/replace config | **Panel** — undocumented for support | |
| Correct balance | **DB/manual** | |
| VPN doesn't work | RUNBOOK-INCIDENT partial | |
| Sleep/resume broken | INCIDENT-003 protocol | **New** |
| Payment not applied | **Missing runbook** | |
| Referral not attributed | **Missing runbook** | |

### H. Monitoring, alerting, incident readiness

| Monitor | Exists | Alert | Required before |
|---------|--------|-------|-----------------|
| Profile 7353B / 6 proxy | Manual scripts | No | Open launch |
| Subscription endpoint | `monitor.sh` | TG alerts exist | Soft OK |
| Relay TCP | `relay_latency_probe.py` | Partial | Paid |
| VLESS functional | **No** | — | Open launch |
| Caddy 5xx sub-page | Partial | — | Open launch |
| Billing job | Scheduler exists | **No alert** | Paid |
| Payment callback | Logs only | **No** | Paid |
| CI/static checks | **No** | — | Open launch |
| Secret scanning | **No** | — | Open launch |

### I. Legal/copy/FAQ/onboarding truth

| Issue | Severity | When fix |
|-------|----------|----------|
| `setup.device_rule` — false self-service new device | **P1** | Before external traffic |
| `referral_preserve_note` — bind not verified | **P1** | Before referral/email growth |
| FAQ/ONBOARDING stale vs policy v1 | P2 | Before open launch |
| Ghost bot labels («Начать бесплатно») | P1 | Before soft launch |
| NL/LV in bot help | P1 | Before soft launch |
| Karing not in primary copy | OK | — |
| Trial 90d vs 1d | Mostly OK | Cabinet grace caveat |

### J. Security/privacy/access hygiene

| Item | Status |
|------|--------|
| `.secrets/` gitignored | OK |
| Diagnostics gitignored | OK (`ops/diagnose_windows_vpn_resume.ps1`) |
| No CI gitleaks | **Gap** — open launch blocker |
| Subscription URLs in docs | Redaction policy in incident docs |
| PII in smoke emails on prod | Low-impact test artifacts documented |
| Script safety registry | Missing (`ops/SCRIPT-SAFETY.md`) |

### K. Commercial product policy

| Policy | Stated | Enforced | Gap |
|--------|--------|----------|-----|
| Invite-only | Soft pilot | No hard gate | Phase 4 |
| 30k cap | Badge | No stop API | Phase 4 |
| 1 active config | PT-06 | No technical block | Support + copy |
| 6.67₽/day | PT-08 | Yes in code | Audit needed |
| TG 90d / email 1d | PT-01/02 | Yes | TG bind |
| No referral bonus | PT-07 | N/A | Copy check |
| Support via bot `/id` | PT-10 | Yes | Runbooks incomplete |

---

## 14. Recommended implementation order (Step 16)

### A. Launch blockers

| ID | Title | Why | Surfaces | Tests | Deploy? | Risk |
|----|-------|-----|----------|-------|---------|------|
| **LAUNCH-001** | Close or monitor G1 sleep/resume | Desktop blocker INCIDENT-003 | docs + owner diagnostics | Route/DNS snapshots | No | Low |
| **LAUNCH-002** | TG bind retest or waiver | G4 BLOCKED | bot bind flow | `smoke_p1_ref_tg_bind_ams.py` | Maybe | Med |
| **LAUNCH-003** | Billing/payment commercial audit | G6 NOT_STARTED | bot billing, webhook | Scenario matrix smokes | No | High if skipped |
| **LAUNCH-004** | Support admin revoke/replace runbook | G7/G8 | docs + admin | Manual panel test | No | Med |
| **LAUNCH-005** | Copy truth sweep (device, referral, bot labels) | G10 | `ru.json`, bot messages | forbidden-copy rg | Yes | Low |

### B. Soft-launch hardening

| ID | Title | Why | Surfaces | Tests | Deploy? |
|----|-------|-----|----------|-------|---------|
| **LAUNCH-006** | P1-ADM-001 admin user lookup | Support scale | `admin_handlers.py` | Admin smoke | Yes |
| **LAUNCH-007** | Wallet/expired/legacy Mini App spot-check | P1-CAB/DEV gaps | portal | Playwright/manual | No |
| **LAUNCH-008** | Sleep/resume support runbook | INCIDENT-003 | docs | — | No |
| **LAUNCH-009** | Wi‑Fi/LTE mobile soak log | G1 incomplete | owner | — | No |

### C. Paid launch blockers

| ID | Title | Why | Surfaces | Tests | Deploy? |
|----|-------|-----|----------|-------|---------|
| **LAUNCH-010** | Payment reconciliation admin view | G14 | bot admin | SQL smoke | Maybe |
| **LAUNCH-011** | Billing job + callback monitor alert | G9 | ops monitor | Alert test | Yes |
| **LAUNCH-012** | Duplicate payment / insufficient balance smokes | G6 | ops smoke scripts | AMS | No |
| **LAUNCH-013** | Enforce max 1 active config (policy) | G7 | DB + panel ops | integration | Yes |

### D. Open launch blockers

| ID | Title | Why | Surfaces | Tests | Deploy? |
|----|-------|-----|----------|-------|---------|
| **LAUNCH-014** | CI + gitleaks minimum | G11 | `.github/workflows` | CI green | No |
| **LAUNCH-015** | Profile integrity scheduled probe + alert | G9 | ops cron | probe exit 0 | Yes |
| **LAUNCH-016** | Capacity dashboard (300 trigger) | G12 | ops | snapshot | No |
| **LAUNCH-017** | FAQ/ONBOARDING policy sync | G10 | docs | review | No |
| **LAUNCH-018** | VLESS functional probe feasibility | G1/G9 | ops research | — | No |

### E. Later improvements

| ID | Title | Why |
|----|-------|-----|
| **LAUNCH-019** | P1-ADM-002 referral ledger | Growth analytics |
| **LAUNCH-020** | Hard invite gate post-300 | G12 enforcement |
| **LAUNCH-021** | Hiddify official fallback decision | G2 owner |
| **LAUNCH-022** | Karing generator parity | G5-G — deferred |
| **LAUNCH-023** | REG-001 phone/email collection | Phase 2 |

**Rule:** one surface per commit; no VPN template in product commits.

---

## 15. Owner decisions required

| # | Decision | Options |
|---|----------|---------|
| 1 | **Desktop commercial support** | Waive until INCIDENT-003 resolved / or exclude desktop from SLA |
| 2 | **TG bind** | Fix and retest / or disable email growth until fixed |
| 3 | **Email 1d fallback in campaigns** | Allow tracking-only / or pause until bind works |
| 4 | **Paid pilot start** | After BILL-001 audit / or manual invoices only |
| 5 | **Hiddify** | Diagnostic only / or official secondary |
| 6 | **Device policy** | Stay Option A (support replace) / or plan Option B multi-device |
| 7 | **Referral growth** | Telegram-only until bind PASS / or full web+TG |
| 8 | **Soft launch volume cap** | e.g. max 50 new users/month manual approval |
| 9 | **INCIDENT-003 profile canary** | Only with phrase `approve INCIDENT-003 desktop profile canary` |
| 10 | **Open launch timeline** | Blocked until G6+G9+G11 minimum |

---

## 16. Exact next prompts / surfaces

1. **Owner:** Run INCIDENT-003 sleep/resume diagnostics on laptop — *«Run ops/diagnose_windows_vpn_resume.ps1 Before/AfterBroken/AfterRecovery and share snapshots»*
2. **Agent:** `LAUNCH-003` BILL-001 billing commercial audit (read-only) — *«Audit billing/payment money flow for commercial launch»*
3. **Agent:** `LAUNCH-002` TG bind controlled retest — *«Retest P1-REF TG bind per TELEGRAM-BIND-FLOW §9 with owner in real Telegram app»*
4. **Agent:** `LAUNCH-005` copy truth sweep — *«Fix setup.device_rule and referral_preserve_note; remove ghost bot labels»*
5. **Agent:** `LAUNCH-006` P1-ADM-001 admin lookup — *«Add admin command: lookup user by Telegram ID»*
6. **Agent:** `LAUNCH-004` support runbook pack — *«Write runbooks: payment not applied, sleep/resume, new device»*
7. **Agent:** `LAUNCH-014` minimal CI — *«Add .github/workflows/ci.yml with py_compile and gitleaks»*
8. **Owner:** Mobile soak 48h log — *«Record disconnect_count after Candidate D on iOS+Android»*

---

## 17. Go / no-go recommendation

| Launch | Verdict | Rationale |
|--------|---------|-----------|
| Internal F&F | **GO** | Owner support; known limits acceptable |
| Closed soft launch | **SOFT-LAUNCH ONLY** | Happ mobile-first; manual support; no email growth push; copy caveats |
| Paid pilot | **NO-GO** | G6 unaudited; G7/G8 weak; payment runbooks missing |
| Open launch | **NO-GO** | G9/G11/G12/G1 desktop/G10 gaps |
| Referral growth | **NO-GO** | G4 bind blocked; G14 missing; migration unproven |

**Strict rules applied:**

- Money flow not audited → paid/open cannot be GO ✅
- Sleep/resume unresolved → desktop support cannot be GO ✅
- TG bind open → web/email referral growth cannot be GO ✅
- Support revoke/replace weak → commercial support risk marked ✅
- Monitoring missing → open launch cannot be GO ✅
- Copy promises unsupported features → external launch blocked ✅

---

## 18. References

- Development gates: [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md)
- Master backlog: [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md)
- Product quality: [`BENDERVPN-PRODUCT-QUALITY-PLAN.md`](BENDERVPN-PRODUCT-QUALITY-PLAN.md)
- Diagnostic script: [`ops/diagnose_windows_vpn_resume.ps1`](../ops/diagnose_windows_vpn_resume.ps1)

**Status:** audit complete · **no implementation** · **no deploy** · **no push**
