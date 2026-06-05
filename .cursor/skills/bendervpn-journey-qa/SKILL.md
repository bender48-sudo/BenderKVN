---
name: bendervpn-journey-qa
description: Full BenderVPN user-journey QA across portal, setup, cabinet, Telegram Mini App and bot flows. Use when asked to QA the product journey, run Playwright smoke across /start/, /setup/, cabinet, referral entry, support paths, or prepare a scenario pass/fail report before/after portal or bot changes. Do not run real payments or mass config issuance without explicit owner approval.
---

# BenderVPN Journey QA

## When to use

- Portal / cabinet / setup visual or flow QA after deploy
- Before merging `product-referral-cabinet-ui-v1` or similar UI branches
- After referral/bot/backend cleanup — **full E2E** including bot callbacks
- Owner asks: «прогони путь пользователя», «journey QA», «smoke воронки»

## When NOT to use (yet)

- Do **not** run full bot/payment/referral E2E while backend WIP is in stash
- Do **not** issue real configs, real payments, or mass notify without approval

## Tools

| Layer | Tool |
|-------|------|
| Browser UI | **Playwright MCP** (preferred) or `python .playwright-review/visual_test.py` |
| Prod smoke | Harmless navigation only — no form submit that creates users |
| Bot callbacks | Code inspection in `bot_src/` — read-only unless task allows bot changes |
| Live URLs | `https://k9x2m1.conntest.xyz:8443` — always cache-bust `?v=<tag>` |

## Safety rules

1. **No real payment** — never complete YooKassa checkout in QA
2. **No repeated real config issuance** — use owner test account only if explicitly approved
3. **No prod data mutation** — no mass notify, no PATCH, no deploy unless task says so
4. **No stash apply** unless owner asks
5. Prod clicks: navigation, accordion expand, copy buttons — OK; destructive actions — stop
6. Capture **full-page screenshots** per scenario in `.playwright-review/screenshots/`
7. If `/setup/api/cabinet` returns 502, report as **backend blocker** — do not fail portal shell if grace UI renders

## Scenarios

### 1. New public visitor

**Entry:** `https://k9x2m1.conntest.xyz:8443/start/?v=qa`

**Steps:**
1. Open `/start/`
2. Check hero, cosmic/glass styling, journey block
3. Check slots counter or honest fallback copy
4. Check Telegram trial CTA and email 24h CTA
5. Open `/setup/` — legal consent checkbox before signup submit

**Expected:**
- Product explanation visible; no technical stubs (`TODO`, `заглушка`, `REQUIRED_SUPPORT_EMAIL`)
- Two clear CTAs; mobile-first layout
- Consent required before config issue

### 2. Referral visitor

**Entry:** `/start/?ref=testinvite&v=qa`

**Steps:**
1. Open with `?ref=` param
2. Check referral welcome block
3. Click Telegram CTA — ref preserved in URL/start param where implemented
4. Read copy — no false «+1 month» unless implemented in `ru.json` / bot

**Expected:**
- Invite state visible; ref note honest
- No invented referral rewards

### 3. Email 24h trial user

**Entry:** `/setup/?v=qa`

**Steps:**
1. Open setup page
2. Enter test email (use disposable / owner-approved only)
3. Accept legal docs checkbox
4. Submit only if task explicitly allows — otherwise stop at form UI check
5. Verify config-ready / QR / graceful error states in copy

**Expected:**
- Glass cosmic setup UI
- Consent gate; path to Telegram registration explained
- QR or copy-link fallback; no raw technical errors as hero

### 4. Telegram Mini App user

**Entry:** `/portal/cabinet.html` inside TG WebView (or `?tid=` smoke)

**Steps:**
1. Open cabinet from bot menu URL
2. Check balance load or graceful inline error (not empty shell)
3. Check configs/devices if API returns data
4. Check action cards + support block

