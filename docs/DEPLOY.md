# BenderVPN — deploy procedure

Этот документ — **источник истины** для управляющих файлов на проде. Цель — никогда больше не править файл «прямо на сервере» так, чтобы об этом не узнал репозиторий. Любое расхождение между этим списком и реальным `/opt/scripts/*` — это **drift**, и закрывается ровно той процедурой, которая описана ниже.

## 1. Карта файлов: репо ↔ прод

| Репо | Хост | Путь на проде | Назначение |
|------|------|---------------|------------|
| `monitor.sh` | LV | `/opt/scripts/monitor.sh` | Каждые 5 мин: LV Xray-порты, **smoke подписки** (`SUB_PUBLIC_ORIGIN` / `SUB_MONITOR_PROBE_URL` после `source /etc/bvpn/balancer.env`, см. **`daily-report.sh`**), **`PANEL_URL`**, бот AMS, disk. Алерты в TG. |
| `daily-report.sh` | LV | `/opt/scripts/daily-report.sh` | 09:00 UTC digest: users/traffic/nodes/… **`/api/users` обязан запрашивать со страницами (`size`/`start`)** — без этого панель отдаёт только ~25 записей и цифры в TG не сходятся с UI. |
| `ops/capacity_snapshot.py` | LV / рабочая станция | — (ops, не cron) | Снимок **§10.1**: активные users (постранично), ноды, мягкая «загрузка» относительно `USERS_PER_NODE`. **P6-SCALE-01**. |
| `balancer.sh` | LV | `/opt/scripts/balancer.sh` | Каждый час: capacity (users/node, CPU). 80/95/100% алерты + daily summary. |
| `backup-remnawave.sh` | LV | `/opt/scripts/backup-remnawave.sh` | **Legacy:** локальный `pg_dump`, только если на LV есть контейнер **`remnawave-db`**. Иначе используйте связку **AMS** → **`ops/pg_dump_remnawave.sh`** и **LV** → **`ops/pull-latest-dump-ams-to-lv.sh`** (см. **`docs/RUNBOOK-BACKUP-REMNAWAVE.md`**, пример cron **`ops/crontab-remnawave-backup.example`**). |
| `ops/pg_dump_remnawave.sh` | AMS | `/opt/scripts/pg_dump_remnawave.sh` (рекомендуемый путь) | Периодический логический дамп Postgres панели в **`/opt/backups/`**. |
| `ops/pull-latest-dump-ams-to-lv.sh` | LV | `/opt/scripts/pull-latest-dump-ams-to-lv.sh` | Копия последнего дампа с AMS на LV (off-host), верификация SHA256. |
| `ops/remnawave_restore_test.sh` | LV | `/opt/scripts/remnawave_restore_test.sh` | Квартальный restore test (ephemeral Postgres 17, см. **`RUNBOOK-BACKUP-REMNAWAVE` §4**). |
| `ops/install-remnawave-backup-cron.sh` | AMS / LV | — (one-shot: `bash … ams` / `… lv`) | Crontab **`pg_dump`** / **`pull-latest-dump`** — см. **`ops/crontab-remnawave-backup.example`**. |
| `ops/deploy-bot-config-ams.ps1` | AMS (с Windows) | hot-patch **`config.py`** | Только **`config.py`** (legacy). |
| `ops/deploy-bot-balance-model-ams.ps1` | AMS (с Windows) | balance model | **`DAILY_RATE`**, topup UI, **`database.balance`**, scheduler. |
| `ru-monitor.py` | LV | `/opt/scripts/ru-monitor.py` | Каждые 5 мин: SNI-reachability через RU-relay (цели из API `hosts`; минимальный порог **≥4** активных после фильтров, см. код). |
| `selfsteal-monitor.py` | LV | `/opt/scripts/selfsteal-monitor.py` | Каждые 5 мин: Caddy selfsteal fingerprint (HTTP коды по 13 SNI). AMS-узел закомментирован на время drain'а. |
| `deploy-node.sh` | LV / AMS | `/opt/scripts/deploy-node.sh` | Развёртывание новой `remnanode`. **Токен через env / argv / interactive read — никогда в `ps`**. |
| `ops/watchdog.sh` | NL | `/opt/scripts/watchdog.sh` | Каждые 15 мин: SSH NL→LV (restricted-key) → проверка mtime двух monitor-логов; алерт «stale >30 мин» только при реальной проблеме. |
| `ops/bvpn-watchdog-probe.sh` | LV | `/usr/local/sbin/bvpn-watchdog-probe` | Read-only probe для watchdog: возвращает три `epoch=…` строки. Вызывается через `command="…"` в `authorized_keys`. |
| `ops/bvpn-docker-firewall.sh` | AMS | `/usr/local/sbin/bvpn-docker-firewall.sh` | Idempotent: вставляет в `DOCKER-USER` пару правил «ACCEPT from LV / DROP all» для `subscription-page` :3010. |
| `bot_src/handlers.py`, `bot_src/user_messages.py` | AMS | `/opt/remna-shop/src/shop_bot/bot/handlers.py` **+** `user_messages.py` **+** `docker cp` в `remna-shop-bot` | Пользовательские тексты и логика бота (до пересборки image). Автоматизация: **`pwsh -File ops/deploy-bot-handlers-ams.ps1`**. |
| `ops/bot-admin-handlers.py` | AMS | `/opt/remna-shop/src/shop_bot/bot/admin_handlers.py` **+** image-copy в `remna-shop-bot` | Admin-only `/admin` и `/status` команды бота. Bot src — image-baked, поэтому деплой = host-edit + `docker cp` + `docker restart`. |
| `compose/**/*.tmpl` + vault | LV / AMS / NL | см. **`docs/SECRETS.md` §3** (пути прод) | SoT для прод-compose и ключевых `/etc/bvpn/*.env`: шаблоны в репо, секреты в `.secrets/vault.env`; синхронность **`python ops/drift-check.py`** (**§7**); реген из прода через `ops/sanitize_compose_templates.py`. |

