# Бэклог флоу для агента Cursor (фаза 3, Q044–050)

**Назначение:** пошаговые инструкции для **флоу / portal polish / веб-ЛК** — **после** продукта.

> **Gate:** **Q044–050** только после **Q062**. До этого: **Q063–078** (security), затем **Q051–062** (продукт). **Не начинать Q044**, если NEXT &lt; **Q044** в **`BACKLOG-QUEUE.md`**.

**Очередь:** **`docs/BACKLOG-QUEUE.md`**.  
**Контекст:** **`docs/USER-FLOW-BACKLOG.md`**, §7.1 **`docs/COMMERCIAL-BACKLOG.md`**.

---

## 0. Правила для агента (флоу)

1. Убедиться, что **`NEXT`** — **Q044+** (продукт уже закрыт или владелец явно переключил очередь).
2. Прочитать секцию этой задачи **ниже (§2)** + **Done when** в §7.1 бэклога.
3. Сделать **один коммит**, обновить очередь (**NEXT → DONE**, следующая **TODO → NEXT**), строка в **§12** при продуктовых задачах.
4. **Остановиться.** Следующий Q — новая сессия (если владелец не написал «продолжай очередь»).
5. **Не трогать P4-DNS** в том же коммите.
6. AMS compose/env — только **`RUNBOOK-AMS-SAFE-DEPLOY`**.

### Архитектурный принцип: один портал — два входа

| Вход | Когда | Технология |
|------|--------|------------|
| **Сайт** (`/start`, `/setup/…`) | Нет VPN; TG заблокирован; «открыл ссылку из рекламы» | Статика на **LV Caddy** (как `/status`) |
| **Telegram Mini App** | TG доступен; пользователь уже в боте | **Тот же** HTML/JS/CSS, URL в BotFather = `public_portal_url()` |
| **Чат-бот** | Кнопки, оплата, поддержка | aiogram + ссылки на сайт / `WebAppInfo` |

**Запрещено:** два разных текста/дизайна для сайта и Mini App. Источник строк — **`web/portal/content/ru.json`** (или один `portal.js` с константами).

```
web/portal/
  content/ru.json      # все тексты RU
  assets/portal.css    # крупный шрифт, контраст (бабушка-тест)
  assets/portal.js     # рендер шагов, QR, copy, Telegram.WebApp
  index.html           # главная = bootstrap
  setup.html           # выдача конфига (?t=token)
```

Деплой: **`/var/www/bvpn-portal/`** на LV; Caddy:
- `handle /start*` → portal
- `handle /portal*` → portal (alias для Mini App)
- `handle /setup/*` → `setup.html` + API (см. Q036)

---

## 1. Карта очереди (полная фаза 3)

| Q | ID | Зависит от | Артефакт |
|---|-----|------------|----------|
| **032** | P5-COM-02 | — | Текст возвратов (оферта) |
| **033** | P3-FLOW-00 | — | **`docs/USER-FLOW-JOURNEY.md`** |
| **034** | P3-FLOW-14 | Q033 | **`web/portal/`** + `ru.json` + базовый CSS |
| **035** | P3-FLOW-01 | Q034 | Caddy `/start`, smoke **`PUBLIC_BOOTSTRAP_OK`** |
| **036** | P3-FLOW-02 | Q035 | `setup.html` + token API + QR |
| **037** | P3-FLOW-12 | Q034, Q036 | Mini App = тот же URL, кнопка в боте |
| **038** | P3-FLOW-03 | Q035–037 | Кнопки бота + Menu Button WebApp |
| **039** | P3-FLOW-04 | Q037 | FSM «Подключить VPN» (может открывать Mini App) |
| **040** | P3-FLOW-07 | — | FAQ, ONBOARDING, бот — оплата live |
| **041** | P3-FLOW-05 | Q036 | QR в боте + portal |
| **042** | P3-FLOW-06 | Q035 | Видео/GIF на portal |
| **043** | P3-FLOW-08 | Q035 | `/start/help/errors` |
| **044** | P3-FLOW-09 | Q034 | Ветки iPhone / Android / Windows |
| **045** | P3-FLOW-13 | Q035 | a11y ≥ 95 |
| **046** | P3-FLOW-10 | Q038 | Метрики воронки (логи + бот events) |
| **047** | P3-FLOW-11 | Q035 | Запасной домен bootstrap |
| **048** | P3-FLOW-15 | Q038, web trial | Баланс в `#cabinet` (API read-only; acquiring позже) |
| **049** | P3-FLOW-16 | Q048, web trial | Bind TG ↔ `BVPN-ID` / email |
| **050** | P3-FLOW-17 | Q049, P2-RED-BOOT-01 | Web/email notify без TG |

