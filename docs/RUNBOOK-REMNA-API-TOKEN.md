# Runbook — смена `REMNA_API_TOKEN` без регресса (502 / 401)

**ID бэклога:** **`P1-OPS-REMNA-TOKEN-01`**  
**Цель:** при перевыпуске machine JWT (**`REMNA_API_TOKEN`**) все потребители обновляются **одновременно**, без инлайна **`eyJ…`** в compose подписки и без наследования токена с LV legacy.

**Запреты:** не коммитить новое значение; не публиковать в TG/почте; допустимо держать в Менеджере паролей и передавать оператору/агенту для наката в сессии (журнал **§12** после факта).

---

## Затронутые места (чеклист)

Перед выдачей токена из панели: прочитать **`docs/SECRETS.md` §1 строка `${REMNA_API_TOKEN}` и §3**.

| # | Хост | Путь | Действие |
|---|------|------|----------|
| 1 | AMS | **`/opt/remna-shop/.env`** | Выставить **`REMNA_API_TOKEN=<новый JWT>`** |
| 2 | AMS | **`/opt/remnawave/sub/.env`** | То же значение (**строка `REMNA_API_TOKEN=`**) |
| 3 | AMS | **`/opt/remnawave/sub/docker-compose.yml`** | Только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`** в `environment` / `environment_file` как у вас заведено; **не** строка **`eyJ…`** |
| 4 | LV | **`/etc/bvpn/balancer.env`** | **`PANEL_TOKEN`** и **`REMNA_API_TOKEN`** = новое значение (как принято у вас) |
| 5 | LV | **`/etc/bvpn/ru-monitor.env`** | **`REMNA_API_TOKEN=`** новое значение |

Опционально: если используете рендер из vault — **`python ops/render_compose.py`** + **`docs/DEPLOY.md` §7**.

---

## Порядок исполнения (рекомендуемый)

### A. Подготовка

1. В панели Remnawave: **Generate API token**, роль **`API`**, срок как у действующей политики (`exp≈2299` и т.д.).
2. Сохранить в Bitwarden/1Password (**`BenderVPN/prod`** / **`REMNA_API_TOKEN`**) **до** копирования в файлы на серверах.
3. С рабочей машины (`ssh_config` с **`bvpn-ams`** / **`bvpn-lv`**): можно прогнать **`bash ops/remna_api_token_rollout.sh dry-run`**.

### B. AMS — запись значений и фикса compose подписки

1. На AMS вручную обновить **`/opt/remna-shop/.env`** и **`/opt/remnawave/sub/.env`** (можно временно только shop, затем синхронизировать — см. шаг **C**).
2. Если **`docker-compose.yml` подписки** уже «сломан» (инлайн JWT): с рабочей машины:
   ```bash
   bash ops/sync-sub-token-ams.sh
   ```
   (подтягивает токен из shop в **`sub/.env`**, чинит YAML, **`docker compose up -d --force-recreate`** subscription-page.)

3. Проверка раскладки на AMS (**обязательно**):
   ```bash
   bash ops/remna_api_token_rollout.sh verify-ams
   ```

### C. Контейнеры AMS

После изменения **`/opt/remna-shop/.env`**:
```bash
# на AMS в каталоге shop
docker compose up -d --force-recreate remna-shop-bot
```
(или как у вас называется сервис бота — см. compose на проде.)

Subscription-page после шага **B.2**.

### D. LV

Обновить **`balancer.env`** и **`ru-monitor.env`**, затем при необходимости перечитать shell-скрипты (cron обычно подхватит при следующем тике; для **`balancer.sh`** — по вашей практике ручной прогон / ожидание cron).

### E. Smoke (минимум)

| Проверка | Ожидание |
|----------|----------|
| Публичный URL подписки (**`curl -fsS`** или монитор-дубль **`SUB_MONITOR_PROBE_URL`**) | **HTTP 200** |
| **`ops/panel_api.py`** или UI панели | список узлов без массовых ошибок авторизации |
| **`ru-monitor`** (лог за один цикл) | нет серии **`401`** |
| При наличии SSH | **`python ops/drift-check.py`** без неожиданного **DRIFT** по набранным файлам |

### F. Закрытие

Строка в **`docs/COMMERCIAL-BACKLOG.md` §12** с датой и кратко «ротация `REMNA_API_TOKEN`, smoke OK».

---

## Автоматизация в репозитории

| Скрипт | Назначение |
|--------|------------|
| **`ops/remna_api_token_rollout.sh`** | Справка **`help`**, **`dry-run`** (чеклист), **`verify-ams`**, **`sync-ams-sub`** |
| **`ops/sync-sub-token-ams.sh`** | SSH AMS → выполнить **`fix-ams-subscription-api-token.sh`** |
| **`ops/check-ams-subscription-token-layout.sh`** | Только на AMS / через SSH: регресс-детектор YAML vs **`.env`** |

Если перевыпуск вызван сменой **`JWT_API_TOKENS_SECRET`** — это **шире**: **`docs/RUNBOOK-P0-SEC04-SEC05.md`** + **`ops/rotate_ams_panel_core_secrets.py`**, затем уже этот сценарий по **`REMNA_API_TOKEN`**.
