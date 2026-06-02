## Summary

Подготовка **полного UX-аудита CodeRabbit**: три пользовательских флоу (TG новичок, подписчик, email/web), **все кнопки бота включая админские**, дружелюбность, копирайт, понятность пути.

Базовый контекст для ревьюера уже в репо:
- `docs/AUDIT-USER-FLOWS-2026-05.md` — матрица кнопок, баги, чеклист
- `docs/AUDIT-CLIENT-UX-2026-05.md` — «дед-тест», 2 кнопки до VPN
- `docs/CODERABBIT-AUDIT-PROMPT-2026-05-USER-FLOWS.md` — **полный промпт для CodeRabbit**

Технические фиксы в PR (не дублировать как открытые без регрессии):
- Диагностика `admin_flow_smoke_all`: HTML parse_mode, таймаут 30 с, ошибки пользователю
- `setup.js`: исправлен `s.invalid_token` → `content.setup.invalid_token`
- `show_main_menu`: `parse_mode="HTML"`

## CodeRabbit — запрос полного ревью

@coderabbitai full review

**Скопируйте промпт из** `docs/CODERABBIT-AUDIT-PROMPT-2026-05-USER-FLOWS.md` **(блок в тройных backticks)** или используйте краткую версию ниже.

Фокус: **UX / product / copy / button wiring** — НЕ security (security: `CODERABBIT-AUDIT-PROMPT-2026-05-PHASE7.md`).

Ожидаемые deliverables от CodeRabbit:
1. Таблица **всех кнопок** (label → callback → handler → OK/BUG/CONFUSING)
2. Оценки флоу A/B/C + админ «Тест флоу» (1–10)
3. P0/P1 по копирайту (цитаты RU + file:line)
4. Логические баги путей (repro steps)
5. «Дед-тест»: шаги сегодня vs идеал 2 кнопки
6. До 20 actionable Q-UX-* рекомендаций

Ключевые файлы: `bot_src/keyboards.py`, `handlers.py`, `admin_handlers.py`, `admin_flow_guide.py`, `web/portal/content/ru.json`, `setup.js`, `portal.js`.

## Test plan

- [ ] CodeRabbit: full review по промпту UX
- [ ] `python ops/test_admin_flow_test.py`
- [ ] Ручной чеклист §4 в `AUDIT-USER-FLOWS-2026-05.md` (новое сообщение «Тест флоу» в TG)
