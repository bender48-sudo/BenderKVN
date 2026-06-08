# BenderVPN Audit Roadmap

**Status:** canonical · **Created:** 2026-06-09
**Purpose:** ordered read-only (first) audits — nothing implemented during audit unless explicitly approved.
**Backlog:** findings feed [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md)
**Policy:** audits must respect [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) and [`VPN-INCIDENT-LESSONS-2026-05-25.md`](VPN-INCIDENT-LESSONS-2026-05-25.md)

---

## Audit principles

1. **Read-only first** — classify scripts safe/unsafe before any prod touch.
2. **No routing PATCH during reliability audit** — diagnose → rank hypotheses → owner approves fix.
3. **No Semgrep** — use listed tools per audit; Semgrep excluded by project rule.
4. **No prod load tests** without owner approval (PERF audits).
5. **One audit report per ID** — markdown artifact in `docs/` or appended to master backlog.
6. **Verify gate after any VPN fix** — `probe_subscription.py`, `diagnose_happ_import.py`, `happ_geosite_guard.py`, manual Happ smoke.

---

## Recommended audit order

```
IMMEDIATE (parallel OK)
├── AUDIT-001  VPN reliability diagnostic     ← START HERE (user reconnect reports)
└── AUDIT-002  VPN architecture map         ← read-only, parallel

THEN (product track)
├── AUDIT-003  Product policy implementation gaps
├── AUDIT-008  Bot live flow
└── AUDIT-007  Billing/topup clarity

THEN (registration & growth)
├── AUDIT-004  REG-001 design
├── AUDIT-005  Referral + anti-fraud
└── AUDIT-006  Device/config sharing

THEN (hardening)
├── AUDIT-010  Security
├── AUDIT-012  Observability/monitoring
└── AUDIT-015  Release/deploy safety

BEFORE SCALE
├── AUDIT-009  Admin/reporting
├── AUDIT-011  Legal/privacy
├── AUDIT-013  Performance/load
└── AUDIT-014  Partner seller channel
```

---

## Audit catalog

### AUDIT-001 — VPN reliability diagnostic

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-001 |
| **Priority** | **P0/P1 — immediate** |
| **Maps to backlog** | VPN-REL-001 |
| **Purpose** | Find why VPN disconnects / reconnect loops for users |
| **Why it matters** | Core product failure; patching without diagnosis risks repeat of gen-13→20 incidents |
| **Scope** | Read-only classification of ops scripts; incident timeline; architecture sketch; hypothesis list; safe probes; log review; per-user/config check; root-cause ranking |
| **Out of scope** | Routing/template PATCH; mass sub refresh; panel edits; Caddy changes |
| **Tools** | `ops/probe_subscription.py`, `ops/diagnose_happ_import.py`, `ops/subscription_fetch.py`, `ops/transport_mux_audit.py`, `ops/drift-check.py`; user `report.zip` / Happ logs if provided; read `VPN-INCIDENT-LESSONS`, `VPN-DIAGNOSTIC-2026-05-25` |
| **Safety rules** | Classify every script safe/unsafe before run; no PATCH; one probe at a time; document gen/template version |
| **Inputs/docs** | `VPN-INCIDENT-LESSONS-2026-05-25.md`, `AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md`, `BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`, `VPN-ROUTING-GEO-GUARDRAILS.md`, skill `bendervpn-vpn-architecture-audit` |
| **Expected output** | `docs/AUDIT-YYYY-MM-DD-VPN-RELIABILITY.md` — timeline, hypotheses ranked (HIGH/MED/LOW), safe next steps, **no patch** section |
| **When to run** | **Now** — before any VPN fix prompt |
| **Unlocks** | Targeted VPN fix backlog items; informs AUDIT-002; prevents blind PATCH |

**Phases (within audit):**

1. Classify ops scripts → safe / unsafe / owner-only
2. Build incident timeline (user reports + known gen changes)
3. Architecture map (subscription → Happ → outbound path)
4. Hypothesis list (observatory, xhttp, relay, DNS, balancer, client, ISP)
5. Safe probes (probe_subscription, diagnose_happ_import, transport_mux_audit)
6. Log analysis (access_log, Happ error_log, bot monitor if relevant)
7. User/config-specific check (sample sub, batch_risk, NL presence)
8. Root-cause ranking + recommended fix **order** (not implementation)