**Флоу NEXT (когда продукт закрыт):** **Q044** (**P3-FLOW-09**). Карта: **`BACKLOG-MAP.md`**.

**Уже закрыто:** Q033–043 (portal MVP, wizard, QR, errors) — не переделывать без регрессии.

**Продукт (Q051–062):** **`docs/AGENT-PRODUCT-BACKLOG.md`**.

---

## 2. Пошаговые инструкции по задачам

### Q032 — P5-COM-02 (возвраты)

- Подготовить блок текста для оферты: массовый даун, срок возврата, как написать в поддержку.
- Файлы: черновик в **`docs/templates/REFUND-POLICY-SNIPPET.md`** (новый) или правка существующей telegra.ph-ссылки — **без** секретов.
- **Verify:** владелец подтвердил публикацию в оферте (в §12: «текст согласован»).
- **Commit:** `docs: P5-COM-02 — refund policy snippet for offer`

---

### Q033 — P3-FLOW-00 (карта пути)

- Создать **`docs/USER-FLOW-JOURNEY.md`**:
  - 3 персоны (бабушка iPhone, Android сын, «TG не открывается»).
  - 10 шагов без жаргона (нет shortUuid, Reality, TLS).
  - Три колонки: **Сайт** | **Mini App** | **Бот** — одинаковые шаги.
  - Критерии приёмки из USER-FLOW-BACKLOG §8.
- **Verify:** чеклист в конце файла; ссылки на ONBOARDING/FAQ.
- **Commit:** `docs: P3-FLOW-00 — user journey + grandma-test`

---

### Q034 — P3-FLOW-14 (единый портал, контент)