Файлы вне таблицы (`intel-digest.py`, `fix-caddy-security.sh`, и т.п.) — **legacy / one-shot / artifacts**. В `monitor.sh.bak-*`, `*.before-blockD-*`, `*.before-ams-drain-*` — это backups, **не SoT**. Чистка backups — задача отдельной полировки.

## 2. Правила работы (Source of Truth)

1. **Любое изменение начинается с правки в репо.** Не на сервере.
2. После правки — локальный sanity:
   - `bash -n FILE.sh` для bash.
   - `python -c "import ast; ast.parse(open('FILE.py').read())"` для Python.
3. Для деплоя — соответствующий helper-скрипт из `.secrets/` (повторно-используемые) или универсальный pattern из §3.
4. Любой deploy создаёт backup: `<dst>.before-<reason>-<YYYYMMDD-HHMMSS>`. Не перетирать backups руками.
5. После deploy: `md5sum` на проде == md5 файла в репо. Это автоматическая проверка drift'а.
6. **Никогда** не редактировать `/opt/scripts/*` через `vi` на сервере. Если очень-очень-очень надо — сначала `scp <prod>:<file> .secrets/prod-pull/` и сравнить с репо, потом править в репо и накатывать обратно.
7. Локально: необязательный **`ops/site.env`** (образец — **`ops/site.env.example`**, файл gitignored как `*.env`) подхватывается **`ops/site_urls.py`** для общих публичных URL/UUID (`PANEL_URL`, `SUB_PUBLIC_ORIGIN`, `REMNA_TEMPLATE_UUID`, relay) во всех maintenance-скриптах Python.

## 3. Универсальный deploy-pattern (LV)

```bash
# 1. Local sanity
bash -n monitor.sh                                            # для bash
python -c "import ast; ast.parse(open('ru-monitor.py').read())" # для python

# (Windows PowerShell, из корня репо — один шаг вместо 2–4 ниже:)
#   pwsh -File ops/deploy-monitor-lv.ps1

# 2. Ship to host /tmp, normalize line endings
scp -P 3333 monitor.sh root@176.126.162.158:/tmp/monitor.sh.new
ssh -p 3333 root@176.126.162.158 "sed -i 's/\r\$//' /tmp/monitor.sh.new"

# 3. Backup current + install
ssh -p 3333 root@176.126.162.158 "ts=\$(date +%Y%m%d-%H%M%S); cp /opt/scripts/monitor.sh /opt/scripts/monitor.sh.before-deploy-\$ts && install -m 0755 /tmp/monitor.sh.new /opt/scripts/monitor.sh"

# 4. Verify md5 match
ssh -p 3333 root@176.126.162.158 "md5sum /opt/scripts/monitor.sh"
python -c "import hashlib; print(hashlib.md5(open('monitor.sh','rb').read()).hexdigest())"
```

