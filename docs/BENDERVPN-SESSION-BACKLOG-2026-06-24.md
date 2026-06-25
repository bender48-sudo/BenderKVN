# BenderVPN — решения и бэклог сессии (2026-06-24/25)

**Status:** canonical owner sync · **Supersedes:** conflicting rows in [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) v1 where noted in [`BENDERVPN-PRODUCT-POLICY-AMENDMENT-2026-06-24.md`](BENDERVPN-PRODUCT-POLICY-AMENDMENT-2026-06-24.md)  
**Master backlog IDs:** [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) §1.1  
**Mini App build:** [`MINI-APP-BUILD-SPEC.md`](MINI-APP-BUILD-SPEC.md) · mockups: `web/portal/design/mockups/`

Принцип неизменён: READ-ONLY аудит → план → owner OK → один PATCH/коммит → probe → smoke.  
`APPLY_ALLOWED=false` по умолчанию. §6 do-not-touch (billing/Remna/routing/schema без owner OK).

---

## 1. Стратегические owner-решения (зафиксированы)

### Модель входа: ЖЁСТКИЙ INVITE-ONLY

- Зайти в BenderVPN **нельзя** без приглашения. Открытой регистрации нет.
- OD invite-gate → **RESOLVED** → invite-only.
- Источники инвайтов: (1) founders/партнёры-основатели руками, (2) стартовый пул тестеров, (3) дружеские рефералки, (4) партнёрские QR.
- «С улицы» не существует — всякий вход = чей-то инвайт.
- Инвайты на старте **безлимитны** (лимиты ввести позже, при 5k–10k юзеров).
- Гейт на уровне **TG-бота** (мини-апка в TG; без инвайта до неё не дойти). Отдельный экран-стена в мини-апке **не нужен**.
- Связь: invite-only + 30k cap = единая boutique-логика контролируемого роста.

**Backlog:** `INVITE-GATE-HARD-001` (bot gate; supersedes soft pilot `PROD-001`).

### Лимит устройств: МЯГКИЙ

- 2-е устройство подключается, но = отдельный конфиг **+6,66 ₽/день**. Не блок.
- Условие: шеринг одного URL должен ловиться → доплата, иначе бесплатная дыра.
- Засада: HWID шлёт только Happ; INCY/V2Ray+/Изи в реестр не попадают → мягкий лимит через HWID для нового iOS не закрыт. Разруливать после G1 (Track A vs Track B).

**Backlog:** `DEVICE-SOFT-LIMIT-001` (supersedes `OD-03` BLOCKED).

### Биллинг: вариант A (DONE, repo)

- `DAILY_RATE` = **6,66 ₽/день** (666 kopeks). 200 ₽ = ровно 30 дней. Вся математика в целых копейках.
- `BILL-UT-001` / `002` / `003` / `004` → **DONE** (repo). 70 tests green. CI billing-job + gitleaks (`5f03b80`).
- Honest-gate kopeks — **СНЯТ**.

---

## 2. iOS-клиенты (Happ удалён из РФ App Store)

- Контекст: РКН-волна; существующие установки работают; ломается только **новая** установка на iOS.
- Стратегия: набор клиентов (живы в РФ App Store, бесплатные):
  - **INCY** — основной (full Xray JSON).
  - **V2Ray Client+** — запасной, только `vless://`.
  - **Изи VPN** — запасной, только `vless://`.
- Матрица (DONE read-only): один конфиг во всех трёх «без танцев» **невозможен** — full JSON родной только INCY. Решение: **UA-ветвление на edge (G13)** — INCY→full JSON, остальным→vless×7.
- Инвариант: fragment **не** возвращать на REALITY (`NL-DIRECT-PATH-FIX`). Stealth TG/Meta/IG→relay.
- G9/G10 отложены (на iOS TUN мимо 127.0.0.1).

### G1 + H1 SMOKE — критический единый блокер (ждём друга с iPhone)

- Пакет: `.local/FRIEND-G1-H1-SMOKE-PACKAGE.md`, профили NL из vault.
- **G1:** импорт canary URL в INCY/V2Ray+/Изи — формат, число профилей, stealth.
- **H1:** NL как второй живой exit (Direct Basic → Split Stealth).
- Разблокирует: выбор клиента, UA-map, INCY HWID (Track A/B), NL promotion, ротацию.

**Backlog:** `G1-H1-SMOKE-001` · `CLIENT-IOS-MATRIX-001` · owner-only.

---

## 3. Устойчивость / ротация IP (multi-provider N+1)

### Стратегия (owner): устойчивая, не докупка IP

- Разные серверы у разных провайдеров; **N+1** — минимум 2 ноды активны параллельно.
- Конвейер: скрипт быстрого поднятия ноды — цель ≤60 мин ops (сейчас 2–4+ ч).
- «Ежедневно за минуты» реально только при 2+ нодах наготове.

### Состояние (read-only)

- `delivery_path_nodes` = 1 (только LV exit). NL up, staging.
- Hot-spare exit IP = 0. User refresh при ротации: 0–12 ч (Happ); INCY auto-update **UNKNOWN**.

### Honest-gate к платному запуску

**Нельзя брать деньги, пока:** `delivery_path ≥ 2` + отрепетированный hot-spare + INCY auto-update.

