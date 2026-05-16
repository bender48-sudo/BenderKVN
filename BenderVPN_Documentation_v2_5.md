# BenderVPN — Техническая документация

**Апрель 2026 | v2.5**

---

## Изменения v2.5 (2026-04-12 / 2026-04-15)

**Закрыто 5 крупных задач:**

1. **Фаза 6 cleanup** — удалены 20 disabled legacy хостов из Remnawave (37 → 17 хостов)
2. **RU monitoring agent** (`ru-monitor.py`) — pull-модель из РФ через Relay, проверка 16 таргетов каждые 5 минут с алертами при недоступности
3. **Selfsteal fingerprint monitor** (`selfsteal-monitor.py`) — мониторит 12 SNI на 2 нодах (24 проверки), сравнивает HTTP коды с baseline из доки, threshold-based alerting
4. **OPSEC Stage 4 — Token unification** — 4 разных Remnawave API токена объединены в один (`Bvpn-Prod`), `monitor.sh` рефакторен через `source /etc/bvpn/balancer.env`, добавлен `REMNA_API_TOKEN` alias
5. **Intel Digest** (`intel-digest.py`) — ежедневный дайджест в 09:05 UTC: новые релизы Xray-core, Remnawave, hyperion-cs commits, изменения DPI whitelist с критическим алертом если наш SNI выпадает
6. **Anti-correlation patterns** — SSH banner sanitize на 3 серверах (`VersionAddendum none` + `DebianBanner no`), cron jitter в 4 bash скриптах, найдены и закрыты 2 buried bugs (hardcoded токены в `daily-report.sh` и `backup-remnawave.sh`)

**Прочее:**
- Пользователей: 19 → 27 (рост через trial)
- Cron jobs (Latvia): 5 → 8
- TD каталог формализован (16 TD пунктов в разделе 21)

---

## 1. Архитектура

### 1.1 Серверы

| Роль | IP | Порт SSH | Провайдер | Hostname (анти-корреляция) | ОС |
|------|----|----------|-----------|----------------------------|-----|
| Latvia (панель + нода) | 176.126.162.158 | 3333 | 4xnet | `vinni204329` | Ubuntu 22.04 |
| Amsterdam (нода + бот) | 168.100.11.140 | 3344 | Hetzner | `69c5c59664ed96ea56a18764` | Ubuntu 22.04 |
| Russia Relay | 72.56.0.145 | 3344 | Selectel | `7216241-oq840923.twc1.net` | Ubuntu 22.04 |

Все 3 hostname provider-generated, нейтральные, не связывают серверы.
Все 3 в timezone `Etc/UTC`.

### 1.2 Компоненты на Latvia

| Компонент | Тип | Порт |
|-----------|-----|------|
| Remnawave Panel | Docker `remnawave/backend:latest` | 3000 (internal) |
| Remnawave Node | Docker `remnanode` | 443, 8443 |
| Caddy | systemd native v2.11.2 | 2053, 2054, 9443 |
| Subscription Page | Docker `remnawave/subscription-page` | 3010 |
| PostgreSQL 17.6 | Docker `remnawave-db` | 5432 |
| Valkey (Redis) | Docker `remnawave-redis` | 6379 |
| AdGuard Home | Docker | — |
| Beszel Hub | Docker | — |

### 1.3 Компоненты на Amsterdam

| Компонент | Тип | Порт |
|-----------|-----|------|
| Remnawave Node | Docker `remnanode` | 443, 8443 |
| Caddy Selfsteal | Docker `caddy:2.9` | 9443 |
| Telegram Bot | Docker `remna-shop-bot` | 1488 (webhook) |
| AdGuard Home | Docker | — |

### 1.4 Russia Relay (72.56.0.145)

Hysteria2 TCP forwarder. Нет Docker.

| Слушает | Форвардит | Назначение |
|---------|-----------|------------|
| `0.0.0.0:443` | `176.126.162.158:443` | Latvia REALITY |
| `0.0.0.0:8443` | `168.100.11.140:443` | Amsterdam REALITY (порт 443, не 8443!) |

Конфиг: `/etc/hysteria/client.yaml`

**v2.5:** На Relay добавлен пользователь `bvpncheck` (uid 995) с forced command `/opt/bvpn-check/check.py` для pull-мониторинга из Latvia (см. раздел 15.2). Только этот пользователь, через `from="176.126.162.158"` и `no-port-forwarding`. Root доступ — только через локальный ключ `selectel_relay` с компа админа.

---

## 2. Remnawave Panel

### 2.1 Config Profiles

| Профиль | UUID | Назначение |
|---------|------|------------|
| Latvia Selfsteal | `32b697b6-5e67-44c1-801b-644327a1420c` | Latvia нода |
| Amsterdam Selfsteal | `59e83b8b-d12a-4106-a8cd-6e8c3e2c1fff` | Amsterdam нода |

### 2.2 Inbounds

| UUID | Tag | Profile | Port | Network |
|------|-----|---------|------|---------|
| `c93ed6fe-7042-4efd-81f4-e6769fc42857` | VLESS_REALITY_LV | Latvia | 443 | tcp |
| `1093ab6d-0028-43bf-9713-9bd30aae1a81` | VLESS_XHTTP_LV | Latvia | 8443 | xhttp |
| `03a39ac4-3a14-4f3e-8659-0b4a11d22176` | VLESS_REALITY_AMS | Amsterdam | 443 | tcp |
| `00fb170f-5a8e-426f-8831-bce4fd2fe786` | VLESS_XHTTP_AMS | Amsterdam | 8443 | xhttp |

### 2.3 SNI (serverNames)

13 SNI разделены на две группы:

**4 западных (Direct-хосты, обход TCP 16-20 блока):**
- `www.microsoft.com`, `www.apple.com`, `api.github.com`, `www.bing.com`

**9 российских (Relay-хосты через 72.56.0.145):**
- `ads.x5.ru`, `eh.vk.com`, `ir-3.ozone.ru`, `sun6-21.userapi.com`
- `google-analytics.com`, `pimg.mycdn.me`, `fonts.googleapis.com`
- `id.x5.ru`, `5post-gate.x5.ru`

### 2.4 Nodes

| UUID | Имя | Disabled |
|------|-----|----------|
| `44d41ba2-5737-4b63-b935-042823be3ef5` | Latvia-Node | false |
| `600d1ae6-0327-4a80-aa0c-1f7bb7753f26` | Amsterdam-01 | false |

### 2.5 Хосты — текущее состояние

**Total: 17 хостов** (после Фазы 6 cleanup в v2.5: удалены 20 disabled legacy)

#### Virtual Host (1)

| Поле | Значение |
|------|----------|
| UUID | `305ccacd-ab74-42a4-b1a2-f80cdde69a25` |
| Remark | `🚀 BenderVPN Auto` |
| Address | `176.126.162.158:443` |
| SNI | `www.microsoft.com` |
| isHidden | false |
| isDisabled | false |
| xrayJsonTemplateUuid | `9ebbce97-ae45-4f39-a7e6-d7e675a94a73` |
| Inbound | VLESS_REALITY_LV (`c93ed6fe...`) |
| Node | Latvia-Node (`44d41ba2...`) |