Скрипт **`ops/deploy-monitor-lv.ps1`** делает шаги 2–4 для **`monitor.sh`**, плюс сравнение MD5 в выводе; нужны OpenSSH (`scp`/`ssh`) и ключ **`%USERPROFILE%\.ssh\id_ed25519`**.

Те же 4 шага для NL (через alias `bvpn-nl`, ключ из ssh-config) и AMS (`-P 3344 root@168.100.11.140`).

## 4. Особые случаи

### 4.1. `ops/watchdog.sh` (NL) — требует подготовленный ключ

`/etc/bvpn/bot-token` (600 root:root) должен лежать на NL. Был положен один раз через `scp -3` с LV. Не теряется.

### 4.2. `ops/bvpn-watchdog-probe.sh` (LV) — вызывается из `authorized_keys`

В `/root/.ssh/authorized_keys` на LV — строка:
```
from="91.90.192.17",command="/usr/local/sbin/bvpn-watchdog-probe",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAA…
```
**Не редактировать `command=…` в authorized_keys руками** — пусть он остаётся ссылкой на скрипт. Любую логику менять в `ops/bvpn-watchdog-probe.sh` → `scp` → `install -m 0755 … /usr/local/sbin/bvpn-watchdog-probe`.

### 4.3. `ops/bot-admin-handlers.py` (AMS) — двойная цель

Бот собран из image, исходники **не** bind-mounted. Чтобы изменение работало **сейчас**:

```bash
# 1. Edit ops/bot-admin-handlers.py in repo, sanity-check
python -c "import ast; ast.parse(open('ops/bot-admin-handlers.py').read())"

# 2. Ship to AMS host + into running container
scp -P 3344 ops/bot-admin-handlers.py root@168.100.11.140:/tmp/admin_handlers.py
ssh -p 3344 root@168.100.11.140 "
  ts=\$(date +%Y%m%d-%H%M%S)
  cp /opt/remna-shop/src/shop_bot/bot/admin_handlers.py /opt/remna-shop/src/shop_bot/bot/admin_handlers.py.before-\$ts
  install -m 0644 /tmp/admin_handlers.py /opt/remna-shop/src/shop_bot/bot/admin_handlers.py
  docker cp /tmp/admin_handlers.py remna-shop-bot:/app/src/shop_bot/bot/admin_handlers.py
  docker restart remna-shop-bot
"
```

При следующей пересборке image (`update.sh` в `remna-shop`) изменение в `/opt/remna-shop/src/` подхватится автоматически.

### 4.3.1. `handlers.py` + `user_messages.py` (**AMS**) — хотфиксы UX / платежей

Тот же приём (хост **`/opt/remna-shop/src/…`** + контейнер **`remna-shop-bot`**):

```bash
python -c "import ast; ast.parse(open('bot_src/handlers.py',encoding='utf-8').read()); ast.parse(open('bot_src/user_messages.py',encoding='utf-8').read())"
scp -P 3344 bot_src/handlers.py bot_src/user_messages.py root@168.100.11.140:/tmp/
ssh -p 3344 root@168.100.11.140 '
  set -e
  ts=$(date +%Y%m%d-%H%M%S)
  BT=/opt/remna-shop/src/shop_bot/bot
  mkdir -p "$BT"
  test -f "$BT/handlers.py" && cp "$BT/handlers.py" "$BT/handlers.py.before-bot-ops-$ts" || true
  test -f "$BT/user_messages.py" && cp "$BT/user_messages.py" "$BT/user_messages.py.before-bot-ops-$ts" || true
  sed -i "s/\r$//" /tmp/handlers.py /tmp/user_messages.py
  install -m 0644 /tmp/handlers.py "$BT/handlers.py"
  install -m 0644 /tmp/user_messages.py "$BT/user_messages.py"
  docker cp /tmp/handlers.py remna-shop-bot:/app/src/shop_bot/bot/handlers.py
  docker cp /tmp/user_messages.py remna-shop-bot:/app/src/shop_bot/bot/user_messages.py
  docker restart remna-shop-bot
  md5sum "$BT/handlers.py" "$BT/user_messages.py"
'
```

На Windows из корня репозитория: **`pwsh -File ops/deploy-bot-handlers-ams.ps1`** (использует тот же **`-P 3344`**, ключ **`%USERPROFILE%\.ssh\id_ed25519`**).

Smoke: **`/start`** в боте, при необходимости admin **`/status`**. Затем (план **P6-SCALE-04**) — baseline **`subscription_load_probe`** до правок edge.

