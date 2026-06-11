# BenderVPN Growth, Positioning & Capacity Strategy

**ID:** STRATEGY-GROWTH-001
**Date:** 2026-06-10
**Status:** strategic direction · documentation only — no implementation in this doc
**Branch:** `product-referral-cabinet-ui-v1`
**Purpose:** capture commercial positioning, copywriting standards, growth volume logic, and server capacity planning **before** UI/copy/backend implementation resumes.

**Related (canonical, do not duplicate here):**

| Document | Role |
|----------|------|
| [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) | Locked product truths (PT-01–PT-12) |
| [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) | MODEL A, DEVICE-ENFORCE-001 |
| [`ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md`](ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md) | Portal-first referral (OPTION 3) |
| [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md) | Full acquisition journey: slots, trial cap, temp/paid conversion |
| [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) | Launch gates (F&F / soft / paid / referral) |
| [`AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md`](AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md) | Frozen backlog tracks |
| [`ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md`](ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md) | Support scale (internal copilot, not F&F blocker) |

---

## 1. Purpose

This document exists so product, copy, and engineering share one **strategic frame** before tomorrow’s implementation work:

- **What BenderVPN is** (closed digital membership, not commodity VPN).
- **How we speak** (honest, calm, human — not hype).
- **How we grow** (CAC, LTV, churn, referral K-factor — not “how many posts to buy”).
- **What infra must scale with growth** (active **devices**, not only paying accounts).
- **What is live today vs gated** (no false promises in UI).

**This doc is not final production copy.** Rough theses and examples below are **positioning anchors**. All user-facing text for portal, cabinet, setup, onboarding, and bot must be produced through the project copywriting workflow (§4.3) and reviewed against BenderVPN tone-of-voice before merge.

---

## 2. Product positioning

### 2.1 What BenderVPN is

BenderVPN is **not** a commodity “VPN for 200 ₽/month” competing on price and superlatives.

It is a **closed digital-membership / invite-only VPN platform**:

- VPN is the **entry product** and daily utility.
- Retention is driven by **trust**, **honest communication**, **fast human support**, **invite-only mechanics**, the feeling of **«для своих»**, **co-building the product with users**, and **simple stable utility**.
- Future **membership hooks** (partner offers, recommendations, community) extend the platform — not MVP blockers.

### 2.2 What we are not selling

| Avoid framing | Prefer framing |
|---------------|----------------|
| Cheapest VPN on the market | Closed access with human support |
| Unlimited everything, always works | Stable utility; we respond when something breaks |
| Mass-market VPN ad | Invite-only system with clear rules |
| Crypto/scammy urgency | Calm, transparent membership |

### 2.3 Positioning theses (tone anchors — not final UI strings)

These phrases guide **direction and tone**. They must be **rewritten** per surface via the copywriting skill (§4.3):

| Anchor | Role |
|--------|------|
| «закрытый VPN по приглашению» | Acquisition — explains access model |
| «для своих» | Membership feeling — subtle in cabinet, stronger on portal |
| «живая быстрая поддержка» | Trust — factual, not “24/7 guaranteed” |
| «без золотых обещаний» | Honesty — pairs with PT-12 |
| «мы не обещаем идеал, но быстро реагируем и улучшаем продукт вместе с вами» | Retention narrative |
| «стабильный VPN без лишнего шума» | Utility (refined from “без цирка”) |
| «интернет, который не отвлекает на поломки» | Calm utility (refined from “без нервов”) |
| «не массовый VPN, а закрытая система с человеческой поддержкой» | Differentiation |

**Polished direction examples (still not mandatory UI text):**

- Portal acquisition: *«Закрытый VPN по приглашению. Стабильный доступ и поддержка от тех, кто сервис собирает.»*
- Retention: *«Если что-то ломается — напишите. Мы смотрим и правим, без обещаний, что всё всегда идеально.»*
- Utility: *«Один профиль в Happ, сервер подбирается автоматически. Подключили — и работаете.»*

---

## 3. Messaging pillars

| Pillar | Acquisition | Retention |
|--------|-------------|-----------|
| **Closed access** | Invite-only, limited capacity, referral as entry | “You’re inside” — subtle in ЛК |
| **Honest VPN** | No superlatives; clear limits | Reliability narrative + incident honesty |
| **Live support** | “Real people who built this” | Fast Telegram support, `/id`, errors page |
| **Calm internet** | Simple outcome: access works | Stable utility, minimal friction |
| **Community / membership** | FOMO, early access, partners (future) | Partner deals, recommendations, voting (roadmap) |

