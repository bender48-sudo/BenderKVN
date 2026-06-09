# BenderVPN Product Policy v1

**Status:** accepted · owner decisions locked 2026-06-09
**Supersedes:** informal copy truths in `BENDERVPN-PRODUCT-QUALITY-PLAN.md` §2 where they conflict
**Scope:** product policy only — no implementation in this document
**Source:** Full Product Audit + Product Decision Workshop (branch `product-referral-cabinet-ui-v1`)

---

## 1. Executive summary

BenderVPN is a **камерный VPN** sold primarily through **Telegram**, with a **web email fallback** when Telegram cannot be opened. The client journey copy is **good enough for pilot**; remaining risk is **policy vs backend mismatch**.

This policy locks owner decisions on nine areas: invite model, capacity, registration, referral, device, trial, billing, support, and admin reporting. It defines **what the product promises**, **what is deferred**, and **implementation phases** without prescribing schema or VPN changes here.

**Pilot stance (now):**

- Soft invite-first positioning; organic entry allowed with monitoring.
- Telegram **90-day** trial; email **1-day** temporary access.
- **One active config per account**; new device via support only.
- Billing communicated as **6,67 ₽/день** from balance; trial does not debit balance.
- **No referral bonus** at MVP; fix attribution end-to-end.
- **No hard invite gate**, **no public capacity counter**, **no SMS**, **no email verification** at MVP.

**Threshold triggers:**

| Trigger | Policy change |
|---------|---------------|
| **~300 active configs** | Users without referral → waitlist/manual approval; **new** Telegram trials become **30 days** (grandfather existing 90-day users). |
| **30 000 active configs** | No new configs/trials unless capacity expanded; waitlist opens; existing users grandfathered. |
| **Partner scale / broader growth** | User-facing support email required. |
| **10 000 active configs** | Emergency communication channel outside Telegram required. |

---

## 2. Accepted product truths

These statements are **canonical** for all user-facing copy, legal drafts, bot messages, and admin runbooks until policy v2.

| ID | Truth | Rule |
|----|-------|------|
| **PT-01** | Primary path | Telegram bot → **90-day** trial (pilot); **30-day** for new users after 300 active configs |
| **PT-02** | Fallback path | Web email → **1-day** temporary access only; purpose is to reach Telegram |
| **PT-03** | Invite model | Камерный VPN, **доступ по приглашению**; soft positioning during pilot |
| **PT-04** | Capacity | **30 000 active configs** (not Telegram registrations); badge only until stable read-only source |
| **PT-05** | VPN profile | **BenderVPN Auto** — no manual server/node picking in user copy |
| **PT-06** | Device | **One active config per account**; one config = one device in messaging |
| **PT-07** | Referral bonus | **Must not be promised** until implemented; no «+1 month» |
| **PT-08** | Billing | **6,67 ₽/день** from balance; **200 ₽ ≈ 30 дней**, not calendar month |
| **PT-09** | Trial billing | During trial, **balance does not decrease** |
| **PT-10** | Support | Telegram bot + `/id` + errors page; standard intake: device, what happened, screenshot, Telegram ID |
| **PT-11** | Forbidden copy | No turbo, wl-direct, wl-routed, NL/LV/9443, manual server pick |
| **PT-12** | Enforcement honesty | Do not claim hard technical enforcement (invite gate, device limit, capacity stop) until it exists |

---

## 3. Access policy

### 3.1 Positioning

- Product is **invite-first / камерный**: growth through referrals and controlled rollout.
- Public badge: **«Доступ по приглашению · лимит 30 000»** — sufficient until a stable public counter exists.
- **No live public counter** at MVP (`capacity_api_enabled: false` remains correct).

### 3.2 Pilot (current → ~300 active configs)

| Rule | Policy |
|------|--------|
| Referral links | Encouraged; `ref_` / `ref_code` should attribute when present |
| Organic `/start` | **Allowed** during pilot |
| Monitoring | Organic signups flagged for **manual review** (ops/admin) |
| Hard gate | **Do not implement** during pilot |

### 3.3 Post-300 active configs

| Rule | Policy |
|------|--------|
| No referral | User goes to **waitlist** or **manual approval** — not automatic 90-day trial |
| With referral | Normal trial path per §7 |
| Implementation | Waitlist UX and enforcement are **Phase 4**; policy is decided now |