### 4.4 Пробный период (**90 дней**) и grandfather **до 2099** (AMS + панель)

**Политика (например с 2026‑05‑16):** уже существующие пользователи в панели Remnawave — **до 2099**; **новые** регистрации через бота — **пробный период ~90 дней**.

1. На машине с `PANEL_TOKEN` и репозиторием:  
   `python ops/grandfather_panel_users_expire.py --dry-run` — проверить список почт → затем **`--apply`**.

2. В **`compose/ams/remna-shop/bot.env.tmpl`** / прод **`/opt/remna-shop/.env`**:  
   **`REMNA_DEFAULT_DAYS=90`**, **`REMNA_TRIAL_DAYS`/`TRIAL_DAYS=90`**; **`BOT_PAYMENTS_LIVE=`** не задан или пустой, пока касса не готова (напоминания об истечении без кнопки оплаты — см. **`bot_src/scheduler.py`**).

3. Выкладка исходников бота (**`bot_src/handlers.py`**, **`scheduler.py`**, **`config.py`**, **`remnawave_api.py`**): скопировать в **`/opt/remna-shop/src/shop_bot/...`** и в контейнер `remna-shop-bot` по тому же принципу, что **`ops/bot-admin-handlers.py`** ( **`docker cp` + `restart`** ), либо пересборка image.

Подробнее для клиентской коммуникации — **`docs/FAQ.md`** (раздел «Пробный период»). Про то, где Git/GitHub — **`docs/VCS-WHERE-IS-GIT.md`**.

Разовый сценарий на AMS («grandfather до 2099» + патч **`/opt/remna-shop/.env`** + копирование исходников бота и `docker compose … remna-shop-bot`): см. **`ops/remote_ams_rollout_trials.sh`** (файлы сначала кладутся в **`/tmp/bvpn-rollout/`** через `scp` с локальной копии репозитория).

### 4.5. `bvpn-docker-firewall.sh` (AMS) — idempotent, можно прогонять заново

Скрипт сам сначала удаляет свои предыдущие правила, потом вставляет заново. Безопасно для пересоздания.

## 5. Crontab — где какие задачи живут

### AMS (`crontab`)
По умолчанию **пусто** — сервисы через docker compose. Для бэкапа БД панели ( **P2-BAK-01** ) добавьте периодический вызов **`ops/pg_dump_remnawave.sh`**: см. **`docs/RUNBOOK-BACKUP-REMNAWAVE.md`** и **`ops/crontab-remnawave-backup.example`**.

### LV (`crontab -l`)
```cron
20 12 * * *   /root/.acme.sh/acme.sh --cron --home /root/.acme.sh > /dev/null
0 */6 * * *   /bin/bash /opt/scripts/backup-remnawave.sh >> /var/log/remnawave-backup.log 2>&1
#             ↑ legacy: локальный remnawave-db; иначе дамп на AMS + pull → **`RUNBOOK-BACKUP-REMNAWAVE`**
*/5 * * * *   /bin/bash /opt/scripts/monitor.sh           >> /var/log/bvpn-monitor.log 2>&1
#             ↑ alert_* → /var/lib/bvpn-monitor/   |   ru-monitor state.json → /var/lib/bvpn-ru-monitor/
0 9 * * *     /bin/bash /opt/scripts/daily-report.sh      >> /var/log/bvpn-monitor.log 2>&1
0 * * * *     /bin/bash /opt/scripts/balancer.sh          >> /var/log/bvpn-balancer.log 2>&1
*/5 * * * *   /opt/scripts/ru-monitor.py                 2>> /var/log/bvpn-ru-monitor.log
*/5 * * * *   /opt/scripts/selfsteal-monitor.py          2>> /var/log/bvpn-selfsteal-monitor.log
5 9 * * *     /opt/scripts/intel-digest.py               2>> /var/log/bvpn-intel-digest.log
0 3 * * *     sleep $((RANDOM % 300)) && cd /opt/remnawave && docker compose restart remnawave >> /var/log/bvpn-maintenance.log 2>&1
```

### NL (`crontab -l`)
```cron
*/15 * * * *  /bin/bash /opt/scripts/watchdog.sh # bvpn-watchdog
```

## 6. State / antispam — где живут маркеры

