# Post-deploy review (2026-05)

**Дата:** 2026-05-19  
**Область:** репозиторий + прод после **Q079–084** (бот AMS, edge **:8443**, panel bind, smokes, drift waive)  
**Масштаб:** ~60 активных пользователей, цель роста ~200 (GTM)  
**Источники:** CodeRabbit / codebase exploration, сверка с **`AUDIT-2026-05-SECURITY.md`**, **`TSPU-OBSERVATIONS.md`**, **`BACKLOG-QUEUE.md`**  
**Статус очереди:** линейная Q001–084 **DONE**; **NEXT** агента не задан

---

## Executive summary

Инфраструктура и продуктовый контур **зрелые для закрытой беты** (~60 users): оплаты, webhook hardening, edge **:8443**, portal/Mini App, runbook ТСПУ закрыты в репо (**Q063–078**, **Q051–062**, **Q079–084**).

Повторный обзор выявил **3 критические дыры**, не покрытые закрытым security-бэклогом: **обход авторизации админ-FSM**, **публичный `:2054` → panel в Caddy-шаблоне**, **утечка секрета в DEBUG print**. Плюс **высокий** риск по **cabinet `bind_url`** для web-trial без привязки TG.

**Вердикт GTM:** **условно не готов** — см. §6.  
**Итоговая зрелость:** **6.8 / 10** (взвешенная, §2).

> **Как читать оценки CodeRabbit «6.5»:** для снимка **до Q063–078** она была занижена относительно уже сделанного P0/P6. Для снимка **после Q084** отдельная оценка **~6–7 по security** уместна из‑за **новых** находок, а не из‑за «ничего не чинили».

---

## 1. Шкала оценок (1–10)

| Балл | Смысл |
|------|--------|
| **1–3** | Критические пробелы; эксплуатация реалистична; GTM/рост опасен |
| **4–6** | Работает, но есть значимые дыры или операционный долг |
| **7–8** | **Production-ready** для текущего масштаба при известном долге |
| **9–10** | Эталон: автоматизация, defense-in-depth, полевые проверки |

Оценки опираются на **файлы/строки** и статус **Q063–084**, не на «ощущения».

---

## 2. Зрелость по доменам

| Домен | Балл | Одна фраза «почему» |
|-------|------|---------------------|
| **Security** | **6.0** | Q063–078 закрыли оплаты/support/webhook; остаются **admin FSM без auth**, **`:2054`**, **DEBUG+api_key**, слабый **cabinet** |
| **Ops / Deploy** | **7.5** | Safe-deploy, бэкапы, smokes, drift waive; нет healthchecks ряда сервисов, **HSTS/CSP**, частичный rollback |
| **Product / UX** | **7.0** | Portal + бот + Mini App на **:8443**; ЛК только для SQLite-users; web-trial race; ручные конфиги вне бота |
| **TSPU / Edge** | **7.0** | Q051–061 в репо/проде (**8443**, MUX, SNI, probes); в шаблоне ещё **:2054**; полевой red-team не зафиксирован |

**Взвешенный итог:**  
`0.35×6.0 + 0.25×7.5 + 0.20×7.0 + 0.20×7.0` ≈ **6.8 / 10**

**Готовность к коммерческому росту (500+):** **условно** — после P0 security и нагрузочного/ТСПУ-контроля; см. §7.

---

## 3. Critical

### C1 — Admin FSM без проверки `ADMIN_ID`

| | |
|--|--|
| **Риск** | Любой пользователь переводит бота в состояние редактирования настроек (`about`, `terms`, legal URLs, support) и **меняет production copy** в SQLite |
| **Вероятность** | **Высокая** — достаточно callback `admin_edit_*` без секрета; message handlers **не** проверяют admin (`admin_handlers.py:37–58`, `:85–114`) |
| **Рекомендация** | В `start_editing_handler` и каждом `AdminEdit.*` handler — `if str(message.from_user.id) != ADMIN_ID: return`; middleware на `admin_router`; smoke «non-admin → no state change» |
| **Verify** | Ручной: второй TG-аккаунт → `admin_edit_about` → текст не сохраняется |
| **Q** | Предложить **Q086** `P3-RED-ADMIN-FSM-01` |

### C2 — Публичный `:2054` → panel proxy в Caddy LV

| | |
|--|--|
| **Риск** | Сигнатура **3X-UI/panel** (см. `EDGE-PORT-RECOMMENDATION.md`); прямой доступ к panel UI/API минуя задуманный bind **127.0.0.1** на AMS (Q081) |
| **Вероятность** | **Средняя–высокая** на LV, если порт открыт UFW — в репо `Caddyfile-latvia-full.txt:47–51` `reverse_proxy http://127.0.0.1:3000` |
| **Рекомендация** | Убрать блок `:2054` с публичного Caddy или bind только loopback + ACL; сверить с прод `caddy validate`; задокументировать в §12 |
| **Verify** | С RU/VPS: `curl -k https://<lv>:2054` → fail или только через VPN ops |
| **Q** | **Q087** `P1-RED-NET-02` |