**Working hypothesis (to validate with data):**

| Offer angle | Hypothesis | Best for |
|-------------|------------|----------|
| **A — Honest VPN** | «Закрытый VPN без обещаний “всегда идеально”. Работает — пользуетесь. Сломалось — чиним.» | **Retention** after onboarding |
| **B — Closed club** | «VPN по приглашению. Для своих. Живая поддержка.» | **Acquisition** / FOMO |
| **C — Calm utility** | «Стабильный доступ к привычному интернету.» | Broad audience, simple value |
| **D — Digital community** | «Закрытое digital-комьюнити: VPN, поддержка, рекомендации, партнёрские предложения.» | Partner / Gorbushka-style acquisition |

**Rule:** B/D may convert better at top of funnel; A/C may retain better post-activation. Test per channel; do not mix hype acquisition with dishonest retention promises.

---

## 4. Copywriting rules

### 4.1 Tone of voice — do / do not

**Do not:**

- «самый быстрый VPN», «лучший VPN 2026», «работает всегда»
- Overpromising, scammy/crypto-style hype, generic commodity VPN copy
- Claim enforcement, per-device billing, or self-service add-device **before backend exists** (PT-12)
- Copy prompt anchors verbatim into UI without editing

**Do:**

- Honest, calm, human, confident but not loud
- Membership-like where appropriate (portal > cabinet)
- Practical, transparent about limitations
- Short sentences; one main idea per block
- Answer: what this is · why it matters · what to do next · what is available vs gated

### 4.2 Acquisition vs retention copy

| Phase | Emphasis |
|-------|----------|
| **Acquisition** | Closed club / invite-only / trust / support — stronger allowed on portal |
| **Retention** | Honest VPN / human support / stable utility — primary after onboarding |

### 4.3 Copywriting operating standard (mandatory before implementation)

**Dedicated skills found in repo — use as primary standard:**

| Skill | Path | Use for |
|-------|------|---------|
| **Copywriting** | [`.cursor/skills/copywriting/SKILL.md`](../.cursor/skills/copywriting/SKILL.md) | Headlines, landing, CTAs, value props — clarity over cleverness |
| **Copy-editing** | [`.cursor/skills/copy-editing/SKILL.md`](../.cursor/skills/copy-editing/SKILL.md) | Polish existing Russian copy |
| **BenderVPN Product UI** | [`.cursor/skills/bendervpn-product-ui/SKILL.md`](../.cursor/skills/bendervpn-product-ui/SKILL.md) | Surface-specific truths (90d TG, 1d email, Auto, forbidden terms) |
| **VPN UI/UX rules** | [`.cursor/rules/vpn-ui-ux.mdc`](../.cursor/rules/vpn-ui-ux.mdc) | Mobile-first, one main action, human errors |

**Workflow for any user-facing copy change:**

1. Read `BENDERVPN-PRODUCT-POLICY.md` PT-* truths and this strategy §4–5.
2. Draft with **copywriting** skill; tighten with **copy-editing** skill.
3. Validate against **bendervpn-product-ui** skill (no NL/LV, no ghost labels, no false enforcement).
4. Per surface: portal (acquisition OK) · onboarding (clarity first) · cabinet (functional) · setup (utility) · bot (short, conversational).
5. Grep forbidden patterns before commit (see COMMERCIAL-UX / COPY-TRUTH checklists).

**Acceptance:** Documentation or UI changes that paste rough slogans from this doc **without** the copywriting workflow are **not accepted**.

### 4.4 Surface-specific expectations

| Surface | Copy priority |
|---------|---------------|
| **Portal** | Invite-only + trust + support; referral path visible; avoid “200 ₽ VPN” as sole value prop |
| **Onboarding** | Step-by-step; why invite-only; what user gets; one setting = one device; support exists; improving with feedback |
| **Cabinet / ЛК** | Functional first; subtle membership tone; device model precise (§5.3) |
| **Setup** | Utility-first; link-first; one setting = one device; no marketing clutter |
| **Bot** | Short, support-friendly; real button labels; no geography/server pick copy |

---

## 5. Product surfaces affected

