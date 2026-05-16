# Runbook: Panel API scale + Valkey eviction (P6-SCALE-05)

**Цель:** при росте базы панель (AMS) и кэш Valkey выдерживают пик **refresh подписки**; Redis не падает на OOM из‑за `noeviction`.

## 1. Valkey eviction (AMS)

| Параметр | Было | Стало |
|----------|------|--------|
| `maxmemory` | 0 (unlimited) | **256mb** |
| `maxmemory-policy` | `noeviction` | **`allkeys-lru`** |

**Репо:** `compose/ams/remnawave/docker-compose.yml.tmpl` — `remnawave-redis` command.

**Накат без полного safe-deploy (runtime, до recreate):**

```bash
ssh bvpn-ams 'bash -s' < ops/apply_valkey_eviction_ams.sh
python ops/valkey_memory_audit.py
```

После изменения tmpl — **`RUNBOOK-AMS-SAFE-DEPLOY`** для `remnawave-redis` recreate.

## 2. Прогон «refresh × N»

Симуляция массового pull подписки (разные `shortUuid` из панели):

```bash
python ops/panel_refresh_load_probe.py --concurrency 25 --total 100
# ожидать: PANEL_REFRESH_LOAD_OK, p95 в разумных пределах, bad_http_rate ≤ 2%
```

Пороги по умолчанию: `--max-error-rate 0.05`, `--max-bad-http-rate 0.02`.

## 3. Пороги роста (§10.1)

| users в БД | Действие |
|------------|----------|
| **> 2k** | Вертикальный апгрейд AMS; split panel/db/redis |
| **> 8k** | Обязательный load test sub + panel; отдельный edge |

Метрики: `python ops/capacity_snapshot.py`.

## 4. Горизонталь (справка)

По доке Remnawave при росте: отдельный хост subscription-page (уже **split-host HA**), вынос Postgres/Redis, апгрейд RAM AMS. Детали — **`docs/COMMERCIAL-BACKLOG.md` §10.1**.

## Связанные файлы

- **`ops/panel_refresh_load_probe.py`**
- **`ops/valkey_memory_audit.py`**
- **`ops/subscription_load_probe.py`** (один URL, edge)
