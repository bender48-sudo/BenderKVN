# AUDIT — Device links, balance display, and instruction UI

**Date:** 2026-06-09 (verification pass)  
**Mode:** Read-only audit — no code, billing, or UI changes  
**Branch context:** `product-referral-cabinet-ui-v1` (local ahead of origin; see final report)  
**Related:** [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md), [`POSTDEPLOY-2026-06-10-P1-REF-001.md`](POSTDEPLOY-2026-06-10-P1-REF-001.md), [`AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md`](AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md) (button paths → same subscription link)

---

## 1. Executive summary

| Area | Finding | Severity |
|------|---------|----------|
| TG bind (P1-REF-001 §9) | **Still FAIL** — `p1bind-` claim unbound; no `funnel_bot_start` / `web_tg_bind` actions in AMS DB | **P1 gate blocker** |
| Device instruction UI | Likely **visual-only** CSS mismatch on guide/setup pages (inline store button vs block buttons) | P2 UX |
| New device journey | **Policy = support-only**; copy in setup/cabinet **over-promises** self-service second config | P1 product truth |
| Balance display | Stored `users.balance`; owner **186.66 ₽** stable ~2 weeks is **consistent with legacy panel bypass** after two daily charges | P1 trust/clarity |
| Multi-config billing | **6.67 ₽ × N not implemented** — one `DAILY_RATE` debit per account per UTC day regardless of key rows | Documented MVP gap |
| **Active config visibility** | Setup/cabinet show **one subscription URL/QR**; **no count**, **no list**, **no revoke** in UI or cabinet API | **P1 product truth** |

**Recommendation:** Do not start multi-device or billing “fixes” until product decision + G2-B cabinet truth. Pilot policy: **Option A (MVP strict)** — see §14. Implement **`billing_profile` in cabinet before** device self-service or copy changes.

---

## 2. Device instruction UI layout issue

### Affected surfaces

| Page | Files | Component |
|------|-------|-----------|
| **Guide** (primary suspect) | `web/portal/guide.html`, `assets/guide.js`, `assets/portal.css` | `#guide-device-tabs`, `#guide-steps-panel` |
| **Setup (post-token)** | `web/portal/setup.html`, `assets/setup.js` | `#setup-device-grid`, `#platform-downloads` |
| **Mini App / portal** | `web/portal/index.html`, `assets/portal.js` | `#device-grid`, device detail sheets |
| **Cabinet actions** | `cabinet.html`, `portal.css` `.cabinet-actions__grid` | 2×2 action cards |

### Root-cause hypothesis

1. **Guide steps card — mixed button models** (`guide.js` + `portal.css`):
   - Store download in step 1 uses `btn btn--secondary guide-store-btn` with **`display: inline-block; min-width: 12rem`** (not `btn--block`).
   - Trouble links use `btn btn--secondary btn--block guide-action-link`.
   - Inside `.guide-steps-card ol li`, the inline store button can **visually extend past the card/content box** on narrow viewports while block buttons align to card width → owner perception of buttons “drifting outside the block”.

2. **Guide device tabs — 2-column grid** (`.device-grid--guide`):
   - Four `device-card` tabs in `grid-template-columns: 1fr 1fr`.
   - Cards use flex + `::after` arrow; long labels + emoji icon can wrap unevenly on very small screens (cosmetic, clicks still work).

3. **Setup platform downloads** (`#platform-downloads` in `.actions`):
   - Up to four full-width secondary buttons stacked; long Russian store labels may feel detached from the “device pick” panel above (spacing/panel boundary, not broken links).

4. **Cabinet action grid** (`.cabinet-action-card`):
   - 2-column grid with `font-size: 0.82rem`; long CTA strings can **overflow card padding** on mobile (visual only).

### Click path

**Likely visual-only** — no evidence of dead zones or `pointer-events` issues in CSS. Manual confirm on iPhone width (~390px) for `/portal/guide.html` and setup token page.

### Minimal fix later (do not implement in this pass)

- Make all guide in-card CTAs consistently `btn--block` **or** wrap store button in a `.guide-step-actions` container with `width: 100%`.
- Add `max-width: 100%; box-sizing: border-box` to `.guide-store-btn`.
- Optional: single-column device grid below 360px for `.device-grid--guide` / `.device-grid--setup`.

### Post-fix test

- Playwright or manual screenshots: guide (each device tab), setup ready state, cabinet actions — **375px and 390px width**.
- Assert no horizontal scroll; store/trouble buttons fully inside `.guide-steps-card`.