Virtual Host — единственный видимый хост в подписке Happ. Он привязан к XRAY_JSON шаблону с `injectHosts` и генерирует один xray конфиг с 16 proxy outbound'ами.

#### Matrix хосты (16, все isHidden=true, isDisabled=false)

| UUID | Remark | Address | Port | SNI | Inbound | Node |
|------|--------|---------|------|-----|---------|------|
| `e7e1d97b...` | Latvia · Direct · MS | 176.126.162.158 | 443 | www.microsoft.com | LV REALITY | Latvia |
| `fa51422a...` | Latvia · Direct · Apple | 176.126.162.158 | 443 | www.apple.com | LV REALITY | Latvia |
| `fb3226f7...` | Latvia · Direct · GitHub | 176.126.162.158 | 443 | api.github.com | LV REALITY | Latvia |
| `33f70ce9...` | Latvia · Direct · Bing | 176.126.162.158 | 443 | www.bing.com | LV REALITY | Latvia |
| `a93ef6dd...` | Latvia · XHTTP · MS | 176.126.162.158 | 8443 | www.microsoft.com | LV XHTTP | Latvia |
| `9f12152d...` | Amsterdam · Direct · MS | 168.100.11.140 | 443 | www.microsoft.com | AMS REALITY | Amsterdam |
| `8f06eb8e...` | Amsterdam · Direct · Apple | 168.100.11.140 | 443 | www.apple.com | AMS REALITY | Amsterdam |
| `26381d72...` | Amsterdam · Direct · GitHub | 168.100.11.140 | 443 | api.github.com | AMS REALITY | Amsterdam |
| `dfbf200b...` | Amsterdam · Direct · Bing | 168.100.11.140 | 443 | www.bing.com | AMS REALITY | Amsterdam |
| `c7f1f9fd...` | Amsterdam · XHTTP · Apple | 168.100.11.140 | 8443 | www.apple.com | AMS XHTTP | Amsterdam |
| `88f34942...` | Relay LV · X5 | 72.56.0.145 | 443 | ads.x5.ru | LV REALITY | Latvia |
| `1ae0b3e4...` | Relay LV · VK | 72.56.0.145 | 443 | eh.vk.com | LV REALITY | Latvia |
| `131c6720...` | Relay LV · Ozon | 72.56.0.145 | 443 | ir-3.ozone.ru | LV REALITY | Latvia |
| `5cd63b49...` | Relay AMS · X5 | 72.56.0.145 | 8443 | ads.x5.ru | AMS REALITY | Amsterdam |
| `0f831e99...` | Relay AMS · VK | 72.56.0.145 | 8443 | eh.vk.com | AMS REALITY | Amsterdam |
| `e4d051a8...` | Relay AMS · Userapi | 72.56.0.145 | 8443 | sun6-21.userapi.com | AMS REALITY | Amsterdam |

Все 16 имеют `sockoptParams` с anti-DPI fragmentation:
```json
{
  "tcpNoDelay": true,
  "tcpKeepAliveIdle": 30,
  "tcpKeepAliveInterval": 15,
  "fragment": {
    "length": "50-100",
    "packets": "1-3",
    "interval": "10-20"
  }
}
```

### 2.6 API Tokens (v2.5)

**В Remnawave UI: ровно 1 активный токен** — `Bvpn-Prod` (UUID `1e5e3bd5-30e7-49fb-8e7c-587a47de5481`).

Используется всеми 5 потребителями инфраструктуры (см. раздел 20).

---

## 3. Auto-Host архитектура (injectHosts)

### 3.1 Как работает

1. Happ отправляет запрос подписки с `User-Agent: Happ/*`
2. Response Rule "Happ (iOS/macOS)" матчит по regex `^[Hh]app` → тип XRAY_JSON
3. Панель находит Virtual Host `305ccacd...` (единственный видимый, не hidden)
4. Virtual Host привязан к шаблону `9ebbce97...` (Default XRAY_JSON)
5. Шаблон содержит `remnawave.injectHosts` с 16 UUID матричных хостов
6. Панель генерирует один xray конфиг:
   - 16 proxy outbound'ов (proxy, proxy-2, ..., proxy-16)
   - `burstObservatory` пингует все 16 каждые 15 секунд
   - `Super_Balancer` (leastLoad) выбирает лучший
7. Клиент видит ОДИН хост "BenderVPN Auto", xray сам балансирует

### 3.2 XRAY_JSON шаблон

UUID: `9ebbce97-ae45-4f39-a7e6-d7e675a94a73`

Ключевые секции:
- `remnawave.injectHosts[0].selector.type = "uuids"` — 16 UUID
- `remnawave.injectHosts[0].tagPrefix = "proxy"` — теги proxy, proxy-2...
- `burstObservatory.subjectSelector = ["proxy"]`
- `burstObservatory.pingConfig.interval = "15s"`
- `routing.balancers[0].tag = "Super_Balancer"` + `strategy.type = "leastLoad"`

### 3.3 sockoptParams

Anti-DPI fragmentation применяется per-host через поле `sockoptParams` (не через defaults в шаблоне — Remnawave Zod-schema не поддерживает defaults в injectHosts).

Цепочка: `host.sockoptParams` → `streamOverrides.sockopt` → `streamSettings.sockopt` в outbound.

### 3.4 Response Rules

| # | Name | Condition | Response |
|---|------|-----------|----------|
| 1 | Browser Subscription | accept contains text/html | BROWSER |
| 2 | Mihomo Clients | UA regex FlClash/clash-verge/... | MIHOMO |
| 3 | Stash (iOS, macOS) | UA regex ^stash | STASH |
| 4 | Sing-box clients | UA regex ^sfa\|sfi\|sfm\|... | SINGBOX |
| 5 | Clash Core Clients | UA regex ^clash | CLASH |
| 6 | **Happ (iOS/macOS)** | UA regex `^[Hh]app` | **XRAY_JSON** |
| 7 | Fallback Base64 | (no conditions) | XRAY_BASE64 |

---

## 4. Telegram Bot (@Bender_KVN_bot)

### 4.1 Расположение

Amsterdam: `/opt/remna-shop/`, Docker контейнер `remna-shop-bot`

### 4.2 Конфигурация (.env)

Переменные (значения не показаны):
```
TELEGRAM_BOT_TOKEN
REMNA_API_URL
REMNA_API_TOKEN          # = Token E (Bvpn-Prod) после OPSEC Stage 4
TRIAL_DURATION_DAYS
TRIAL_TRAFFIC_GB
WEBAPP_URL
```

`REMNA_SERVER_SNI` удалён в v2.4. Бот теперь берёт SNI из `serverNames[0]` config-profile автоматически через API.

`REMNA_API_TOKEN` после v2.5 синхронизирован с `PANEL_TOKEN` на Latvia (см. раздел 20).

### 4.3 Перезапуск бота

```bash
cd /opt/remna-shop && docker compose up -d
```

Для изменений `.env` не нужен `docker compose build` — только `up -d`.
Для изменений кода — `docker compose build && docker compose up -d`.

---

## 5. Caddy — Selfsteal и Reverse Proxy

### 5.1 Архитектура selfsteal

XRay Reality dest = `127.0.0.1:9443`. При active probing (non-Reality клиент) трафик попадает в Caddy на :9443.

