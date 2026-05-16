# Миграция панели LV → AMS: бэкапы и откат

Дата снимка: **2026-05-11** (UTC на серверах).

## Снимки бэкапа

### Latvia (`bvpn-lv`)

Каталог: **`/opt/backups/panel-migrate-20260511-182407`**

| Файл | Назначение |
|------|------------|
| `remnawave-logical.sql.gz` | Логический дамп PostgreSQL (pg_dump) |
| `remnawave-db-data_VOLUME.tgz` | Физический снимок Docker volume `remnawave-db-data` |
| `remnawave-redis-data_VOLUME.tgz` | Физический снимок volume `remnawave-redis-data` |
| `opt-remnawave.tgz` | `/opt/remnawave` (compose, `.env`, патчи) |
| `opt-remnanode.tgz` | `/opt/remnanode` |
| `docker-inspect-all.json` | `docker inspect` ключевых контейнеров |
| `docker-ps-a.txt`, `df-h.txt` | Состояние на момент бэкапа |

### Amsterdam (`bvpn-ams`)

Каталог: **`/opt/backups/panel-migrate-20260511-182635`**

| Файл | Назначение |
|------|------------|
| `remnawave-db-data_VOLUME.tgz` | Старый volume на AMS (если был отключённый стек) |
| `opt-remnanode.tgz`, `opt-remna-shop.tgz`, `opt-caddy.tgz` | Рабочие каталоги |
| `opt-remnawave-sub.tgz`, `opt-remnawave-root.tgz` | Subscription compose и корень `/opt/remnawave` |
| `docker-ps-a.txt` | Список контейнеров |

---

## Откат (если после изменений на Latvia всё сломалось)

**Цель:** вернуть панель и БД как до миграции, из бэкапа `panel-migrate-20260511-182407`.

1. Остановить на LV текущие контейнеры панели (если они в полусостоянии):  
   `cd /opt/remnawave && docker compose down` (осторожно: даунтайм).
2. Восстановить **том БД** из физического снимка (только если логический дамп не подошёл):  
   - остановить контейнер `remnawave-db`;  
   - очистить данные volume (опасно — иметь второй полный бэкап);  
   - распаковать `remnawave-db-data_VOLUME.tgz` в корень volume.  
   Предпочтительнее для отката: **восстановить из `remnawave-logical.sql.gz`** в чистую БД того же major Postgres.
3. Восстановить файлы: `tar xzf opt-remnawave.tgz -C /` (проверить пути).
4. `docker compose up -d` в `/opt/remnawave` и `/opt/remnanode`.
5. Проверить панель, подписку, ноду.

Подробные команды восстановления volume выполнять **только в окне обслуживания** и после копии бэкапа off-box при необходимости.

---

## Откат на Amsterdam

Если на AMS трогали compose/volumes: восстановить из **`/opt/backups/panel-migrate-20260511-182635`** тем же способом (`tar xzf` по каталогам), затем `docker compose up` в соответствующих `/opt/...`.

---

## Дамп на Amsterdam (для импорта)

Файл: **`/opt/backups/panel-migrate-20260511-182635/remnawave-from-lv-logical.sql`**  
(скопирован с Latvia логическим `pg_dump`, без повторного gzip.)

## Важно

- Не удалять каталоги бэкапа до успешной стабилизации миграции (несколько дней).
- Секреты в `.env` уже внутри `opt-*.tgz` — не выкладывать архивы в публичные места.
- Следующие шаги cutover: `ops/MIGRATION-NEXT-STEPS.md`.