| Что | Каталог | Сохраняется при reboot |
|-----|---------|------------------------|
| `monitor.sh` alert markers | `/var/lib/bvpn-monitor/alert_*` | ✅ да (был `/tmp` → переехал 2026-05-14) |
| `ru-monitor.py` antispam | `/var/lib/bvpn-monitor/ru_monitor_*` | ✅ да |
| `selfsteal-monitor.py` antispam | `/var/lib/bvpn-monitor/selfsteal_monitor_*` | ✅ да |
| `ru-monitor.py` state.json | `/var/lib/bvpn-ru-monitor/state.json` | ✅ да |
| `selfsteal-monitor.py` state.json | `/var/lib/bvpn-selfsteal-monitor/state.json` | ✅ да |
| `watchdog.sh` (NL) antispam | `/var/lib/bvpn-watchdog/alert_*` | ✅ да |
| `balancer.sh` daily markers | `/tmp/bvpn_states/*_<YYYY-MM-DD>` | ⚠️ нет, но это OK — markers всегда per-day и просто перепосылаются после reboot |

При мажорной правке монитора (state-format / schema) — переместите `state.json` в `…corrupted.<ts>` или просто удалите, монитор перенакатает.

## 7. Drift-чек: скрипты + compose/env (sanitized templates)

Цель §1 — синхронность **управляющих** файлов (`monitor.sh`, `ru-monitor.py`, …).  
Compose и prod-`.env` держим как **sanitized templates** под **`compose/<host>/…/*.tmpl`** (см. **`docs/SECRETS.md`**). Реальные значения — в **`.secrets/vault.env`** (gitignored), собирается скриптом **`python ops/extract_vault.py`** из копий прода (`.secrets/prod-compose/`, тоже gitignored).

### 7.1 Утилита `ops/drift-check.py`

Запуск из корня репозитория:

```powershell
python ops/drift-check.py
```

Поведение:

- Пары **`(репо, прод)`** заданы в **`ops/drift-check.py`** (`PAIRS`): обычные файлы (`kind=file`) и шаблоны (`kind=tmpl`).
- Для **`file`** сравнивается MD5 файла в репо с MD5 на проде.
- Для **`tmpl`**: из шаблона и vault строится **рендер** так же, как на проде; сравнивается MD5 рендера с MD5 prod-файла. Параметр **`tmpl_only_keys`** в `PAIRS` задаёт, какие `${KEY}` подставлять из vault:
  - **`None`** — подставить все плейсхолдеры, для которых есть ключ в vault (типичные `.env`);
  - **`frozenset()`** — не подставлять ничего: compose остаётся с `${POSTGRES_*}` и, для **subscription-page**, с literal **`${REMNA_API_TOKEN}`** в YAML (интерполяция на сервере из **`sub/.env`**, см. `compose/ams/remnawave-sub/docker-compose.yml.tmpl`);
  - **`frozenset({"X"})`** — только перечисленные ключи (например `SECRET_KEY_NODE_AMS` в `remnanode` compose или раньше точечная подстановка в отдельных шаблонах).
- **Один SSH на хост**, внутри — `md5sum` по чанкам путей (меньше таймаутов на LV).
- Если для chunk приходит **`subprocess.TimeoutExpired`**, утилита **повторяет** тот же запрос: до **4** попыток для **`bvpn-lv`**, до **2** для остальных хостов, с **увеличением** `timeout` и короткой паузой между попытками (см. **`P2-ENG-DRIFT-CHECK-01`** / журнал §12).
- Локальный MD5 для шаблонов считается по **нормализованным** байтам: **CRLF / lone CR → LF** (`md5_hex_norm`), чтобы копии с Windows не давали ложный DRIFT.

Exit code **0** — все пары совпали; **1** — DRIFT, MISSING, пустой vault для tmpl, или TIMEOUT.

### 7.2 Рендер вручную перед деплоем

```powershell
# Полный .env (все ключи из vault)
python ops/render_compose.py compose/ams/remnawave/panel.env.tmpl .secrets/vault.env

# Compose: только выбранные секреты; ${POSTGRES_USER} и т.д. остаются для compose
python ops/render_compose.py --only SECRET_KEY_NODE_AMS compose/ams/remnanode/docker-compose.yml.tmpl

# Subscription YAML: drift-check подставляет 0 ключей (как на проде остаётся ${REMNA_API_TOKEN})
python ops/render_compose.py --none compose/ams/remnawave-sub/docker-compose.yml.tmpl
```

Список `--only …` для каждого файла смотри в **`tmpl_only_keys`** у соответствующей строки `PAIRS` в **`ops/drift-check.py`** (они совпадают с логикой сравнения).