**v2.4:** Caddy проксирует все 13 SNI на настоящие домены через `reverse_proxy`. Active prober получает ответ НАСТОЯЩЕГО сервера — отличить от реального невозможно.

### 5.2 Caddyfile — Latvia

Путь: `/etc/caddy/Caddyfile` (systemd native)
Caddy v2.11.2

Структура:
- `p4n7q.conntest.xyz:2053` — subscription proxy → localhost:3010
- `:2054` — panel proxy → localhost:3000
- `k9x2m1.conntest.xyz:2053` — panel proxy → localhost:3000
- `lv.conntest.xyz:9443` — file_server (ConnTest page)
- **13 reverse_proxy блоков** — по одному на каждый SNI

### 5.3 Caddyfile — Amsterdam

Путь на хосте: `/opt/caddy/Caddyfile`
Путь в контейнере: `/etc/caddy/Caddyfile` (bind mount)
Caddy v2.9.1 (Docker `caddy:2.9`)

Структура:
- `conntest.xyz:9443` — file_server (ConnTest page)
- **13 reverse_proxy блоков** — по одному на каждый SNI

### 5.4 Шаблон reverse_proxy блока

```
www.microsoft.com:9443 {
    tls internal
    reverse_proxy https://www.microsoft.com {
        header_up Host www.microsoft.com
        header_up -X-Forwarded-For
        header_up -X-Forwarded-Proto
        header_up -X-Real-IP
        header_up -X-Forwarded-Host
        transport http {
            tls
            tls_server_name www.microsoft.com
            dial_timeout 5s
            versions 1.1 2
        }
    }
}
```

Пояснения:
- `tls internal` — Caddy генерирует self-signed cert (для Reality dest)
- `header_up -X-Forwarded-*` — убираем прокси-заголовки чтобы upstream не видел нас как прокси
- `tls_server_name` — SNI для исходящего TLS к настоящему серверу
- `dial_timeout 5s` — защита от зависания при недоступности upstream
- `versions 1.1 2` — поддержка HTTP/1.1 и HTTP/2

### 5.5 Bind mount workaround (Amsterdam)

Docker bind mount следит за inode, не за путём. `sed -i` создаёт новый inode → контейнер видит старый файл.