### 3.4 At 30 000 active configs

| Rule | Policy |
|------|--------|
| Definition | **Active configs** on panel (valid subscription / ACTIVE user with issued config) |
| New signups | **No new configs or trials** unless capacity is expanded |
| Existing users | **Grandfathered** — service continues |
| Waitlist | **Opens** for new demand |
| Public counter | Still hidden until stable read-only API; internal dashboard required |

### 3.5 Copy principles

- Say **«по приглашению»** and **«лимит 30 000»** — do not imply a live seat counter.
- Do not promise **«места заканчиваются сейчас»** without real data.
- Two valid entry paths must remain visible: **Telegram (90d)** and **email fallback (1d)**.

---

## 4. Registration / contact policy (REG-001)

### 4.1 Telegram path (90-day trial)

| Field | Pilot rule |
|-------|------------|
| Telegram ID | Implicit via bot; primary identity |
| Phone | Ask **softly in onboarding**; **do not block** 90-day trial |
| Email | Ask **softly in onboarding**; **do not block** 90-day trial |
| Collection method (phone) | **Telegram contact share** when implemented — not SMS, not mandatory form at MVP |
| SMS | **Not at MVP** |
| Email verification | **Not at MVP**; revisit if abuse appears |

### 4.2 Email fallback path (1-day access)

| Field | Rule |
|-------|------|
| Email | **Mandatory** |
| Phone | **Optional** |
| One email | One claim per email (anti-abuse) |
| Purpose copy | Temporary access to reach Telegram — not a substitute for 90-day trial |

### 4.3 Refusal during pilot

If user refuses phone and email on Telegram path:

- **Still allow 90-day Telegram trial** during pilot.
- **Later high-risk actions** may require contact or support:
  - Second device / additional config
  - Referral rewards (when/if implemented)
  - Account recovery without Telegram access
  - Top-up edge cases (disputes, chargebacks, identity checks)

### 4.4 Privacy alignment

- Update **privacy policy / terms** when REG-001 fields are collected in bot (Phase 2).
- Until then, web path email collection remains the only mandatory PII beyond Telegram ID.
- See `docs/DATA-MINIMIZATION-POLICY.md` — reconcile before mandatory collection.

---

## 5. Referral policy

### 5.1 Attribution (required)

| Channel | Requirement |
|---------|-------------|
| Telegram `ref_` | Must record inviter → invitee |
| Web `ref_code` | **Fixed** (P1-REF-001) — `apply_web_referral` at email trial; bind migration **unproven** (G4 BLOCKED) |
| Storage | `referred_by` / equivalent must be queryable in admin |

### 5.2 User-facing rewards (MVP)

| Rule | Policy |
|------|--------|
| Bonus at MVP | **None** |
| Copy | **Do not promise** +1 month, balance credit, or extra days |
| UI | No referral reward CTAs until implemented |

### 5.3 Future bonus (deferred — owner pre-approval shape only)

If approved in a future policy revision:

| Parameter | Recommended shape |
|-----------|-------------------|
| Type | **Small time credit only** — not money, not +1 month |
| Trigger | Invitee **active 7–14 days** OR **first payment** — not registration alone |
| Fraud | Same-IP clusters, disposable email, self-referral loops — admin review |

### 5.4 Abuse controls (Phase 3)

- Attribution completeness metric before scaling invites.
- Manual pause / suspicious flag on referral chains.
- No automated payout at MVP.

### 5.5 Acquisition entrypoint — **pending owner** (REFERRAL-ARCH-001)

**Audit:** [`ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md`](ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md) (2026-06-10).

| Item | Current | Proposed target | Status |
|------|---------|-----------------|--------|
| **Public share URL** | Telegram `t.me/...?start=ref_{code}` only | **Portal landing** `{origin}/portal/?ref={code}` primary; bot link secondary CTA | **Pending owner approval** |
| **Portal role** | Captures `?ref=` if user visits; no share URL | Primary referral landing + path choice (TG / email) | Pending |
| **Email referral growth** | Web attribution at signup works | **Not growth channel** until G4 TG bind PASS | **NO-GO** until bind |
| **Referral counter** | Bot invite screen only | Bot + cabinet (tracking-only) | Pending REF-COUNTER-001 |
| **Admin ledger** | None | P1-ADM-002 / REF-ADMIN-001 | Pending |

