# ARCH — Referral Acquisition, Portal Role & Analytics

**ID:** REFERRAL-ARCH-001  
**Date:** 2026-06-10  
**Mode:** architecture audit + decision design · no implementation · no prod mutation  
**Branch:** `product-referral-cabinet-ui-v1`  
**Repo HEAD:** `ed31440` (synced with `origin`)  
**Parent:** [`AUDIT-2026-06-10-USER-LIFECYCLE-SCENARIOS.md`](AUDIT-2026-06-10-USER-LIFECYCLE-SCENARIOS.md), [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md)  
**Owner concern:** Referral share link goes **directly to Telegram bot**, weakening portal’s acquisition role and contradicting two-path product logic (Telegram 90d + email 1d fallback).

**Evidence method:** code + docs + postdeploy only. Status: **CONFIRMED** / **PARTIAL** / **BLOCKED** / **UNKNOWN**.

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **Current share link** | **Telegram bot only** — `https://t.me/{bot}?start=ref_{code}` |
| **Portal role today** | Captures `?ref=` on landing; shows welcome panel; **does not** generate share URL |
| **Target architecture** | **OPTION 3 Hybrid** — public share → **portal referral landing**; bot `ref_*` as in-page CTA |
| **Referral counter today** | **Bot only** («Уже приглашено: N») |
| **Target counter** | **Bot + cabinet** (tracking-only, no bonus copy) |
| **Admin ledger today** | **None** in bot admin |
| **TG bind** | **BLOCKED** — web→TG migration unproven live |
| **Referral growth safe now?** | **Tracking-only TG path: CONDITIONAL**; **email/web growth: NO-GO**; **campaigns: NO-GO** |

**Referral-driven growth launch:** **NO-GO** until G4 bind PASS + REF-ADMIN-001 + REF-COPY-001.

**Cross-device context (DEVICE-ENFORCE-001):** Referral invites increase users who may **share one subscription URL** across devices. Without reuse detection, referral growth scales **infra load** without matching attribution, billing, or enforcement — see [`ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md`](ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md) §14. Paid/open referral campaigns require **DEVICE-ENFORCE-001** (or waiver) in addition to REF-* gates.

---

## 2. Owner concern

The product has **two acquisition paths** (Telegram 90d trial + web/email 1d fallback) and a **portal** for explanation, setup, and cabinet. If inviters share only a **bot deep link**:

- Browser-first invitees skip product education and path choice.
- Portal `?ref=` capture works only if user manually visits portal — not from share URL.
- Email fallback attribution depends on `localStorage.bvpn_ref_code` — fragile if user never hits portal.
- Portal looks like a secondary Mini App shell, not the **public growth surface**.

**Architecture must fix entrypoint**, not preserve bot-only links because they exist.

---

## 3. Current referral behavior (Phase B1)

### 3.1 Share link generation

| Item | Status | Evidence |
|------|--------|----------|
| Link format | **CONFIRMED** — Telegram bot | `handlers.referral_invite_payload` L87: `https://t.me/{username}?start=ref_{ref_code}` |
| Portal share URL | **CONFIRMED absent** | No code builds `{portal_origin}/portal/?ref=` for invite |
| Web `ref_code` API param | **CONFIRMED** — attribution only | `web_referral.apply_web_referral` on email trial POST |
| `ref_code` per user | **CONFIRMED** | `ensure_user_ref_code` — `secrets.token_urlsafe(6)` |

### 3.2 Where link is displayed

| Surface | Status | Evidence |
|---------|--------|----------|
| Bot menu «Пригласить» | **CONFIRMED** | `invite_friend_handler` → `present_referral_invite` |
| Bot `/invite` command | **CONFIRMED** | `invite_command_handler` |
| Bot keyboard URL button | **CONFIRMED** | `create_referral_keyboard(ref_url)` — opens t.me |
| Cabinet «Пригласить друга» | **CONFIRMED** — **bot link** | `portal.js` L1089: `href: botUrlWithReferral()` → t.me `?start=ref_` |
| Portal landing share | **CONFIRMED absent** | No inviter share UI on portal for logged-out users |
| Setup page | **CONFIRMED** — capture only | `setup.js` stores `?ref=` to localStorage |

