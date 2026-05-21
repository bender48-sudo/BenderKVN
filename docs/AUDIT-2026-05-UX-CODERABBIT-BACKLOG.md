# UX backlog — CodeRabbit + наши аудиты (2026-05)

Источники: промпт `CODERABBIT-AUDIT-PROMPT-2026-05-USER-FLOWS.md`, `AUDIT-CLIENT-UX-2026-05.md`, `AUDIT-USER-FLOWS-2026-05.md`, сессия правок ЛК/меню.

**Статус:** ☐ открыто · ✅ сделано · 🔄 в работе

---

## P0 — ломает доверие / путь

| ID | Задача | Где | Verify | Статус |
|----|--------|-----|--------|--------|
| Q-UX-001 | `get_setting` import в `admin_handlers.py` | admin_handlers | admin guide nb step 1 | ✅ |
| Q-UX-002 | `smoke_email_web`: реальный POST `/setup/api/web-trial`, не `ok: True` | admin_flow_test.py | smoke / curl | ☐ |
| Q-UX-003 | Copy: TG trial ~3 мес vs web 1 день — явно в UI | ru.json, handlers, wizard | бабушка-тест | ☐ |
| Q-UX-004 | Убрать jargon: `inbound`, `pull подписки` | user_messages.py | grep | ☐ |
| Q-UX-005 | ЛК Mini App: карточка HIT-style (статус, 3 CTA) | cabinet.html, portal.js | TG cabinet | 🔄 |
| Q-UX-006 | «Мой VPN» → разделить настройку / аккаунт | keyboards.py | главное меню | ✅ |

---

## P1 — трение / путаница

| ID | Задача | Где | Verify | Статус |
|----|--------|-----|--------|--------|
| Q-UX-011 | Orphan handlers: убрать или вернуть кнопки | handlers.py | grep callback | ☐ |
| Q-UX-012 | После trial ≤4 кнопки | keyboards trial_success | после get_trial | ☐ |
| Q-UX-013 | Одна точка «Помощь» vs «Подключить» | keyboards main | меню новичка | ✅ |
| Q-UX-014 | Ошибки панели: inline «Написать в поддержку» | handlers, user_messages | симуляция down | ☐ |
| Q-UX-015 | `show_referrals` = invite_friend | handlers.py | рефералка | ✅ |
| Q-UX-016 | WIZARD_STUCK URL на `/setup/` | vpn_setup_wizard.py | wizard stuck | ✅ |
| Q-UX-017 | `menu_help` + `setup_url` | handlers menu_help | помощь с ключом | ✅ |
| Q-UX-018 | Админ прод-сим вместо demo-only | admin_handlers | ADMIN-FLOW-PROD-REPLAY | ☐ |
| Q-UX-019 | QR на portal devices без localStorage | portal.js | /portal/#device | ☐ |
| Q-UX-020 | Скрыть turbo/wl в copy для trial | vpn_setup_wizard CONFIG_STEP | текст мастера | ☐ |

---

## Уже закрыто (false positives для Rabbit)

- admin_flow_smoke_all HTML + timeout
- setup.js `s.invalid_token`
- show_main_menu parse_mode HTML
- keyboard stubs → полные функции (Claude)
- contact_support → URL кнопка

---

## Порядок работ (предложение)

1. **Q-UX-005** ЛК v2 — согласование `CABINET-UX-REFERENCE-HIT-2026-05.md`
2. **Q-UX-018** админ прод-сим
3. **Q-UX-003, 004, 012, 002** — один PR «copy + smoke + trial keyboard»