### C3 — DEBUG print с участием crypto API key

| | |
|--|--|
| **Риск** | `string_to_hash` включает **api_key**; `print` в stdout контейнера → логи/Docker/journal (**утечка секрета**) |
| **Вероятность** | **Высокая** при любом crypto payment — `handlers.py:1412–1415` |
| **Рекомендация** | Удалить print; redact в логах; pre-commit запрет `print(` в `bot_src/` |
| **Verify** | `grep -n 'DEBUG \[Final\]' bot_src/` пусто; оплата crypto → в логах нет ключа |
| **Q** | **Q088** `P6-RED-PAY-08` |

---

## 4. High

### H1 — Cabinet API отдаёт `bind_url` по email / BVPN-ID без аутентификации

| | |
|--|--|
| **Риск** | Публичный `POST /setup/api/cabinet` → при знании email жертвы web-trial — **ссылка привязки TG** (`portal_cabinet.py:74–75`) |
| **Вероятность** | **Средняя** (нужен email); для web-only аккаунтов — реалистичный сценарий |
| **Рекомендация** | Не отдавать `bind_url` без HMAC/session; rate limit per email; captcha или одноразовый код на email |
| **Verify** | POST без секрета → нет `bind_url` в ответе |

### H2 — `YOOKASSA_WEBHOOK_SKIP_API_VERIFY` без fail-fast на проде

| | |
|--|--|
| **Риск** | Опечатка env → приём webhook без verify API |
| **Вероятность** | **Низкая**, но impact критичен |
| **Рекомендация** | При `SKIP=true` и `BOT_PAYMENTS_LIVE=1` — **refuse start** (не только `logger.critical`) — `auth.py:91–95` |
| **Verify** | Smoke: prod env template не содержит SKIP |

### H3 — PromoCreate FSM: defense-in-depth (уточнение CodeRabbit)

| | |
|--|--|
| **Факт** | Вход в промо **защищён** — `admin_promo_create_start` проверяет admin (`handlers.py:1033–1035`) |
| **Риск** | Message handlers `:1040+` без повторной проверки — стандартный **depth** gap |
| **Вероятность** | **Низкая** без другого бага FSM |
| **Рекомендация** | Admin check в каждом `PromoCreate.*` message handler |
| **Severity** | **Medium** (не High), зависит от **C1** |

### H4 — Нет HSTS / CSP на Caddy vhost

| | |
|--|--|
| **Риск** | SSL stripping; усиление XSS с CDN scripts |
| **Вероятность** | Средняя (зависит от атакующего) |
| **Рекомендация** | `header Strict-Transport-Security`, базовый `Content-Security-Policy` на portal/setup |
| **Verify** | `curl -I` → заголовки присутствуют |

### H5 — Subscription-page `0.0.0.0:3010/3011`

| | |
|--|--|
| **Риск** | Обход intent loopback-only (`compose/ams/remnawave-sub/docker-compose.yml.tmpl:8,24`) |
| **Вероятность** | Средняя, если UFW не закрывает |
| **Рекомендация** | `127.0.0.1:3010:3010`; smoke с внешнего IP |
| **Verify** | Q081-стиль external fail |

### H6 — CDN scripts без SRI

| | |
|--|--|
| **Риск** | Компромисс `telegram.org` / jsdelivr → XSS в Mini App |
| **Вероятность** | Низкая |
| **Рекомендация** | SRI + fallback; или self-host |
| **Файлы** | `web/portal/index.html`, `cabinet.html` |

### H7 — Web trial check-then-act

| | |
|--|--|
| **Риск** | Двойной trial при гонке |
| **Вероятность** | Низкая при малой базе |
| **Рекомендация** | UNIQUE + transaction в `web_trial_db` |

---

## 5. Medium

| ID | Находка | Риск | Вероятность | Рекомендация |
|----|---------|------|-------------|--------------|
| M1 | Crypto webhook secret в query (логи access) | Утечка в Caddy log | Средняя | Только POST body / header |
| M2 | Hardcoded `kitsura.fun` vs `KEY_EMAIL_DOMAIN` | Неверный email в edge cases | Низкая | Единый env |
| M3 | Нет healthcheck: sub-page, remnanode, adguard, shop-bot | Медленный fail | Средняя | `healthcheck` в compose tmpl |
| M4 | Rate limit только по IP | Обход CGNAT | Средняя | + fingerprint / user id |
| M5 | `/api/ops/status.json` публичный | Разведка | Высокая | Ок для status; не класть секреты |
| M6 | `ADMIN_ID` vs `ADMIN_TELEGRAM_ID` naming | Путаница ops | Низкая | Один env name |
| M7 | `localStorage` sub URL / email | Shared device | Низкая | Док + TTL в UX |

