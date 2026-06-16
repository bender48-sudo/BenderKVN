# COMMERCIAL-READINESS-CLIENT-JOURNEY-CHECKPOINT-001

**Date:** 2026-06-15  
**Branch:** `product-referral-cabinet-ui-v1`  
**HEAD (committed):** `c03f638` — CodeRabbit launch triage
**Mode:** read-only audit · **no prod mutation** · **no deploy**  
**Parent audits:** [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) · [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) · [`CODERABBIT-AUDIT-TRIAGE-2026-06-14.md`](CODERABBIT-AUDIT-TRIAGE-2026-06-14.md)

**CodeRabbit triage (2026-06-15):** Accepted **P0** billing/terms blockers — **BILL-TERMS-GUARD-001**, **BILL-UT-001/002** — before **automated paid pilot**. Repeat relay2 active soak **PASS** (`4fdf06c` / report(8)); sleep/wake **OPEN**. Rabbit capacity/test overclaims **rejected** (see triage doc).

**Capacity architecture pack (2026-06-15):** [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) — relay2-only supports **owner/F&F workaround** only; **commercial / public / 300 active configs / 30k** remain **NO-GO** until **backend-controlled multi-node delivery** (`delivery_path_nodes ≥ 2`, node registry, cohort subscription strategy) is **implemented and proven** — not merely documented.

**Parallel owner work:** REPEAT-SOAK-001 **DONE** (report(8) PASS); sleep/wake track remains separate (CLIENT-SMOKE-001).

---

## 1. Executive verdict

| Question | Verdict |
|----------|---------|
| **Is the product commercially ready today?** | **NO** for paid/open/referral/public acquisition. **CONDITIONAL GO** for trusted internal/friends use with disclosed limits. |
| **What is safe now?** | **GO** — owner + trusted circle; Telegram 90d trial path; Happ mobile-first for F&F with manual support; read-only ops. |
| **What is conditional?** | **CONDITIONAL GO** — small paid beta **only** with owner manual reconciliation per user (≤10), no growth campaigns, v2rayN fallback documented for Windows support. |
| **What is blocked?** | **NO-GO** — invite-only commercial launch at scale, referral growth, public acquisition, **300 active configs/devices** target, **automated paid self-serve** until **BILL-TERMS-GUARD-001** + **BILL-UT-001/002** + **BILL-SMOKE-001..004** |

**Explicit statements (not “almost ready”):**

- **VPN profile integrity (Candidate D):** **PASS** for Happ-class emit — 6 relay outbounds, DoH, selector parity ([`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md)).
- **Happ DirectIp fix:** **Deployed** to prod `happRouting` (owner context); repo `0258d00`; owner retest `0635067`; prod smoke recorded `9f4f3b4`. **Do not rollback.**
- **Desktop Happ launch gate:** **OPEN** — relay2 active-session evidence **improved** (report(7) SOFT PASS + report(8) repeat **PASS**); **sleep/wake still OPEN**; normal Bender row soak pending.
- **Mobile Happ launch gate:** **OPEN** — smoke plan `b85df09`; summarizer `3c850e8`; **PASS not recorded**.
- **Delivery capacity for growth:** **NO-GO** — effective **one LV geography** behind relays; NL **not** normal Auto capacity ([`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) § capacity).
- **Referral/acquisition growth:** **NO-GO** until client stability, capacity ≥2 delivery paths, anti-abuse/admin, and payment gates close.

---

## 2. Launch mode matrix

