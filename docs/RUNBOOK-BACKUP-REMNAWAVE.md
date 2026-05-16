# Runbook: бэкап БД Remnawave (AMS → LV, restore test)

Цель бэклога **P2-BAK-01** / **P2-BAK-02**: воспроизводимый дамп с хоста панели (**Amsterdam**), копия **off-host** на **Latvia**, отдельная дисциплина **патчей** схемы (не смешивать с «просто дампом»).

## 1. Компоненты в репозитории

| Файл | Где выполнять | Назначение |
|------|----------------|------------|
| **`ops/pg_dump_remnawave.sh`** | **AMS** | Логический `pg_dump` контейнера **`remnawave-db`** → **`/opt/backups/remnawave-*.sql.gz`** + `sha256sum`. |
| **`ops/pull-latest-dump-ams-to-lv.sh`** | **LV** | Берёт **последний** `remnawave-*.sql.gz` с AMS по SSH/SCP, кладёт в **`/opt/backups/`** на LV, сверяет SHA256. |
| **`ops/remnawave_restore_test.sh`** | **LV** | Квартальный **restore test**: ephemeral **`postgres:17`**, restore последнего дампа, smoke по таблицам. |
| **`backup-remnawave.sh`** (корень репо) | LV (`/opt/scripts/`) | **Legacy**: локальный `docker exec remnawave-db`. Имеет смысл только если на **этой** машине реально крутится **`remnawave-db`**. После переноса панели на AMS канонический путь — **дамп на AMS + pull на LV** (см. ниже). |

## 2. Рекомендуемое расписание (календарь)

| Хост | Периодичность | Задача |
|------|-----------------|--------|
| **AMS** | каждые 6 ч (пример: `5 */6 * * *`) | Вызов **`pg_dump_remnawave.sh`**, лог в файл по выбору (`/var/log/pg_dump_remnawave.log`). |
| **LV** | каждые 6 ч, **смещение +10–15 мин** после AMS | Вызов **`pull-latest-dump-ams-to-lv.sh`**, лог → `/var/log/remnawave-pull.log` (имя на усмотрение). |

Чертёж примеров смотри в **`ops/crontab-remnawave-backup.example`**.

**P2-BAK-02 (патчи):** миграции/ручные SQL к панели ведите отдельно (миграции приложения, one-shot скрипты с бэкапом до применения). Не подменяйте этим «квартальный restore test» из §4.

## 3. Установка скриптов на прод

1. Скопировать с репозитория на **AMS**: `ops/pg_dump_remnawave.sh` → например `/opt/scripts/pg_dump_remnawave.sh`, `chmod +x`.
2. Скопировать на **LV**: `ops/pull-latest-dump-ams-to-lv.sh` → `/opt/scripts/pull-latest-dump-ams-to-lv.sh`, `chmod +x`.
3. **Состояние репо 2026-05-16:** оба файла задеплоены на прод (`install` в `/opt/scripts/`, `bash -n` OK). Добавьте строки в crontab по §2 / `ops/crontab-remnawave-backup.example` при необходимости.
4. Убедиться, что SSH LV→AMS с ключом и портом из скрипта совпадают с реальностью (`AMS_IP`, `AMS_PORT` при необходимости через env).
5. Каталог **`/opt/backups`** существует на обоих хостах (`mkdir -p`).

## 4. Квартальный restore test (**P2-BAK-01** runbook + **`P2-OPS-RESTORE-TEST-01`** на проде)

Цель: убедиться, что дамп **читается** и **поднимается** в изолированном Postgres, без затрагивания прод-БД.

**Автоматизация (рекомендуется):** на **bvpn-lv** — **`ops/remnawave_restore_test.sh`** → `/opt/scripts/remnawave_restore_test.sh`. Перед прогоном при необходимости: **`pull-latest-dump-ams-to-lv.sh`**. Скрипт поднимает ephemeral **`postgres:17`** на **`127.0.0.1:55432`**, восстанавливает последний **`remnawave-*.sql.gz`**, проверяет отсутствие **`ERROR`/`FATAL`** и **≥5** таблиц в **`public`**.

Ручной сценарий (если без скрипта):

1. Взять последний файл **`remnawave-*.sql.gz`** с LV (`/opt/backups/` после pull).
2. На **тестовой** ВМ или контейнере поднять пустой Postgres (другой инстанс/порт).
3. `zcat dump.sql.gz | psql -h … -U … -d …` в **новую** БД (роль **`postgres`**, как в дампе).
4. Зафиксировать: время прогона, версию Postgres, размер дампа, ошибки (`ERROR` в выводе = fail).
5. **Записать дату успешного теста** в журнал бэклога (**`docs/COMMERCIAL-BACKLOG.md` §12**) — в репозитории хранится только факт «тест выполнен», без данных дампа.

Последний зафиксированный успешный прогон (**`P2-OPS-RESTORE-TEST-01`**): **2026-05-16** — **bvpn-lv**, дамп **`remnawave-20260514-203204.sql.gz`** (163K, SHA256 сверен при pull), Postgres **17.10**, **36** таблиц **`public`**, **97** строк **`_prisma_migrations`**, ~**5 s**, exit **0**. Следующий — по календарю (+квартал) или до массового GTM (**`docs/GTM-GROWTH-OUTLINE.md`**).

## 5. Связанные документы

- **`docs/DEPLOY.md`** — карта скриптов и crontab LV.
- **`docs/SECRETS.md`** — где лежат креды Postgres на AMS (не в git).