### 5.1 Portal (public)

**Strategic direction:**

- Explain **invite-only closed VPN / membership**, not only daily price.
- Carry trust, support, honest positioning.
- Show referral/invite logic (portal-first share URL — target architecture).
- Route: Telegram (90d) · email fallback (1d) · setup · cabinet per current architecture.

**Implemented now (repo, deploy pending):** MODEL A device copy in cabinet/setup; two-path landing. See COMMERCIAL-UX-DEVICE-MVP-001.

**Gated:** Public capacity counter; hard invite gate; portal-generated share URL (REF-PORTAL-001).

### 5.2 Onboarding

Must explain without false promises:

- Why invite-only / камерный rollout.
- What the user gets (trial length by channel — PT-01/PT-02).
- How to get a setting (bot / setup page).
- **One setting = one device** (MODEL A direction).
- Live support path (bot, `/id`, errors page).
- Product improves with user feedback — no guarantee of perfection.

### 5.3 Cabinet / ЛК

**Membership feeling:** subtle (status, invite, support) — balance and configs remain primary.

**Device model (MODEL A UX — implemented in repo, backend gated):**

| Element | Today | Target |
|---------|-------|--------|
| Title | «Мои устройства / настройки» | Same |
| Active configs | Show `configurations[]` / count | Multi-card |
| Add device | Visible; **support-routed** or «скоро» | Self-service when backend ready |
| Replace device | Visible; **support-routed** | Tracked revoke + new config |
| Reuse warning | Copy only — **no auto-block claim** | DEVICE-ENFORCE-001 |
| Per-device billing | **Not live** — future language only | OD-03 + DEVICE-BILL-001 |
| 8th device block | **Do not claim** | MODEL B not ready |

### 5.4 Setup page

**Implemented direction (COMMERCIAL-UX-DEVICE-MVP-001):**

- **Primary:** Open in Happ · copy subscription link · visible link field.
- **Secondary:** QR for another device — collapsible, must not dominate first screen.
- No hidden primary link behind «Показать ссылку» only.
- Copy: this setting is for **one device**; another device needs separate setting / add-device / support.
- Mobile layout must not overflow.

### 5.5 Bot

- Short, conversational; real menu labels (COPY-TRUTH-001 done in repo).
- No ghost labels («Мой VPN»), no NL/Latvia in user copy.
- Device add/replace → support until backend ready.

### 5.6 Referral

Referral is **part of closed-entry positioning**, not only a bonus mechanic.

| Item | Status |
|------|--------|
| Bot-only `t.me/...?start=ref_{code}` | **Live today** |
| Target public share | `{PUBLIC_PORTAL_ORIGIN}/portal/?ref={ref_code}` (OPTION 3 Hybrid) |
| Bot `ref_*` | Backward compatible · secondary CTA on portal |
| Referral growth launch | **NO-GO** until gates in §12 |

---

## 6. Growth target: 10k stable paying users

### 6.1 North star

| Metric | Target |
|--------|--------|
| **Stable paying users** | **10 000** |
| **Average check** | **~200 ₽/month** (~6,67 ₽/day from balance per **account** today — per-device coefficient **not live**) |
| **MRR at target** | **~2 000 000 ₽/month** (illustrative; excludes churn, refunds, multi-device future pricing) |

**Frame growth through:** CAC · LTV · retention · churn · referral K-factor · **server capacity** · **support capacity** · **device/account enforcement** — not ad-buy volume alone.

### 6.2 Churn replacement logic

At **10k paying users**, if monthly churn ≈ **10%**:

- **~1 000 paying users/month** must be acquired just to **maintain** the base.
- **Net growth** requires acquisition **above** churn replacement.
- LTV ≈ `ARPU / churn` (e.g. 200 ₽ / 0.10 ≈ **2 000 ₽** illustrative — validate with real cohort data).

### 6.3 Unit economics (planning model — fill with real data)

| Variable | Planning default | Notes |
|----------|------------------|-------|
| ARPU | 200 ₽/mo | Per **account** today |
| Monthly churn | 8–12% | **Owner validate** before campaigns |
| CAC target | TBD | Must be < LTV × gross margin |
| K-factor | 0.3–0.6 | Only if attribution + ledger + anti-abuse exist |
| Support load | TBD tickets / 100 users | Scale with placements |

---

## 7. Acquisition volume scenarios