---

### AUDIT-002 — VPN architecture audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-002 |
| **Priority** | **P1 — immediate read-only** |
| **Maps to backlog** | VPN-ARCH-001 |
| **Purpose** | End-to-end map: Happ profile, BenderVPN Auto, subscription generation, DNS, routing, failover, Remna, Caddy, nodes, relay/direct |
| **Why it matters** | Product promises Auto-only; ops reality includes NL/LV/relay/xhttp — map needed for reliable fixes |
| **Scope** | Read-only code + ops doc review; live probe samples; subscription structure; node policy; failover paths |
| **Out of scope** | Template PATCH; node provisioning; new transports |
| **Tools** | `probe_subscription.py`, `diagnose_happ_import.py`, `transport_mux_audit.py`, `verify_vpn_balancer_profile.py`, `happ_geosite_guard.py`, DeepWiki/Context7 for Happ/xray refs |
| **Safety rules** | Probes only; no deploy; no panel API writes |
| **Inputs/docs** | `PRODUCT-TIER-PROFILES.md`, `TRANSPORT-MUX-MATRIX.md`, `NODE-POLICY-LV-NL.md`, `HAPP-MATRIX.md`, `BACKLOG-VPN-FULL-AUDIT-2026-05-28.md` |
| **Expected output** | Architecture diagram (mermaid) + narrative doc; gap list vs product copy |
| **When to run** | Parallel with AUDIT-001 or immediately after |
| **Unlocks** | Informed VPN backlog prioritization; bot help copy accuracy |

---

### AUDIT-003 — Product policy implementation audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-003 |
| **Priority** | **P1 — after AUDIT-001/002 started** |
| **Maps to backlog** | PROD-001…007, DEC-IMPL-002…007, DEC-IMPL-013 |
| **Purpose** | Map Product Policy v1 (PT-01…12) to actual code/copy gaps |
| **Why it matters** | Unlocks Phase 1 implementation prompt with exact file-level gaps |
| **Scope** | `bot_src/` (read), `web/portal/` (read), `database.py` (read), admin surfaces; no writes |
| **Out of scope** | Implementation; schema migration; VPN routing |
| **Tools** | ripgrep, read-only code review, live portal curl, transcript of Full Product Audit |
| **Safety rules** | No file patches; document only |
| **Inputs/docs** | `BENDERVPN-PRODUCT-POLICY.md`, Full Product Audit findings, `BENDERVPN-PRODUCT-QUALITY-PLAN.md` |
| **Expected output** | Gap matrix: Policy section → code state → backlog ID → Phase 1 task list |
| **When to run** | After policy v1 committed; before Phase 1 code |
| **Unlocks** | Phase 1 implementation prompt (ref fix, labels, admin, cabinet API) |

---

### AUDIT-004 — Registration / REG-001 audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-004 |
| **Priority** | **P2 — before Phase 2** |
| **Maps to backlog** | REG-001, DEC-IMPL-011, 012, 016 |
| **Purpose** | Design phone/email collection, consent, storage, recovery, fraud controls |
| **Why it matters** | Owner locked soft collection rules; implementation needs exact field/schema/consent flow |
| **Scope** | Bot onboarding flow design; web path review; `DATA-MINIMIZATION-POLICY.md`; refusal → high-risk action rules |
| **Out of scope** | DB migration; SMS; mandatory block at trial start |
| **Tools** | Policy review, data inventory, bot flow diagram |
| **Safety rules** | Design doc only until owner approves OD-09 |
| **Inputs/docs** | Policy §4, `DATA-MINIMIZATION-POLICY.md`, `DATA-INVENTORY-INTERNAL.md` |
| **Expected output** | REG-001 design spec: fields, UX, storage, legal diff, rollout plan |
| **When to run** | After Phase 1; before any REG-001 code |
| **Unlocks** | Phase 2 REG-001 implementation |

---

