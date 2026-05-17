# Runbook: Postgres resilience (P6-RED-PG-01)

**Цель:** при росте базы панель не исчерпывает Postgres соединениями; есть план read-replica; нагрузочный тест «утреннего stampede» задокументирован.

**Хост БД:** AMS, контейнер **`remnawave-db`**.

---

## 1. Pool limits (прод)

| Потребитель | Подключение к Postgres | Лимит |
|-------------|------------------------|-------|
| **`remnawave`** (Prisma) | `DATABASE_URL` в `/opt/remnawave/.env` | **`connection_limit=15`** |
| **`remnawave-subscription-page`** | только API панели | — |
| **`remna-shop-bot`** | SQLite локально | — |
| Резерв (cron, `psql`, бэкап) | прямой доступ | ≤ **10** |

**Postgres:** `max_connections=100` в `compose/ams/remnawave/docker-compose.yml.tmpl`.

**Накат pool limit на живой AMS** (без смены пароля):

```bash
scp -P 3344 ops/patch_pg_pool_limits_ams.sh root@168.100.11.140:/tmp/
ssh -p 3344 root@168.100.11.140 'bash /tmp/patch_pg_pool_limits_ams.sh'
python ops/check_pg_pool_limits_ams.py
```

Полный compose — только **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**.

---

## 2. Read replica (когда включать)

| users в БД | Действие |
|------------|----------|
| **< 8 000** | Одна primary на AMS достаточна при pool limits + edge HA (**P6-RED-SUBHA-01**) |
| **≥ 8 000** | Обязательный stampede load test; рассмотреть **streaming replica** (read-only) для отчётов/тяжёлых SELECT или managed Postgres |
| Перенос на managed | Заменить replica-план на провайдерский HA + PITR |

Replica **не** развёрнута на текущем масштабе — зафиксировано в §12.

---

## 3. Нагрузочный тест «массовое обновление клиентов»

Прокси сценария «много refresh подписки за час» — параллельные GET `/api/sub/{shortUuid}` + снимок `pg_stat_activity`:

```bash
python ops/pg_stampede_load_probe.py --total 120 --concurrency 25
python ops/pg_stampede_load_probe.py --json
```

Проба делит запросы **50/50** между **p4n7q** и **k9x2m1**, чтобы не упереться в Caddy **120/min/IP** на одном origin.

Ожидание: **`PG_STAMPEDE_LOAD_OK`**, **`PANEL_REFRESH_LOAD_OK`**, utilization connections **< 85%** `max_connections`.

Перед GTM / при **users > 8k** — повторить с `--total 200 --concurrency 30`.

---

## 4. Пороги (§10.1)

См. **`docs/COMMERCIAL-BACKLOG.md` §10.1** — строки Postgres stampede / connections.

---

## Связанные файлы

- **`ops/pg_stampede_load_probe.py`**, **`ops/panel_refresh_load_probe.py`**
- **`ops/pg_remnawave_audit.py`**, **`ops/check_pg_pool_limits_ams.py`**
- **`docs/RUNBOOK-P6-POSTGRES-MAINTENANCE.md`** (индексы, бэкап)