---

## 3. New device / link user journey

### Current behavior (code + policy)

| Question | Answer |
|----------|--------|
| More than one active config per account? | **Not product-supported at MVP.** Backend allows multiple `vpn_keys` rows; no hard enforcement. |
| User self-service second device link? | **No safe self-service path.** `web_tg_bind.merge_web_user_to_telegram` rejects `both_have_keys`. Bot `menu_get_setup` returns **same subscription setup URL** (refresh), not a new Remna user/key. |
| Where exposed? | Cabinet `new_device_cta` → bot URL; FAQ says support; setup copy implies cabinet/bot self-issue (**mismatch**). |
| Replace vs additional | Same sub link = **refresh/re-import** on same or another device; **new Remna key = admin/support** today. |

### Policy source

- [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) PT-06, §8.2: one active config; new device **support-only**; future multi-device billing **not MVP**.
- [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) PROD-004: accepted gap — policy documented, enforcement open.

### User confusion

- `ru.json` `setup.device_rule`: *«Для нового устройства выпусти новую настройку в личном кабинете или боте»* — implies self-service.
- FAQ `cabinet.faq` correctly says second device via support.
- Errors/help: *«Мой VPN» → QR / ссылка»* reads like a new link, but bot returns **existing** subscription URL.

### Product decision needed

Choose one messaging line for later copy (not now):

- **Refresh existing link** — same config, new phone OK.
- **Get link for another device** — only after backend supports N keys + billing.
- **Replace device** — support/admin rotates key.
- **Contact support** — current MVP truth.

### Backend/admin preconditions for self-service multi-device

- Enforce max active configs per account (DB + Remna).
- Billing rule: explicit **6.67 ₽ × active_configs** with tests.
- Cabinet `billing_profile` showing per-config cost.
- HWID or fair-use policy if claiming “one device”.

---

## 4. Current one-device vs multi-device policy

| Layer | Stated policy | Implementation |
|-------|---------------|----------------|
| Product docs | 1 active config / account | Documented |
| Portal copy | Mixed (setup vs FAQ) | **Mismatch** |
| `vpn_keys` table | — | Multiple rows possible |
| Daily billing | 1× `DAILY_RATE` / account / day | **Not per key** |
| TG web bind | Blocks if both sides have keys | Enforced at bind only |

**6.67 ₽ × 2 per day:** **Not implemented.** `charge_daily_balance_if_due` deducts fixed `DAILY_RATE` once; `sync_panel_from_balance` uses `keys[0]` only.

---

## 5. Balance display source of truth

| Display | Source |
|---------|--------|
| Bot / Mini App cabinet API | `users.balance` via `portal_cabinet.cabinet_snapshot` → `balance_rub`, `days_left = balance_to_days(balance)` |
| Web-only trial cabinet | Same table on web surrogate or bound TG user |
| Panel expiry shown elsewhere | Remna `expireAt` — can diverge when profile is `legacy` |

**Not computed from panel expiry** for wallet users except via `sync_panel_from_balance` after charge.

---

## 6. Daily billing / drain implementation

| Item | Detail |
|------|--------|
| Rate | `DAILY_RATE = 6.67` in `bot_src/config.py` |
| Charge function | `balance_billing.charge_daily_balance_if_due` — idempotent per UTC day (`daily_balance:YYYY-MM-DD`) |
| Live gate | `BOT_PAYMENTS_LIVE` env must be true; else `skipped` |
| Trigger | `scheduler._poll_vpn_user` → `process_daily_balance_user` each monitor cycle (~5 min batch) |
| Profile gate | `subscription_profile.access_profile` must return **`wallet`** |

**Charge scope:** Per **telegram user id**, not per `vpn_keys` row.

---

## 7. Manual ~78-year access caveat (owner diagnostic)

Read-only AMS check on owner account (TG id redacted; internal ops id ending …8094):

| Field | Observed |
|-------|----------|
| Balance | **186.66 ₽** (UI ~187 ₽ — rounding) |
| Top-up | **200 ₽** on **2026-05-26** |
| Daily debits | **2026-05-26** and **2026-05-27** only (`6.67` each) → 200 − 13.34 = **186.66** |
| Key expiry (local DB) | **2099-12-31** prefix |
| Keys count | **1** |