Правильный порядок изменения Caddyfile на Amsterdam:
```bash
# 1. Записать на хост
cp /tmp/Caddyfile.new /opt/caddy/Caddyfile

# 2. Синхронизировать в контейнер
cat /opt/caddy/Caddyfile | docker exec -i caddy-selfsteal tee /etc/caddy/Caddyfile > /dev/null

# 3. Reload
docker exec caddy-selfsteal caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

**НЕЛЬЗЯ:** `sed -i` (inode trap), `docker cp` (busy device), `docker compose restart` (теряет соединения).

### 5.6 Защита от active probing

**Угроза:** Цензор (DPI) обнаруживает Reality-сервер через active probing — отправляет TLS ClientHello с нашим SNI на наш IP. XRay перенаправляет probe в Caddy (dest=127.0.0.1:9443). Если Caddy отдаёт заглушку "ConnTest" — это маркер VPN.

**Защита:** Caddy проксирует к настоящему домену. Prober получает настоящий microsoft.com/apple.com. Неотличимо от реального сервера.

**Ответы реальных серверов:**

| SNI | HTTP | Size | Описание |
|-----|------|------|----------|
| www.microsoft.com | 200 | 201KB | Полная HTML страница |
| www.apple.com | 200 | 254KB | Полная HTML страница |
| api.github.com | 200 | 2.4KB | JSON API |
| www.bing.com | 200 | 58KB | Полная HTML страница |
| ads.x5.ru | 503 | 107b | HAProxy 503 (реальный) |
| eh.vk.com | 400 | 40b | VK bad header (реальный) |
| ir-3.ozone.ru | 403 | 146b | nginx 403 (реальный) |
| sun6-21.userapi.com | 403 | 148b | kittenx 403 (реальный) |
| google-analytics.com | 301 | 230b | Redirect → Google (реальный) |
| pimg.mycdn.me | 404 | 0b | Пустой 404 (реальный) |
| fonts.googleapis.com | 404 | 1.6KB | Google 404 page (реальный) |
| id.x5.ru | 200 | 7.1KB | X5 ID login (реальный) |
| 5post-gate.x5.ru | 404 | 146b | nginx 404 (реальный) |

Даже 4xx/5xx ответы — это **настоящие** ответы с настоящим fingerprint сервера. Заглушка "ConnTest" однозначно маркирует VPN, а 403 от Ozon — нет.

В v2.5 эти ожидаемые коды захардкожены в `selfsteal-monitor.py` как baseline для алертинга при отклонениях (см. раздел 15.3).

---

## 6. Карта файлов

### Latvia (176.126.162.158)

| Путь | Назначение |
|------|------------|
| `/etc/caddy/Caddyfile` | Конфиг Caddy (selfsteal + subscription proxy) |
| `/opt/caddy/html/index.html` | ConnTest заглушка (322b, используется только для lv.conntest.xyz) |
| `/etc/bvpn/balancer.env` | **Единый источник секретов** (BOT_TOKEN, PANEL_TOKEN, REMNA_API_TOKEN — все = Token E) |
| `/etc/bvpn/ru-monitor.env` | Конфиг ru-monitor.py (RELAY_HOST, RELAY_SSH_PORT, REMNA_API_TOKEN = Token E) |
| `/opt/scripts/balancer.sh` | Capacity monitor (ежечасно) |
| `/opt/scripts/monitor.sh` | Health check (каждые 5 мин) |
| `/opt/scripts/daily-report.sh` | Daily report (09:00 UTC) |
| `/opt/scripts/backup-remnawave.sh` | Бэкап БД (каждые 6 часов) |
| `/opt/scripts/ru-monitor.py` | RU reachability check через Relay (каждые 5 мин) |
| `/opt/scripts/selfsteal-monitor.py` | Selfsteal fingerprint check (каждые 5 мин) |
| `/opt/scripts/intel-digest.py` | Daily GitHub intel digest (09:05 UTC) |
| `/opt/scripts/deploy-node.sh` | Скрипт деплоя новой ноды |
| `/var/lib/bvpn-ru-monitor/state.json` | State ru-monitor (16 таргетов с историей) |
| `/var/lib/bvpn-selfsteal-monitor/state.json` | State selfsteal-monitor (24 проверки) |
| `/var/lib/bvpn-intel-digest/state.json` | State intel-digest (5 ключей: 3 repos + whitelist + last_run) |
| `/opt/diagnostics/matrix-migration/` | Артефакты миграции v2.4 |
| `/opt/diagnostics/phase6-cleanup-*/` | Артефакты Фазы 6 (v2.5) |
| `/opt/diagnostics/ru-monitor-deploy-*/` | Артефакты задачи 2a (v2.5) |
| `/opt/diagnostics/selfsteal-monitor-*/` | Артефакты задачи 2b (v2.5) |
| `/opt/diagnostics/monitor-sh-refactor-*/` | Артефакты OPSEC Stage 4 (v2.5) |
| `/opt/diagnostics/intel-digest-*/` | Артефакты задачи 3 (v2.5) |
| `/opt/diagnostics/anti-correlation-*/` | Артефакты задачи 4 (v2.5) |
| `/var/log/bvpn-balancer.log` | Лог балансировщика |
| `/var/log/bvpn-monitor.log` | Лог монитора + daily-report |
| `/var/log/bvpn-ru-monitor.log` | Лог RU monitor |
| `/var/log/bvpn-selfsteal-monitor.log` | Лог selfsteal monitor |
| `/var/log/bvpn-intel-digest.log` | Лог intel digest |
| `/var/log/bvpn-broadcast.log` | Лог рассылок |
| `/var/log/remnawave-backup.log` | Лог backup-remnawave |
| `/root/.ssh/id_ed25519` | Ключ Latvia → Relay (для bvpncheck@Relay через ru-monitor.py) |

### Amsterdam (168.100.11.140)

| Путь | Назначение |
|------|------------|
| `/opt/caddy/Caddyfile` | Конфиг Caddy (bind mount → контейнер) |
| `/opt/caddy/html/` | ConnTest страница (13KB, используется только для conntest.xyz) |
| `/opt/remna-shop/.env` | Конфиг Telegram бота (REMNA_API_TOKEN = Token E после OPSEC Stage 4) |
| `/opt/remna-shop/` | Исходники бота |

### Russia Relay (72.56.0.145)

| Путь | Назначение |
|------|------------|
| `/etc/hysteria/client.yaml` | Hysteria2 TCP forwarding |
| `/opt/bvpn-check/check.py` | Stateless проверочный скрипт для bvpncheck (forced command) |
| `~bvpncheck/.ssh/authorized_keys` | Ключ Latvia с from= и command= ограничениями |

---

## 7. Cron Jobs (Latvia)

```
20 12 * * *   acme.sh --cron > /dev/null              # сертификаты
0  */6 * * *  backup-remnawave.sh                     # бэкап БД (jitter 0-600s)
*/5 * * * *   monitor.sh                              # health check (jitter 0-60s)
0  9 * * *    daily-report.sh                         # дневной отчёт (jitter 0-600s)
0  * * * *    balancer.sh                             # capacity monitor (jitter 0-600s)
*/5 * * * *   ru-monitor.py                           # RU reachability (jitter 0-120s, внутренний flock)
*/5 * * * *   selfsteal-monitor.py                    # selfsteal fingerprint (jitter 0-90s, внутренний flock)
5  9 * * *    intel-digest.py                         # daily intel (jitter 0-60s, внутренний flock)
```

**v2.5 anti-correlation**: все скрипты имеют jitter:
- bash скрипты — `sleep $((RANDOM % N))` после `source` или shebang
- python скрипты — `time.sleep(random.randint(0, JITTER_MAX))` после `acquire_lock`

**Anti-pattern**: `intel-digest.py` запускается в `5 9 * * *` (не `0 9`) чтобы не создавать одновременный паттерн с `daily-report.sh` в 09:00 UTC.

---

## 8. Балансировщик (balancer.sh)

### 8.1 Модель

Клиентский `leastLoad` + `burstObservatory` распределяет нагрузку автоматически. Серверный балансировщик **только мониторит** и алертит.

### 8.2 Метрики

- `USERS` — количество ACTIVE пользователей (через API `/api/users`)
- `NODES` — количество активных нод (через API `/api/nodes`)
- `CAPACITY` = NODES × 50
- `LOAD_PCT` = USERS × 100 / CAPACITY
- `LV_CPU`, `AMS_CPU` — load average с обеих нод

### 8.3 Пороги capacity

| Уровень | Порог | Действие |
|---------|-------|----------|
| WARN | 80% | "Начать разворачивание новой ноды" |
| ALERT | 95% | "Закупай срочно" |
| CRITICAL | 100%+ | "Добавлять СЕЙЧАС" |

### 8.4 Пороги CPU

| Уровень | Порог | Описание |
|---------|-------|----------|
| WARN | >1.5 | Наблюдаем |
| CRITICAL | >2.0 | Деградация |

### 8.5 Anti-spam

State-файлы в `/tmp/bvpn_states/`:
- `capacity_warn_YYYY-MM-DD`, `capacity_alert_YYYY-MM-DD`, `capacity_critical_YYYY-MM-DD`
- `cpu_warn_YYYY-MM-DD`, `cpu_critical_YYYY-MM-DD`
- `summary_YYYY-MM-DD`

Один алерт каждого типа в сутки. Cleanup файлов старше 7 дней.

### 8.6 Конфиг

Секреты: `source /etc/bvpn/balancer.env` (`BOT_TOKEN`, `PANEL_TOKEN`)
`ADMIN_CHAT_ID="924498094"` хардкоден (не секрет)
Лог: `/var/log/bvpn-balancer.log`
Формат: `[timestamp] USERS=X NODES=Y CAP=Z% LV_CPU=A AMS_CPU=B`

---

## 9. Пользователи

### 9.1 Текущее состояние

Total: 27 | Active: 27

**Именные пользователи:**

| Username | telegramId | Subscription |
|----------|-----------|-------------|
| Lera | — | `JLCF43RGjyq4ML78Qcsbq7Kf2` |
| Egor | — | `oR1xjFHwd8y3027-TNSmoYwRY` |
| Diana | — | `BfjyAL2RwLZZjvkKP49sKUfJN` |
| Daniil | — | `n9UWyA1QJGa5m64WdAhub4z2E` |

**Trial пользователи:** 23 (все с telegramId, созданы через бота)

### 9.2 Internal Squads

Все пользователи в одном squad: `Vless reality` (`2cbf24bd-0bc6-4711-a789-375c3d7da908`). Фильтрации хостов по пользователям нет.

---

## 10. Subscription Settings

| Параметр | Значение |
|----------|----------|
| profileTitle | BenderVPN |
| profileUpdateInterval | 12 часов |
| serveJsonAtBaseSubscription | false |
| randomizeHosts | false |
| subscription-autoconnect | true |
| subscription-autoconnect-type | lowestdelay |
| supportLink | https://t.me/Bender_KVN_bot |

---

## 11. Russia Relay — Hysteria2

### 11.1 Конфигурация

Server: `/etc/hysteria/config.yaml` — слушает :443, TLS, password auth
Client: `/etc/hysteria/client.yaml` — TCP forwarding

### 11.2 Forwarding таблица

| Listen | Remote | Протокол |
|--------|--------|----------|
| 0.0.0.0:443 | 176.126.162.158:443 | Latvia REALITY |
| 0.0.0.0:8443 | 168.100.11.140:443 | Amsterdam REALITY (**порт 443**, не 8443) |

**Важно:** Relay :8443 → Amsterdam:443. Через relay доступен только REALITY inbound Amsterdam, XHTTP недоступен.

### 11.3 SSH доступ

**Root access (только с компа админа):**
```bash
ssh -i ~/.ssh/selectel_relay -p 3344 root@72.56.0.145
```

**Pull monitoring access (Latvia → Relay через bvpncheck):**
- User: `bvpncheck` (uid 995)
- Key: Latvia `/root/.ssh/id_ed25519`
- Restrictions в `authorized_keys`:
  ```
  from="176.126.162.158",command="/opt/bvpn-check/check.py",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty
  ```
- Любая команда от bvpncheck → запускается ТОЛЬКО `/opt/bvpn-check/check.py` (forced command)
- Это архитектурное решение: при компрометации Latvia — атакующий не получит root на Relay

---

## 12. Subscription Templates

| UUID | Name | Type | Назначение |
|------|------|------|------------|
| `9ebbce97-...` | Default | XRAY_JSON | **Auto-host шаблон** с injectHosts |
| `f4811e35-...` | Default | MIHOMO | Для Clash/Mihomo клиентов |
| `55db2391-...` | Default | STASH | Для Stash |
| `784df335-...` | Default | CLASH | Для Clash Core |
| `740aca96-...` | Default | SINGBOX | Для Sing-box |
| `2bbabb77-...` | test | SINGBOX | Тестовый |

---

## 13. Правила безопасности

### 13.1 Что НЕЛЬЗЯ делать

1. **НЕ** удалять Virtual Host (`305ccacd-...`) — без него Happ получит пустой массив
2. **НЕ** менять Default XRAY_JSON шаблон (`9ebbce97-...`) без проверки — он используется Virtual Host для injectHosts
3. **НЕ** создавать хосты с UUID которые уже в `injectHosts.values`
4. **НЕ** использовать `sed -i` на Amsterdam Caddy (bind mount inode trap)
5. **НЕ** использовать `docker cp` на bind mount (busy device)
6. **НЕ** перезапускать `docker compose restart caddy-selfsteal` (теряет соединения)
7. **НЕ** читать токены из БД Remnawave напрямую
8. **НЕ** делать PATCH config-profiles без полного конфига (partial update ломает)
9. **НЕ** хардкодить токены в скриптах (`/opt/scripts/`) — только через `source /etc/bvpn/balancer.env` или python `load_env()`
10. **НЕ** ротировать токены без pre-revoke audit (см. раздел 20.4) — проверить все скрипты на hardcoded значения
11. **НЕ** редактировать `sshd_config` без `sshd -t` syntax check + `systemctl reload ssh` (не restart!)
12. **НЕ** менять анти-correlation jitter в скриптах без понимания зачем — паттерны размывают наблюдаемость снаружи

### 13.2 Полезные команды

```bash
# TOKEN из единого источника (на Latvia)
TOKEN=$(grep "^PANEL_TOKEN=" /etc/bvpn/balancer.env | cut -d= -f2- | tr -d '"' | tr -d "\n")