### 7.3 Обновление шаблонов после правок на проде

Не коммитить живые секреты. Последовательность:

1. Снять копию prod-файла в `.secrets/prod-compose/<host>/…` (как уже принято для DRIFT-02).
2. **`python ops/sanitize_compose_templates.py`** → перегенерирует **`compose/**/*.tmpl`** (скрипт **полностью пересоздаёт** каталог **`compose/`** только из **`MAP`** в себе же; скрытые там сервисы не попадут); при утечке похожих на секрет строк — **выход с ошибкой** (leak-scan).
3. При необходимости обновить **`.secrets/vault.env`**: **`python ops/extract_vault.py`**.
4. **`python ops/drift-check.py`** — все строки должны быть **OK**.

### 7.4 Периодичность

Раз в 1–2 недели или перед/после релиза. По возможности — шаг CI (без vault: только то, что можно в публичном runner'е).

### 7.5 Safe-deploy gate на AMS (обязательно)

Перед накатом **`compose/ams/**`** на **`/opt/remnawave`**, **`/opt/remnawave/sub`**, **`/opt/remna-shop`**:

1. **`python ops/extract_vault.py`** из свежих **`.secrets/prod-compose/`** (не подгонять секреты вручную).
2. Рендер в **`/tmp`**, diff с продом; **`bash ops/remna_api_token_rollout.sh dry-run`**.
3. Бэкап целевых файлов → накат → smoke sub/panel → **`python ops/drift-check.py`**.

Полный чеклист: **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`** (**`P2-OPS-AMS-SAFE-DEPLOY-01`**). Урок: инцидент **502** **2026-05-17** (§12 бэклога).

---

## 8. Что ещё под капотом (не в §1 таблице)

| Что | Почему отдельно |
|-----|----------------|
| Compose и prod-**.env** для стеков remnawave / remnanode / subscription / bot / adguard | Sanitized **`compose/**/*.tmpl`** + vault; проверка в **`ops/drift-check.py`** (**§7**). |
| `/etc/bvpn/balancer.env` (LV) | `BOT_TOKEN`, `PANEL_TOKEN`, … — **никогда не коммитим**; шаблон **`compose/_shared/etc-bvpn-lv/balancer.env.tmpl`**. |
| `/etc/bvpn/ru-monitor.env` (LV) | Аналогично; **`compose/_shared/etc-bvpn-lv/ru-monitor.env.tmpl`**. |
| `/etc/bvpn/bot-token` (NL) | **`compose/_shared/etc-bvpn-nl/bot-token.tmpl`**. |
| Прочее (`intel-digest.py`, one-shot скрипты) | Артефакты / legacy, не обязательно в drift-matrix. |

## 9. Что делать при первом расхождении

1. `md5sum` на проде vs repo (**или сразу** `python ops/drift-check.py`).
2. Решить, кто SoT (обычно свежее и осмысленнее).
3. Применить **§3** для скриптов или **§7.3** для compose/env.
4. Запись в журнал **`docs/COMMERCIAL-BACKLOG.md`** — что / когда / откуда / куда.

## 10. История

- **2026-05-14** — P1-OPS-DRIFT-01 закрыта. Все 10 файлов синхронизированы (репо ← прод после большой серии правок P0-block / Monitor-block / AMS-decom). Этот документ создан.
- **2026-05-15** — **P1-OPS-DRIFT-02**: в §1 добавлена строка **`compose/**/*.tmpl`**; §7 описывает vault, `sanitize_compose_templates` / `extract_vault`, `render_compose.py` (`--only`, `--none`, согласованность с `tmpl_only_keys` в `drift-check.py`), нормализацию CRLF при сравнении MD5 с продом.
- **2026-05-16** — **§7.5** safe-deploy gate AMS: **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`** (**`P2-OPS-AMS-SAFE-DEPLOY-01`**).
- **2026-05-16** — **`daily-report.sh`**: сбор юзеров через **`/api/users?size=&start=`** постранично (раньше один **`GET /api/users`** давал только первую страницу ~25 записей → расхождение с панелью). Деплой: **`pwsh -File ops/deploy-daily-report-lv.ps1`**. `ru-monitor.py`: текст алерта «cert changed» для внешних SNI (апстрим CDN, не только Caddy/MITM). (и меньший лимит для прочих) при **`TimeoutExpired`**. **`monitor.sh`** в таблице §1: описание **`SUB_*`** / **`PANEL_URL`** (как **`daily-report.sh`**).