### AUDIT-005 — Referral + anti-fraud audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-005 |
| **Priority** | **P2** |
| **Maps to backlog** | PROD-003, DEC-IMPL-006, AF-001, AF-002, DEC-IMPL-017 |
| **Purpose** | End-to-end referral attribution paths, abuse vectors, reward economics, partner separation |
| **Why it matters** | Web ref drop is known P0; scaling invites without fraud controls is dangerous |
| **Scope** | TG `ref_`, web `ref_code`, `link_referral`, localStorage, admin visibility; abuse paths (self-ref, IP, email) |
| **Out of scope** | Bonus implementation; partner payout automation |
| **Tools** | Code trace, test signups (safe users), SQL read-only queries |
| **Safety rules** | No prod data mutation; no bonus promises in test |
| **Inputs/docs** | Policy §5, Full Product Audit referral section |
| **Expected output** | Attribution flow diagram; abuse matrix; admin report requirements |
| **When to run** | After Phase 1 ref fix or in parallel with AUDIT-004 |
| **Unlocks** | Phase 3 referral/fraud features; OD-02 decision input |

---

### AUDIT-006 — Device / config sharing audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-006 |
| **Priority** | **P2** |
| **Maps to backlog** | PROD-004, DEC-IMPL-014, OD-03 |
| **Purpose** | One active config/account policy vs actual keys, subscription reuse, panel deviceLimit |
| **Why it matters** | Copy promises one device; backend may allow multiple keys — support and fairness risk |
| **Scope** | `vpn_keys` model, panel HWID/deviceLimit capabilities, subscription link reuse patterns |
| **Out of scope** | HWID enforcement implementation |
| **Tools** | DB read-only sample, panel API docs, Remna capabilities review |
| **Safety rules** | No key revocation tests on real users without approval |
| **Inputs/docs** | Policy §6, legal terms device clause |
| **Expected output** | Policy vs reality matrix; enforcement options ranked (support-only → deviceLimit → HWID) |
| **When to run** | Phase 2–3 boundary |
| **Unlocks** | DEC-IMPL-014 design; OD-03 second-device SKU input |

---

### AUDIT-007 — Billing / topup clarity audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-007 |
| **Priority** | **P1** |
| **Maps to backlog** | BILL-001, DEC-IMPL-013, OD-10 |
| **Purpose** | Trial vs wallet, daily rate, 200 ₽ ≈ 30 days, autopay, expiry, cabinet state accuracy |
| **Why it matters** | Users confuse trial with balance; cabinet API may not expose trial/wallet state |
| **Scope** | Read `config.py` DAILY_RATE, charge logic, bot cabinet messages, portal cabinet, terms; **no billing logic changes** |
| **Out of scope** | YooKassa; price changes; new payment methods |
| **Tools** | Code read, safe test user cabinet inspection, terms review |
| **Safety rules** | No real payments; no balance mutations |
| **Inputs/docs** | Policy §8, `bot_src/config.py`, `portal_cabinet.py`, `portal.js` |
| **Expected output** | User-facing billing model doc; copy gaps; cabinet API field spec |
| **When to run** | With AUDIT-003/008 in product track |
| **Unlocks** | DEC-IMPL-013; marketing copy alignment |

---

### AUDIT-008 — Bot live flow audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-008 |
| **Priority** | **P1** |
| **Maps to backlog** | BOT-001, PROD-005, DEC-IMPL-003–005 |
| **Purpose** | Real Telegram flow: `/start`, terms, trial, `/id`, menu, cabinet, support, invite, topup |
| **Why it matters** | Ghost labels and post-trial copy only visible in live bot |
| **Scope** | Safe test user journey; screenshot/log capture; Mini App cabinet |
| **Out of scope** | Billing mutations; mass notify; referral gate changes |
| **Tools** | Telegram test account, manual flow, optional Playwright for Mini App webview |
| **Safety rules** | Dedicated test user; no broadcast; no prod payment |
| **Inputs/docs** | Policy §3, §9; quality plan persona map |
| **Expected output** | Flow checklist with pass/fail per step; label mismatch list |
| **When to run** | After AUDIT-003; before Phase 1 bot copy deploy |
| **Unlocks** | DEC-IMPL-003–005 implementation list |

---

