# BenderVPN — реестр секретов

Этот документ описывает **где живут реальные значения** для placeholder'ов из `compose/` и `docs/DEPLOY.md`. Сами секреты в репо отсутствуют — они хранятся отдельно (Bitwarden, sealed-secrets, или, временно, в `.secrets/` который в `.gitignore`).

## 1. Каталог placeholder'ов

| Placeholder | Где используется (templates / прод) | Что это | Источник | Ротация |
|-------------|-------------------------------------|---------|----------|---------|
| `${SECRET_KEY_NODE_JWT_BUNDLE}` | `compose/lv/remnanode/node.env.tmpl`<br>`compose/ams/remnanode/node.env.tmpl`<br>`compose/nl/remnanode/node.env.tmpl`<br>(во всех трёх: поле `SECRET_KEY=` в `.env`; рендер ключей vault `SECRET_KEY_NODE_{LV,AMS,NL}`) | Строка ключей ноды, которую отдаёт панель при добавлении Node. Уникальна per-host. | Из панели (UI → Nodes). | Перевыпуск ноды → обновить `/opt/remnanode/.env` → `docker compose up -d`. |
| `${JWT_AUTH_SECRET}` | `compose/ams/remnawave/panel.env.tmpl`<br>`compose/_archive/lv-remnawave-2026-04/panel.env.tmpl` | HMAC-secret панели для подписи JWT auth-токенов (web admin sessions). Hex, 128 символов. | Сгенерирован при init панели (`openssl rand -hex 64`). | Ротация **инвалидирует все активные admin-сессии** — нужно перевыйти и заново зайти. Не требует пересборки. |
| `${JWT_API_TOKENS_SECRET}` | `compose/ams/remnawave/panel.env.tmpl`<br>`compose/_archive/lv-remnawave-2026-04/panel.env.tmpl` | HMAC-secret панели для подписи **long-lived API-token'ов** (роль `API`). Hex, 128 символов. | Сгенерирован при init панели. | **КРИТИЧНО**: ротация инвалидирует все API-токены, нужно **переподпись всех `REMNA_API_TOKEN`** во всех зависимых сервисах (bot, sub-page, balancer.env, ru-monitor.env). |
| `${POSTGRES_USER}` | `compose/ams/remnawave/panel.env.tmpl` | Имя пользователя БД. По умолчанию `postgres`. | Дефолт официального образа. | Не ротируется (не секрет). |
| `${POSTGRES_PASSWORD}` | `compose/ams/remnawave/panel.env.tmpl` + `docker-compose.yml.tmpl`<br>`compose/_archive/lv-remnawave-2026-04/panel.env.tmpl` | Пароль БД. Используется backend'ом для подключения через `DATABASE_URL`. | Сгенерирован при init (`openssl rand -base64 24`, 30 символов). | Ротация: (1) `ALTER USER postgres WITH PASSWORD '<new>'`, (2) обновить `.env`, (3) `docker compose up -d remnawave-db remnawave`. |
| `${REMNA_API_TOKEN}` | `compose/ams/remna-shop/bot.env.tmpl`<br>`compose/ams/remnawave-sub/docker-compose.yml.tmpl`<br>`compose/_shared/etc-bvpn-lv/balancer.env.tmpl`<br>`compose/_shared/etc-bvpn-lv/ru-monitor.env.tmpl` | Long-lived API-токен (роль `API`, `exp=2299-12-21`) для машинных вызовов `/api/*`. JWT в формате `eyJ…`. **Один токен** используется ботом, sub-page, balancer.sh, ru-monitor.py. | Сгенерирован через панель «API → Generate token, role=API, expires=never». | Регенерация через панель (предыдущий продолжит работать до перевыпуска `JWT_API_TOKENS_SECRET` — следить, что в `iss`/`uuid` нет коллизии). Прописать в 4 местах одновременно. |
| `${BOT_TOKEN}` | `compose/ams/remna-shop/bot.env.tmpl`<br>`compose/_shared/etc-bvpn-lv/balancer.env.tmpl`<br>`compose/_shared/etc-bvpn-nl/bot-token.tmpl` | Telegram bot-token (`@Bender_KVN_bot`). Формат `<numeric>:AA...`. | @BotFather → /mybots → API token. | При компрометации: `/revoke` в BotFather → новый token → обновить во всех 3 местах. |
| `${METRICS_PASS}` | `compose/ams/remnawave/panel.env.tmpl`<br>`compose/_archive/lv-remnawave-2026-04/panel.env.tmpl` | Basic-Auth password для `/metrics` panel (Prometheus scraping). Hex, 32 символа. | Сгенерирован при init (`openssl rand -hex 16`). | Ротация: безопасно в любой момент, нужно лишь обновить Prometheus scrape config (у нас Prometheus сейчас не используется — disabled). |
| `${WEBHOOK_SECRET_HEADER}` | `compose/ams/remnawave/panel.env.tmpl`<br>`compose/_archive/lv-remnawave-2026-04/panel.env.tmpl` | Shared secret для webhook-receiver'а. У нас `WEBHOOK_ENABLED=false`, реально не используется. | n/a (placeholder ставится при init). | Не ротируется (не активен). |
| `${CLOUDFLARE_TOKEN}` | `compose/ams/remnawave/panel.env.tmpl`<br>`compose/_archive/lv-remnawave-2026-04/panel.env.tmpl` | API-токен Cloudflare для DNS-челленджа Let's Encrypt. На проде сейчас placeholder `ey...` — функция не используется. | Cloudflare dashboard → My Profile → API Tokens. | Если включим — генерируем zone-scoped token и обновляем. |
| `${REMNA_PUBLIC_KEY}` | `compose/ams/remna-shop/bot.env.tmpl` | Reality public key для VLESS-конфигов в боте. **НЕ секрет** (буквально public key), но привязан к pair private/public Reality на ноде. | Output `xray x25519` при инициализации Reality. | Ротация только при перевыпуске Reality-keypair (комплексно). |