### 3.3 Invite flow by channel

| Scenario | Behavior | Status |
|----------|----------|--------|
| New user opens `t.me/...?start=ref_X` | `start_handler` → `link_referral` → `referred_by` + `referrals` row | **CONFIRMED** code |
| User already in Telegram | Same; attribution only if `referred_by IS NULL` | **CONFIRMED** |
| User opens link in **browser** | Opens Telegram app or web.telegram.org — **no portal** | **CONFIRMED** |
| User wants 1-day email | Must find portal separately; ref only if `?ref=` was stored earlier | **PARTIAL** — weak |
| Web email trial with `ref_code` | `apply_web_referral` → `link_referral` on web surrogate uid | **CONFIRMED** POSTDEPLOY §5 |
| Web→TG bind | `merge_web_user_to_telegram` migrates `referred_by` + `referrals.referred_user_id` | **CONFIRMED** code; **BLOCKED** live |
| TG bind broken | `funnel_bot_start bind:*` = 0; `NOT_BOUND` | **CONFIRMED** POSTDEPLOY §9, TELEGRAM-BIND-FLOW |

### 3.4 Data writes

| Field / table | Write path | Status |
|---------------|------------|--------|
| `users.referred_by` | `link_referral` — stores **ref_code string**, not inviter TG id | **CONFIRMED** |
| `referrals` | `INSERT (referrer_code, referred_user_id)` | **CONFIRMED** |
| `user_actions` | `referral_linked` with ref code; web: `web:{code}` | **CONFIRMED** |
| Self-referral | Blocked if owner telegram_id == new_user_id | **CONFIRMED** |
| Overwrite attribution | `referred_by IS NULL` guard — no overwrite | **CONFIRMED** |
| Duplicate invite same user | Second link fails silently (`link_referral` no-op) | **CONFIRMED** |

### 3.5 TG `ref_*` vs web `ref_code`

| Aspect | Telegram `ref_*` | Web `ref_code` |
|--------|------------------|----------------|
| Entry | `/start ref_{code}` | `?ref=` → localStorage → POST body |
| User id at link | Real `telegram_id` | Web surrogate negative `web_user_id` until bind |
| `link_referral` | Same function | Same via `apply_web_referral` |
| After bind | N/A | Migrate `referred_user_id` web→tg | **BLOCKED** live |

### 3.6 Bonus and copy

| Item | Status | Evidence |
|------|--------|----------|
| User-facing bonus promise | **CONFIRMED absent** | `msg_referral_invite` — count + link only; policy §5.2 |
| Hidden +3d invitee bonus | **GATED OFF** (P1-REF-002) | `referral_invitee_first_purchase_bonus_days()` — `REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED` default OFF |
| Referrer reward (target) | **NOT IMPLEMENTED** | Owner model: **+1 month to inviter** after invitee first confirmed payment (`REF-BONUS-001`); flag `REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_ENABLED` OFF |
| Portal bonus copy | **CONFIRMED absent** | `ru.json` referral welcome — no bonus |

### 3.7 Counter and admin visibility

| Item | Status | Evidence |
|------|--------|----------|
| User referral counter | **CONFIRMED** — bot only | `count_referrals(ref_code)` in invite screen |
| Cabinet counter | **CONFIRMED absent** | `portal_cabinet.py` — no referral fields |
| Admin ledger | **CONFIRMED absent** | `admin_handlers.py` — no referral queries |
| Support lookup inviter | **BLOCKED** | Manual SQL only |
| Conversion metrics | **CONFIRMED absent** | No trial/wallet/paid status on referrals |

### 3.8 Support/admin question matrix

