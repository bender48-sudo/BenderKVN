# AUDIT — Telegram access-flow scenarios (S1–S8)

**Date:** 2026-06-10  
**Mode:** Read-only audit + static code trace — no deploy, no prod mutation, no copy/UI changes  
**Branch:** `product-referral-cabinet-ui-v1` @ `fd1136f` (local HEAD = origin)  
**Related:** [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md), [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md), [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md), [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md)

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| Why did two buttons show the same setup screen / subscription link? | For users who **already have a Remna subscription**, every “get setup” path **reuses** the existing subscription URL. No second key is created. |
| Is that a backend bug? | **No** — reuse is intentional (`get_setup_url_for_user` → `resolve_subscription_url` → signed `/setup/?t=…`). |
| Is it a UX/copy bug? | **Yes** — setup page does not say “this is your **current** link”; copy implies a fresh or different access path; “1 сутки” is shown in contexts where Telegram users already have 90-day access. |
| When is a **new** key created? | Only **`get_trial`** (bot, 90d), **`issue_web_trial`** (browser email, 1d), admin/manual provision — **not** `menu_get_setup`, cabinet `/setup/`, or `portal-telegram-setup`. |
| Is 6,67 ₽ × N configs billed? | **No** — one `DAILY_RATE` debit per account per UTC day when `access_profile == wallet`; billing sync uses `keys[0]` only. |

**Pilot policy (Option A — MVP strict) confirmed by code:** one active config per account; existing users see current config; new device = support/admin; “1 сутки” = web/email fallback only; no multi-device billing until designed.

**Verification:** static code audit only this pass. Controlled AMS smoke for `*@bendervpn-smoke.invalid` deferred (not required to answer owner confusion). Owner account not touched.

---

## 2. Why the owner saw the same link

### 2.1 Owner label → canonical copy

Exact strings **«Получить доступ»** / **«Получить доступ на сутки»** are **not** in `ru.json`. Closest canonical labels:

| Owner wording (observed) | Canonical UI copy | Surface |
|--------------------------|-------------------|---------|
| «Получить доступ» | «Как получить доступ» (`setup.title`), «Получить настройку» (bot/cabinet), «Открыть Telegram-бота» | `/setup/`, bot `menu_get_setup`, cabinet `action_setup` |
| «Получить доступ на сутки» | «Временный доступ на 1 сутки» (`buttons.setup_browser`, `cabinet.grace_cta_trial`, `setup.signup_submit`) | Landing, browser cabinet grace, browser `/setup/` email path |

### 2.2 Convergence point

All Telegram “show my setup” flows end here:

```
resolve_subscription_url(telegram_id)
  → panel by telegramId, else newest-expiry vpn_keys row by email
  → portal_links.setup_url_for_sub(sub_url)  // HMAC token, 72h TTL
  → GET /setup/?t=… → verify → showSetupResult(sub_url)
```

**Same underlying `subscriptionUrl`** → same QR and «Скопировать ссылку» even if entry buttons differ.

### 2.3 Where both paths appear together

| Context | TG path button | 1-day button | Same `/setup/` result for existing TG user? |
|---------|----------------|--------------|---------------------------------------------|
| **Browser** `/setup/` (no `?t=`) | Card «90 дней…» → opens **bot** (not setup directly) | Email form → **creates** 1d trial (new user only) | TG user in Mini App: paths **hidden**; auto `loadTelegramSetup` → **reuse** |
| **Browser** `cabinet.html` actions | `action_setup` → `/setup/` | `action_email_access` → **`/setup/`** (same href) | Both links go to same URL; existing TG Mini App session still **reuse** |
| **Browser** cabinet grace block | «Открыть Telegram-бота» | «Временный доступ на 1 сутки» → `/setup/` | Grace visible when account panel hidden |
| **Telegram Mini App** cabinet actions | «Получить настройку» → `/setup/` | **Not shown** in TG action grid | Only one setup CTA |
| **Bot** main menu | «Получить настройку» (`menu_get_setup`) | No 1-day button | Reuse or trial gate |

**Interpretation:** Owner in Telegram/Mini App most likely clicked **«Получить настройку»** (bot or cabinet) and a **1-day-labelled** control from **landing, grace, or browser setup** (or paraphrased the two `/setup/` path cards). Both resolve to **existing subscription** — correct backend, misleading UX.

---

