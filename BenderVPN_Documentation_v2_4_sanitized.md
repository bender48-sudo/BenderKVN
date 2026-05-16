# BenderVPN — Техническая документация

**Апрель 2026 | v2.4**

---

## Изменения v2.4 (2026-04-08/09)

- Полная миграция на матрицу 16 хостов (Фазы 1–5 завершены)
- Virtual Host "BenderVPN Auto" через injectHosts — один хост в подписке, 16 outbound'ов под капотом
- Anti-DPI fragmentation (`sockoptParams`) на всех 16 хостах
- Selfsteal reverse_proxy на всех 13 SNI (защита от active probing)
- Балансировщик переписан: capacity-based monitoring вместо bulk_disable/enable
- Удалён `REMNA_SERVER_SNI` из бота — SNI берётся из config-profile автоматически
- Response rule "Happ → XRAY_JSON" для клиента Happ

---

## 1. Архитектура

### 1.1 Серверы

| Роль | IP | Порт SSH | Провайдер | ОС |
|------|----|----------|-----------|-----|
| Latvia (панель + нода) | 176.126.162.158 | 3333 | 4xnet | Ubuntu 22.04 |
| Amsterdam (нода + бот) | 168.100.11.140 | 3344 | Hetzner | Ubuntu 22.04 |
| Russia Relay | 72.56.0.145 | 3344 | Timeweb | Ubuntu 22.04 |

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

**Total: 37 хостов** (17 active, 20 disabled)

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

Все 16 имеют `sockoptParams` с anti-DPI fragmentation (параметры в серверных конфигах, не документируются здесь).

#### Disabled legacy (20 хостов)

8 старых fonts/pimg (isHidden=true) + 12 старых активных (Латвия, Нидерланды, Резервы). Все isDisabled=true. Помечены для удаления в Фазе 6.

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

Переменные (значения хранятся в password manager):
```
TELEGRAM_BOT_TOKEN=<BOT_TOKEN>
REMNA_API_URL=<PANEL_URL>
REMNA_API_TOKEN=<API_JWT>
TRIAL_DURATION_DAYS
TRIAL_TRAFFIC_GB
WEBAPP_URL
ADMIN_TELEGRAM_ID=<ADMIN_CHAT_ID>
SUPPORT_GROUP_ID=<GROUP_ID>
```

`REMNA_SERVER_SNI` **удалён** в v2.4. Бот теперь берёт SNI из `serverNames[0]` config-profile автоматически через API.

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
- `<SUB_DOMAIN>:2053` — subscription proxy → localhost:3010
- `:2054` — panel proxy → localhost:3000
- `<PANEL_DOMAIN>:2053` — panel proxy → localhost:3000
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

---

## 6. Карта файлов

### Latvia (176.126.162.158)

| Путь | Назначение |
|------|------------|
| `/etc/caddy/Caddyfile` | Конфиг Caddy (selfsteal + subscription proxy) |
| `/opt/caddy/html/index.html` | ConnTest заглушка (322b, используется только для lv.conntest.xyz) |
| `/etc/bvpn/balancer.env` | Секреты балансировщика (BOT_TOKEN, PANEL_TOKEN) |
| `/opt/scripts/balancer.sh` | Capacity monitor (ежечасно) |
| `/opt/scripts/monitor.sh` | Health check (каждые 5 мин) |
| `/opt/scripts/daily-report.sh` | Daily report (09:00 UTC) |
| `/opt/scripts/backup-remnawave.sh` | Бэкап БД (каждые 6 часов) |
| `/opt/diagnostics/matrix-migration/` | Артефакты миграции (бэкапы, UUIDs) |
| `/var/log/bvpn-balancer.log` | Лог балансировщика |
| `/var/log/bvpn-monitor.log` | Лог монитора |
| `/var/log/bvpn-broadcast.log` | Лог рассылок |

### Amsterdam (168.100.11.140)

| Путь | Назначение |
|------|------------|
| `/opt/caddy/Caddyfile` | Конфиг Caddy (bind mount → контейнер) |
| `/opt/caddy/html/` | ConnTest страница (13KB, используется только для conntest.xyz) |
| `/opt/remna-shop/.env` | Конфиг Telegram бота |
| `/opt/remna-shop/` | Исходники бота |

---

## 7. Cron Jobs (Latvia)

```
20 12 * * *   acme.sh --cron (сертификаты)
0  */6 * * *  backup-remnawave.sh (бэкап БД)
*/5 * * * *   monitor.sh (health check)
0  9 * * *    daily-report.sh (дневной отчёт)
0  * * * *    balancer.sh (capacity monitor, ежечасно)
```

---

## 8. Балансировщик (balancer.sh)

### 8.1 Новая модель (v2.4)

Клиентский `leastLoad` + `burstObservatory` распределяет нагрузку автоматически. Серверный балансировщик **только мониторит** и алертит.

### 8.2 Метрики

- `USERS` — количество ACTIVE пользователей (через API `/api/users`)
- `NODES` — количество активных нод (через API `/api/nodes`)
- `CAPACITY` = NODES * 50
- `LOAD_PCT` = USERS * 100 / CAPACITY
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

### 8.6 Daily summary

В 09:XX UTC — отчёт с текущими значениями users/capacity/CPU.

### 8.7 Конфиг

Секреты: `/etc/bvpn/balancer.env` (переменные: `BOT_TOKEN`, `PANEL_TOKEN`)
Лог: `/var/log/bvpn-balancer.log`
Формат: `[timestamp] USERS=X NODES=Y CAP=Z% LV_CPU=A AMS_CPU=B`

---

## 9. Пользователи

