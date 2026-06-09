# AUDIT — Device links, balance display, and instruction UI

**Date:** 2026-06-09 (verification pass)  
**Mode:** Read-only audit — no code, billing, or UI changes  
**Branch context:** `product-referral-cabinet-ui-v1` (local ahead of origin; see final report)  
**Related:** [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md), [`POSTDEPLOY-2026-06-10-P1-REF-001.md`](POSTDEPLOY-2026-06-10-P1-REF-001.md)

---

## 1. Executive summary

| Area | Finding | Severity |
|------|---------|----------|
| TG bind (P1-REF-001 §9) | **Still FAIL** — `p1bind-` claim unbound; no `funnel_bot_start` / `web_tg_bind` actions in AMS DB | **P1 gate blocker** |
| Device instruction UI | Likely **visual-only** CSS mismatch on guide/setup pages (inline store button vs block buttons) | P2 UX |
| New device journey | **Policy = support-only**; copy in setup/cabinet **over-promises** self-service second config | P1 product truth |
| Balance display | Stored `users.balance`; owner **186.66 ₽** stable ~2 weeks is **consistent with legacy panel bypass** after two daily charges | P1 trust/clarity |
| Multi-config billing | **6.67 ₽ × N not implemented** — one `DAILY_RATE` debit per account per UTC day regardless of key rows | Documented MVP gap |

**Recommendation:** Do not start multi-device or billing “fixes” until product decision + G2-B cabinet truth. Close TG bind with a **clean test Telegram account** (no existing keys) before P1-REF-002.

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
