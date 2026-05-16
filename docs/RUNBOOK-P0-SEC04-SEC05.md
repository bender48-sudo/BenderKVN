# P0-SEC-04 + P0-SEC-05 — закрытие (LV + AMS)

Окно работ: низкий трафик. Иметь SSH к **LV** и **AMS**, доступ админа к панели Remnawave, бэкап Bitwarden/хранилища секретов.

Скрипты в репозитории (копируйте на сервер или `git pull` там, где есть клон):

- `ops/archive_lv_remnawave_legacy.sh`
- `ops/rotate_ams_panel_core_secrets.py`

---

## 1. P0-SEC-04 — LV: убрать живой `/opt/remnawave/`

1. Под root на **bvpn-lv**:
   ```bash
   bash /opt/scripts/archive_lv_remnawave_legacy.sh
   ```
   (либо положите скрипт из репо в `/opt/scripts/` и запустите его.)
2. Проверка: `test ! -d /opt/remnawave && echo OK`.
3. Опционально: `ls -la /opt/_archive/remnawave-legacy-*` — каталог с **`chattr +i`** (если поддерживается ФС).

**Откат:** снять immutable (`chattr -i`), вернуть каталог обратно в `/opt/remnawave` (только если осознанно нужно).

---

## 2. P0-SEC-05 — AMS: фаза A — ядро панели (JWT + Postgres)

Ротуирует **`JWT_AUTH_SECRET`**, **`JWT_API_TOKENS_SECRET`**, **`POSTGRES_PASSWORD`** и перезапускает контейнер **`remnawave`**. Все действующие **admin-сессии** и **API-токены** панели перестанут быть валидны до фазы B.

1. На **AMS**, root, каталог **`/opt/remnawave`**:
   ```bash
   python3 /opt/scripts/rotate_ams_panel_core_secrets.py --compose-dir /opt/remnawave --dry-run
   python3 /opt/scripts/rotate_ams_panel_core_secrets.py --compose-dir /opt/remnawave --apply
   ```
2. Дождаться `healthy` у `remnawave` (`docker compose ps`). Если в логах **Prisma P1000** сразу после ротации — контейнер мог остаться со **старым** `DATABASE_URL` в `Config.Env`: тогда **`docker compose up -d --no-deps --force-recreate remnawave`** (plain `restart` **не** подхватывает новый `env_file`).
3. Записать **новые** значения из `/opt/remnawave/.env` в менеджер паролей: `JWT_*`, `POSTGRES_PASSWORD`, `DATABASE_URL` (файл `.env.bak-p0sec05-*` — предыдущая версия).

**Откат:** остановить стек, восстановить `.env` из бэкапа, поднять контейнеры; при необходимости вернуть пароль в Postgres из снимка (сложнее — лучше не применять `--apply` без свежего `pg_dump`).

---

## 3. P0-SEC-05 — фаза B — новый `REMNA_API_TOKEN`

После фазы A зайти в панель **с нуля** (логин/пароль админа), в UI создать **новый API token** (роль API, долгий срок).

Обновить **одинаковый** токен в четырёх местах (везде заменить строку токена, не коммитить в git):

| # | Хост | Файл / примечание |
|---|------|-------------------|
| 1 | AMS | `/opt/remna-shop/.env` → `REMNA_API_TOKEN=` |
| 2 | AMS | `/opt/remnawave/sub/docker-compose.yml` или рядом лежащий `.env`, откуда подставляется `REMNAWAVE_API_TOKEN` / `REMNA_API_TOKEN` |
| 3 | LV | `/etc/bvpn/balancer.env` → `REMNA_API_TOKEN` / `PANEL_TOKEN` |
| 4 | LV | `/etc/bvpn/ru-monitor.env` → `REMNA_API_TOKEN` |

Затем перезапуск сервисов (пример):

```bash
# AMS
cd /opt/remna-shop && docker compose up -d
cd /opt/remnawave/sub && docker compose up -d
```

На LV cron-скрипты подхватят env при следующем запуске; при необходимости тронуть процесс вручную.

**Проверки:** `/status` в боте (если есть), `panel_api`/nodes с LV, суточный `daily-report`, smoke подписки.

---

## 4. После успеха

1. `python ops/drift-check.py` (с машины с рабочим `ssh` к `bvpn-*`).
2. Строка в **`docs/COMMERCIAL-BACKLOG.md` §12** с датой и кратким «P0-SEC-04/05 DONE».
3. Обновить **Bitwarden** / **vault** под фактические значения.