### 9.1 Статистика

Total: 19 | Active: 19

> Конкретные имена, Telegram ID и subscription ключи пользователей
> НЕ хранятся в документации. Используйте Remnawave Panel UI
> или API `GET /api/users` для актуальных данных.

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

```bash
ssh -i ~/.ssh/selectel_relay -p 3344 root@72.56.0.145
```

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
9. **НЕ** хранить токены, ключи и пользовательские данные в документации
10. **НЕ** коммитить файлы с секретами в git

### 13.2 Полезные команды

```bash
# Получить список хостов
curl -s -H "Authorization: Bearer $TOKEN" "$PANEL_URL/api/hosts"

# Скрыть хост (не убирает из injectHosts)
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data '{"uuid": "...", "isHidden": true}' "$PANEL_URL/api/hosts"

# Получить шаблон
curl -s -H "Authorization: Bearer $TOKEN" \
  "$PANEL_URL/api/subscription-templates/9ebbce97-..."

# Reload Caddy Latvia
systemctl reload caddy

# Reload Caddy Amsterdam
cat /opt/caddy/Caddyfile | docker exec -i caddy-selfsteal tee /etc/caddy/Caddyfile > /dev/null
docker exec caddy-selfsteal caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile

# Перезапуск бота
cd /opt/remna-shop && docker compose up -d

# Токен из .env бота
TOKEN=$(grep "^REMNA_API_TOKEN=" /opt/remna-shop/.env | cut -d= -f2 | tr -d "\r\n")
```

---

## 14. Масштабирование

### 14.1 Текущая capacity

- 2 ноды * 50 users = **100 users capacity**
- Текущая нагрузка: **19/100 (19%)**
- Правило: при 80% начинать деплой 3-й ноды

### 14.2 Добавление ноды

1. Развернуть сервер (скрипт: `/opt/scripts/deploy-node.sh`)
2. Добавить config-profile в Remnawave Panel
3. Создать матричные хосты для новой ноды (4 Direct + 1 XHTTP + 3 Relay)
4. Добавить UUID новых хостов в `injectHosts.values` шаблона
5. Обновить Russia Relay forwarding (Step K' в deploy-node.sh)
6. Добавить reverse_proxy блоки в Caddyfile новой ноды
7. `balancer.sh` автоматически пересчитает capacity

---

## 15. Мониторинг

### 15.1 monitor.sh

Каждые 5 минут. Проверяет:
- XRay alive (Latvia + Amsterdam)
- Subscription endpoint (HTTP 200)
- Selfsteal alive (`id.x5.ru:9443` → HTTP 200)
- Panel alive (localhost:3000)
- Bot alive (docker ps)

### 15.2 Логи

| Лог | Путь | Что пишет |
|-----|------|-----------|
| Балансировщик | `/var/log/bvpn-balancer.log` | USERS, NODES, CAP%, CPU |
| Монитор | `/var/log/bvpn-monitor.log` | Health checks, alerts |
| Caddy access | `/var/log/caddy/sub-access.log` | Subscription requests (JSON) |
| Broadcast | `/var/log/bvpn-broadcast.log` | Telegram рассылки |

---

## 16. Правила работы с Claude Code

1. **Бэкап ПЕРЕД изменением**, всегда с timestamp
2. **Rollback команда** явно прописана перед каждым действием
3. **Python f-string** — одинарные кавычки внутри двойных
4. **TOKEN:** `grep "^REMNA_API_TOKEN=" /opt/remna-shop/.env | cut -d= -f2 | tr -d "\r\n"`
5. **Heredoc внутри SSH** — использовать `/tmp/script.py` файл, не inline
6. **PATCH config-profiles** — всегда полный конфиг
7. **sed замены** — использовать `^` якорь для строк .env
8. **Amsterdam Caddy** — `cp` на хост + `cat | docker exec -i tee` + reload
9. **НЕ** `docker cp` на bind mount (busy device)
10. **Длинные выводы** — сохранять в `/opt/diagnostics/`
11. **НЕ** читать токены из БД
12. **Перед изменением** — показывать текущее значение
13. **НЕ продолжать** к следующему шагу автоматически — ждать подтверждения
14. **Описывать ЗАДАЧУ полностью** с контекстом. Claude формирует команды лучше когда понимает зачем
15. **Разведка → план → действия.** Не "сразу делать"
16. **Caddyfile** — менять через Python или целиком, не sed (хрупко для блоков)
17. **Таблицы** для структурированных данных, минимум текста
18. **Active probing защита** — все selfsteal SNI через reverse_proxy
19. **Секреты** — никогда в документации, только через env vars или password manager

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

---

## 18. Артефакты миграции

Все артефакты сохранены на Latvia: `/opt/diagnostics/matrix-migration/`

| Файл | Содержимое |
|------|------------|
| `hosts-pre-migration.json` | Бэкап 20 хостов до миграции |
| `hosts-before-phase5.json` | Бэкап 36 хостов перед отключением старых |
| `created-hosts.json` | UUID всех 16 новых матричных хостов |
| `virtual-host.json` | UUID Virtual Host |
| `inbound-uuids.json` | UUID 4 inbound'ов |
| `new-hosts-templates.json` | Шаблоны 16 хостов (POST body) |
| `old-hosts-to-disable.json` | UUID 12 старых хостов (для rollback) |
| `rollout-groups.json` | Группы staged rollout |
| `caddyfile-latvia-original.txt` | Оригинальный Caddyfile Latvia |
| `caddyfile-amsterdam-original.txt` | Оригинальный Caddyfile Amsterdam |

---

## 19. История изменений

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
