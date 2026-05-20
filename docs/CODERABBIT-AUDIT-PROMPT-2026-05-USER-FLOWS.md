# CodeRabbit — аудит UX / флоу / кнопки бота (2026-05)

**Когда:** после правок admin «Тест флоу», диагностики, `/setup/`.  
**Цель:** полная диагностика **логики флоу**, **всех кнопок** (пользователь + админ), **дружелюбности**, **копирайтинга**, **понятности** — не security (для security см. `CODERABBIT-AUDIT-PROMPT-2026-05-PHASE7.md`).

**Контекст агента (уже найдено — проверьте и расширьте):**
- `docs/AUDIT-USER-FLOWS-2026-05.md` — матрица кнопок, 3 флоу, баги
- `docs/AUDIT-CLIENT-UX-2026-05.md` — «дед-тест», 2 кнопки до VPN
- `docs/USER-FLOW-JOURNEY.md` (если есть) — продуктовый journey

---

## Промпт (скопировать в CodeRabbit / PR comment)

```
Repo: BenderVPN — commercial VPN bot + web portal (/setup/, /portal/, Mini App).

LANGUAGE: Review UX/copy in Russian (ru.json, bot messages). Report in Russian.

MUST READ FIRST (agent baseline — validate, extend, disagree where wrong):
- docs/AUDIT-USER-FLOWS-2026-05.md
- docs/AUDIT-CLIENT-UX-2026-05.md

THREE USER FLOWS (end-to-end logic + every button destination):

A) Telegram NEWBIE: /start → agree_to_terms → main menu (no sub) → get_trial OR connect_vpn wizard OR menu_help
B) Telegram SUBSCRIBER: main menu (active key) → WebApp cabinet, connect_vpn, show_topup, my_account
C) EMAIL/WEB: browser /setup/ → POST /setup/api/web-trial → verify ?t= → Happ → bind TG ?start=bind_*

ADMIN MIRROR: open_admin_panel → admin_flow_test_menu → guides (admin_flow_g_nb_*, ex_*, web_*) + admin_flow_smoke_all diagnostics

PRIMARY FILES (grep every callback_data → handler):
- bot_src/keyboards.py — ALL inline buttons
- bot_src/handlers.py — user_router callbacks
- bot_src/admin_handlers.py — admin_router, admin flow guides, smoke
- bot_src/admin_flow_guide.py, bot_src/admin_flow_test.py
- bot_src/user_messages.py, bot_src/vpn_setup_wizard.py
- web/portal/assets/setup.js, portal.js, web/portal/content/ru.json
- web/portal/setup.html, cabinet.html
- bot_src/portal_cabinet.py, portal_telegram_setup.py, portal_web_trial.py, web_tg_bind.py

KNOWN FIXES IN THIS PR (do not re-report as open unless regression):
- admin_flow_smoke_all: HTML parse_mode, 30s timeout, error messages
- setup.js: invalid token used undefined `s` → content.setup.invalid_token
- show_main_menu: parse_mode HTML

SCOPE — FULL UX / PRODUCT REVIEW:

1) BUTTON INVENTORY
   - Build table: button label (RU) | callback_data or URL | handler function | expected next screen | dead-end / orphan / duplicate?
   - Include ALL admin_* and admin_flow_* callbacks
   - Flag: two buttons same callback (e.g. duplicate «Помощь»), misleading labels, buttons that only show alert in admin guide vs real user action

2) FLOW LOGIC (3 flows + admin)
   - Step count to «VPN works» for non-technical user («дед-тест»)
   - Dead ends, loops, back buttons that lose state
   - Trial: TG «3 месяца» vs web WEB_TRIAL_DAYS=1 — consistency and user trust
   - get_trial: trial_used before provision success?
   - Stale Telegram inline keyboards after deploy (document as UX pitfall if no code fix)

3) COPYWRITING & CLARITY (RU)
   - Tone: friendly vs bureaucratic; jargon (SNI, inbound, sub_url) exposed to users?
   - Contradictions between bot, ru.json, admin guide text
   - CTA hierarchy: is there ONE obvious next step per screen?
   - Post-trial message: too many buttons? (8+ reported)

4) FRIENDLINESS / ERROR STATES
   - What user sees on: panel down, trial already used, invalid setup token, bind failed, payment cancelled
   - Empty/generic errors vs actionable («что делать дальше»)
   - menu_help vs connect_vpn — same intent?

5) WEB / MINI APP
   - btn-open-happ: HTTPS sub vs happ:// deep link
   - setup journey steps vs bot wizard alignment
   - cabinet WebApp: tid in URL, bind flow copy

6) ADMIN «ТЕСТ ФЛОУ»
   - Do guides truthfully simulate user path?
   - smoke_email_web marks API ok without HTTP probe — misleading?
   - admin merge keyboards (ex guide step 1) — Telegram edit failures?

DELIVERABLES:

| Section | Content |
|---------|---------|
| Flow scores | 1–10 for Flow A, B, C, Admin tools — with one-line rationale |
| Button matrix | Markdown table (label → handler → OK/BUG/CONFUSING) — top 40 issues max |
| Copy issues | P0 confusing / P1 polish — quote exact RU strings + file:line |
| Logic bugs | P0 broken path / P1 friction — file:line + repro steps |
| «Дед-тест» | Min steps today vs ideal 2-button path — gap list |
| Recommendations | Max 20 actionable items (Q-UX-001…), each: user story + file hint + verify (manual step or smoke name) |
| False positives | What agent audit already fixed — do not duplicate |

Constraints:
- No vault/secrets; no drive-by refactors
- Prefer product/UX findings over security (separate audit exists)
- Be harsh on duplicate buttons, lying diagnostics greens, and trial copy mismatch
```

---

## Как запустить CodeRabbit

1. **PR:** открыть PR с этой веткой → в описании PR вставить блок промпта выше + ссылку на `AUDIT-USER-FLOWS-2026-05.md`.
2. **Или:** в UI CodeRabbit → Full review → вставить промпт.
3. **Review type:** выбрать **product / UX** (не security-only).

---

## После ответа CodeRabbit

1. Сохранить сырой вывод → `docs/AUDIT-2026-05-USER-FLOWS-CODERABBIT.md`
2. Валидация: сверка callback → handler в коде; отсечь дубли из agent audit
3. Новые UX-задачи → `docs/USER-FLOW-BACKLOG.md` или `COMMERCIAL-BACKLOG.md` § product

**Verify:** ручной чеклист §4 в `AUDIT-USER-FLOWS-2026-05.md` + `python ops/test_admin_flow_test.py`