**Interpretation:** `is_legacy_manual_panel()` triggers on year ≥ **2030** (`LEGACY_PANEL_MIN_YEAR`). Profile becomes **`legacy`**, so `process_daily_balance_user` **returns without charging**. Balance frozen after the last wallet-classified days is **expected**, not a arithmetic bug.

**UX gap:** Cabinet may still show balance and “days left” as if wallet billing were active, while panel access is effectively manual/unlimited — confuses owner.

---

## 8. Whether 6.67 ₽ × N active configs is implemented

**No.** MVP policy explicitly says one daily charge per account regardless of key rows until multi-device product ships. Code matches policy (single debit). **Do not assume** future multiplier exists.

---

## 9. User-facing confusion / mismatch

1. Balance unchanged ~2 weeks despite “pay per day” mental model → **legacy bypass not explained in UI**.
2. Setup copy suggests self-issue for new device; FAQ says support → **contradiction**.
3. “Get new link” vs “refresh subscription in Happ” not distinguished.
4. Cabinet `new_device_cta` opens bot without explaining support-only policy.
5. **No active-config count or revoke** on setup/cabinet — user cannot see or delete links (see §14).

---

## 10. Risks

| Risk | Impact |
|------|--------|
| TG bind never verified | Referral migration on bind unproven live → G2-A blocked |
| Legacy + wallet balance coexist | Users think balance drains but access is manual |
| Multiple keys without billing | Fair-use / capacity |
| Copy promises second config | Support load + trust |
| Guide UI overflow | Lower confidence in setup flow |

---

## 11. Recommended backlog items

### UI layout fix
- **P2-UX-GUIDE-001:** Unify guide in-card buttons (`btn--block`, overflow guard). Verify mobile 375px.

### Copy clarification (after product sign-off)
- **P2-COPY-DEVICE-001:** Align `setup.device_rule`, cabinet CTA, FAQ to support-only MVP.
- Distinguish **refresh sub** vs **new device**.

### Backend policy enforcement
- **PROD-004 / AUDIT-006:** Max one active config or explicit multi-device product spec.

### Balance display truth
- **P1-CAB-001 / G2-B:** Expose `billing_profile` (`legacy` | `wallet` | `trial`) in cabinet; hide or annotate balance when `legacy`.

### Billing drain verification
- **P1-BILL-AUDIT:** Document legacy-first ordering in `access_profile`; add read-only admin probe for profile kind + last `daily_balance:*` action.

### Multi-device support (only if product approves)
- Schema + Remna provisioning + **6.67 × N** charges + enforcement — **Phase 3+**, not now.

---

## 12. No-go items before development

- Do not enable self-service second config without billing + enforcement design.
- Do not change owner balance or run billing jobs manually.
- Do not “fix” legacy owner panel expiry during audit.
- Do not grant referral bind bonuses during bind retest.
- Do not close P1-REF-002 until TG bind PASS on clean account.

---

## 13. Proposed next surfaces and commit order

1. **Owner: TG bind retest** — dedicated TG account, no keys, open exact `p1bind-` bind URL; confirm bot success message; re-run AMS verify → expect `P1_BIND_VERIFY_OK`.
2. **P1-CAB-001 / G2-B** — cabinet `billing_profile` + legacy wallet messaging (addresses owner 187 ₽ confusion).
3. **P2-UX-GUIDE-001** — guide button layout (visual only).
4. **P2-COPY-DEVICE-001** — device/copy alignment after backend truth.
5. **P1-REF-002** — hidden +3d referral bonus gate (after G2-A bind PASS).

**Priority rationale:** Backend billing truth and TG bind gate outweigh pure CSS; referral bonus is next only if live code path confirmed risky.

---

## 14. Active config visibility and revoke/delete gap

**Audit date:** 2026-06-09 (device/config management pass)  
**Trigger:** User on setup/cabinet screen saw QR, subscription link, «Скопировать ссылку», «Инструкция по устройству», and warning *«Одна конфигурация — одно устройство. Для нового устройства выпусти новую настройку в личном кабинете или боте.»* — then asked: how many active links, how to delete, and whether a second device doubles daily charge.

### 14.1 Current user confusion

| Question | User expectation | Current product reality |
|----------|------------------|------------------------|
| How many active links/configs do I have? | A visible count or list | **Not shown** on setup; cabinet list **empty stub** (API gap) |
| How to delete/revoke a link? | Self-service revoke | **No user-facing revoke**; support/admin only |
| Second device → 6.67 ₽ × 2? | Per-device billing | **No** — one `DAILY_RATE`/account/day; multi-key not billed × N |
| Balance ~187 ₽ with 78-year access | Balance should drain daily | **Legacy profile bypasses drain**; UI does not explain |