Until owner approves OPTION 3: existing bot-only share link remains in production; **do not run referral growth campaigns**.

---

## 6. Device / config policy

### 6.1 MVP rule

| Rule | Policy |
|------|--------|
| Active configs | **One per account** |
| New device | **Support-only** — no self-serve second key |
| Multi-device product | **Not at MVP** |
| Link reuse | Copy states one config = one device; **no hard block** until enforcement exists |

### 6.2 Messaging

- State clearly: **«Одна настройка — одно устройство»**.
- Do not claim panel HWID / deviceLimit enforcement until implemented.
- If user asks for second device: route to support with device + Telegram ID.

### 6.3 Future enforcement (evaluate in Phase 2–3)

- Panel `deviceLimit`, HWID, subscription telemetry.
- Policy trigger for second device: paid add-on (+6,67 ₽/day per extra active config) — **not decided**; see §12.

### 6.3.1 Architecture decision — **pending owner** (DEVICE-ARCH-001)

**Audit:** [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) (2026-06-10).

| Item | Proposed direction | Status |
|------|-------------------|--------|
| **Target model** | **MODEL A** — one tracked config per device; billing coefficient per active billable device | **Pending owner approval** |
| **MODEL B** (one sub, N devices, block 8th) | **NOT READY** — Remna HWID/session enforcement unproven in bot | Do not promise in copy |
| **Pricing coefficient** | `6,67 ₽/день × active_billable_device_count` | **Pending OD-03** — no silent billing change |
| **Trial** | One trial device only until wallet path proven | Recommended in arch doc |
| **Manual Remna configs** | **Prohibited** without matching app DB row | Support policy |

Until owner approves MODEL A: MVP remains **one active billable config** + support **tracked** replace (not vague support-only).

### 6.4 Backend reality (audit)

- Multiple `vpn_keys` per user may exist today — **policy is one active config**; technical consolidation/enforcement is implementation, not copy change.

---

## 7. Trial policy

### 7.1 By channel

| Channel | Trial length | Notes |
|---------|--------------|-------|
| **Telegram** (pilot) | **90 days** | Main path |
| **Telegram** (after 300 active configs) | **30 days** for **new** trials only | Announce before switch |
| **Email fallback** | **1 day** always | Unchanged at any threshold |
| **Partner channel** | **Not defined** | Defer until partner program exists |

### 7.2 Grandfathering

| Cohort | Rule |
|--------|------|
| Users who started 90-day trial **before** policy switch date | **Keep remaining 90-day period** |
| New users after switch | **30-day** Telegram trial only |
| Email fallback | Always 1 day regardless of cohort |

### 7.3 Threshold definition

- **300** means **active configs**, not Telegram registrations or paid users.
- Owner must **announce** trial shortening in product surfaces before enforcement.

### 7.4 Trial → paid transition

- After trial ends: daily balance billing at **6,67 ₽/день** unless balance empty and service paused per billing rules.
- Trial period: **no balance deductions** — must be visible in cabinet/bot.

---

## 8. Billing / topup policy

### 8.1 User-facing model

| Element | Communication |
|---------|---------------|
| Primary | **6,67 ₽/день** списывается с баланса |
| Top-up preset | **200 ₽** = **«примерно 30 дней»** — not «200 ₽/месяц» as calendar subscription |
| Trial | **«Бесплатный период — списания с баланса не идут»** |
| Payment surface | Telegram bot / Mini App (primary); browser cabinet is fallback UX |

### 8.2 Multi-config billing

| Rule | Policy |
|------|--------|
| MVP | **Per account** — one daily charge regardless of key rows until multi-device product exists |
| Future multi-device | **+6,67 ₽/день per extra active config** — design in Phase 3+ if product approved |

### 8.3 Cabinet requirements

When cabinet API is aligned (Phase 1–2):

- Show: balance, daily rate, estimated days remaining, trial vs wallet state.
- Do not show calendar-month subscription renewal dates unless billing model changes.
- Browser cabinet: no false promise of live balance without Mini App `initData`.

### 8.4 Legal / terms

- Terms must distinguish Telegram 90d (→ 30d after threshold) vs email 1d.
- Wallet model described as prepaid balance with daily debit — not recurring card subscription unless added later.

---

