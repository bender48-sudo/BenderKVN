# BenderVPN Product Quality Plan

**Status:** portal journey complete · product policy locked → **`docs/BENDERVPN-PRODUCT-POLICY.md`**
**Branch:** `product-referral-cabinet-ui-v1`
**Last updated:** 2026-06-09  
**Owner loop:** product-quality (portal copy) done; next = Phase 1 product-logic alignment per policy v1

---

## 1. Current product state

### Fixed (verified live)

| Area | State |
|------|--------|
| `/start/help/errors/` route | Repaired (PHASE 1) |
| Capacity console 404 | Frontend skips fetch when API disabled (PHASE 1 + UX-207) |
| Broken hero counter | Hidden; badge «Доступ по приглашению · лимит 30 000» (UX-207) |
| `/status` visual language | Portal cosmic/glass + footer (UX-201) |
| Status Russian copy | No English ops strings (UX-202) |
| Setup duplicate steps | Single journey block (UX-203) |
| Landing journey 90d/1d | Step 1 explicit (UX-204) |
| Support `/id` hint | Global support block (UX-205) |
| Legal preliminary banner | Removed (UX-206) |

### Commits ahead of origin (as of plan creation)

| Hash | Message |
|------|---------|
| `6ceadcf` | ux(portal): align status support and setup copy |
| `cd15959` | ux(portal): hide capacity counter when live source is unavailable |

Base on origin: `9f248d3` fix(portal): repair errors route and capacity fallback

### Remaining semantic issues (from audit 2026-06-09)

See prioritized backlog below (SEM-001 … UX-212).

---

## 2. Product truths

| Truth | User-facing rule |
|-------|------------------|
| Telegram trial | **90 days** — main path |
| Email access | **1 day only** — fallback to reach Telegram |
| Invite model | Камерный VPN, по приглашениям |
| Capacity limit | **30 000** — positioning; no fake live counter |
| VPN profile | **BenderVPN Auto** — no manual server/node picking |
| Forbidden copy | No turbo, wl-direct, wl-routed, NL/LV/9443 |
| Device rule | One config = one device (unless backend proves otherwise) |
| Referral bonus | Must not be promised unless implemented |
| Support | Telegram bot; `/id` for Telegram ID |
| Tone | Clear, human, calm, premium; no operator/internal language |

---

## 3. Client journey map

```
Реферальная ссылка /start/?ref=…
        ↓
Лендинг: камерный VPN · invite-only · лимит 30 000
        ↓
┌─ Telegram открывается ──→ Бот → trial 90 дней → настройка/QR
│                                    ↓
└─ Telegram заблокирован ──→ /setup → email 1 сутки → QR/ссылка
                                    ↓
                              Happ + BenderVPN Auto
                                    ↓
                              Зайти в Telegram → завершить в боте
                                    ↓
Инструкция /portal/guide.html
                                    ↓
Личный кабинет (бот → Mini App): баланс, конфиги, пополнение
                                    ↓
Проблема → /start/help/errors/ или поддержка (устройство, /id)
                                    ↓
После trial → 6,67 ₽/день с баланса · пополнение в боте
```

---

## 4. Persona map

| Persona | Entry | Success criteria |
|---------|-------|------------------|
| **A. New user from friend** | `/start/?ref=` | Understands product, invite-only, 90d vs 1d, trusts enough to click TG |
| **B. Telegram blocked** | `/setup` | Understands 1-day temp access → VPN → Telegram |
| **C. Bot / Mini App cabinet** | Bot → Mini App | Balance, configs, trial days, one device, topup path clear |
| **D. Browser cabinet** | `/portal/cabinet.html` | Graceful fallback; no false promise of balance in browser |
| **E. Happ install** | `/portal/guide.html` | App, import, Auto, per-platform steps |
| **F. Problem / support** | errors + support block | Self-service first; knows what to send + `/id` |
| **G. Payment / topup** | cabinet + terms | 6,67 ₽/day after trial; no trial/balance contradiction |

---

## 5. Prioritized backlog

### P0 — none open

### P1 — conversion / trust blockers

| ID | Problem | Desired behavior | Files | Deploy |
|----|---------|------------------|-------|--------|
| **P1-1 / SEM-001** | Browser cabinet headline promises balance/configs; grace hides data | Browser: explicit Mini App path + what browser page offers; TG: keep full cabinet copy | `ru.json` `cabinet.*`, `portal.js` `renderCabinet()` | portal LV |
| **P1-2 / SEM-002** | Terms «пробный период» ambiguous (90d vs 1d) | Legal text distinguishes Telegram 90d vs email 1d | `legal/terms.html` | portal LV (legal scp) |

### P2 — conversion / trust

| ID | Problem | Files |
|----|---------|-------|
| **P2-1 / SEM-003** | Landing too long; hero/journey/why-limited/folds repeat | `ru.json`, `index.html`, `portal.js` |
| **P2-2 / SEM-004 + UX-210** | tg-blocked «Получить настройку» vs CTA «Временный доступ на 1 сутки» | `ru.json` `telegram_blocked` |
| **P2-3 / SEM-005** | Cabinet grace lacks Mini App explanation | `ru.json` `cabinet.grace_*` |
| **P2-4 / SEM-006** | invite_model_note internal tracking tone | `ru.json` `home.invite_model_note` |
| **P2-5 / SEM-007** | FAQ support answer omits `/id` | `ru.json` `faq.items` |
| **P2-6 / SEM-008** | Setup recover fold hidden without teaser | `setup.html`, `ru.json`, `setup.js` |
| **P2-7** | Phone field copy too alarming | `ru.json` `signup_phone_*` |