# Получить список хостов
curl -s -H "Authorization: Bearer $TOKEN" "https://k9x2m1.conntest.xyz:2053/api/hosts"

# Скрыть хост (не убирает из injectHosts)
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"uuid": "...", "isHidden": true}' "https://k9x2m1.conntest.xyz:2053/api/hosts"

# Применить sockoptParams
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"uuid": "...", "sockoptParams": {"fragment": {"length": "50-100", ...}}}' \
  "https://k9x2m1.conntest.xyz:2053/api/hosts"

# Получить шаблон
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://k9x2m1.conntest.xyz:2053/api/subscription-templates/9ebbce97-..."

# Reload Caddy Latvia
systemctl reload caddy

# Reload Caddy Amsterdam
cat /opt/caddy/Caddyfile | docker exec -i caddy-selfsteal tee /etc/caddy/Caddyfile > /dev/null
docker exec caddy-selfsteal caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile

# Перезапуск бота
cd /opt/remna-shop && docker compose up -d

# JWT UUID decode (для идентификации токена без показа значения)
python3 -c "import sys, json, base64; t=open('/etc/bvpn/balancer.env').read(); \
  v=[l for l in t.split() if 'PANEL_TOKEN' in l][0].split('=',1)[1].strip('\"'); \
  p=v.split('.')[1]; p+='='*(-len(p)%4); \
  print(json.loads(base64.urlsafe_b64decode(p))['uuid'])"

# SSH banner check (anti-correlation)
for ip in 176.126.162.158 168.100.11.140 72.56.0.145; do \
  port=$([ "$ip" = "176.126.162.158" ] && echo 3333 || echo 3344); \
  banner=$(timeout 5 bash -c "exec 3<>/dev/tcp/$ip/$port && head -1 <&3" 2>/dev/null); \
  echo "$ip:$port — $banner"; \
done
```

---

## 14. Масштабирование

### 14.1 Текущая capacity

- 2 ноды × 50 users = **100 users capacity**
- Текущая нагрузка: **27/100 (27%)**
- Правило: при 80% начинать деплой 3-й ноды

### 14.2 Добавление ноды

1. Развернуть сервер (скрипт: `/opt/scripts/deploy-node.sh`)
2. Добавить config-profile в Remnawave Panel
3. Создать матричные хосты для новой ноды (4 Direct + 1 XHTTP)
4. Добавить UUID новых хостов в `injectHosts.values` шаблона
5. Добавить reverse_proxy блоки в Caddyfile новой ноды
6. Применить sshd banner sanitize (`VersionAddendum none`, `DebianBanner no`)
7. Применить timezone UTC, hostname проверить на нейтральность
8. Развернуть мониторинговые хуки (если нужно — добавить новые SNI в `selfsteal-monitor.py` EXPECTATIONS)
9. `balancer.sh` автоматически пересчитает capacity

---

## 15. Мониторинг

### 15.1 monitor.sh — health check

Каждые 5 минут (jitter 0-60s). Проверяет:
- XRay alive (Latvia + Amsterdam)
- Subscription endpoint (HTTP 200)
- Selfsteal alive (`id.x5.ru:9443` → HTTP 200)
- Panel alive (localhost:3000)
- Bot alive (docker ps на Amsterdam)
- Disk usage Latvia (>90% → WARNING)
- Relay tunnel alive (nc -z 72.56.0.145 443)

Алерты в Telegram админу, anti-spam через state files в `/tmp/bvpn_states/`.

Секреты: `source /etc/bvpn/balancer.env` (BOT_TOKEN, PANEL_TOKEN).

### 15.2 ru-monitor.py — pull check из РФ

**Архитектура:**

```
Latvia cron (каждые 5 мин)
    ↓ flock + jitter 0-120s
ru-monitor.py
    ↓ GET /api/hosts из Remnawave (16 таргетов)
    ↓ SSH bvpncheck@Relay (forced command)
Relay /opt/bvpn-check/check.py
    ↓ stateless: получает JSON со списком таргетов на stdin
    ↓ TCP+TLS handshake к каждому, cert SHA256 fingerprint
    ↓ Возвращает JSON {host, status, code, sha256_cert} per target
Latvia (обратно)
    ↓ Сравнить с предыдущим state, выявить transitions
    ↓ Если cert поменялся — CERT CHANGED alert
    ↓ Если статус деградировал → WARNING/ALERT
    ↓ Save state, send Telegram если есть transitions