## 9. Support / recovery policy

### 9.1 MVP channels

| Channel | Status |
|---------|--------|
| Telegram bot support | **Primary** |
| `/id` command | **Required** — user provides Telegram ID to support |
| `/start/help/errors/` | **Self-service first** |
| Support email (user-facing) | **Not required for current pilot** |
| Support email | **Required before partner scale or broader growth** |

### 9.2 Standard support intake

User should provide:

1. **Device** (model + OS)
2. **What happened** (steps, error text)
3. **Screenshot** if possible
4. **Telegram ID** via `/id`

### 9.3 Recovery lookup (admin-side)

| Identifier | Lookup use |
|------------|------------|
| Telegram ID | Primary — maps to user account |
| Email | Web trial claims, fallback users |
| Customer ID | Payment / claim reconciliation |
| Phone | Only after REG-001 collection |

### 9.4 Emergency communication

| Threshold | Requirement |
|-----------|-------------|
| **Before 10k active configs** | **Emergency channel outside Telegram** (e.g. status page broadcast, ops email list, status subdomain) |
| Telegram outage | Users must have non-TG path to learn of incidents |

### 9.5 Recovery without Telegram

- Email fallback users: recover via email claim record.
- Telegram-only users without TG access: **support-assisted** — may require proof; contact data from REG-001 improves recovery (Phase 2).

---

## 10. Admin / reporting policy

### 10.1 Must-have before broader invite rollout

| Capability | Purpose |
|------------|---------|
| **Referral ledger** | Who invited whom; completeness audit |
| **User lookup** | By Telegram ID, email, customer ID |
| **Balance / keys / trial state** | Single-pane user status |
| **Payment reconciliation** | Payment ID ↔ balance credit |
| **Manual pause / suspicious flag** | Ops response without schema-heavy automation |

### 10.2 Must-have before 300 active configs

| Metric | Purpose |
|--------|---------|
| **Active config count** | Threshold for trial shortening + waitlist |
| **Trial → paid funnel** | Conversion signal |
| **Referral attribution completeness** | % signups with `referred_by` |
| **REG-001 contact capture rate** | Phone/email optional field adoption |
| **Fraud signals** | Same IP/email clusters, abnormal referral velocity |

### 10.3 Must-have before partner scale

| Capability | Purpose |
|------------|---------|
| Partner-tagged ref codes | Separate from user-to-user referral |
| CAC / payout ledger (manual OK) | Partner economics |
| Abuse alerts | Partner fraud review |

### 10.4 Capacity dashboard

- Internal only at MVP.
- Source: ops snapshot (`active_keys` / panel ACTIVE users) — align with §3.4 definition.
- Public API optional in Phase 4+.

---

## 11. Open decisions deferred

These were discussed in the workshop but **not locked** by owner; do not implement until decided.

| ID | Topic | Options | Blocks |
|----|-------|---------|--------|
| **OD-01** | Partner program | Separate channel, trial, payout vs user referral | Phase 5 |
| **OD-02** | Referral bonus economics | +7d inviter vs invitee vs both; exact trigger day | Phase 3 |
| **OD-03** | Second device as paid SKU | Price, self-serve vs support, billing split | Phase 3+ |
| **OD-04** | Email verification | Codes at signup vs at topup only | Phase 3 |
| **OD-05** | Mandatory phone before topup | Hard block vs soft nudge | Phase 2 |
| **OD-06** | Public capacity API | Endpoint shape, cache, rounding | Phase 4 |
| **OD-07** | Support email address | hello@ vs support@; SLA | Pre-partner |
| **OD-08** | Emergency comms channel | Status-only vs email list vs both | Pre-10k |
| **OD-09** | Privacy policy revision | REG-001 fields in bot onboarding | Phase 2 |
| **OD-10** | Calendar-month subscription | Keep wallet-only vs add card recurring | Future billing |

---

## 12. Implementation phases

Phases describe **engineering sequencing** after this policy. No code in this document.

### Phase 1 — Product-logic alignment (no schema-heavy work)

**Goal:** Align copy, attribution, and admin visibility with policy v1.