| Question | Answerable today? |
|----------|-----------------|
| Who invited this user? | **PARTIAL** — `users.referred_by` = code string; need map code→inviter |
| Whom did this user invite? | **PARTIAL** — `COUNT referrals WHERE referrer_code = user.ref_code` |
| Who converted to trial? | **UNKNOWN** — no status on `referrals` row |
| Who converted to wallet? | **UNKNOWN** |
| Who paid? | **UNKNOWN** |
| Whose bind failed? | **PARTIAL** — `web_trial_claims.telegram_id NULL` + no funnel row |

---

## 4. Surface roles (Phase B2)

| Surface | Current role | Target role | Gap | Launch impact |
|---------|--------------|-------------|-----|---------------|
| **Telegram bot** | Identity, trial, pay, support, **only referral share** | Trial issue, payments, support; **secondary** ref entry from portal CTA | Share URL still bot-only | Soft: confusing; Growth: high |
| **Portal / landing** | Product explainer, `?ref=` capture, referral welcome UI | **Primary referral landing** + path choice (TG / email) + attribution | No share URL; cabinet invite → bot | **Core gap** |
| **Web/email 1d** | Fallback trial + ref at signup | Attribution capture; **not growth channel** until bind PASS | Bind BLOCKED | Email referral growth **NO-GO** |
| **Cabinet** | Balance, devices, invite → bot | **Referral counter + statuses** + portal share link | No referral API fields | Paid campaigns blocked |
| **Admin** | Settings, flow test | **Referral ledger**, inviter/invitee lookup, funnel health | No implementation | Growth **NO-GO** |

**Why portal exists in acquisition:** Public HTTPS surface for **education**, **ref capture**, **analytics**, **two-path choice**, and **device/setup** — independent of Telegram app install moment.

---

## 5. Entrypoint options (Phase B3)

### OPTION 1 — Referral → Telegram bot direct (current)

| Criterion | Assessment |
|-----------|------------|
| Acquisition clarity | **Low** — no landing, no path choice |
| Attribution (TG path) | **High** — `ref_*` immediate |
| Attribution (email path) | **Low** — user may never hit portal |
| TG bind dependency | Low for TG-only invites |
| Analytics | **Poor** — no web funnel events |
| Friction | Low for TG-native users |
| Launch readiness | OK for **tracking-only TG** F&F |

### OPTION 2 — Referral → portal/landing first

| Criterion | Assessment |
|-----------|------------|
| Acquisition clarity | **High** |
| Attribution | **High** — `?ref=` + localStorage + API |
| TG bind dependency | **High** for email path completion |
| Analytics | **Good** |
| Friction | +1 click before bot |
| Launch readiness | **PARTIAL** until G4 bind |

### OPTION 3 — Hybrid (recommended)

| Element | Design |
|---------|--------|
| **Default share URL** | `{PUBLIC_PORTAL_ORIGIN}/portal/?ref={ref_code}` |
| Portal page | Referral welcome (exists) + two-path CTAs |
| TG CTA | `botUrlWithReferral()` — `t.me/...?start=ref_{code}` |
| Email CTA | Setup with preserved ref (1d) — **internal/low volume until bind PASS** |
| Bot `ref_*` | Still works for direct opens (backward compatible) |
| Bot share screen | Show **portal link** as primary copy; bot link as «Открыть в Telegram» |

| Criterion | Assessment |
|-----------|------------|
| Best balance | Education + attribution + backward compat |
| Implementation risk | Medium — URL builder + copy + cabinet |
| Launch readiness | **Soft launch OK** for portal-first share; email CTA caveated |

### OPTION 4 — Platform-adaptive deep link

| Criterion | Assessment |
|-----------|------------|
| UX | Best on mobile |
| Complexity | **High** — device detection, fallbacks |
| Launch readiness | **Defer** post OPTION 3 |

### Recommendation

**Target = OPTION 3 Hybrid.**

- **Do not** keep bot-only link as the **public** share default.
- **Keep** `ref_*` bot deep link as **in-portal** and **power-user** entry.
- **Do not** push email 1d as referral growth channel until **G4 bind PASS**.