**Expected:**
- Full cabinet shell even if API fails
- TG action grid: setup, guide, topup, invite, support

### 5. Returning browser user (no Telegram identity)

**Entry:** `/portal/cabinet.html?v=qa`

**Steps:**
1. Open in clean browser context (no TG initData)
2. Optionally inject stale `localStorage` email — must still show grace card
3. Check recover fold collapsed by default
4. Expand recover — email path secondary, not main hero

**Expected:**
- «Открой ЛК из Telegram-бота» grace state
- Action cards: Настройка / Инструкция / Статус / Поддержка
- **No** «Войди по email или укажи ID» as main hero

### 6. Setup / config user

**Entry:** `/setup/?v=qa` with valid token if available

**Steps:**
1. Config-ready title when token valid
2. QR renders or fallback message
3. Link in collapsible fold
4. Device cards: iPhone, Android, Windows, Mac

**Expected:**
- `setup-ready` glass block; device grid complete

### 7. Support user

**Entry:** any portal page with `#support-block-mount`

**Steps:**
1. Support block visible
2. Telegram link works (`https://t.me/Bender_KVN_bot`)
3. `message_hint` lists device, channel, what happened, screenshot
4. No `REQUIRED_SUPPORT_EMAIL` if email not configured

### 8. Payment / topup user

**Entry:** bot only — **read-only** unless approved

**Steps:**
1. Inspect bot menu for topup entry
2. Verify copy matches balance model (6,67 ₽/day), not old month tariffs
3. Do **not** complete payment

**Expected:**
- Topup path exists; no broken callback signatures in code review

### 9. Admin / referral audit

**Entry:** admin flows — code review only unless owner session provided

**Steps:**
1. Confirm admin reports not linked from public portal
2. No PII in public `ru.json` or HTML

**Expected:**
- Admin-only surfaces not exposed on `/start/`, `/portal/`

## Execution workflow

```
1. Read allowed file scope for the task
2. Run placeholder grep on web/portal (see Phase 3 in task template)
3. For each scenario: Playwright goto → wait → screenshot → DOM probe
4. Build scenario table
5. List blockers separately (backend 502, missing bot deploy, stash WIP)
6. Propose safe next fixes — portal-only vs bot vs ops
```

## DOM probes (Playwright evaluate)

```javascript
() => ({
  cosmic: document.body.classList.contains('cosmic'),
  grace: !document.getElementById('cabinet-grace')?.classList.contains('hidden'),
  actions: !document.getElementById('cabinet-actions')?.classList.contains('hidden'),
  support: !!document.querySelector('.support-block'),
  accordions: document.querySelectorAll('.cabinet-accordion').length,
  loadError: document.getElementById('load-error')?.classList.contains('hidden') === false,
})
```

## Output format (required)

Return these sections in order:

### 1. Scenario QA table

| Scenario | Entry | Steps (short) | Expected | Actual | Pass/Fail | Blocker | File/function |
|----------|-------|---------------|----------|--------|-----------|---------|---------------|

### 2. Broken buttons

List any dead CTAs with selector + page URL.

### 3. Dead routes

HTTP ≠ 200 or blank shell.

### 4. Copy inconsistencies

Mismatches between `ru.json`, live HTML, bot messages.

### 5. Backend blockers

502 cabinet API, missing webhook, unstaged bot handlers, etc.

### 6. Product decisions needed

Ambiguous expected behavior — ask owner.

### 7. Screenshots path

`.playwright-review/screenshots/<name>.png` per scenario.

### 8. Safe next fix list

Ordered, scoped: `web/portal/**` first; bot/ops only when explicitly allowed.

## Related

- UI/UX rules: `.cursor/rules/vpn-ui-ux.mdc`
- Portal deploy: `ops/deploy-user-portal-lv.ps1` (run only when task allows deploy)
- Incident skill: `.cursor/skills/vpn-incident-tg-only-ru/SKILL.md` — VPN connectivity only, not product journey