## 3. Button / handler map

### 3.1 Bot (aiogram)

| Label (RU) | `callback_data` / trigger | Handler | Creates new key? |
|------------|---------------------------|---------|------------------|
| «Получить настройку» | `menu_get_setup` | `handlers.menu_get_setup_handler` | **No** — `get_setup_url_for_user` |
| «Начать бесплатный период» (gate) | `get_trial` (via `create_trial_before_setup_keyboard`) | `handlers.trial_period_handler` | **Yes** — `provision_key(..., REMNA_TRIAL_DAYS=90)` + `add_new_key` |
| «Получить бесплатный VPN» (no sub) | `get_trial` | same | **Yes** |
| «Личный кабинет» | WebApp | `telegram_cabinet_webapp_url` | No |
| «Мой VPN» / account (legacy) | `my_account` | Shows balance + same sub via cache | No |

**`menu_get_setup_handler` logic:**

1. If **no keys** and `trial_used == false` → show trial keyboard (must `get_trial` first).
2. Else → `_wizard_setup_url` → setup link message (`MSG_SETUP_LINK`).

Files: `bot_src/keyboards.py`, `bot_src/handlers.py`, `bot_src/user_messages.py`.

### 3.2 Portal / Mini App

| Label | Href / API | Client code | Backend | New key? |
|-------|------------|-------------|---------|----------|
| «Получить настройку» | `/setup/` | `setup.js` `loadTelegramSetup` if Mini App | `POST /setup/api/telegram-setup` → `telegram_setup_for_user` | **No** |
| Token link | `/setup/?t=…` | `fetch(API_VERIFY)` | HMAC verify → `sub_url` | **No** |
| «Временный доступ на 1 сутки» (signup) | form submit | `POST /setup/api/web-trial` | `portal_web_trial.issue_web_trial` | **Yes** (1d, web surrogate uid) |
| «Восстановить настройку» | recover | `POST /setup/api/web-trial-recover` | `recover_web_trial` | **No** |
| Cabinet «Получить настройку» | `/setup/` | `portal.js` `renderCabinetActions` | same as row 1 | **No** |
| Cabinet «Временный доступ…» (browser only) | `/setup/` | same href as setup | Browser may show email path | **Only if new email trial** |

Files: `web/portal/assets/setup.js`, `web/portal/assets/portal.js`, `web/portal/content/ru.json`, `bot_src/webhook_server/app.py`, `bot_src/portal_telegram_setup.py`.

### 3.3 Answers (Step 2 checklist)

1. **«Получить настройку»** — bot inline menu, Mini App cabinet actions, errors page, post-trial bot keyboard.
2. **«1 сутки»** — landing, browser cabinet grace/actions, `/setup/` email card, guide ghost CTA — **not** TG cabinet action grid.
3. **Same handler?** **No** — trial creation (`get_trial` / `web-trial`) vs setup display (`menu_get_setup` / `telegram-setup` / verify token).
4. **Same setup URL intentionally?** **Yes** for display paths — all resolve existing `subscriptionUrl`.
5. **Copy-only difference?** **No** — email path hits different API and can create a **separate** web account; display paths share resolver.
6. **Is «1 сутки» web fallback mislabeled on TG?** **Yes** when shown to users who already completed TG registration — should not appear in TG Mini App actions (today it does not); browser cabinet/grace still shows it.
7. **Message when user already has config?** Bot: `MSG_SETUP_LINK` + URL button. Setup: `config_ready_title` / QR — **no “existing link” flag**.
8. **Message when new?** Bot: trial gate or trial success with expiry. Web email: signup success with `expire_at`. Setup TG error: `error_no_subscription_new`.

---

## 4. Setup screen map

File: `web/portal/setup.html`, `web/portal/assets/setup.js`, `ru.json` → `setup.*`.

| Question | Answer |
|----------|--------|
| Knows new vs existing link? | **No** — `showSetupResult(url)` only receives `sub_url`; no `recovered` / `created` flag from TG path. Web recover sets `recovered: true` in API but client does not surface it in hero copy. |
| Knows trial / wallet / legacy / expired? | **No** — verify response is `{ ok, sub_url }` only. No `billing_profile`, expiry, or access kind. |
| Knows active config count? | **No** |
| Distinguishes TG 90d vs email 1d? | **No** on result screen — same QR UI. Email signup success may show `success_trial` + `expire_at` once. |
| Misleading device copy? | **Yes** — `setup.device_rule`: *«…выпусти новую настройку в личном кабинете или боте»* — **no self-service second config** in bot/cabinet today. FAQ correctly says support for second device. |