---

## 6. User referral counter spec (Phase B4)

### 6.1 Placement

| Surface | MVP | Later |
|---------|-----|-------|
| **Bot «Пригласить»** | Keep count + **portal share URL** primary | Status breakdown |
| **Cabinet** | **Add** «Приглашено: N» block | Per-invitee statuses |
| Portal (inviter) | Optional read-only if Mini App session | Full widget |

**Recommendation:** **Both bot and cabinet** for MVP counter.

### 6.2 Fields (tracking-only, no bonus)

| Field | Show now? | Privacy |
|-------|-----------|---------|
| `invited_total` | **Yes** | Aggregate only |
| `activated_trial` | **Later** | Aggregate |
| `wallet_converted` | **Later** | Aggregate |
| `bind_pending` | **Later** | Aggregate |
| `reward_pending` | **No** until REF-BONUS-001 | — |
| Invitee names | **No** | Privacy — statuses only later |

### 6.3 Safe copy (now)

| OK | Not OK |
|----|--------|
| «Вы пригласили **N** пользователей» | «Получите бонус» |
| «Доступ по приглашению» | «+1 месяц другу» |
| «Поделитесь ссылкой на сайт» | «Заработайте» |

### 6.4 API sketch (future)

```text
referral_summary:
  ref_code: string
  invited_total: int
  share_url_portal: string   # primary
  share_url_telegram: string  # secondary
  # later: activated_trial, wallet_count, bind_pending
```

---

## 7. Admin referral analytics spec (Phase B5)

### 7.1 MVP ledger (read-only)

Admin must answer (P1-ADM-002 / REF-ADMIN-001):

| Field | Source |
|-------|--------|
| Inviter `telegram_id`, `username`, `ref_code` | `users` |
| Invitee `telegram_id` or web surrogate | `referrals.referred_user_id` |
| Invitee masked email | `web_trial_claims.contact_email` if web path |
| Source channel | `user_actions.referral_linked` meta (`web:` prefix vs plain) |
| `created_at` | `referrals.created_at` |
| Trial issued | Derive from `vpn_keys` / `trial_used` |
| TG bind status | `web_trial_claims.bound_at`, `telegram_id` |
| Wallet / paid | `users.balance`, `user_actions` topup keys — **join logic needed** |
| Active / expired | `subscription_profile` |

### 7.2 Delivery options

| Option | MVP fit |
|--------|---------|
| `/admin referral <tg_id>` bot command | **Recommended** |
| Read-only SQL script `ops/report_referrals_ams.py` | **Immediate** without UI |
| Dashboard | Later REF-METRICS-001 |

### 7.3 Privacy redactions

- No full emails in bot output — mask `u***@domain`.
- No payment IDs, subscription URLs, or phone numbers.
- Support use: dispute attribution, bind failure triage, fraud clusters.

### 7.4 Missing data today

- No `referral_events` history (only single `referrals` insert).
- No conversion status column.
- No bind failure reason stored.
- No funnel stage timestamps beyond `created_at`.

---

## 8. Data model & attribution correctness (Phase B6)

### 8.1 Current model assessment

| Question | Answer | Status |
|----------|--------|--------|
| Is `referred_by` enough? | **PARTIAL** — stores code not inviter id; OK for link, weak for admin | |
| Does `referrals` preserve history? | **PARTIAL** — one row per successful link; no status updates | |
| Web→TG duplication | Code migrates `referred_user_id`; **not proven live** | **BLOCKED** |
| Double attribution | Prevented by `referred_by IS NULL` | **CONFIRMED** |
| Self-referral | Blocked | **CONFIRMED** |
| Idempotent re-link | Fails if already attributed | **CONFIRMED** |
| Failed binds visible | **PARTIAL** — infer from `web_trial_claims` | |

### 8.2 Target model (design only)