```

**Конфиг:** `/etc/bvpn/ru-monitor.env` (RELAY_HOST, RELAY_SSH_PORT, RELAY_SSH_USER=bvpncheck, RELAY_SSH_KEY, REMNA_API_TOKEN = Token E).

**Лог:** `/var/log/bvpn-ru-monitor.log`. Формат: `[timestamp] total=N ok=M fail=K transitions=T`.

**State:** `/var/lib/bvpn-ru-monitor/state.json` — 16 таргетов с историей.

### 15.3 selfsteal-monitor.py — fingerprint check

**Цель:** убедиться что наши selfsteal endpoints отдают **именно те HTTP коды** которые ожидает active prober (см. раздел 5.6). Любое отклонение — потенциальная поломка selfsteal или active probing.

**Архитектура:**

- 12 SNI × 2 ноды = 24 проверки каждые 5 минут (jitter 0-90s)
- Latvia: локально через `curl -k --resolve SNI:9443:127.0.0.1`
- Amsterdam: через SSH с Latvia → curl на amsterdam:9443
- Сравнение с hardcoded `EXPECTATIONS` dict (взято из доки 5.6)
- 3-tier classification: ok / warning (tolerated) / critical
- Threshold-based alerting: critical_count >= 2 consecutive → alert
- antispam: alerted=true в state, clear после recovered

**Исключения (TD-2):** `www.microsoft.com` исключён из EXPECTATIONS из-за нестабильности Caddy reverse_proxy + HTTP/2 для Microsoft Edge anycast (6 spurious 000 за 22h в начальный период тестирования). Реальный selfsteal для MS работает, только мониторинг отключён до решения TD-1 (Caddy http_transport tuning).

**Конфиг:** не нужен (использует SSH ключ Latvia + хардкоженные expectations).

**Лог:** `/var/log/bvpn-selfsteal-monitor.log`. Формат: `[timestamp] total=24 ok=N critical=M warning=K retried=R transitions=T`.

**State:** `/var/lib/bvpn-selfsteal-monitor/state.json` — 24 entries (key=`node:sni`).

### 15.4 intel-digest.py — daily upstream intel

См. раздел 22.

### 15.5 daily-report.sh

Запускается в 09:00 UTC (jitter 0-600s). Шлёт сводку: количество пользователей, capacity, статус нод, остатки месячной квоты на провайдерах. Использует `${BOT_TOKEN}` и `${PANEL_TOKEN}` из `source /etc/bvpn/balancer.env`.

### 15.6 Логи

| Лог | Путь | Что пишет |
|-----|------|-----------|
| Балансировщик | `/var/log/bvpn-balancer.log` | USERS, NODES, CAP%, CPU |
| Монитор | `/var/log/bvpn-monitor.log` | Health checks, alerts, daily report |
| RU monitor | `/var/log/bvpn-ru-monitor.log` | total/ok/fail/transitions, CERT CHANGED |
| Selfsteal monitor | `/var/log/bvpn-selfsteal-monitor.log` | total/ok/critical/warning, PENDING |
| Intel digest | `/var/log/bvpn-intel-digest.log` | digest sent / no changes / errors |
| Backup | `/var/log/remnawave-backup.log` | pg_dump status, размер бэкапа |
| Caddy access | `/var/log/caddy/sub-access.log` | Subscription requests (JSON) |
| Broadcast | `/var/log/bvpn-broadcast.log` | Telegram рассылки |

---

## 16. Правила работы с Claude Code

1. **Бэкап ПЕРЕД изменением**, всегда с timestamp
2. **Rollback команда** явно прописана перед каждым действием
3. **Python f-string** — одинарные кавычки внутри двойных
4. **TOKEN:** `grep "^PANEL_TOKEN=" /etc/bvpn/balancer.env | cut -d= -f2- | tr -d '"' | tr -d "\n"` (унифицировано в OPSEC Stage 4)
5. **Heredoc внутри SSH** — использовать `/tmp/script.py` файл, не inline
6. **PATCH config-profiles** — всегда полный конфиг
7. **sed замены** — использовать `^` якорь для строк .env
8. **Amsterdam Caddy** — `cp` на хост + `cat | docker exec -i tee` + reload
9. **НЕ** `docker cp` на bind mount (busy device)
10. **Длинные выводы** — сохранять в `/opt/diagnostics/` + `scp` на локальный комп пользователя
11. **НЕ** читать токены из БД
12. **Перед изменением** — показывать текущее значение
13. **НЕ продолжать** к следующему шагу автоматически — ждать подтверждения
14. **Описывать ЗАДАЧУ полностью** с контекстом. Claude формирует команды лучше когда понимает зачем
15. **Разведка → план → действия.** Не "сразу делать"
16. **Caddyfile** — менять через Python или целиком, не sed (хрупко для блоков)
17. **Таблицы** для структурированных данных, минимум текста
18. **Active probing защита** — все selfsteal SNI через reverse_proxy
19. **Show real output, NOT summary** (TD-6) — когда пользователь просит вывод файла/команды/diff, выводить РЕАЛЬНЫЙ stdout. Если файл большой или содержит секреты — сохранить через sed-маскирование и `scp` на локальный комп. Никогда не заменять реальный вывод на таблицу "что я увидел".
20. **Pre-revoke audit** (TD-13) — перед ротацией любого токена сделать global grep `/opt/scripts/`, `/etc/`, Amsterdam `/opt/remna-shop/` на наличие hardcoded значения. Иначе риск buried bug как в `daily-report.sh` (см. раздел 19).
21. **JWT UUID decode** (TD-7) — для сравнения токенов использовать UUID из payload, не md5 значения (md5 чувствителен к whitespace/newline).
22. **SSH banner / sshd_config** — `sshd -t` syntax check ДО `systemctl reload ssh`. НЕ restart (теряются активные сессии).

---

## 17. SNI стратегия

### 17.1 Двухуровневая модель

**Direct (4 западных SNI)** — клиент подключается напрямую к Latvia/Amsterdam:
- Обходят TCP 16-20 блок цензора (whitelisted в hyperion-cs)
- `www.microsoft.com`, `www.apple.com`, `api.github.com`, `www.bing.com`

**Relay (9 российских SNI)** — клиент подключается через Russia Relay (72.56.0.145):
- Российский destination IP, цензор видит трафик к "своему" серверу
- Используют реальные российские домены для маскировки
- `ads.x5.ru`, `eh.vk.com`, `ir-3.ozone.ru`, `sun6-21.userapi.com`, `google-analytics.com`, `pimg.mycdn.me`, `fonts.googleapis.com`, `id.x5.ru`, `5post-gate.x5.ru`

### 17.2 Selfsteal для всех SNI

Все 13 SNI настроены как reverse_proxy в Caddy на обеих нодах. Active prober получает ответ настоящего сервера.

### 17.3 Whitelist watch (v2.5)

`intel-digest.py` ежедневно проверяет директорию `ru/tcp-16-20_dwc/results/` в hyperion-cs/dpi-checkers. При появлении нового файла whitelist (типа `based_on_opendns_2026-XX-YY.txt`):
- Diff старого и нового файла
- Если кто-то из 4 наших Direct SNI (apple.com, bing.com, github.com, microsoft.com) выпал из whitelist → **критический алерт** с инструкцией заменить SNI

Текущий whitelist: `based_on_opendns_2025-07-02.txt`. Все 4 наших SNI присутствуют.

---

## 18. Артефакты миграций и задач

### 18.1 v2.4 — Matrix migration

`/opt/diagnostics/matrix-migration/` — артефакты миграции v2.4 (16-host matrix, Virtual Host, injectHosts).

### 18.2 v2.5 — артефакты задач

| Папка | Задача |
|---|---|
| `/opt/diagnostics/phase6-cleanup-*/` | Удаление 20 disabled legacy хостов |
| `/opt/diagnostics/ru-monitor-deploy-*/` | Деплой ru-monitor.py |
| `/opt/diagnostics/selfsteal-monitor-*/` | Деплой selfsteal-monitor.py (5 итераций v1-v5) |
| `/opt/diagnostics/monitor-sh-refactor-*/` | OPSEC Stage 4 token unification + monitor.sh refactor |
| `/opt/diagnostics/intel-digest-*/` | Деплой intel-digest.py + hyperion recon |
| `/opt/diagnostics/anti-correlation-*/` | SSH banner sanitize + cron jitter + buried bugs fixes |

Каждая папка содержит SUMMARY.md + бэкапы + логи verification.

Локальный архив у админа: `~/bvpn-artifacts/{phase2a,phase2b,phase2c,phase3,phase4}/`.

---

## 19. История изменений

### v2.5 (2026-04-12 / 2026-04-15)

**Фаза 6 (Cleanup):**
- Удалены 20 disabled legacy хостов (37 → 17). Матрица: 1 Virtual + 16 матричных.

**RU monitoring agent (ru-monitor.py):**
- Pull-модель: Latvia cron каждые 5 мин → SSH к Relay → stateless check.py → JSON обратно
- 16 таргетов проверяются TCP+TLS handshake с cert fingerprint
- Transitions detection + Telegram alerts
- Bvpncheck user на Relay с forced command (анти-эскалация при компрометации Latvia)
- Конфиг `/etc/bvpn/ru-monitor.env`, state `/var/lib/bvpn-ru-monitor/state.json`

**Selfsteal monitor (selfsteal-monitor.py):**
- 12 SNI × 2 ноды = 24 проверки каждые 5 мин
- Hardcoded EXPECTATIONS dict из доки 5.6
- 3-tier classification (ok/warning/critical)
- Threshold-based alerting (2 consecutive critical → alert)
- 5 итераций v1-v5 с разработкой багов: warning logging, recovered format, CURL_TIMEOUT tuning, threshold suppression, microsoft.com исключение (TD-1, TD-2)
- State `/var/lib/bvpn-selfsteal-monitor/state.json`

**OPSEC Stage 4 — Token unification:**
- Найдено 4 разных Remnawave API токена, унифицировано в один: `Bvpn-Prod` (UUID `1e5e3bd5-...`)
- 4 потребителя мигрированы: `balancer.env` (PANEL_TOKEN + REMNA_API_TOKEN alias), `monitor.sh` (refactor через source), `ru-monitor.env`, Amsterdam `remna-shop/.env`
- Все старые 4 токена revoked в UI
- API создание токенов недоступно для role=API (только UI или ADMIN)
- Bug 2 (incomplete grep): пропущены `daily-report.sh` и `backup-remnawave.sh` — обнаружены и закрыты в задаче 4

**Intel Digest (intel-digest.py):**
- Daily 09:05 UTC дайджест через GitHub API
- 3 источника: XTLS/Xray-core releases, remnawave/panel releases, hyperion-cs/dpi-checkers commits (с фильтрацией `dpi-ch` → `unrelated`)
- Whitelist watch: list directory `ru/tcp-16-20_dwc/results/`, при новом файле → diff, критический алерт если наш SNI выпал
- Без GitHub token (60 req/h хватает с запасом)
- State `/var/lib/bvpn-intel-digest/state.json`

**Anti-correlation:**
- SSH banner sanitize на 3 серверах: `VersionAddendum none` + `DebianBanner no` (убирает `Ubuntu-3ubuntu0.14` суффикс)
- Cron jitter в 4 bash скриптах: `monitor.sh` (60s), `balancer.sh`/`daily-report.sh`/`backup-remnawave.sh` (600s)
- 5 направлений разведано, 3 решено не трогать (hostnames OK, timezone UTC по дизайну, MOTD стандартный)
- Buried bugs найдены: `daily-report.sh` имел hardcoded BOT+PANEL_TOKEN (PANEL_TOKEN был revoked → 401 ежедневно скрытно), `backup-remnawave.sh` имел hardcoded BOT_TOKEN (security smell, не активный bug)
- Оба скрипта рефакторены через source pattern

### v2.4 (2026-04-08/09)

**Миграция на матричную модель:**
- Созданы 16 матричных хостов (4 LV Direct + 1 LV XHTTP + 4 AMS Direct + 1 AMS XHTTP + 3 Relay LV + 3 Relay AMS)
- Staged rollout (Фазы 1–5): создание → тест → включение → верификация → отключение старых
- Virtual Host `305ccacd-...` с injectHosts → один хост в подписке
- Anti-DPI sockoptParams на всех 16 хостах
- Response Rule "Happ → XRAY_JSON"

**Selfsteal reverse_proxy:**
- Все 13 SNI на обеих нодах: reverse_proxy вместо file_server
- Multi-SNI блок удалён полностью
- Monitor.sh обновлён: selfsteal check через id.x5.ru (HTTP 200)

**Балансировщик:**
- Полная перезапись balancer.sh: capacity-based вместо connection-based
- Удалены bulk_disable/enable, LV_SECONDARY_UUIDS
- Cron: `*/5` → `0 * * * *` (ежечасно)

**Бот:**
- Удалён REMNA_SERVER_SNI из .env
- SNI берётся из config-profile автоматически

### v2.3 (2026-04-05/07)

- Первоначальная документация
- 12 хостов, ручная балансировка
- Selfsteal через file_server (ConnTest заглушка)
- Connection-based балансировщик с bulk_disable/enable

---

## 20. OPSEC и управление секретами (v2.5)

### 20.1 Источники секретов

**Latvia (единый источник):**
```
/etc/bvpn/balancer.env       — BOT_TOKEN, PANEL_TOKEN, REMNA_API_TOKEN (alias на PANEL_TOKEN)
/etc/bvpn/ru-monitor.env     — RELAY_HOST/PORT/USER/KEY + REMNA_API_TOKEN
```

**Amsterdam (отдельный источник для бота):**
```
/opt/remna-shop/.env         — TELEGRAM_BOT_TOKEN, REMNA_API_TOKEN (= Token E), ...
```

Все REMNA_API_TOKEN значения = Token E. Один источник истины — Remnawave UI, токен `Bvpn-Prod`.

### 20.2 Скрипты — паттерн загрузки

**Bash скрипты (Latvia):**
```bash
#!/bin/bash
source /etc/bvpn/balancer.env