### 14.2 Exact UI surface and copy

**Primary screen (user report):** **`/setup/` token success state** — not a config manager.

| Element | File | ID / key |
|---------|------|----------|
| Page | `web/portal/setup.html` | `#setup-content.setup-ready` |
| Logic | `web/portal/assets/setup.js` | `showSetupResult()` |
| QR | `#setup-qr` | single canvas |
| Subscription URL | `#setup-link` in `#setup-link-fold` | one URL from trial/recover/token |
| «Скопировать ссылку» | `#btn-copy` | `ru.json` → `setup.copy` |
| «Инструкция по устройству» | `#btn-setup-instruction` | `setup.instruction_link` → `/portal/guide.html` |
| Device rule warning | `#setup-device-rule` | `setup.device_rule` — *«…выпусти новую настройку в личном кабинете или боте»* |
| Device pick (instructions only) | `#setup-device-grid` | links to guide per platform — **not** new config issuance |

**Also relevant:**

| Surface | Files | What it shows |
|---------|-------|---------------|
| **Cabinet** (Mini App / `cabinet.html`) | `portal.js`, `cabinet.html` | `#cabinet-configs-list` — expects `doc.configurations[]` |
| **Cabinet CTA** | `#btn-new-device` | `cabinet.new_device_cta` → bot URL |
| **Bot** | `handlers.py` `menu_get_setup` | Returns **same** setup URL (existing sub), not new Remna key |
| **FAQ** | `ru.json` `cabinet.faq` | Second device → **support** (contradicts `setup.device_rule`) |

**What UI lacks today:**

- Active config **count** (e.g. «Активна 1 настройка»)
- **List** of configs with id, created, expiry, status
- **Revoke/delete** control
- **Replace device** vs **add device** distinction
- **`billing_profile`** / legacy manual access explanation
- Clarification that displayed link is **current** subscription, not a catalog of links

### 14.3 Backend source of truth

| Layer | Location | Notes |
|-------|----------|-------|
| **Local DB** | `vpn_keys` table (`bot_src/database.py`) | `key_id`, `user_id`, `vless_uuid`, `key_email`, `expiry_date`, `created_date` |
| **Remna panel** | `remnawave_api.provision_key()` | One Remna user per `key_email`; subscription URL derived from panel user |
| **Subscription URL cache** | `subscription_resolve.py`, `setup_url_service.py` | Resolves **one** URL per Telegram user (first key / panel lookup) |
| **Cabinet API** | `portal_cabinet.cabinet_snapshot()` | Returns balance, days, daily_rate — **no** `configurations`, **no** `billing_profile`, **no** count |
| **Portal UI (expects more)** | `portal.js` `applyCabinetDoc()` | Reads `doc.configurations`, `doc.billing_profile` — **fields not returned by backend today** → list stays empty |

**What defines “active”:**

- Handlers filter: `expiry_date > now` (`handlers.py` profile/active_keys)
- DB stats: `COUNT(*) FROM vpn_keys WHERE expiry_date > CURRENT_TIMESTAMP` (`database.py`)
- **No** separate `status=revoked` column; row deleted only when Remna sync finds missing remote user (`update_key_status_from_server` → `DELETE`)

**Enforcement:**