| Item | Priority |
|------|----------|
| Fix web `ref_code` → attribution chain | P0 |
| Bot/Mini App label alignment (ghost strings) | P1 |
| Remove forbidden NL/LV from help copy | P1 |
| Post-trial invite copy matches §3 | P1 |
| Minimal admin: referral ledger + user lookup | P1 |
| Cabinet API: `billing_profile`, trial/wallet state fields | P1 |
| Publish runbook: support intake + `/id` | P2 |

**Explicitly not Phase 1:** invite hard gate, REG-001 DB fields, device HWID, capacity enforcement, referral bonus.

### Phase 2 — REG-001 design / implementation

**Goal:** Soft phone/email in Telegram onboarding; optional web phone uniqueness.

| Item | Priority |
|------|----------|
| Bot onboarding: optional phone (contact share) + email | P1 |
| Store contact fields; privacy/terms update (OD-09) | P1 |
| Phone UNIQUE when collected | P2 |
| Refusal rules for high-risk actions (§4.3) | P2 |
| REG-001 capture rate metric | P2 |

### Phase 3 — Referral / anti-fraud

**Goal:** Trustworthy growth mechanics.

| Item | Priority |
|------|----------|
| Referral attribution completeness reporting | P1 |
| Fraud signals (IP/email clusters) | P2 |
| Future bonus implementation **if OD-02 approved** | P3 |
| Email verification **if OD-04 approved** | P3 |
| Device enforcement design (deviceLimit/HWID) | P2 |

### Phase 4 — Capacity / waitlist

**Goal:** Enforce §3.3 and §3.4 at scale.

| Item | Priority |
|------|----------|
| Internal capacity dashboard | P1 |
| Waitlist UX + data model | P1 |
| Trial 90→30 switch with grandfather rules | P1 |
| Invite gate: no-ref → waitlist after 300 active configs | P1 |
| Hard stop new configs at 30k | P2 |
| Public capacity API **if OD-06 approved** | P3 |

### Phase 5 — Partner scale

**Goal:** Commercial channel without contaminating user referral.

| Item | Priority |
|------|----------|
| User-facing support email (§9.1) | P0 |
| Emergency comms outside Telegram (§9.4) | P0 |
| Partner ref codes + manual payout ledger | P1 |
| Partner-specific trial policy **if OD-01 approved** | P2 |
| CAC reporting | P2 |

---

## 13. Do-not-implement-yet list

Do **not** start these until the relevant phase and open decision are closed:

| Item | Reason |
|------|--------|
| Hard invite gate | Pilot allows organic; Phase 4 only |
| +1 month (or any) referral bonus | OD-02; PT-07 |
| Mandatory phone before 90-day TG trial | §4.1 pilot rule |
| SMS verification | §4.1 explicit no |
| Email verification codes | OD-04; abuse-triggered only |
| Public live 30k counter | PT-04; no stable API |
| Self-serve second device / multi-key | §6.1 |
| Device fingerprinting at signup | Phase 3 evaluation only |
| Partner payout automation | Phase 5 |
| VPN routing / infra changes | Separate architecture track |
| Full portal copy loop reopen | Journey good enough; narrow bot fixes only |
| Database schema changes for REG-001 | Phase 2 |
| Billing logic changes (daily rate, trial skip) | Already correct; communication only |

---

## References

| Document | Role |
|----------|------|
| `docs/BENDERVPN-PRODUCT-QUALITY-PLAN.md` | Portal UX execution; journey map |
| `docs/BENDERVPN-MASTER-BACKLOG.md` | Implementation tracking (PROD/DEC-IMPL/OD items) |
| `docs/BENDERVPN-AUDIT-ROADMAP.md` | Ordered audits before implementation |
| `docs/DATA-MINIMIZATION-POLICY.md` | Privacy baseline — reconcile in Phase 2 |
| `web/portal/content/ru.json` | User-facing copy source |
| `bot_src/config.py` | `REMNA_TRIAL_DAYS`, `WEB_TRIAL_DAYS`, `DAILY_RATE` |

---

## Implementation tracked in master backlog

Policy decisions in §2–13 are **not rewritten here**. Engineering tasks, acceptance criteria, audit sequence, and open decisions (OD-01…10) are tracked in **[`docs/BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md)**.

Audits required before implementation phases: **[`docs/BENDERVPN-AUDIT-ROADMAP.md`](BENDERVPN-AUDIT-ROADMAP.md)**.

---

**Version:** 1.0 · **Next review:** at 300 active configs or policy v2 trigger from owner