### 7.1 Placement yield benchmarks (planning — not promises)

| Yield tier | Paying users per placement | Placements/month for ~1 500 new payers |
|------------|---------------------------|----------------------------------------|
| **Weak** | ~30 | ~50 |
| **Medium** | ~80 | ~20 |
| **Strong** | ~150 | ~10 |

### 7.2 Referral K-factor impact

If **K ≈ 0.5** (each paid-acquired user brings 0.5 additional paying users):

- **1 000** paid-acquired users → **~500** additional organic/referred payers.
- Reduces paid placement pressure **only if** tracking, attribution, cabinet visibility, admin ledger, and anti-abuse exist.

**Today:** referral tracking partial; G4 bind **BLOCKED**; REF-ADMIN-001 missing — **do not plan growth on K-factor until gates pass.**

### 7.3 Paths to 10k (model templates — populate with live metrics)

Assumptions for illustration: start **~500 paying users**, target **10 000**, churn **10%/mo**, required **net +1 583 users/mo** for 6-month path (simplified — real model must compound churn on growing base).

| Horizon | Net new users needed (illustrative) | Implied gross acquisition/mo (with 10% churn on path) | Paid vs organic split (example) |
|---------|-------------------------------------|------------------------------------------------------|--------------------------------|
| **6 months** | ~9 500 | ~2 000–2 500 gross | 60% paid placements / 40% referral+organic |
| **8 months** | ~9 500 | ~1 500–1 800 gross | 50% / 50% |
| **10 months** | ~9 500 | ~1 200–1 500 gross | 40% / 60% |
| **12 months** | ~9 500 | ~1 000–1 300 gross | 30% / 70% |

**Each scenario must eventually include:** monthly new users · paid vs organic split · churn · net growth · MRR · LTV · CAC · ROMI · cashflow · **server capacity additions** · **support load** · **active devices** (not only accounts).

**Owner action:** Build spreadsheet from §8 metrics when baseline counts are confirmed.

---

## 8. Server capacity and quality gates

### 8.1 Core principle

**Marketing, referral growth, and paid placements must not launch independently from infrastructure scaling.**

Growth plan must be tied to **server capacity** and **quality thresholds**. Capacity is **not proven for 10k** today.

**Capacity math (2026-06-11, PROOF-001 + QUALITY-PROOF-001):**

- **Do not count** paid, connected, failover-ready, backup-edge, or **pre-qualified** NL as **active capacity** until **controlled A2/A4 smoke passes** and post-inclusion audit proves ACTIVE users receive NL path.
- **Relay diversity** (two RU relay IPs) improves RU reachability but **does not equal** a second geographic VPN exit if all relays terminate on **LV**.
- Live normal path: **Candidate D relay-only×6** → effective **single LV exit**; **NL=0** in ACTIVE Happ subs.
- **Next infra step:** **controlled smoke** after **MONITOR-FLAP-001** soak — **not** blind prod PATCH; **not** decommission NL (healthy, failover value).

**BACKLOG-CAPACITY-NODES-001 — commercial acquisition/referral growth must also wait on (existing IDs only):**

- **≥2 production-capable nodes on the customer delivery path** — both must participate in auto host / generated subscriptions / routing, **or** non-participating paid server is decommissioned/replaced; **one Latvia-only exit is not acceptable**
- **VPN-ARCH-001** — **PROOF-001** + **QUALITY-PROOF-001 DONE** (2026-06-11): NL not active; pre-qualified for **A2/A4 controlled smoke** after soak; owner approval pending
- **VPN-NODE-RUNBOOK-001** — fast node+relay bring-up template for influx scaling (not **Q120** / **VPN-AUD-201**, which is historical second relay)
- **MONITOR-FLAP-001** + **OPS-ALERT-HYGIENE-001** — monitoring trustworthy before infra scale decisions
- **ACQ-SLOTS-001** + **ACQ-TRIAL-CAP-001** — product gate at 300 active configs/devices **plus** node capacity acceptance checklist (not **OPS-CAPACITY-300-001**)

Canonical list: [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) §ACQUISITION-JOURNEY-001 + §Node capacity.

### 8.2 Metrics to track (future capacity dashboard)