# Anti-correlation jitter
sleep $((RANDOM % N))

# ... код использует ${BOT_TOKEN}, ${PANEL_TOKEN} ...
```

**Python скрипты:**
```python
env = load_env("/etc/bvpn/balancer.env")  # или ru-monitor.env
api_token = env.get("REMNA_API_TOKEN")
bot_token = env.get("BOT_TOKEN")
```

### 20.3 Rotation процедура

Когда нужно ротировать токен Remnawave API:

1. **Pre-revoke audit** (TD-13, обязательный шаг):
   ```bash
   # Latvia
   for f in /opt/scripts/*.sh /opt/scripts/*.py; do
     grep -nE "^(BOT|PANEL|REMNA_API)_TOKEN\s*=\s*[\"']" "$f" 2>/dev/null
   done
   for f in /etc/bvpn/*.env; do
     grep -nE "^[A-Z_]*TOKEN" "$f" 2>/dev/null | cut -d= -f1
   done
   # Amsterdam
   ssh -p 3344 root@168.100.11.140 'grep -E "TOKEN" /opt/remna-shop/.env | cut -d= -f1'
   ```
   Все hardcoded токены — рефакторить через source pattern до ротации.

2. **Создать новый токен в Remnawave UI** (API CRUD недоступен для role=API)

3. **Сохранить значение в `/tmp/new-token.txt` на Latvia** (`umask 077`, без вывода в чат)

4. **Verify HTTP 200** через curl с новым токеном

5. **Apply через Python скрипт** (идемпотентный update):
   - `/etc/bvpn/balancer.env` — `PANEL_TOKEN` и `REMNA_API_TOKEN`
   - `/etc/bvpn/ru-monitor.env` — `REMNA_API_TOKEN`
   - Amsterdam `/opt/remna-shop/.env` — `REMNA_API_TOKEN`

6. **Verify через UUID decode** что во всех файлах одинаковое значение

7. **Restart Amsterdam bot**: `cd /opt/remna-shop && docker compose up -d`

8. **Test runs** всех скриптов (`monitor.sh`, `balancer.sh`, `ru-monitor.py`)

9. **Подождать 1 cron цикл** (5-15 мин), проверить логи на 401/Unauthorized

10. **Cleanup `/tmp/new-token.txt`** на обеих сторонах

11. **Revoke старого токена в UI** (Remnawave Panel → API Tokens)

12. **Final verification**: API запрос со старым токеном должен дать HTTP 401, с новым — HTTP 200

### 20.4 Anti-correlation меры

**SSH banners** — все 3 сервера: `SSH-2.0-OpenSSH_8.9p1` (без Ubuntu суффикса).

Применяется через `sshd_config`:
```
VersionAddendum none
DebianBanner no
```

**Cron jitter** — все periodic скрипты имеют random delay:
- bash: `sleep $((RANDOM % N))` после `source` или shebang
- python: `time.sleep(random.randint(0, JITTER_MAX))` после `acquire_lock`

**Anti-pattern в timing** — `intel-digest.py` смещён на `5 9 * * *` (не `0 9`) чтобы не создавать одновременный паттерн с `daily-report.sh` в 09:00 UTC.

**Hostnames** — provider-generated, нейтральные. **Не менять при добавлении нод** на что-то типа `bvpn-node-3`.

**Timezone** — все серверы в Etc/UTC по дизайну (упрощает отладку, корреляция через timezone — слабый сигнал).

---

## 21. Технический долг

| ID | Severity | Описание | Источник |
|---|---|---|---|
| TD-1 | medium | Caddy reverse_proxy HTTP/2 tuning для MS Edge anycast (versions 1.1, dial_timeout 10s, response_header_timeout 10s, max_conns_per_host 1) | задача 2b |
| TD-2 | low | После TD-1 — re-enable `www.microsoft.com` в `selfsteal-monitor.py` EXPECTATIONS | задача 2b |
| TD-3 | DONE | OPSEC Stage 4 — closed in задаче 2c | — |
| TD-4 | medium | Отдельный мониторинг-бот (не делить @Bender_KVN_bot между клиентами и алертами админа) | задача 2a |
| TD-5 | low | `humanize_since()` в `selfsteal-monitor.py` — добавить unit test | задача 2b |
| TD-6 | process | Claude Code working agreement v2: "show real output not summary". Mitigation: explicit "save to file and scp" в каждом промте. Нарушалось 5+ раз. | задачи 2b/2c/3 |
| TD-7 | low | Token discovery scripts — использовать JWT UUID decode, не md5 (md5 чувствителен к whitespace) | задача 2c |
| TD-8 | DONE | Revoke 4 legacy токенов — closed | — |
| TD-9 | low | Intel digest readability — `\n\n` между секциями (вместо `\n`) для воздуха | задача 3 |
| TD-10 | low | Intel digest release body preview — не рендерится. Проверить пустой ли body или формат wrong | задача 3 |
| TD-11 | future v2 | Intel digest — добавить парсинг net4people/bbs Discussions через GraphQL для community signal | задача 3 |
| TD-12 | future v2 | Intel digest — добавить GitHub PAT для higher rate limit когда будем crawl-ить больше источников | задача 3 |
| TD-13 | important | Pre-revoke audit (раздел 20.3 шаг 1) — формализован после buried bugs в задаче 4 | задача 4 |
| TD-14 | low | SSH banner — рассмотреть индивидуальные `VersionAddendum` строки на разные серверы (текущая идентичность сама по себе слабый сигнал) | задача 4 |
| TD-15 | low | `broadcast-2026-04-09.sh` — dead code, удалить | задача 4 |
| TD-16 | low | `backup-remnawave.sh` post-refactor verification — дождаться следующего cron цикла, проверить что нет 401 в `/var/log/remnawave-backup.log` | задача 4 |

---

## 22. Intel Digest (intel-digest.py)

### 22.1 Цель

Ежедневный дайджест upstream changes в экосистеме обхода цензуры. Информирование, не auto-apply.

### 22.2 Источники

| Source | Type | Frequency |
|---|---|---|
| XTLS/Xray-core | GitHub releases | 1-2/мес |
| remnawave/panel | GitHub releases | 1-2/мес |
| hyperion-cs/dpi-checkers | commits (filtered) | редко (только tcp16-20) |
| hyperion-cs whitelist | new file in `ru/tcp-16-20_dwc/results/` | очень редко |

### 22.3 Filter logic для hyperion-cs commits

Regex: `tcp[\s-]?16[\s-]?20\b` (case-insensitive). Ловит варианты `tcp16-20`, `tcp-16-20`, `tcp 16-20`, с/без бэктиков.

Всё что не подходит → `filtered_out` (не показывается в дайджесте, считается).

### 22.4 Whitelist watch

1. List `ru/tcp-16-20_dwc/results/` через GitHub API
2. Sort .txt файлов лексикографически (даты в именах: `based_on_opendns_YYYY-MM-DD.txt`)
3. Самый свежий = current latest
4. Сравнить с `state.latest_whitelist_file`
5. Если новый файл → diff old/new через raw.githubusercontent.com
6. Если кто-то из `OUR_SNI_IN_WHITELIST` (`apple.com`, `bing.com`, `github.com`, `microsoft.com`) в `removed` → **CRITICAL alert** отдельным сообщением до дайджеста

### 22.5 Execution safety

- `flock` на `/tmp/bvpn-intel-digest.lock` — single instance
- Jitter 0-60s после lock
- Atomic state.json через tempfile + rename
- State corruption handling: rename в `.corrupted.TS`
- Save state ДО Telegram send (прогресс не теряется)
- `is_first_run` detection: пустой state → save baseline, не шлём

### 22.6 Rate limit

GitHub API без токена — 60 req/hour на IP. Один прогон делает ~5-8 запросов. С запасом.

### 22.7 Конфиг

Использует `BOT_TOKEN` из `/etc/bvpn/balancer.env`. ADMIN_CHAT_ID хардкоден.

State: `/var/lib/bvpn-intel-digest/state.json`
Лог: `/var/log/bvpn-intel-digest.log`
Cron: `5 9 * * * /opt/scripts/intel-digest.py 2>> /var/log/bvpn-intel-digest.log`

---