**«Инструкция по устройству»:** link to `/portal/guide.html?device=…` from device grid after setup result — does not affect subscription.

**Mini App behavior:** on `/setup/` without token, `loadTelegramSetup` hides dual paths, POSTs `telegram_id`, redirects to signed URL — user never sees browser dual-path UI inside Mini App.

---

## 5. Backend source of truth

### 5.1 Data model

| Store | Role |
|-------|------|
| `users` | `telegram_id`, `balance`, `trial_used`, `agreed_to_terms`, … |
| `vpn_keys` | `user_id`, `key_email`, `vless_uuid`, `expiry_date` — **multiple rows allowed**, no hard max |
| `web_trial_claims` | email ↔ web surrogate `web_user_id`, bind token, optional `telegram_id` |
| Remna panel | `subscriptionUrl`, `expireAt`, `telegramId` |

**Key selection:**

| Function | Selection rule |
|----------|----------------|
| `resolve_subscription_url` | Panel by `telegramId`; else iterate `vpn_keys` **newest `expiry_date` first** |
| `sync_panel_from_balance` | **`keys[0]`** — `get_user_keys` orders **`key_id ASC`** (oldest row) |
| `menu_get_setup` / setup page | Via `resolve_subscription_url` (newest expiry path) |

**Anomaly (S7):** if multiple active keys exist, **setup may show newest sub** while **daily billing sync updates oldest email** — documented risk, not exercised in prod audit.

### 5.2 Trial duration env

| Env | Default | Used by |
|-----|---------|---------|
| `REMNA_TRIAL_DAYS` | 90 | Bot `get_trial` |
| `WEB_TRIAL_DAYS` | 1 | `issue_web_trial` |
| `DAILY_RATE` | 6.67 | `balance_billing.charge_daily_balance_if_due` |

### 5.3 When keys are created vs reused

| Event | New Remna user/key? | Notes |
|-------|---------------------|-------|
| Bot `get_trial` | **Yes** | Sets `trial_used`; email `user{tg}-key{n}-trial@…` |
| Web `issue_web_trial` | **Yes** | Surrogate negative `web_user_id`; `web{n}-key{m}-trial@…` |
| Web `recover_web_trial` | **No** | Returns existing sub if not expired |
| `menu_get_setup` | **No** | Trial gate if no keys |
| `telegram_setup_for_user` | **No** | Explicit docstring |
| `get_setup_url_for_user` | **No** | Cache + sign token only |
| Web→TG bind `merge_web_user_to_telegram` | **No new key** | Moves `vpn_keys` rows; fails if **both** sides have keys |
| Top-up + daily job | **No new key** | Extends/charges against existing `keys[0]` when wallet profile |

### 5.4 `access_profile` (`subscription_profile.py`)

| Profile | Billing | Shown in cabinet API today? |
|---------|---------|-------------------------------|
| `legacy` | No daily drain | **No** — `portal_cabinet.cabinet_snapshot` omits `billing_profile` |
| `wallet` | 6.67 ₽/day/account | **No** (UI expects field) |
| `trial` | No balance debit | **No** |
| `silent` | No | **No** |

### 5.5 Cabinet API gap

`portal_cabinet.cabinet_snapshot` returns: `balance_rub`, `days_left`, `daily_rate`, `telegram_bound`, `source`.

**Does not return:** `billing_profile`, `configurations[]`, `active_config_count`, legacy flag, trial expiry, link freshness.

`portal.js` `applyCabinetData` **already handles** `billing_profile` and `configurations[]` if present — backend never sends them.

---

## 6. Scenario matrix (S1–S8)