### AUDIT-009 — Admin / reporting audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-009 |
| **Priority** | **P1 before scale** |
| **Maps to backlog** | ADMIN-001, DEC-IMPL-006, 007 |
| **Purpose** | What admin can see/do today vs policy §10 requirements |
| **Why it matters** | Cannot scale invites or hit 300-config threshold without visibility |
| **Scope** | Existing admin commands, SQL queries, ops scripts, payment logs |
| **Out of scope** | Building admin UI (that's implementation) |
| **Tools** | Read-only admin access, code review |
| **Safety rules** | No user data export to insecure channels |
| **Inputs/docs** | Policy §10, master backlog §4.7 |
| **Expected output** | Must-have gap list; minimal admin MVP spec |
| **When to run** | Before broader invite rollout |
| **Unlocks** | DEC-IMPL-006, 007 implementation |

---

### AUDIT-010 — Security audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-010 |
| **Priority** | **P1** |
| **Maps to backlog** | SEC-001 |
| **Purpose** | Secrets, dependencies, API auth, web trial abuse, rate limits, tokens, admin access |
| **Why it matters** | Growing surface (portal, web trial, Mini App) since May 2025 audits |
| **Scope** | bot, portal, ops compose templates, webhook endpoints, env handling |
| **Out of scope** | Semgrep; invasive prod penetration without approval |
| **Tools** | Trivy, Gitleaks, Snyk, Bandit, pip-audit, detect-secrets, Grype/Syft, Checkov (Docker), ZAP baseline **when approved** |
| **Safety rules** | No credential commits; no prod brute force; ZAP only on approved target |
| **Inputs/docs** | `AUDIT-2026-05-SECURITY.md`, `AUDIT-2026-05-SECURITY-02.md`, `SECRETS.md` |
| **Expected output** | Findings by severity; remediation backlog IDs |
| **When to run** | Phase 2 hardening track |
| **Unlocks** | Security remediation items in master backlog |

---

### AUDIT-011 — Legal / privacy audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-011 |
| **Priority** | **P2 before scale** |
| **Maps to backlog** | LEGAL-001, DEC-IMPL-016, OD-09 |
| **Purpose** | Terms/privacy vs phone/email collection, notifications, retention, deletion, support visibility |
| **Why it matters** | REG-001 and support lookup expand PII handling |
| **Scope** | `legal/terms.html`, `legal/privacy.html`, bot consent, web signup, `DATA-MINIMIZATION-POLICY.md` |
| **Out of scope** | Legal advice; implementing new fields |
| **Tools** | Document diff, policy crosswalk |
| **Safety rules** | Flag conflicts; owner/legal review required |
| **Inputs/docs** | Policy §4, §9; OD-09 |
| **Expected output** | Redline recommendations; blocking issues before REG-001 |
| **When to run** | Before Phase 2 REG-001 code |
| **Unlocks** | DEC-IMPL-016; OD-09 resolution |

---

### AUDIT-012 — Observability / monitoring audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-012 |
| **Priority** | **P2 — before 10k** |
| **Maps to backlog** | OBS-001, OD-08, DEC-IMPL-009 |
| **Purpose** | Status page, health checks, active config counter, error logs, incident detection, user-impact detection |
| **Why it matters** | Emergency comms outside Telegram required before 10k (policy §9.4) |
| **Scope** | `public_status_page.py`, `MONITORING.md`, ops cron, capacity snapshot, bot monitor logs |
| **Out of scope** | New monitoring SaaS procurement |
| **Tools** | Read ops docs, status page review, log sampling |
| **Safety rules** | No alert storm tests on prod |
| **Inputs/docs** | `MONITORING.md`, `CAPACITY-AND-FAILOVER-ROADMAP.md`, policy §9.4 |
| **Expected output** | Observability gap map; emergency comms recommendation |
| **When to run** | Phase 4 prep |
| **Unlocks** | OD-08 decision; DEC-IMPL-009 dashboard design |

---

### AUDIT-013 — Performance / load audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-013 |
| **Priority** | **P3 — before scale** |
| **Maps to backlog** | PERF-001 |
| **Purpose** | Portal, API, bot, web-trial load characteristics |
| **Why it matters** | Invite scale increases portal and web-trial traffic |
| **Scope** | Portal static assets, setup API, bot webhook latency |
| **Out of scope** | Heavy prod load without approval; DDoS simulation |
| **Tools** | `oha`, `k6` — **approved target/profile only** |
| **Safety rules** | Staging or off-peak; rate-limited; owner approves profile |
| **Inputs/docs** | `RUNBOOK-P6-SUBSCRIPTION-EDGE` load probe history |
| **Expected output** | Baseline p95; bottleneck list; safe load limits |
| **When to run** | Before 10k marketing push |
| **Unlocks** | Infra scale decisions |

---

### AUDIT-014 — Partner seller channel audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-014 |
| **Priority** | **P3 — before partner scale** |
| **Maps to backlog** | PARTNER-001, DEC-IMPL-019, OD-01 |
| **Purpose** | CAC, payout trigger, fraud controls, partner ref codes, partner trial policy |
| **Why it matters** | Partner channel ≠ user referral; economics undefined |
| **Scope** | GTM wiki, ref code design, manual payout process, fraud |
| **Out of scope** | Payout automation implementation |
| **Tools** | Doc review, policy workshop output |
| **Safety rules** | No partner promises in product until approved |
| **Inputs/docs** | Policy §10.3, OD-01, commercial backlog |
| **Expected output** | Partner program spec or explicit NO-GO |
| **When to run** | Phase 5 prep |
| **Unlocks** | OD-01 resolution; DEC-IMPL-019 |

---

### AUDIT-015 — Release / deploy safety audit

| Field | Detail |
|-------|--------|
| **ID** | AUDIT-015 |
| **Priority** | **P2** |
| **Maps to backlog** | OPS-001 |
| **Purpose** | Staging, rollback, dirty tree handling, deploy script stale smokes, Caddy patch safety |
| **Why it matters** | Product track adds portal+bot deploys; incident lessons show deploy errors cause outages |
| **Scope** | `deploy-user-portal-lv.ps1`, `RUNBOOK-AMS-SAFE-DEPLOY.md`, smoke scripts, git hygiene |
| **Out of scope** | Running deploys; changing production |
| **Tools** | Script read, dry-run where safe, `drift-check.py` read |
| **Safety rules** | No prod deploy during audit |
| **Inputs/docs** | `bendervpn-release-guard` skill, `POLICY-REPO-WORKFLOW.md` |
| **Expected output** | Deploy checklist gaps; rollback verification steps |
| **When to run** | Before Phase 1 deploy batch |
| **Unlocks** | Safer commit/release discipline updates |

---

## Audit → implementation mapping

| Audit | Primary backlog unlock | Implementation phase |
|-------|------------------------|----------------------|
| AUDIT-001 | VPN-REL-001, VPN-INC-001 | VPN fix (owner-approved) |
| AUDIT-002 | VPN-ARCH-001, VPN-AUD+* | Infra backlog |
| AUDIT-003 | DEC-IMPL-002–007, 013 | Phase 1 |
| AUDIT-004 | REG-001, DEC-IMPL-011–012 | Phase 2 |
| AUDIT-005 | AF-001, AF-002, DEC-IMPL-017 | Phase 3 |
| AUDIT-006 | DEC-IMPL-014, OD-03 | Phase 3 |
| AUDIT-007 | BILL-001, DEC-IMPL-013 | Phase 1 |
| AUDIT-008 | BOT-001, DEC-IMPL-003–005 | Phase 1 |
| AUDIT-009 | DEC-IMPL-006, 007 | Phase 1 |
| AUDIT-010 | SEC-001 | Hardening |
| AUDIT-011 | LEGAL-001, DEC-IMPL-016 | Phase 2 |
| AUDIT-012 | OBS-001, OD-08, DEC-IMPL-009 | Phase 4 |
| AUDIT-013 | PERF-001 | Pre-scale |
| AUDIT-014 | PARTNER-001, OD-01 | Phase 5 |
| AUDIT-015 | OPS-001 | Ongoing |

---

## Next action

**Run AUDIT-001 (VPN reliability diagnostic)** — read-only, no routing PATCH.

Suggested prompt:

> Conduct **AUDIT-001 VPN reliability diagnostic** per `docs/BENDERVPN-AUDIT-ROADMAP.md`. Read-only only. Classify ops scripts safe/unsafe. Use probe_subscription, diagnose_happ_import, transport_mux_audit. Rank reconnect-loop hypotheses. Reference VPN-INCIDENT-LESSONS. Output `docs/AUDIT-YYYY-MM-DD-VPN-RELIABILITY.md`. Do not PATCH template, routing, Caddy, or deploy.

---

**Version:** 1.0 · **Maintained with:** `BENDERVPN-MASTER-BACKLOG.md`