| Mode | Verdict | Required gates | Current blockers | Owner decision needed |
|------|---------|----------------|------------------|---------------------|
| **Internal / owner testing** | **GO** | None for trusted operator | Sleep/wake on desktop; document limits | — |
| **Friends-only controlled beta** | **CONDITIONAL GO** | Manual support; disclose desktop sleep + Windows fallback; Happ mobile preferred | Desktop long-session OPEN; mobile smoke PENDING | Waive desktop gate for F&F? |
| **Small paid beta** | **CONDITIONAL GO** | Manual payment reconciliation; whitelist ≤10; BILL-FIX deployed | **LIVE-TERMS-UX-SMOKE owner taps OPEN**; **BILL-SMOKE not PASS**; G6 PARTIAL | Manual pilot only until owner live terms smoke + BILL-SMOKE |
| **Automated paid pilot** | **NO-GO** | BILL-TERMS-GUARD + BILL-UT + BILL-SMOKE | CodeRabbit CB-1..4 open | — |
| **Invite-only commercial launch** | **NO-GO** | G1 client stability; G6 billing proof; G8 support tooling; monitoring trustworthy | Desktop gate OPEN; mobile PENDING; bind FAIL (G4) | — |
| **Referral growth** | **NO-GO** | G4 bind; REF-ADMIN; anti-abuse; client stability; capacity ≥2 nodes | All open | Approve portal-first share before bind fixed? |
| **Public acquisition** | **NO-GO** | Above + capacity + CI/monitoring + copy honesty | Capacity 1 path; 30k cap not enforced | — |
| **300 active configs/devices** | **NO-GO** | Policy trigger ([`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) §1); ≥2 delivery-path nodes; monitoring clean | **delivery_path_nodes < 2**; growth architecture not implemented | Keep invite-only until 2 nodes? |

---

## 3. Client journey map

Legend: **DONE** = deployed + evidence · **PARTIAL** = works with gaps · **BLOCKED** = known fail · **PENDING** = owner test missing · **UNKNOWN** = needs verification

| Step | User sees | Status | Known risks | Evidence | Missing test | Copy/support gap |
|------|-----------|--------|-------------|----------|--------------|------------------|
| **Discovery / invitation** | Portal `/start/`, bot link, optional `?ref=` | **PARTIAL** | Referral bonus not implemented; invite gate copy-only | Portal live; P1-REF-001 web attr PASS | Live TG `ref_*` post-deploy | Do not promise bonus ([guardrails](.cursor/rules/bendervpn-guardrails.mdc)) |
| **Portal landing** | Value prop, TG vs email paths | **DONE** (repo) | COMMERCIAL-UX deploy pending for some fixes | Portal two-path journey | Playwright audit optional | Device rule copy improved in repo, deploy pending |
| **Telegram bot onboarding** | `/start`, trial, menu | **DONE** | — | AUDIT S1–S3; 90d trial PT-01 | Abuse monitoring | Ghost bot labels fixed in repo |
| **Email 1-day trial** | `/setup`, temp access | **DONE** | Fallback path only; bind broken | Web trial works | G4 bind retest | Do not sell as primary |
| **90-day Telegram trial** | Bot trial button | **DONE** | Trial abuse unmonitored at scale | Policy PT-01 | — | Clear vs email 1d |
| **Account / balance** | Cabinet `billing_profile` | **PARTIAL** | Wallet logic unaudited live | P1-CAB-001 deployed | BILL-SMOKE | 6.67 ₽/day messaging OK in policy |
| **Payment / top-up** | YooKassa presets | **PARTIAL** | Guards deployed AMS 2026-06-15; owner live terms taps pending | POSTDEPLOY-2026-06-15; offline UX smoke PASS | **LIVE-TERMS-UX-SMOKE-001** (owner), **BILL-SMOKE-001..004** | Automated pilot blocked until owner live smoke + BILL-SMOKE |
| **Subscription / config issuance** | Bot link, QR, Happ import | **DONE** | One config = one device (support manual) | Candidate D sub; Remna provision | DEVICE-ENFORCE not live | No multi-device promise |
| **App setup** | Portal setup + Happ routing import | **PARTIAL** | Users skip **BenderVPN RU** routing → wrong split | Setup docs; DirectIp guard | Journey QA scenarios 3,6 | Routing import must stay in setup |
| **First connection** | Happ TUN / mobile VPN | **PARTIAL** | Desktop long-session; mobile unproven | DirectIp fix; TUN fast | REPEAT-SOAK; MOBILE-SMOKE | Windows: disclose sleep risk |
| **Daily use** | Auto profile, no server pick | **PARTIAL** | Relay #1 bias report(6); resets under load | report(7)+(8) relay2 active evidences | Normal Bender soak; prod selector planning only with owner approval | No NL/LV/relay pick in copy |
| **Renewal / top-up** | Balance debit 6.67 ₽/day | **PARTIAL** | Sync fail → balance credited, VPN not extended | BILL-001 S10 | BILL-SMOKE-002/003 | Support runbook for sync fail |
| **Support** | TG support, `/id` | **PARTIAL** | No user lookup by TG/email; AI arch only | SUPPORT-AI-ARCH designed | Admin lookup P1-ADM-001 | Fallback scripts below §8 |
| **Fallback (Windows/Happ fail)** | v2rayN / relay2 lab | **PROTOCOL READY** | v2rayN = LV direct only; not Auto-equivalent | `9c3400e` desktop fallback doc | CLIENT-SMOKE-003 owner | Support path documented; not product default |

---

## 4. Client app readiness

| Client | Launch role | Status | Evidence | Blockers | Support action |
|--------|-------------|--------|----------|----------|----------------|
| **Happ desktop — normal Auto** | Primary product path | **PARTIAL** | Candidate D; DirectIp fixed; TUN ~1.2s | Long-session OPEN (report(6)); sleep/wake OPEN (report(7)); **desktop launch gate OPEN** | Stay on Happ + **BenderVPN RU** routing; export report.zip before switching VPN |
| **Happ relay2 lab** | Owner/support isolation | **PASS** (repeat active) + **SOFT PASS** (report(7)) | report(7)+(8); 0 dial/open storm; repeat ~59 min post-wake | Sleep/wake **OPEN**; not prod default; **eligible** for controlled selector design | Import local lab JSON; **no refresh** on lab row |
| **v2rayN fallback** | Windows support alternate | **PROTOCOL READY** | `9c3400e`; `probe_fallback_client_sub.py` | Not Auto-equivalent; no stealth split; **owner smoke PENDING** (CLIENT-SMOKE-003) | Give existing sub URL; warn RU sites may proxy |
| **Karing exploratory** | Second alternate | **EXPLORATORY** | Client audit | LV-direct sing-box; not launch default | Only if v2rayN insufficient |
| **Happ mobile** | **Launch primary mobile** | **PENDING** | [FULLDAY deep-dive](CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md): evening traffic OK; sub import noise all day | **Access log 21 min only**; PASS not recorded | **CLIENT-MOBILE-OBSERVABILITY-001** |
| **Karing mobile exploratory** | Diagnostic only | **NOT LAUNCH** | Stripped emit | No Auto parity | Do not recommend publicly |

---

## 5. Infrastructure / capacity readiness

| Item | Status | Evidence |
|------|--------|----------|
| **Live Auto profile** | Candidate **D** relay-only×6 | relay #1×3 + relay #2×3; NL=0, LV direct=0 in injectHosts |
| **Effective delivery geography** | **~1** (LV behind relays) | PROOF-001 + QUALITY-PROOF-001; not relay diversity alone |
| **NL / Amsterdam normal capacity** | **NO** — failover/pre-qualified only | RU→NL TCP PASS; not in live injectHosts; A2/A4 gated |
| **Growth / 300 configs gate** | **BLOCKED** | Requires **≥2 production-capable delivery-path nodes** + controlled smokes |
| **Node bring-up** | **DOCS READY** | [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) + checklist; automation **OPEN** |
| **30k / multi-node architecture** | **DOCS READY / IMPL NO-GO** | [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md); registry + cohort engine **not built** |
| **NL A2/A4 controlled smoke** | **NOT STARTED** | Blocked: owner approval + monitoring closeout + client gates |
| **MONITOR-FLAP-001** | **SOAK PARTIAL** | Deployed LV `50a6ac4`; closeout `7e1d2d4` |
| **MONITOR-FLAP-TUNE-001** | **DEPLOYED LV; SOAK OPEN** | `21f5a97`, deploy doc `2e95cec` — verify 6h review before claiming PASS |
| **OPS-ALERT-HYGIENE-001** | **SOAK PASS** | Cert digest batched |

**Rule:** Paid/connected NL ≠ active customer capacity. Do not count NL toward growth until post-inclusion audit shows ACTIVE users on NL path.

---

## 6. Payments / billing readiness

Source: [`AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md`](AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md) · POSTDEPLOY BILL-FIX-001

| Area | Status | Notes |
|------|--------|-------|
| **YooKassa integration** | **Implemented** | Create + webhook queue |
| **Webhook idempotency** | **Improved** | `yk:{payment_id}` via `payment_idempotency.py`; BILL-FIX-001 deployed AMS |
| **Live top-up smoke** | **PENDING** | BILL-SMOKE-001 not PASS |
| **Daily debit 6.67 ₽/day** | **Code exists** | BILL-SMOKE-002 not PASS |
| **Expired → top-up recovery** | **Code exists** | BILL-SMOKE-003 not PASS |
| **Duplicate webhook** | **Designed** | BILL-SMOKE-004 not PASS |
| **Reconcile `--apply`** | **NOT RUN** | Dry-run only; explicit approval required |
| **Refunds** | **GAP** | Auto-renew stale recovery only; no YooKassa refund flow |
| **Admin reconciliation** | **MISSING** | Manual DB/panel — high risk at scale |
| **G6 gate** | **PARTIAL** | Automated paid pilot **NO-GO**; manual pilot **CONDITIONAL** |

---

## 7. Referral / acquisition readiness

| Item | Status |
|------|--------|
| **Target model (+1 month to referrer after paid conversion)** | **Designed** — not live |
| **Hidden invitee +3d** | **Gated OFF** (P1-REF-002) |
| **Web `ref_code` attribution** | **Deployed PASS** (P1-REF-001) |
| **TG `ref_*` attribution** | Code exists — **live retest UNKNOWN** |
| **Web→TG bind (G4)** | **BLOCKED** — zero `funnel_bot_start bind:*` |
| **REF-ADMIN / ledger / anti-abuse / hold window** | **NOT READY** |
| **Portal-first acquisition (ACQUISITION-JOURNEY-001)** | **Docs only** — not implemented |
| **Referral growth** | **NO-GO** |
| **Acquisition campaigns** | **NO-GO** — blocked by capacity + client stability + G4 |

---

## 8. Support readiness

### Known failure modes

| Mode | Status | User-facing guidance |
|------|--------|----------------------|
| Happ desktop long session (Cursor/Docs) | **OPEN** | Suspect relay path; relay2 lab for owner; v2rayN if unusable |
| Sleep / wake (Windows) | **OPEN** | INCIDENT-003 Track A; do not promise laptop sleep reliability |
| Happ Proxy (Bender) | **NOT RECOMMENDED** | Owner reports fail; SafeVPN Proxy was control only |
| Mobile lock / LTE handoff | **PENDING** | MOBILE-SMOKE-001 |
| DirectIp mis-routing | **FIXED** | Ensure **BenderVPN RU** routing imported |
| Fallback v2rayN | **Support path** | [`CLIENT-STABILITY-DESKTOP-FALLBACK.md`](CLIENT-STABILITY-DESKTOP-FAILBACK.md) |

### Support scripts (what to ask / not ask)

**Ask:**

1. Client app + OS version (Happ iOS/Android/Windows).
2. TUN vs system proxy; routing profile name (**BenderVPN RU** expected).
3. Symptom window: connect time, sites affected, sleep involved?
4. For Happ issues: **`report.zip` from Happ before switching VPN** ([recovery capture](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md)).
5. For mobile: Wi‑Fi vs LTE; lock test; filled `.local/mobile_smoke_results.md`.

**Do not ask normal users:**

- Manual server / relay / NL / LV selection.
- Refresh lab profile or prod template changes.
- SafeVPN comparison unless internal debug.
- Subscription URL in public channels — use `/id` + support DM.

**When to offer v2rayN:** Windows desktop unusable on Happ after routing confirmed; work urgency; document LV-direct limitations.

---

## 9. Data / metrics readiness

| Metric | Must measure | Current state |
|--------|--------------|---------------|
| Activation (trial → first connect) | Yes | **MISSING** — no funnel dashboard |
| Trial start (TG vs email) | Yes | Bot logs partial; no unified view |
| First connect success | Yes | **MISSING** — no client telemetry |
| Payment conversion | Yes | `user_actions` exists; no reconciliation UI |
| Churn / expiry | Yes | Scheduler logs; no product dashboard |
| Support incidents by class | Yes | **MANUAL** — tag sleep/TUN/mobile/billing |
| Client app type | Yes | **MISSING** — infer from support only |
| Server capacity / active configs | Yes | Panel + policy ~300 trigger; **no public counter** |
| Referral attribution | Yes | Web PASS; TG/bind partial; **no admin ledger** |

**Missing:** REF-ADMIN export, billing reconciliation view, G9 automated profile alert, CI secret scan (P2-CI-001).

---

## 10. Top blockers (ranked)

| Rank | Sev | Blocker | Evidence |
|------|-----|---------|----------|
| 1 | **P0** | **BILL-TERMS-GUARD-001** — callback terms bypass | CodeRabbit triage CB-1; `handlers.py` |
| 2 | **P0** | **BILL-UT-001/002** + **BILL-SMOKE** not PASS | G6 PARTIAL; automated paid **NO-GO** |
| 3 | **P0** | Desktop Happ launch gate OPEN | sleep/wake OPEN; relay2 active PASS (report(8)); normal Bender soak pending |
| 4 | **P0** | Mobile smoke PASS not recorded | `b85df09` plan only |
| 5 | **P0** | Capacity: **<2 delivery-path nodes** | Master backlog § capacity |
| 6 | **P0** | G4 TG bind FAIL (live) | G4 audit; **G4-TG-BIND-RETEST-001** |
| 7 | **P1** | TRIAL-GRANT / BALANCE-KOPEKS / WEBHOOK-TOCTOU | CodeRabbit CB-2, CB-4, triage §4 |
| 8 | **P1** | Referral admin / anti-abuse missing | REF-ADMIN not ready |
| 9 | **P1** | MONITOR-FLAP-TUNE soak OPEN | `21f5a97` deployed |
| 10 | **P2** | CI / gitleaks | P2-CI-001 NOT_STARTED |

---

## 11. Next implementation tasks (canonical order)

Synced from [`CODERABBIT-AUDIT-TRIAGE-2026-06-14.md`](CODERABBIT-AUDIT-TRIAGE-2026-06-14.md) + master backlog (`c03f638`). **Before automated paid pilot:** items **1–5**.

| # | Task ID | Action | Gate |
|---|---------|--------|------|
| **1** | **BILL-TERMS-GUARD-001** | Enforce terms on all trial/pay/wizard callbacks + tests | Automated paid pilot |
| **2** | **TRIAL-GRANT-ATOMIC-001** | Atomic/idempotent trial grant | Paid beta scale |
| **3** | **BILL-AUTOPAY-LIVE-GUARD-001** | Internal `BOT_PAYMENTS_LIVE` guard in autopay batch | PAY-AUTO-001 |
| **4** | **BILL-BALANCE-KOPEKS-001** | Kopeks/Decimal day-rate + preset labels | Copy truth |
| **5** | **BILL-UT-001** / **BILL-UT-002** | Offline billing + webhook/idempotency tests | G6 / automated paid |
| **6** | **G4-TG-BIND-RETEST-001** | Owner live bind after handoff deploy | Referral growth |
| **7** | **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** | Owner approval only — snapshot, dry-run, rollback | Not auto from soak PASS |
| **8** | **CLIENT-STABILITY-MOBILE-SMOKE-001** | Owner phone smoke; record PASS/SOFT/FAIL | Mobile acquisition |
| **9** | **MONITOR-FLAP-TUNE-001 closeout** | LV log review; SOAK PASS or accept PARTIAL | Before NL A2/A4 |
| **10** | **VPN-ARCH-001** | NL A2/A4 controlled smoke after gates | ≥2 delivery paths |

**Also tracked (P1/P2, not in top-10 sequence):** **BILL-WEBHOOK-CLAIM-TOCTOU-001**, **BOT-QR-MISSING-KEY-UX-001**, **BILL-LEGACY-PAYMENT-FLOW-GATE-001**, **SUBSCRIPTION-RESOLVE-TZ-001**, **BILL-SMOKE-001..004** (live AMS), **CLIENT-SMOKE-001** (sleep/wake).

---

## 12. Owner decision list

| # | Decision | Default if no answer |
|---|----------|----------------------|
| 1 | Allow controlled prod selector change (reduce relay #1)? | **Planning eligible only** — repeat relay2 active soak **PASS**; requires explicit owner approval + snapshot/dry-run/rollback before any prod change |
| 2 | Allow NL A2/A4 controlled smoke after MONITOR-FLAP-TUNE closeout? | **No** — until soak reviewed |
| 3 | Allow small paid beta before desktop fully fixed if v2rayN fallback documented? | **Conditional** — manual reconciliation only, ≤10 users |
| 4 | Launch messaging: Happ mobile primary + desktop fallback disclosed? | **Recommended** for any paid users |
| 5 | Keep invite-only / no public growth until **2 delivery nodes**? | **Yes** — per policy + backlog |

---

## 13. Final go/no-go summary

| Area | Status | Evidence | Blocker | Next action |
|------|--------|----------|---------|-------------|
| VPN profile (Candidate D) | **PASS** | APPLY Candidate D; probes | — | Continue probe cadence |
| Happ DirectIp / routing | **PASS** (prod) | `0258d00`, `0635067`, owner context | Do not rollback | Guard on change |
| Desktop Happ commercial | **OPEN** | report(7)+(8) relay2 active; gate OPEN | Sleep/wake; normal Bender soak | PROD-SELECTOR-CONTROLLED-001 (owner approval) |
| Mobile Happ commercial | **PENDING** | FULLDAY-DEEPDIVE-2026-06-16 — 766 flows 19:19–19:40; sub full-day; **access 1.4% coverage** | No PASS; observability gap | **CLIENT-MOBILE-OBSERVABILITY-001** |
| Windows fallback | **PROTOCOL READY** | `9c3400e` | Owner smoke pending | CLIENT-SMOKE-003 |
| Capacity / growth | **NO-GO** | 1 LV exit; NL not Auto | <2 delivery nodes | NL A2/A4 after gates |
| Billing automated paid | **NO-GO** | BILL-001; CodeRabbit triage | **BILL-TERMS-GUARD-001**, BILL-UT, BILL-SMOKE | Items 1–5 in §11 |
| Billing manual pilot | **CONDITIONAL** | BILL-FIX deployed | Owner reconciliation | Whitelist ≤10 |
| TG bind / email path | **BLOCKED** | G4 audit FAIL | bind:* = 0 live | **G4-TG-BIND-RETEST-001** |
| Referral growth | **NO-GO** | REF arch | Admin/anti-abuse | REF-ADMIN after bind |
| Monitoring | **PARTIAL** | FLAP PARTIAL; TUNE soak OPEN | Residual CDN quorum | TUNE closeout |
| F&F / internal use | **GO** | Launch audit §5A | Disclose limits | Manual support |

---

## References (commits)

| Hash | Topic |
|------|-------|
| `c03f638` | CodeRabbit launch triage |
| `4fdf06c` | Repeat relay2 soak PASS (report(8)) |
| `ed8b563` | G4 bind handoff UX (repo) |
| `2e2bca9` | report(7) relay2 lab evidence |
| `3c850e8` | mobile smoke log summarizer |
| `b85df09` | mobile stability smoke plan |
| `9c3400e` | Windows desktop fallback path |
| `d2bf8da` | relay2 lab profile generator |
| `0258d00` | DirectIp routing fix (repo) |
| `0635067` | DirectIp owner retest PASS |
| `7e1d2d4` | MONITOR-FLAP soak closeout (PARTIAL) |
| `21f5a97` / `2e95cec` | MONITOR-FLAP tune + LV deploy |
| `8b9923e` | BILL-FIX idempotency (see POSTDEPLOY) |