---

## 6. Low (бэклог)

| Находка | Рекомендация |
|---------|--------------|
| Fallback URL с prod hostname в коде | Централизовать `site_urls.py` |
| Support rate limit in-memory | Redis при росте |
| Single `ADMIN_ID` | RBAC позже |
| `get_claim_by_customer_id` O(N) | Индекс / SQL WHERE |
| Нет бэкапа Caddy/Xray state | Runbook export |
| `remnawave/node:latest`, `caddy:2.9` float | Digest pin (Q016 частично) |
| Token в `monitor.sh` probe | Env / short-lived |

---

## 7. Top-5 на 2 недели

| # | Действие | Файлы / зона | Что снимает | Verify |
|---|----------|--------------|-------------|--------|
| **1** | **Admin auth на все FSM admin paths** | `admin_handlers.py` | **C1** | non-admin smoke |
| **2** | **Убрать/закрыть `:2054`** на LV Caddy | `Caddyfile-latvia-full.txt`, прод Caddy | **C2**, ТСПУ fingerprint | external curl fail |
| **3** | **Убрать DEBUG print** (+ запрет в CI) | `handlers.py:1415` | **C3** | grep + log review |
| **4** | **Cabinet: не отдавать `bind_url` анонимно** | `portal_cabinet.py`, `setup_verify_service.py` | **H1** | POST без auth |
| **5** | **HSTS + CSP** на portal/setup/sub | Caddy snippets | **H4**, **H6** частично | `curl -I` |

После **1–3** — повторный mini-audit и обновление вердикта §8.

---

## 8. Вердикт GTM

### Статус: **условно не готов к GTM**

| Условие | Тип | Список |
|---------|-----|--------|
| **Блокеры** | Must fix | **C1, C2, C3** |
| **До GTM** | Strongly recommended | **H1, H4, H5** (+ owner **Q032** оферта, **MANUAL-OWNER-CHECKLIST**: BotFather **:8443**, CryptoBot POST) |
| **Можно отложить** | Backlog | M*, L*, H6–H7, ТСПУ field report (**Q085**), CodeRabbit общий проход |
| **Уже сделано** | — | Q063–078, Q051–062, Q079–084 |

**«Готов к GTM» когда:** блокеры закрыты + smokes зелёные + один E2E (бот → ключ → Happ на LTE) + owner Q032.

**Контрольная точка:** после Q086–088 — обновить §12 в `COMMERCIAL-BACKLOG.md` и этот документ (вердикт → «готов с оговорками»).

---

## 9. Рост (500+ users) — отдельно от GTM

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| Архитектура 3 ноды | **7/10** | LV/AMS/NL, multi-origin, MUX — ок до ~200 |
| Платежи | **8/10** | Idempotency, amount verify, webhook auth (post-Q063) |
| Ops | **7/10** | Restore test ✅; healthchecks/rollback — долг |
| Scale blockers | — | O(N) web_trial lookup; in-memory RL; single admin |

---

## 10. Предлагаемые Q (не менять NEXT без владельца)

| Q | ID | Суть |
|---|-----|------|
| **Q085** | P2-RED-TSPU-AUDIT-02 | Полевой red-team → `AUDIT-2026-05-TSPU-REDTEAM.md` |
| **Q086** | P3-RED-ADMIN-FSM-01 | **C1** |
| **Q087** | P1-RED-NET-02 | **C2** `:2054` |
| **Q088** | P6-RED-PAY-08 | **C3** debug print |
| **Q089** | P3-RED-CABINET-02 | **H1** bind_url |
| **Q090** | P2-RED-EDGE-HEADERS-01 | **H4** HSTS/CSP |

---

## 11. Расхождения с сырым CodeRabbit (важно для оценок)

| Утверждение CR | Вердикт |
|----------------|---------|
| Оценка **6.5** «слишком низкая» для всего репо | **Частично верно** для мая до Q063; **не** переносить на post-Q084 security |
| PromoCreate «нет admin check» | **Неточно** на входе; **да** на message handlers (**Medium**, H3) |
| «16 remediated» vs 3 Critical | **Оба верны** — разные волны аудита |
| Cabinet hijack | **High**, не Critical (нужен email / BVPN-ID) |

---

## 12. Связанные документы

- `docs/AUDIT-2026-05-SECURITY.md` — волна Q063–078  
- `docs/BACKLOG-QUEUE.md` — очередь (NEXT пуст)  
- `docs/TSPU-OBSERVATIONS.md` — полевая матрица  
- `docs/MANUAL-OWNER-CHECKLIST.md` — владелец  
- `docs/AGENT-PROD-DEPLOY-BACKLOG.md` — Q079–084  

---

*Версия: 2026-05-19. Обновлять после закрытия Q086–088 и TSPU red-team Q085.*
