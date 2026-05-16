# Runbook: публичная подписка (edge, P6-SCALE-04)

Цель **P6-SCALE-04**: при росте базы **пик обновлений подписок** не должен класть **edge** (TLS / reverse proxy / контейнер subscription-page) и **панель**.

## 0. Рекомендуемый порядок на проде

1. **Бот AMS** при необходимости: хотфиксы **`handlers` / user_messages`** — см. **`docs/DEPLOY.md` §4.3.1** или **`pwsh -File ops/deploy-bot-handlers-ams.ps1`**, смок **`/start`** в Telegram.
2. **Baseline без нового RL:** с узла с доступом к публичному URL (или локально через `site_urls`) — один прогон **`python ops/subscription_load_probe.py --json`** (параметры сохраните в **`COMMERCIAL-BACKLOG` §12**).
3. **Включить** CDN **или** rate-limit на краю (**§2**), не трогая **`/api/sub/*`** токены и upstream на AMS (**`REMNA_API_TOKEN`**, см. **`RUNBOOK-REMNA-API-TOKEN`**).
4. Повторить **`subscription_load_probe`** (можно **`--max-bad-http-rate`**, если договорились о допустимой доле не-200/304); зафиксировать в **§12**.

## 1. Текущая схема (ориентир)

| Компонент | Где | Заметка |
|-----------|-----|---------|
| Публичный HTTPS подписки | `SUB_PUBLIC_ORIGIN` (пример: **`p4n7q…:2053`**) | За Caddy / тем же краём, что отдаёт панель по другому host/SNI. |
| Контейнер **`remnawave-subscription-page`** | AMS, порт **`3010`** в compose | См. **`compose/ams/remnawave-sub/docker-compose.yml.tmpl`**. |
| Ограничение доступа к **3010** с интернета | **`ops/bvpn-docker-firewall.sh`** / systemd на AMS | Закрытие «широкого» **0.0.0.0:3010** — см. **P0-SEC-03**, журнал бэклога. |

Смоки подписки в репозитории: **`monitor.sh`**, **`ops/capacity_snapshot.py`** (probe `site_urls.sub_monitor_probe_url()`).

## 2. Защита от абьюза и пиков (выбор стека)

Делайте **один основной** слой + мониторинг латентности:

1. **CDN / WAF перед доменом подписки** (Cloudflare и аналоги): rate limit, bot fight, кэш статики; минус — доверие к третьей стороне (политика продукта).
2. **Rate limit на edge** (Caddy / nginx перед `subscription-page`): лимит по **client IP** на путь **`/api/sub/*`** или весь vhost подписки. Проверять поддержку в вашей версии Caddy / модулей (см. [Caddy rate limiting](https://caddyserver.com/docs/) и плагины).
3. **Прикладной уровень** Remnawave / subscription-page — только если даёт документация (пороги, кэш ответа).

### 2.1 Caddy без «магии» в образе по умолчанию

Стандартный **`caddy:2.x`** из Docker Hub / пакеты дистрибутива обычно **не включают** middleware rate‑limit; его подключают отдельной сборкой через **`xcaddy`**. На практике для LV смотрите модуль **[`mholt/caddy-ratelimit`](https://github.com/mholt/caddy-ratelimit)** (Apache‑2.0): ключ зоны типично **`{remote_ip}`**, matcher только на **`/api/sub/*`** и при необходимости на **отдельный host** подписки — чтобы не задеть панель на том же edge.

Не копировать в прод **числовые пороги** из чужих гайдов: снимите профиль через **`subscription_load_probe.py`** (низкая → высокая параллельность), зафиксируйте p95 до/после. **`429`** от лимитера ожидаемы при намеренном душении; массовые **`502`** трактуйте как деградация upstream (**`remnawave-subscription-page`** / панель на AMS).

### 2.2 Без сборки своего бинаря Caddy

- **CDN / WAF** (пункт **1** выше) — самый короткий путь без смены бинаря на VPS.
- **nftables**/conntrack — грубо по IP и порту, без понимания пути; только если нет времени ни на CDN, ни на **`xcaddy`**.

Для **первого поколения** при ~60–500 пользователей часто достаточно: **edge лимит + алерт по HTTP ≠ 200** на smoke URL (уже есть в мониторинге + расширенный вывод в **`capacity_snapshot`**).

## 3. Нагрузочный тест (критерий «готово» P6-SCALE-04)

Минимум: снять **p95 latency** и **долю 5xx** при **N** параллельных `GET` на публичный URL подписки (короткий ключ smoke или отдельный staging-домен **без** утечки прод-данных).

Утилита в репозитории (тот же URL по умолчанию, что **`site_urls.sub_monitor_probe_url()`** / **`monitor.sh`**):

```bash
python ops/subscription_load_probe.py --concurrency 30 --total 120
python ops/subscription_load_probe.py --json   # машиночитаемый отчёт
# опционально: упасть, если доля ответов не 200/304 слишком высокая (сверяйте с базой до внедрения RL):
python ops/subscription_load_probe.py --max-bad-http-rate 0.15
# свой URL без правки site.env:
python ops/subscription_load_probe.py --url 'https://хост:2053/api/sub/SHORTID' --total 80
```

Смотреть **p50/p95/p99**, **status_histogram** (в т.ч. доля **5xx** и **429** после edge RL), **hard_errors** (только TLS/DNS/таймаут — не HTTP-коды).

Зафиксировать в журнале **`docs/COMMERCIAL-BACKLOG.md` §12**: дата, N, параллельность, p95, гистограмма статусов (или `--json`).

## 4. Связанные файлы

- **`ops/subscription_load_probe.py`** — нагрузочный смок по умолчанию для §3.
- **`docs/COMMERCIAL-BACKLOG.md` §10.1** — порог «ошибки на `p4n7q…/api/sub/*`».
- **`docs/RUNBOOK-CADDY-SUBSCRIPTION-LOGS.md`** — логирование без утечки сырого `/api/sub/` в access-log.
- **`compose/ams/remnawave-sub/docker-compose.yml.tmpl`**