| Scenario | Entry button/path | User pre-state | Expected policy | Actual code path | Actual result | New key? | Reuse key? | Duration | Balance effect | UX shown | Risk | Recommendation |
|----------|-------------------|----------------|-----------------|------------------|---------------|----------|------------|----------|----------------|----------|------|----------------|
| **S1** New TG user | Bot «Получить настройку» | No user / no keys | 90d trial on first activation | `menu_get_setup` → trial keyboard → `get_trial` | New key + trial message | **Yes** (after trial click) | — | 90d | None during trial | Trial success + QR buttons | Low | OK; gate is correct |
| **S1b** | `get_trial` directly | Same | 90d | `provision_key` + `add_new_key` | Active sub | **Yes** | — | 90d | None | Bot inline QR/copy | Low | OK |
| **S2** Web 1d → TG | Email signup then bind | Web surrogate + claim | Bind merges; **one** config; TG keeps web key | `issue_web_trial` → `/start bind_*` → `merge_web_user_to_telegram` | Keys moved to TG id; panel `telegramId` patched | **Yes** (web), then merge | Reuse web key | 1d panel until extended in bot | Web balance merged | Bind messages + bot menu | **High** if bind fails (G2-A FAIL) | Fix bind entry before relying on S2 |
| **S2b** | TG user submits email on `/setup/` | TG already has key | Should not create second account | `issue_web_trial` (new email) | **New surrogate** + second key possible | **Yes** (separate web uid) | TG key unchanged | 1d on web row | Separate | Two parallel accounts if user tries | **Medium** | Hide email path for bound TG users |
| **S3** Active trial TG | «Получить настройку» + any setup link | Active trial key | Show **current** link; no new key | `get_setup_url_for_user` | Same `subscriptionUrl` | **No** | **Yes** | Unchanged (panel expiry) | None | Generic “настройка готова” | **UX** — looks like new issue | Add “текущая ссылка” + expiry |
| **S3b** | «1 сутки» (browser) | Active TG trial | N/A for TG user | Browser `/setup/` email or cabinet email CTA | Mini App: still reuse TG sub; browser email: new web trial if new email | Browser only: **Yes** if new email | TG: reuse | — | — | Confusing dual messaging | **Medium** | Hide 1d CTAs for TG sessions |
| **S4** Paid wallet | Both setup buttons | Balance > 0, active key | Same config; billing 6.67/day **once** | Same resolver + `access_profile=wallet` scheduler | Same link | **No** | **Yes** | Panel synced from balance | Daily debit | “Доступ активен” (cabinet guess) | Low billing UX | P1-CAB-001 `billing_profile` |
| **S5** Expired / stopped | «Получить настройку» | Expired key, trial_used | Top-up renew; no free re-trial | Resolver may fail → `subscription_unavailable` | Error messages point to top-up | **No** (unless admin) | Stale sub if panel not synced | — | No debit if wallet empty | `subscription_expired` copy in API | Medium | Clear expired state on setup page |
| **S6** Legacy/manual | Setup buttons | expiry ≥2030 / legacy profile | No billing drain; show legacy status | Same link resolver; `access_profile=legacy` skips daily charge | Same link | **No** | **Yes** | Far future | Balance static | No legacy badge anywhere | **Trust** | P1-CAB-001 legacy label |
| **S7** Multiple `vpn_keys` | Setup | >1 row (anomaly) | Policy: one active | Newest expiry for sub; `keys[0]` for billing | One link in UI | **No** on setup click | **Yes** (which key ambiguous) | Billing vs display may diverge | Single daily charge | One QR only | **Medium** | P1-DEV-001 count + enforce PROD-004 |
| **S8** TG user + «1 сутки» button | Browser grace/cabinet/landing | TG registered | **Should not apply** | Email CTAs still visible in **browser** surfaces | Same `/setup/` or new web trial | Only if email trial submitted | TG setup: reuse | — | — | **UX bug** — wrong audience | **High** copy | Hide email/grace 1d when `telegram_id` known |

### 6.1 Verification method per scenario

| Scenario | Method |
|----------|--------|
| S1 | Static + optional smoke `*@bendervpn-smoke.invalid` |
| S2 | Static; bind path **requires** G2-A fix + controlled smoke |
| S3–S6 | Static (owner-like S6: read-only, **do not mutate owner**) |
| S7 | Static; prod anomaly test **not safe** without smoke isolation |
| S8 | Static UI trace |

---

## 7. Billing / config implications

| Topic | Finding |
|-------|---------|
| Second link on setup click | **Never billed** — no new key |
| 6.67 × 2 | **Not implemented** — one charge per UTC day per account in wallet profile |
| Multi-key rows | Possible in DB; **not** reflected in UI count |
| Self-service second device | **Not implemented** — copy over-promises |
| TG bind + both have keys | `merge_web_user_to_telegram` → `both_have_keys` error |