| Metric | Why |
|--------|-----|
| Active paying accounts | Revenue / support load |
| **Active devices / configs** | **Primary infra load driver** (MODEL A) |
| Active devices per paying account | Device multiplier for forecasting |
| CPU / RAM / bandwidth per node | Scale triggers |
| Error / drop / reconnect rate | Quality gate (INCIDENT-003/004) |
| Support tickets per 100 users | Support staffing |
| Incidents after placements | Campaign throttle signal |
| Post-placement churn (7d / 30d) | Placement quality |

### 8.3 Policy capacity thresholds (from Product Policy v1)

| Threshold | Policy trigger |
|-----------|----------------|
| **~300 active configs/devices** | Stricter invite; new TG trials → 30d; **infra capacity acceptance** (≥2 delivery-path nodes, headroom, quality, failover) per **ACQ-TRIAL-CAP-001** / **ACQ-SLOTS-001** |
| **10 000 active configs** | Emergency comms outside Telegram |
| **30 000 active configs** | Registration stop / waitlist |

**Note:** «Active configs» ≠ «paying users». Growth model must use **devices**, especially before DEVICE-ENFORCE-001.

### 8.4 When to add capacity / pause acquisition

| Signal | Action |
|--------|--------|
| Sustained high CPU / connection cap on nodes | Add node capacity **before** next placement wave |
| Reconnect / drop rate above baseline after campaign | **Pause** acquisition; diagnose VPN stability |
| Support queue > SLA | Throttle campaigns; add support runbook / AI copilot |
| Incident open (P0 VPN) | **No new paid placements** until owner all-clear |
| Active configs approach 300 / 10k / 30k policy lines | Apply Product Policy thresholds |

### 8.5 Campaign rollback / throttle

- Rollback = stop placements + communicate on status page — not silent degradation.
- Throttle = reduce placement frequency until quality metrics recover.
- Never scale referrals/partners faster than DEVICE-ENFORCE + bind + ledger readiness.

---

## 9. Device model impact on growth (MODEL A)

**Canonical architecture:** [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md)

| Fact | Growth impact |
|------|---------------|
| **MODEL A** — one tracked config per physical device | Server load scales with **devices**, not accounts |
| One paying account may have **>1 device** (future) | Multiply infra forecast by **device multiplier** |
| Same subscription URL on multiple devices **undetected today** | Commercial + capacity risk; bypasses billing × N |
| **DEVICE-ENFORCE-001** | **Paid/open blocker**; required before scale claims |
| Per-device billing `6,67 ₽ × active_billable_device_count` | **Not live** — OD-03 owner decision |

**Growth model must include `active_billable_device_count` or `active_device_count` proxy** — not only `paying_user_count`.

**Implemented now:** Commercial UX toward MODEL A (cabinet/setup copy, gated add/replace) — COMMERCIAL-UX-DEVICE-MVP-001.

**Not implemented:** Add-device backend · replace/revoke backend · DEVICE-ENFORCE detection · per-device billing.

---

## 10. Retention hooks / membership roadmap

**Not MVP blockers** — inform positioning and backlog priority.

| Hook | Description | Phase |
|------|-------------|-------|
| Closed partner offers / tech discounts | Gorbushka-style deals for members | Post-soft |
| Early access «что завезли» | New features / imports for insiders | Post-soft |
| Verified recommendations | What to buy / avoid (curated) | Community phase |
| Closed moderated community | Telegram / forum — TBD | Owner decision |
| Feature voting | Members influence roadmap | Post-soft |
| Family / extra devices | Packaged or paid add-on | MODEL A + billing |
| Emergency fast Telegram support | Already core promise | **Now** (manual) |

---

## 11. Partner / seller KPI and anti-abuse

### 11.1 Do not use naive dual-payout without fraud controls

**Avoid:** «100 ₽ за регистрацию + 100 ₽ за оплату» with no verification — attracts fraud.

### 11.2 Preferred payout models

| Model | Structure | Risk |
|-------|-----------|------|
| **1 — Safest** | Pay only on **first confirmed payment** | Lowest fraud |
| **2 — Recommended hybrid** | Small bonus for verified install/activity; **main** bonus on first confirmed payment | Balanced |
| **3 — Tier system** | Bronze / Silver / Gold / Platinum by **quality** paid users after hold | Scales partners |

### 11.3 Anti-abuse — do not count reward when