```text
referral_attributions (or extend referrals):
  id
  referrer_user_id      -- inviter telegram_id (resolved from ref_code)
  referrer_code
  invitee_user_id       -- telegram_id or web surrogate
  invitee_contact_hash  -- optional privacy-safe email hash
  source                -- tg_ref | web_ref | bind_migrate
  status                -- linked | bind_pending | bound | trial | wallet | expired | fraud_flag
  bind_status           -- na | pending | success | failed
  conversion_status     -- none | trial | wallet | paid
  created_at
  converted_at
  idempotency_key       -- UNIQUE(referrer_code, invitee_user_id) or event id

referral_events (optional audit trail):
  event_type            -- link | bind_start | bind_ok | bind_fail | trial | topup
  attribution_id
  meta_json_redacted
  created_at
```

**Migration:** Backfill from `referrals` + `users.referred_by` + `user_actions`.

---

## 9. Growth readiness gates (Phase B7)

| Gate | Status | F&F | Soft | Paid | Referral growth | Action |
|------|--------|-----|------|------|-----------------|--------|
| **REF-ARCH-001** | **DONE** | — | — | — | — | Owner approve OPTION 3 |
| **REF-PORTAL-001** | NOT_STARTED | No | **Yes** | Yes | **Yes** | Portal share URL as default |
| **REF-BIND-001** (G4) | **BLOCKED** | No | **Yes** | **Yes** | **Yes** | Owner in-app bind retest |
| **REF-COUNTER-001** | PARTIAL | No | Yes | Yes | Yes | Cabinet + bot portal URL |
| **REF-ADMIN-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | P1-ADM-002 ledger |
| **REF-COPY-001** | PARTIAL | No | **Yes** | Yes | Yes | Remove +3d; fix preserve note |
| **REF-ATTR-001** | PARTIAL | No | Yes | Yes | Yes | Idempotency spec + bind migration test |
| **REF-BONUS-001** | NOT_STARTED | No | No | No | No | Owner OD-02 |
| **REF-FRAUD-001** | NOT_STARTED | No | No | Partial | Yes | Phase 3 |
| **REF-METRICS-001** | NOT_STARTED | No | No | Yes | Yes | Conversion funnel |
| **DEVICE-ENFORCE-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | Shared-sub abuse; blocks paid referral campaigns |

---

## 10. Launch policy (Phase B8)

| Activity | Safe now? | Condition |
|----------|-----------|-----------|
| Telegram referral **tracking-only** (F&F) | **CONDITIONAL YES** | No bonus copy; manual support |
| Portal referral link as share default | **NO** until REF-PORTAL-001 | Spec ready; not implemented |
| Email fallback referral growth | **NO-GO** | G4 bind BLOCKED |
| Referral ad campaigns | **NO-GO** | REF-ADMIN-001 + bind + metrics |
| Bonus promises | **NO-GO** | Policy §5.2; P1-REF-002 gated invitee +3d OFF; referrer +1m not live |
| User counter in cabinet | **NO** until REF-COUNTER-001 | Bot counter OK today |
| Admin manual SQL report | **CONDITIONAL** | Ops script read-only |

**Strict rule:** If TG bind remains BLOCKED, **web/email referral growth is NO-GO** and `referral_preserve_note` must be softened (REF-COPY-001).

---

## 11. Implementation roadmap (Phase B9)

