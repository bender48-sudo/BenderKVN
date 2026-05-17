# Runbook: Postgres панели Remnawave (P6-SCALE-03)

**Цель:** при росте базы панель не деградирует из‑за отсутствия индексов, «слепых» запросов и **`pg_dump`** в пик обновлений подписок.

**Хост:** **AMS**, контейнер **`remnawave-db`** (`compose/ams/remnawave/docker-compose.yml.tmpl`).

---

## 1. Регулярный аудит (рекомендуется раз в месяц / перед GTM)

На машине с SSH к AMS (или с репо на AMS):

```bash
python3 ops/pg_remnawave_audit.py
python3 ops/pg_remnawave_audit.py --json
```

Скрипт (read-only):

- размеры таблиц **`public`**;
- индексы и «лишние» дубликаты по имени;
- **`pg_stat_statements`** (если расширение включено);
- число подключений.

**Интерпретация:** таблицы **> 500 MB** или seq scan на горячих таблицах в top queries → завести задачу на индекс / обращение к доке Remnawave + Prisma migrations.

---

## 2. Включить `pg_stat_statements`

Требует **перезапуска** `remnawave-db` (preload в `shared_preload_libraries`). Накат только по **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`**.

1. В репо: в **`docker-compose.yml.tmpl`** у **`remnawave-db`** задан `command` с `pg_stat_statements` (см. коммит **P6-SCALE-03**).
2. На AMS:

```bash
bash ops/pg_enable_stat_statements_ams.sh --dry-run   # показать план
bash ops/pg_enable_stat_statements_ams.sh --apply     # compose + recreate db + CREATE EXTENSION
```

3. Smoke: `python3 ops/pg_remnawave_audit.py` — в отчёте **`pg_stat_statements: enabled`**.

**Окно:** низкая нагрузка (ночь UTC **01:00–04:00** / **22:00–01:00 MSK**). Краткий рестарт БД: панель **`remnawave`** переподключится после healthcheck (~30–60 с).

---

## 3. Индексы

- **Не** создавать индексы вручную на проде без бэкапа и понимания схемы Prisma.
- Новые индексы — через **миграции приложения** (релиз Remnawave) или согласованный one-shot SQL с дампом **до** изменения.
- Аудит **`pg_remnawave_audit.py`** подсвечивает таблицы без PK и кандидаты на проверку FK — финальное решение за инженером.

---

## 4. Окно бэкапа (не в пик)

| Было (пример) | Стало (P6-SCALE-03) | Зачем |
|---------------|---------------------|--------|
| AMS `5 */6` (в т.ч. **06:05 UTC** ≈ утро MSK) | **`35 1,7,13,19 * * *`** | Убрать дамп из **06:xx UTC** (пик refresh подписок **~06–09 MSK**) |
| LV `15 */6` | **`50 1,7,13,19 * * *`** | +15 мин после AMS |

Установка cron (идемпотентно):

```bash
# AMS
bash ops/install-remnawave-backup-cron.sh ams
# LV
bash ops/install-remnawave-backup-cron.sh lv
```

См. также **`docs/RUNBOOK-BACKUP-REMNAWAVE.md`**.

---

## 5. План обслуживания (чеклист)

| Периодичность | Действие |
|---------------|----------|
| **Еженедельно** | Просмотр алертов AMS RAM / **`capacity_snapshot`** (users **> 2000**) |
| **Ежемесячно** | **`pg_remnawave_audit.py`** → сохранить `--json` в тикет / §12 при аномалиях |
| **После релиза панели** | Повтор аудита; при миграции — бэкап до наката |
| **Раз в квартал** | Restore test (**`RUNBOOK-BACKUP-REMNAWAVE` §4**) |
| **При users > 8000** | Обязательный **`pg_stampede_load_probe`** + read-replica (**`RUNBOOK-P6-POSTGRES-RED`**) |

---

## 6. Связанные файлы

- **`ops/pg_remnawave_audit.py`**
- **`ops/pg_enable_stat_statements_ams.sh`**
- **`ops/pg_dump_remnawave.sh`**, **`ops/install-remnawave-backup-cron.sh`**
- **`docs/COMMERCIAL-BACKLOG.md` §10.2** — **P6-SCALE-03**