- Same IP / device fingerprint patterns suggest fraud.
- Virtual / disposable phone numbers.
- One card across many accounts.
- No installation / no VPN activity.
- Very short-lived user (< hold period).
- Refund / chargeback / fraud indicators.

### 11.4 Hold period

- **~14 days** before seller/partner payout.
- Cancel payout if user churns, refunds, or fraud signals during hold.

**Requires:** REF-ADMIN-001 ledger · anti-abuse rules in code · owner-approved partner terms.

---

## 12. Launch gates and owner decisions

### 12.1 Current launch classification (frozen audit)

| Launch type | Status |
|-------------|--------|
| F&F | **GO** (manual support) |
| Soft launch | **SOFT-LAUNCH ONLY** |
| Paid pilot | **NO-GO** |
| Open launch | **NO-GO** |
| Referral-driven growth | **NO-GO** |

### 12.2 Referral growth blockers

- **G4** TG bind PASS (or Telegram-only growth only).
- **ACQ-PORTAL-001** portal-first share URL + referral landing (see ACQUISITION-JOURNEY-001).
- **REF-ADMIN-001** admin ledger.
- **REF-METRICS-001** funnel metrics.
- **P1-REF-002** hidden +3d invitee bonus gated OFF (repo).
- **REF-BONUS-001** referrer +1 month reward — **not live** until owner approves.
- Anti-abuse controls defined and implemented.
- **DEVICE-ENFORCE-001** at campaign scale (or written waiver).

### 12.3 Paid/open blockers (summary)

- **BILL-SMOKE-001..004** live money-path proof.
- **DEVICE-ENFORCE-001** L3/L4 reuse detection.
- **DEVICE-ADMIN-001** tracked revoke.
- Add-device / replace backend (MODEL A complete).
- **G9/G11** monitoring + CI for open scale.

### 12.4 Owner decisions needed

| ID | Decision |
|----|----------|
| **OD-03** | Approve per-device billing coefficient |
| **MODEL A** | Confirm as commercial target (arch recommended) |
| **REF-PORTAL-001** | Approve OPTION 3 portal-first share URL |
| **Partner program** | Payout model + hold period + tiers |
| **Growth pace** | 6/8/10/12-month path to 10k |
| **Capacity waiver** | Any campaign before DEVICE-ENFORCE proof |

---

## 13. Backlog impact

| Backlog item | Relationship to this strategy |
|--------------|-------------------------------|
| **STRATEGY-GROWTH-001** | **This doc** — positioning + growth + capacity frame |
| **COMMERCIAL-UX-DEVICE-MVP-001** | Portal cabinet/setup MODEL A UX (**done repo**) |
| **COPY-TRUTH-001** | Bot label honesty (**done repo**) |
| **REF-PORTAL-001** | Portal-first share URL (§5.6) |
| **REF-ADMIN-001** | Partner/seller ledger (§11) |
| **DEVICE-ENFORCE-001** | Scale blocker (§9) |
| **DEVICE-BILL-001** | Per-device billing — after BILL-SMOKE + OD-03 |
| **G4-BIND-RETEST** | Referral/email growth blocker |
| **CAPACITY-MON-001** (proposed) | §8 metrics dashboard — **not in backlog yet**; add when owner prioritizes |
| **GROWTH-MODEL-001** (proposed) | Spreadsheet/scenario model from §7.3 — owner metrics |

**Update pointers:** [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) · [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) §3 · [`AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md`](AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md) · [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md)

---

## 14. Status summary

| Area | Implemented now | Strategic direction | Blocked / gated |
|------|-----------------|---------------------|-----------------|
| Positioning doc | **This file** | Closed membership platform | — |
| Portal MODEL A UX | Repo (not deployed) | Invite-only + trust | REF-PORTAL share URL |
| Setup link-first | Repo (not deployed) | §5.4 | — |
| Copywriting workflow | Skills in `.cursor/skills/` | §4.3 mandatory | — |
| Per-device billing | — | MODEL A coefficient | BILL-SMOKE, OD-03 |
| DEVICE-ENFORCE | Design only | §9 | Paid/open blocker |
| Referral growth | Bot-only share | Portal-first §5.6 | §12.2 |
| 10k capacity proof | — | §8 | Not proven |
| Partner payouts | — | §11 | REF-ADMIN, anti-abuse |

---

*End of STRATEGY-GROWTH-001 · documentation only · no prod mutation*