### P3 — polish / a11y

| ID | Problem |
|----|---------|
| **P3-1 / SEM-009** | English «trial» in RU UI |
| **P3-2 / SEM-010** | events-card noise on healthy cold landing |
| **P3-3 / UX-211** | Guide «← Кабинет» for non-cabinet entrants |
| **P3-4 / UX-212** | Hidden empty-label buttons |
| **P3-5 / UX-209** | Referral not on support/footer TG links |

---

## 6. Backlog item template (acceptance)

### P1-1 / SEM-001 — Browser cabinet headline

- **User impact:** Browser user expects balance; sees empty grace → distrust.
- **Acceptance:**
  - [ ] `/portal/cabinet.html` in browser: subline does not promise visible balance/configs
  - [ ] Copy states full LK opens from Telegram bot
  - [ ] Browser offers: temp access, guide, support
  - [ ] Mini App path unchanged (balance visible when `initData` present)
- **Checks:** `json.tool ru.json`, `node --check portal.js`, forbidden-copy rg
- **Deploy:** `deploy-user-portal-lv.ps1`

### P1-2 / SEM-002 — Legal trial distinction

- **User impact:** User may think email = 90-day trial.
- **Acceptance:**
  - [ ] terms.html §1 or §2 states Telegram 90 days vs email 1 day
  - [ ] No contradiction with `/setup` or landing
- **Checks:** visual read of terms; forbidden-copy rg
- **Deploy:** legal scp if not in deploy script

---

## 7. Do not touch

- Billing logic, YooKassa, Remna provisioning
- Database schema, VPN routing, payment logic, config issuing
- Referral gate logic, stash, `deploy-node.sh`
- Ops patch scripts unrelated to portal/status
- Production data mutation
- Fake capacity numbers

---

## 8. Release sequence

| Batch | Scope | Commit message (suggested) |
|-------|--------|--------------------------|
| **Batch 1** | P1 only (SEM-001, SEM-002) | `ux(portal): clarify cabinet fallback and access terms` |
| **Batch 2** | P2 copy/IA (SEM-003–008, phone) | `ux(portal): tighten onboarding copy and support guidance` |
| **Batch 3** | P3 polish/a11y | `ux(portal): polish guide navigation and accessibility` |
| **Batch 4** | Technical VPN architecture audit | separate runbook |
| **Batch 5** | Security / performance / reliability | phase 8 backlog |

---

## 9. Definition of Done

- [ ] No open P0/P1 in backlog
- [ ] All primary personas pass semantic audit
- [ ] No false promises (trial, bonus, capacity, balance in browser)
- [ ] No broken routes (`/start/help/errors/`, legal, status)
- [ ] No forbidden copy; no «Количество мест обновляется» in hero
- [ ] No default blue links; no console 404 on capacity when API off
- [ ] Live screenshots per batch saved
- [ ] Scoped commits; deploy verified on LV
- [ ] Push only after Batches 1–3 live-verified

---

## 10. Open questions (owner decision)

**Resolved in `docs/BENDERVPN-PRODUCT-POLICY.md` v1 (2026-06-09).** Remaining deferred items: OD-01 … OD-10 in policy §11.

| Question | Resolution |
|----------|------------|
| Real capacity source | Hidden badge; 30k = active configs; public API deferred (OD-06) |
| Referral bonus | No bonus at MVP; fix attribution; future small time credit only (OD-02) |
| One-device enforcement | One config/account; support-only new device; HWID Phase 3 |
| Support email | TG-only for pilot; required before partner scale (policy §9) |
| Legal final review | Still open — reconcile REG-001 in Phase 2 (OD-09) |
| Paid/topup after trial | 6,67 ₽/day; 200 ₽ ≈ 30 days; trial skips balance debit |

---

## Execution log

| Phase | Date | Result |
|-------|------|--------|
| A — Git stabilize | 2026-06-09 | 2 commits ahead; UX-207 committed; no uncommitted portal changes |
| B — This plan | 2026-06-09 | Created |
| C — Batch 1 | 2026-06-09 | `7ffe7c5` cabinet fallback + legal 90d/1d |
| D — Batch 2 | 2026-06-09 | `a54f7a2` onboarding copy, support /id, recover teaser |
| E — Batch 3 | 2026-06-09 | `19678fa` guide nav, events-card hide, a11y labels |
| F — Re-audit | 2026-06-09 | No P0/P1; see audit summary below |
| G — Push | 2026-06-09 | `3a9fa73` two-path landing; synced to origin |
| H — Product audit | 2026-06-09 | Full audit complete; journey good enough |
| I — Decision workshop | 2026-06-09 | Owner decisions captured |
| J — Product policy v1 | 2026-06-09 | `docs/BENDERVPN-PRODUCT-POLICY.md` |