## 2. Где НА САМОМ ДЕЛЕ хранятся текущие значения

**Сейчас**: в `.secrets/prod-compose/` (gitignored) после `P1-OPS-DRIFT-02` pull'a. Это **локальная копия** того что лежит на прод-серверах. Не считается каноническим хранилищем.

**Должно быть** (в порядке убывания «правильности»):

1. **Менеджер паролей** (Bitwarden / 1Password / etc): один item на каждый placeholder с тегом `BenderVPN/prod`. Каждый item — имя placeholder'а + значение + дата создания + предыдущее значение (если была ротация).
2. **Sealed-secrets** или **vault**: для CI/CD автоматизации. У нас CI/CD пока нет → не критично.
3. **Файловая система прода** (`/etc/bvpn/*`, `<service>/.env`): operational copy. Должна совпадать с (1).

При ротации: обновить (1), затем накатить в (3): рендер шаблонов **`python ops/render_compose.py`** (или **`ops/render-compose.sh`**) с `.secrets/vault.env`, см. **`docs/DEPLOY.md` §7`. Публичные URL панели и подписки (без секретов) для локальных ops — см. **`ops/site_urls.py`** / **`ops/site.env.example`**.

## 3. Файлы prod-серверов где лежат текущие реальные секреты

| Хост | Путь | Что внутри |
|------|------|------------|
| **LV** | `/opt/remnanode/.env` | `SECRET_KEY_NODE_JWT_BUNDLE` (для LV-ноды) |
| **LV** | `/etc/bvpn/balancer.env` | `BOT_TOKEN`, `PANEL_TOKEN==REMNA_API_TOKEN`, `REMNA_API_TOKEN`, `ADMIN_CHAT_ID` (последний не секрет) |
| **LV** | `/etc/bvpn/ru-monitor.env` | `REMNA_API_TOKEN`, `REMNA_API_URL`, ssh-параметры RELAY |
| **LV** | `/opt/_archive/remnawave-legacy-*/**` (после **`P0-SEC-04`**) | Исторический снимок panel + `.env` с **теми же секретами**, что у активного AMS — офлайн, ожидается **`chattr +i`** на каталог архива. Живого **`/opt/remnawave/`** на LV быть **не должно**. |
| **AMS** | `/opt/remnawave/.env` | `JWT_AUTH_SECRET`, `JWT_API_TOKENS_SECRET`, `POSTGRES_PASSWORD`, `METRICS_PASS`, `WEBHOOK_SECRET_HEADER` |
| **AMS** | `/opt/remna-shop/.env` | `BOT_TOKEN`, `REMNA_API_TOKEN`, `REMNA_PUBLIC_KEY` |
| **AMS** | `/opt/remnawave/sub/.env` | Только **`REMNA_API_TOKEN=`** (machine JWT). Compose подставляет в YAML как **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**. **Запрет:** не встраивать JWT в **`docker-compose.yml`**. После нового token в UI: записать в **`/opt/remna-shop/.env`**, затем с машины разработки **`bash ops/sync-sub-token-ams.sh`** (не тянуть токен с LV — LV **`/opt/remnawave/`** больше не источник правды). |
| **AMS** | `/opt/remnawave/sub/docker-compose.yml` | **subscription-page**. В **`environment:`** строка только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**, не `eyJ…`. Регрессия: см. **`ops/check-ams-subscription-token-layout.sh`**. |
| **AMS** | `/opt/remnanode/docker-compose.yml` + `/opt/remnanode/.env` | digest-pinned образ + `SECRET_KEY_*` AMS-ноды (может быть drained / stopped) |
| **NL** | `/opt/remnanode/docker-compose.yml` + `/opt/remnanode/.env` | digest-pinned образ + `SECRET_KEY_*` NL-ноды |
| **NL** | `/etc/bvpn/bot-token` | `BOT_TOKEN` (одной строкой, без `=`) |

## 4. Аутстандинг secrets-related issues

**P0-SEC-04 / P0-SEC-05** — пошаговое закрытие: **`docs/RUNBOOK-P0-SEC04-SEC05.md`** (скрипты **`ops/archive_lv_remnawave_legacy.sh`**, **`ops/rotate_ams_panel_core_secrets.py`**). После выполнения на проде — строка журнала **`docs/COMMERCIAL-BACKLOG.md` §12** с датой.

| ID | Issue |
|----|-------|
| **P0-SEC-04** | **`/opt/remnawave/` на LV** — legacy-снимок секретов AMS. **Закрытие:** архив в **`/opt/_archive/remnawave-legacy-<ts>/`**, права + опц. **`chattr +i`** — см. runbook §1. |
| **P0-SEC-05** | Ротация **`JWT_AUTH_SECRET`**, **`JWT_API_TOKENS_SECRET`**, **`POSTGRES_PASSWORD`** на AMS и новый **`REMNA_API_TOKEN`** в 4 местах — см. runbook §2–3 (короткий даунтайм API/админки до перевыпуска токена). |
| **P1-OPS-TOKEN-SCOPE** | Один `REMNA_API_TOKEN` с `exp=2299` используется **четырьмя разными подсистемами**: bot, sub-page, balancer.sh, ru-monitor.py. Лучше иметь 4 разных token'а с разным scope'ом, чтобы при компрометации одного — не было полной потери. (Текущий Remnawave не поддерживает scope; нужна доработка панели или просто 4 разных `role=API` token'а.) |
| **P1-OPS-DRIFT-02** ✅ | (Закрыто этим документом.) Sanitized templates в `compose/` + этот `docs/SECRETS.md`. |

## 5. Процедура «новый секрет» / «новая нода»

0. **Массовая ротация панели AMS после компрометации LV-копии (`P0-SEC-05`):** **`docs/RUNBOOK-P0-SEC04-SEC05.md`** + **`ops/rotate_ams_panel_core_secrets.py`** (не смешивать с одиночной подстановкой placeholder'а).

1. Сгенерировать значение (см. колонку «Источник» в §1).
2. Записать в Bitwarden с тегом `BenderVPN/prod` и именем placeholder'а.
3. Если на прод — рендер из `compose/` с vault:  
   `python ops/render_compose.py compose/ams/remnawave/panel.env.tmpl .secrets/vault.env`  
   Для `docker-compose.yml.tmpl`, где `${POSTGRES_*}` должен остаться для Compose, используйте  
   `python ops/render_compose.py --only SECRET_KEY_NODE_AMS compose/ams/remnanode/node.env.tmpl`  
   (список ключей совпадает с `tmpl_only_keys` для соответствующей пары в `ops/drift-check.py` — см. **`docs/DEPLOY.md` §7**.)
4. Накатить compose: `docker compose -f /opt/<svc>/docker-compose.yml up -d`.
5. Снять новый снимок drift: `python ops/drift-check.py`.

## 6. Что НЕ секрет (но выглядит похоже)

| Значение | Где встречается | Почему не секрет |
|----------|------------------|-------------------|
| `ADMIN_TELEGRAM_ID=924498094` | bot.env | Это Telegram user-id, легко выясняется, ничем не открывает доступ. |
| `SUPPORT_GROUP_ID=-1003675105450` | bot.env | Group-id поддержки, технически публично. |
| `METRICS_USER=0287d665ff0a` | panel.env | Имя HTTP-basic пользователя для Prometheus. Слабая корреляция с паролем, можно оставить. |
| `REMNA_SQUAD_UUID`, `TEMPLATE_UUID` | bot.env, ops/* | Identifier'ы записей в БД панели. Без `REMNA_API_TOKEN` ничего не открывают. |
| `SUB_PUBLIC_DOMAIN=p4n7q.conntest.xyz` / `PANEL_DOMAIN=k9x2m1.conntest.xyz` | panel.env | Публичные хостнеймы (видны в DNS), не секреты. Но изменение требует обновления Caddy/DNS/template. |
| `REMNA_PUBLIC_KEY=pjVp95UavI7ldaz8c-3N_1tys-gJfZx4kiHfrQlRKXk` | bot.env | Reality public key — буквально public по дизайну. |
| `image: …@sha256:…` | все compose | Image digest. Public, не секрет. |