| Order | ID | Objective | Files likely | Deploy? | Prerequisite | Approval |
|-------|-----|-----------|--------------|---------|--------------|----------|
| 1 | REF-ARCH-001 | Decision doc | docs | No | — | Owner approve OPTION 3 |
| 2 | G4-BIND-RETEST | Prove bind + migration | ops smoke | AMS read | — | owner retest bind in TG app |
| 3 | ~~P1-REF-002~~ | Gate hidden invitee +3d OFF; document +1m referrer target | `config.py`, `handlers.py` | Yes | — | **DONE** repo |
| 3b | REF-COPY-001 | Soften preserve note | `ru.json` | Yes | — | approve REF-COPY-001 |
| 4 | REF-PORTAL-001 | Portal share URL builder + inviter copy | `handlers.py`, `portal.js`, `ru.json` | Yes LV+bot | ARCH approved | approve REF-PORTAL-001 |
| 5 | REF-ATTR-001 | Attribution spec + bind migration test | docs, tests | No | BIND PASS | — |
| 6 | REF-COUNTER-001 | Cabinet `referral_summary` API + UI | `portal_cabinet.py`, `portal.js` | Yes | PORTAL-001 | approve REF-COUNTER-001 |
| 7 | REF-ADMIN-001 | Admin ledger command / ops report | `admin_handlers.py`, `ops/` | Yes AMS | — | approve REF-ADMIN-001 |
| 8 | REF-METRICS-001 | Conversion statuses on attributions | schema, scheduler | Yes | ADMIN-001 | approve REF-METRICS-001 |
| 9 | REF-BONUS-001 | Reward engine | billing, bot | Yes | OD-02 owner | approve REF-BONUS-001 |

**Do not implement** in this pass.

---

## 12. Owner decisions required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Referral entrypoint | 1 bot / 2 portal / 3 hybrid / 4 adaptive | **OPTION 3** |
| 2 | Default share URL | Bot vs `{origin}/portal/?ref=` | **Portal** |
| 3 | Email path on referral landing | Prominent vs hidden until bind PASS | **Hidden/caveated** until G4 |
| 4 | Referral growth while G4 BLOCKED | Allow tracking-only TG vs pause all growth | **TG tracking-only F&F**; no campaigns |
| 5 | Counter placement | Bot / cabinet / both | **Both** |
| 6 | Hidden +3d invitee bonus | Remove vs gate | **Gated OFF** (P1-REF-002 DONE repo) — not target reward model |
| 7 | Referral campaigns | When allowed | After REF-ADMIN-001 + G4 + REF-METRICS-001 + anti-abuse |
| 8 | Bonus program | Target: +1 month to **referrer** after invitee paid conversion | **No** until REF-BONUS-001 + controls (ledger, anti-abuse, copy, idempotency) |

---

## 13. Explicit NO-GO items

- Public referral campaigns with email 1d path while G4 BLOCKED.
- Bonus/reward copy without REF-BONUS-001.
- Changing share behavior in prod without REF-PORTAL-001 deploy.
- Promising «ref preserved through email→TG» without bind proof (REF-COPY-001).
- Admin-scale growth without REF-ADMIN-001.
- Implementing referral rewards in this architecture pass.

---

## 14. What can be done immediately

1. Owner approve **OPTION 3** (this document).
2. **G4-BIND-RETEST** — controlled bind with in-app open + DB proof.
3. ~~**P1-REF-002**~~ — hidden invitee +3d gated OFF (repo). **REF-COPY-001** — soften `referral_preserve_note`.
4. **REF-PORTAL-001** spec review — portal URL = `{portal_origin()}/portal/?ref={code}` from `public_urls.portal_origin()`.
5. Read-only ops script design for referral ledger (no prod mutation).

---

## 15. References

| Artifact | Role |
|----------|------|
| `bot_src/handlers.py` | `referral_invite_payload`, `start_handler ref_*`, invitee bonus gate |
| `bot_src/config.py` | `REFERRAL_INVITEE_*` (OFF), `REFERRAL_REFERRER_*` (future +1m, OFF) |
| `bot_src/web_referral.py` | Web attribution |
| `bot_src/web_tg_bind.py` | Bind migration |
| `bot_src/database.py` | `link_referral`, `count_referrals` |
| `web/portal/assets/portal.js` | `preserveReferralFromUrl`, `botUrlWithReferral` |
| `POSTDEPLOY-2026-06-10-P1-REF-001.md` | Web ref PASS; bind FAIL |
| `BENDERVPN-PRODUCT-POLICY.md` §5 | Referral policy |

---

**Architecture audit complete.** No implementation. No prod mutation.