| Question | Answer |
|----------|--------|
| Multiple `vpn_keys` rows per account? | **Yes, technically** (`add_new_key` on each trial/purchase/admin action; `get_next_key_number = len(keys)+1`) |
| One active config enforced? | **No** in code — policy only ([`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) PT-06, PROD-004) |
| Device name/platform stored? | **No** on `vpn_keys` row |
| Last used / last connected? | **Not in shop DB** (would be Remna/panel telemetry if available) |
| User-safe revoke/delete API? | **No** |
| Admin revoke path? | Implicit delete on Remna sync miss; **no** documented user/admin «revoke key» flow in bot |

### 14.4 Multi-device billing (read-only confirmation)

| Question | Answer |
|----------|--------|
| Billing unit today | **Per account** (Telegram `user_id`), not per key |
| 6.67 ₽ × N implemented? | **No** |
| Actual charge | `charge_daily_balance_if_due(user_id, DAILY_RATE)` once per UTC day when `access_profile == wallet` |
| Two `vpn_keys` rows today | Still **one** daily debit; `sync_panel_from_balance` uses **`keys[0]`** only |
| Legacy / manual (e.g. expiry ≥2030) | **`legacy` profile → no wallet drain** (see §7) |
| Self-service «new device» before policy fix | **High billing/copy mismatch risk** |

**Product decision required before multi-device:** approve Option B (paid N configs + enforcement + billing change) or stay on Option A.

### 14.5 Safe product options (pilot)

| Option | Summary | Pilot fit |
|--------|---------|-----------|
| **A — MVP strict** (recommended) | One active config/account; «new device» = **replace** via support until safe revoke; **no** extra billing; setup link = **refresh current** sub | **Matches current policy + code** |
| **B — Multi-device paid** | N configs; 6.67 ₽ × N/day; cabinet shows count+cost; revoke required; backend enforcement | **Not ready** — billing + API + Remna lifecycle missing |
| **C — Same URL multi-device** | One sub on many devices | **Contradicts** current copy and fair-use; needs policy reversal |

**Recommendation for current pilot:** **Option A.** Do not ship self-service second config until revoke + policy enforcement exist.

### 14.6 Required cabinet/API fields (later — do not implement in this pass)

Proposed `cabinet_snapshot` extensions for G2-B / device management:

```text
access_profile: wallet | trial | legacy | expired
balance_rub, daily_rate, days_left
active_config_count
billable_config_count        # 0 for legacy/trial; 1 for MVP wallet
active_configs[]:
  - key_id, label, created_at, expires_at, active, platform (if known)
  - subscription_url_masked  # never full secret in list API
  - billable: bool
can_revoke: false            # true only when revoke endpoint exists
can_replace_device: false     # true when replace flow shipped
support_required: true       # MVP default for second device
legacy_access_note: string    # e.g. manual access; balance not draining
```

### 14.7 Proposed copy (later — do not edit `ru.json` now)

| Instead of | Use later |
|------------|-----------|
| «выпусти новую настройку в личном кабинете или боте» | «Скопировать **текущую** ссылку» + «Новое устройство — через поддержку» |
| Silent balance display for legacy | «Баланс не списывается: у вас ручной доступ до …» |
| Implied multi-config | «Активна **1** настройка» or «Дополнительные устройства пока не поддерживаются» |

### 14.8 Backlog items (device/config management)

| ID | Scope | Depends on |
|----|-------|------------|
| **P1-CAB-001** | `billing_profile` + legacy/wallet messaging in cabinet API + UI | G2-B |
| **P1-DEV-001** | Cabinet `active_config_count` + `active_configs[]` read-only from `vpn_keys` + Remna | P1-CAB-001 |
| **P1-DEV-002** | Admin/support revoke: disable Remna user + delete/archive `vpn_keys` row | ops runbook |
| **P1-DEV-003** | Self-service **replace device** (revoke old + issue one new) — not additive multi-device | P1-DEV-002 + product sign-off |
| **PROD-004** | Enforce max 1 active config per account (or explicit N after Option B) | policy decision |
| **P1-BILL-002** | If Option B: `DAILY_RATE × billable_config_count` + tests | product approval only |
| **P2-COPY-DEVICE-001** | Align setup/cabinet/FAQ to chosen option | after P1-CAB-001 truth |
| **P2-UX-GUIDE-001** | Guide button layout (§2) | independent |

### 14.9 No-go before changing copy/UI

- Do not promise «выпусти новую настройку» self-service until **P1-DEV-003** or support path is explicit.
- Do not show config count without **P1-DEV-001** backend fields.
- Do not add revoke button without **P1-DEV-002** Remna+DB lifecycle.
- Do not imply 6.67 ₽ × N until **P1-BILL-002** shipped and tested.
- Do not change legacy owner balance display without **`access_profile: legacy`**.

### 14.10 Suggested next implementation surface

**Order:**

1. **P1-CAB-001** — `billing_profile` + legacy balance explanation (fixes owner 187 ₽ confusion).
2. **P1-DEV-001** — read-only config count/list in cabinet (answers «how many links» without revoke).
3. **P1-DEV-002 + PROD-004** — support/admin revoke + one-config enforcement.
4. **P2-COPY-DEVICE-001** — honest copy after backend truth exists.

**Not next:** multi-device self-service (Option B) or UI-only copy fixes alone.