- Создать **`web/portal/`** (см. дерево §0).
- **`content/ru.json`**: ключи `home.title`, `steps[]`, `buttons.support`, `buttons.status`, `setup.copy_link`, `errors.generic`, …
- **`assets/portal.css`**: `font-size: 18px+`, контраст WCAG AA, кнопки min-height 48px, `lang=ru`.
- **`assets/portal.js`**: загрузка JSON, рендер шагов; заглушка `Telegram.WebApp.ready()` если `window.Telegram`.
- **`index.html`**: главная — 3 большие кнопки: «Подключить VPN», «Статус сервиса», «Написать в поддержку».
- **`ops/site_urls.py`**: `public_bootstrap_url()`, `public_portal_url()`, `public_setup_url(token)`.
- **Verify:** открыть `index.html` локально (file:// или `python -m http.server`); JSON валиден.
- **Commit:** `product: P3-FLOW-14 — shared portal bundle (ru.json + base UI)`

---

### Q035 — P3-FLOW-01 (bootstrap на проде)

- **`docs/RUNBOOK-USER-BOOTSTRAP-SITE.md`**: деплой LV, Caddy snippet, rollback.
- **`ops/deploy-user-portal-lv.ps1`**: rsync `web/portal/` → `/var/www/bvpn-portal/`.
- Патч **`Caddyfile-latvia-full.txt`**: `handle_path /start/*`, `/portal/*` → file_server.
- **`ops/smoke_public_bootstrap.py`**: HTTP 200, строки из `ru.json` на странице, нет `eyJ`/BOT_TOKEN.
- **Verify:** `PUBLIC_BOOTSTRAP_OK` с рабочей станции без VPN.
- **Commit:** `product: P3-FLOW-01 — bootstrap /start on LV + smoke`

---

### Q036 — P3-FLOW-02 (выдача конфига)

- **`setup.html`**: query `?t=` — HMAC token (shortId + expiry), генерируется ботом позже.
- Показать: QR (библиотека qrcode в JS или PNG с бэкенда), «Скопировать ссылку», шаги Happ.
- **`ops/portal_setup_token.py`** (или endpoint в боте): `sign_setup_token(short_id, ttl_hours=72)`.
- Rate limit на `/setup/*` в Caddy (как sub RL, мягче).
- **Verify:** тестовый token → страница 200; curl без VPN.
- **Commit:** `product: P3-FLOW-02 — setup page + signed token helper`

---

### Q037 — P3-FLOW-12 (Telegram Mini App)

**Цель:** Mini App **визуально и по шагам = сайт** (тот же `public_portal_url()`).

1. **URL в BotFather** (владелец): Menu Button → Web App URL = `https://k9x2m1.conntest.xyz:2053/portal/` (или `/start/` — один canonical в `site_urls.py`).
2. **Бот** (`bot_src/handlers.py` / keyboards):
   - `MenuButton(web_app=WebAppInfo(url=portal_url))` при старте или в `/start`.
   - Inline-кнопка «📱 Открыть инструкцию» → тот же URL.
3. **`portal.js`**:
   - `Telegram.WebApp.expand()`, `setHeaderColor`, `enableClosingConfirmation`.
   - `themeParams` для тёмной темы (как CSS variables).
   - Кнопка «Скопировать» через `Telegram.WebApp.openLink` / clipboard API.
4. **Безопасность:** не передавать в Mini App JWT панели; только setup token или sub URL уже выданный пользователю.
5. **Опционально v2:** `initData` verify на AMS — отдельный Q, не блокер MVP.
6. **`ops/smoke_telegram_miniapp.py`**: проверка URL 200, в HTML есть `telegram-web-app.js`, ключевые строки из `ru.json`.
7. **Verify:** `TELEGRAM_MINIAPP_PORTAL_OK`; ручной тест в TG на телефоне.
8. **Commit:** `product: P3-FLOW-12 — Telegram Mini App mirrors portal`

**Док для владельца:** **`docs/RUNBOOK-TELEGRAM-MINIAPP.md`** (BotFather, WEBAPP_URL в env если нужен).

---

### Q038 — P3-FLOW-03 (бот ↔ портал)

- После выдачи ключа: кнопки «📱 Инструкция (Mini App)», «🌐 Открыть в браузере», «🔗 Моя настройка» → `public_setup_url(token)`.
- Тексты из **`user_messages.py`**, URL только **`site_urls`**.
- **Verify:** новый user ≤ 3 тапа до всех ссылок.
- **Commit:** `product: P3-FLOW-03 — bot portal + setup links`

---

### Q039 — P3-FLOW-04 (мастер в боте)

- FSM: выбор устройства → «Открыть Mini App» **или** пошаговые сообщения с картинками.
- Предпочтительно: главный CTA = Mini App (дублирует сайт), fallback = текст в чате.
- **Verify:** сценарий в USER-FLOW-JOURNEY проходит.
- **Commit:** `product: P3-FLOW-04 — VPN setup wizard + Mini App CTA`

---

### Q040 — P3-FLOW-07 (синхронизация текстов)

- Исправить **`docs/FAQ.md`**: оплата **включена** (баланс, пополнение, Stars).
- Синхронить **`ONBOARDING.md`**, `ru.json`, ключевые сообщения бота.
- **Commit:** `docs: P3-FLOW-07 — FAQ/onboarding/portal payment copy sync`

---

### Q041–Q047

См. **`docs/USER-FLOW-BACKLOG.md` §4**; те же Verify, что в таблице очереди.

---

## 3. Mini App — UX-требования («бабушка»)

| # | Требование |
|---|------------|
| 1 | На первом экране **одна** главная кнопка: «Подключить интернет (VPN)» |
| 2 | Шаги **пронумерованы** 1–5; не больше 2 предложений на шаг |
| 3 | Иконки 📱 🍎 🤖 — не обязательны, но помогают |
| 4 | «Не получается» → поддержка + `/status` |
| 5 | Шрифт не мельче **18px**; кнопки на всю ширину |
| 6 | Работа в **светлой и тёмной** теме TG (`themeParams`) |
| 7 | Тот же контент, что на **`/start`** — diff `ru.json` = 0 между каналами |

---

## 4. Smoke-маркеры (для §12)

| Маркер | Задача |
|--------|--------|
| `PUBLIC_BOOTSTRAP_OK` | Q035 |
| `PORTAL_SETUP_PAGE_OK` | Q036 |
| `TELEGRAM_MINIAPP_PORTAL_OK` | Q037 |
| `BOT_PORTAL_LINKS_OK` | Q038 |

---

## 5. Файлы, которые агент будет трогать чаще всего

| Область | Пути |
|---------|------|
| Портал | `web/portal/**` |
| URL | `ops/site_urls.py`, `ops/site.env.example` |
| Деплой LV | `ops/deploy-user-portal-lv.ps1`, `Caddyfile-latvia-full.txt` |
| Бот | `bot_src/handlers.py`, `bot_src/user_messages.py`, keyboards |
| Доки | `docs/USER-FLOW-JOURNEY.md`, runbooks |
| Smoke | `ops/smoke_public_bootstrap.py`, `ops/smoke_telegram_miniapp.py` |

---

## 6. Вне scope агента (владелец)

- Публикация текста оферты (Q032) на telegra.ph
- BotFather: создание Mini App, URL, иконка 640×360
- Юридическое согласование возвратов

---

*При конфликте приоритет: **BACKLOG-QUEUE.md** > этот файл > USER-FLOW-BACKLOG.md.*