**Backlog:** `HONEST-GATE-PAID-001` · `IP-ROTATE-NPLUS1-001`.

### OK дано (pre-provision, `APPLY=false`)

- Detect стадия 0 (P1–P5) — SUSPECT-ONLY.
- Hot-spare HS-B (NL): pre-provision remnanode+hosts+UUID+snapshot+dry-run+registry.
- H1 owner-smoke NL (в пакете с G1).
- **Не трогать:** Swap стадия 1, Push/TG стадия 2, реальный флип NL.

### Очередь после smoke (owner OK на каждом)

`H1 PASS` → NL A2/A4 APPLY → detect → конвейер v2 → `SUB-GEN-SELECTOR-APPLY` → INTEGRATION

---

## 4. Поддержка (дизайн + логика)

### Архитектура: мост в Telegram

- Юзер в мини-апке → тикет в TG-чат поддержки `#тикет_NNNN`.
- Команда отвечает в TG → ответ в приложение.
- Статусы: **Ждёт ответа** · **Ответ есть** · **Закрыто** (ручное или авто 3 дня тишины; переоткрытие при новом сообщении).
- Первый ответ дублируется в приложение + email + TG; дальше — по каналу ответа юзера.
- Авто-отбивка редактируема админами из TG (глобальный режим); не меняет статус.
- Fallback: **help@bendervpn.io** (подвал/оферта/бот; ФЗ-152 — проверить юр-доки).
- Темы: Подключение, Оплата, Устройства, Другое, Вывод средств (партнёры).

**Backlog:** `SUPPORT-TICKET-BRIDGE-001` (extends `SUPPORT-TICKET-001` + `SUPPORT-DIAG-001`).

### SUPPORT-AI-AGENT-001 (P3→P4, TRACK 6, запись не в работу)

S1 read-only → S2 suggest → S3 whitelist → S4 node reboot (только после S1–S3 + предохранители).

---

## 5. Рефералка + партнёрка (две программы)

### Обычная рефка

- **30%** от первого пополнения друга → баланс реферера.
- Друг по рефке → **+100 ₽** сразу на баланс.
- Без вывода.

### Партнёрка (одобрение вручную)

- **50%** с первого пополнения + **10%** со всех последующих.
- Вывод: от **5000 ₽**, 15-е число, 2 раб. дня, вся сумма или копить.
- Клиент по партнёрскому QR: +100 ₽ при пополнении на 200 ₽.
- Заявка → предзаполненный тикет «Партнёрство».

### Withdrawal flow (только партнёры)

Форма реквизитов → тикет «Вывод средств» → админ «Обнулить баланс после перевода» + аудит-лог.

**Навигация:** рефералка = ядро роста — 5-я кнопка в нижнем меню + бургер + баннер на главной.

**Backlog:** `REF-PROGRAM-001` · `PARTNER-PROGRAM-001` · `DEC-IMPL-006` / `007` (ledger/admin, spec без prod schema).

---

## 6. Колесо фортуны

- 1 прокрутка за ~10 **активных** (оплаченных) дней; накапливаются.
- Выпадение **по весам:** Мимо 55% · Доп.спин 25% · +2₽ 14% · +5₽ 5% · +20₽ 0,9% · ДЖЕКПОТ +50₽ 0,1%.
- Средний ≈ 0,76 ₽/спин × ~3/мес ≈ 2,3 ₽/юзер/мес.
- Призы — только рубли на баланс (не дни, не «устройство»).

**Backlog:** `GAME-FORTUNE-001` (P4, после запуска) · `GAME-2D` (P4, phaser open-source).

---

## 7. Параллельные задачи (без prod, без ожидания smoke)

| Статус | ID / тема |
|--------|-----------|
| **DONE** | BILL-UT, kopeks, CI billing+gitleaks, copy 6,66 |
| **Очередь** | `SUPPORT-TICKET-001` + `SUPPORT-DIAG-001` |
| **Можно** | `DEC-IMPL-006`/`007`, `SUBSCRIPTION-RESOLVE-TZ`, `ROUTING-PROFILE-RU-DIRECT` impl, `MONITOR-CAPACITY` design, `BOT-QR-MISSING-KEY` |
| **Owner-only** | live taps, G4-bind, desktop `CLIENT-SMOKE`, **`G1-H1-SMOKE-001`** |

---

## 8. Дизайн — экраны-эталоны

`home`, `access`, `access_detail`, `wizard`, `balance`, `support` (3), `referral` (2), `fortune`.

Единый стиль: Onest, чёрно-рыжая палитра, бинарный код-фон, пиксель-робот, 5-кнопочное нижнее меню.  
Honest-UI: не показываем данных, которых нет (см. [`MINI-APP-BUILD-SPEC.md`](MINI-APP-BUILD-SPEC.md)).

**Backlog:** `MINI-APP-BUILD-001` · mockups в `web/portal/design/mockups/`.

---

## Ключевые блокеры

| Блокер | Ждёт |
|--------|------|
| **G1+H1 smoke** (iPhone) | Клиент, UA-map, INCY HWID, NL exit, ротация e2e |
| **delivery_path=1** | 300/30k NO-GO до 2-го exit в live sub |
| **Honest-gates к деньгам** | (1) mobile stability, (2) NL в delivery + hot-spare, (3) kopeks — **DONE** |