---

## 8. UX / copy mismatches

| Copy | Says | Backend truth |
|------|------|---------------|
| `setup.device_rule` | Self-issue new config in cabinet/bot | Support/admin only |
| `setup.config_ready_title` | «Твоя настройка готова» | May be **existing** config |
| Dual «90d / 1d» on browser surfaces | Two access products | For existing TG user, both lead to **same** sub (Mini App) or misleading parallel paths (browser) |
| Cabinet `configs_empty` | «Пока одна основная настройка» | API does not list configs — empty state always |
| Bot «Получить настройку» | Sounds like issuance | **Display** existing subscription |
| FAQ vs setup device rule | FAQ: support for 2nd device | Setup: self-service — **internal inconsistency** |

---

## 9. What is safe now (product behavior)

- Reusing one subscription URL for an active account is **correct** and avoids accidental multi-key proliferation.
- Trial gate before first setup (`menu_get_setup` without keys) is **correct**.
- Web 1-day trial isolated to browser API is **correct** for PT-02 fallback.
- Single daily wallet debit matches PT-08/PT-09 policy intent.
- Legacy bypass of daily billing matches owner balance observation (see device/balance audit).

---

## 10. What is broken / blocked

| Item | Status |
|------|--------|
| TG web-trial bind (S2 completion) | **G2-A FAIL** — see [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md) |
| Cabinet `billing_profile` / config list | API missing fields UI expects |
| Honest setup/cabinet copy | Over-promises self-service second config |

---

## 11. What is not implemented

- `active_config_count` / `configurations[]` in cabinet API (**P1-DEV-001**)
- Self-service new device / revoke (**P1-DEV-002**, **PROD-004**)
- Multi-device billing (**P1-BILL-002** / OD-03)
- Hide web-only 1d CTAs for authenticated TG Mini App users
- Setup page state: `existing_link`, `expires_at`, `access_kind`

---

## 12. Required product decisions

1. Confirm **Option A (MVP strict)** as pilot — audit supports it.
2. When bind works: after merge, is web 1d expiry **extended to 90d** in bot or keep until top-up? (Code today: **no automatic extension** on bind alone.)
3. Should browser cabinet **drop** «1 сутки» action when session is Telegram Mini App? (**Recommended: yes.**)
4. Second device: remain **support-only** until OD-03 / multi-device billing approved?

---

## 13. Recommended backlog order

1. **P1-CAB-001** (`DEC-IMPL-013`) — `billing_profile`, legacy/trial/wallet in `cabinet_snapshot`
2. **P1-DEV-001** — read-only `active_config_count` + list
3. **P2-COPY-DEVICE-001** — honest setup/cabinet copy after API truth
4. **P2-UX-GUIDE-001** — guide button layout (orthogonal, see device-links audit §2)
5. **G2-A** — fix TG bind entry before marketing email→TG path

---

## 14. No-go before implementation

- Do not add «выпусти новую настройку» self-service without **P1-DEV-003**
- Do not change setup copy alone without **P1-CAB-001** + **P1-DEV-001**
- Do not run prod billing experiments or create multi-key anomalies on real users
- Do not claim live verification of owner session without owner Telegram retest

---

## 15. Key code references

| Concern | File / symbol |
|---------|---------------|
| Setup URL reuse | `bot_src/setup_url_service.py` → `get_setup_url_for_user` |
| TG setup API | `bot_src/portal_telegram_setup.py` → `telegram_setup_for_user` |
| Sub resolution | `bot_src/subscription_resolve.py` → `resolve_subscription_url` |
| Bot menu setup | `bot_src/handlers.py` → `menu_get_setup_handler`, `trial_period_handler` |
| Web 1d trial | `bot_src/portal_web_trial.py` → `issue_web_trial`, `recover_web_trial` |
| Web→TG bind | `bot_src/web_tg_bind.py` → `merge_web_user_to_telegram` |
| Cabinet snapshot | `bot_src/portal_cabinet.py` → `cabinet_snapshot` |
| Billing | `bot_src/balance_billing.py`, `bot_src/subscription_profile.py` |
| Mini App setup client | `web/portal/assets/setup.js` → `loadTelegramSetup`, `showSetupResult` |
| Cabinet client | `web/portal/assets/portal.js` → `renderCabinetActions`, `applyCabinetData` |

---

*End of audit — implementation not started.*
