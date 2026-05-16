# Runbook — смена machine JWT (**`REMNA_API_TOKEN=`**) без регресса (502 / 401)

**ID бэклога:** **`P1-OPS-REMNA-TOKEN-01`**  
**Цель:** перевыпуск **API-токена** для вызовов панели — без инлайна **`eyJ…`** в compose подписки и без наследования токена с LV legacy.

**Модель на проде (2026-05):** переменная в файлах всё так же **`REMNA_API_TOKEN=`**, но это **может быть два разных JWT**:

- **AMS** — один токен на **telegram-shop** и **subscription-page** (строки в **`/opt/remna-shop/.env`** и **`/opt/remnawave/sub/.env`** совпадают).
- **LV** — свой токен в **`/etc/bvpn/balancer.env`** (**`PANEL_TOKEN`** и **`REMNA_API_TOKEN`** совпадают между собой) и строка **`REMNA_API_TOKEN=`** в **`/etc/bvpn/ru-monitor.env`**.

При ротации уточните операционно: обновляем **только AMS**, **только LV**, **обе стороны** или **выравниваем оба значения одним новым JWT** из панели.

**Шаблоны в репо / vault для drift:** **`${REMNA_API_TOKEN_AMS}`** vs **`${REMNA_API_TOKEN_LV}`** (`docs/SECRETS.md` §1).

**Запреты:** не коммитить новое значение; не публиковать в TG/почте; допустимо держать в Менеджере паролей и передавать оператору/агенту для наката в сессии (журнал **§12** после факта).

---

## Затронутые места (чеклист)

Перед выдачей токена из панели прочитать **`docs/SECRETS.md` §1** (строки **`REMNA_API_TOKEN_*`**) и **§3**.

### A. Если меняете **AMS** JWT (бот + подписка к панели)

| # | Хост | Путь | Действие |
|---|------|------|----------|
| 1 | AMS | **`/opt/remna-shop/.env`** | Выставить **`REMNA_API_TOKEN=<новый JWT>`** |
| 2 | AMS | **`/opt/remnawave/sub/.env`** | То же значение (**строка `REMNA_API_TOKEN=`**) |
| 3 | AMS | **`/opt/remnawave/sub/docker-compose.yml`** | Только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**; **не** строка **`eyJ…`** в YAML |

LV при этом **не трогаем**.

### B. Если меняете **LV** JWT (balancer / ru-monitor → панели)

| # | Хост | Путь | Действие |
|---|------|------|----------|
| 4 | LV | **`/etc/bvpn/balancer.env`** | **`PANEL_TOKEN`** и **`REMNA_API_TOKEN`** = новое значение (как у вас принято они совпадают) |
| 5 | LV | **`/etc/bvpn/ru-monitor.env`** | **`REMNA_API_TOKEN=`** новое значение |

### C. Если выравниваете **всё** одним токеном из панели

Выполните **таблицы A и B одним и тем же JWT** (явное решение: один токен в панели → пять записей в таблице выше).

После любых изменений локально можно обновить **`.secrets/vault.env`** с копии прода: **`python ops/extract_vault.py`**.

Опционально: рендер из vault — **`python ops/render_compose.py`** + **`docs/DEPLOY.md` §7**.

---

## Порядок исполнения (рекомендуемый)

### A. Подготовка

1. В панели Remnawave: **Generate API token**, роль **`API`**, срок как у действующей политики (`exp≈2299` и т.д.).
2. Сохранить в Bitwarden/1Password (**`BenderVPN/prod`**) до копирования в файлы: отдельно пометьте **AMS-shop/sub** vs **LV** если значения расходятся.
3. С рабочей машины (`ssh_config` с **`bvpn-ams`** / **`bvpn-lv`**): можно прогнать **`bash ops/remna_api_token_rollout.sh dry-run`**.

### B. AMS — запись значений и фикса compose подписки

Только если в scope шага **§A** есть AMS.

1. На AMS обновить **`/opt/remna-shop/.env`** и **`/opt/remnawave/sub/.env`** (можно сначала shop, затем **`bash ops/sync-sub-token-ams.sh`**).
2. Если **`docker-compose.yml` подписки** «сломан» (инлайн JWT): с рабочей машины **`bash ops/sync-sub-token-ams.sh`** или **`bash ops/fix-ams-subscription-api-token.sh`** на AMS.
3. Проверка раскладки на AMS (**обязательно**): **`bash ops/remna_api_token_rollout.sh verify-ams`**

### C. Контейнеры AMS

```bash
# на AMS в каталоге shop
docker compose up -d --force-recreate remna-shop-bot
```

Subscription-page после шага **B** (если трогали sub).

### D. LV

Только если в scope есть **§B**.

Обновить **`balancer.env`** и **`ru-monitor.env`**, затем при необходимости перечитать shell-скрипты (cron обычно подхватит при следующем тике).

### E. Smoke (минимум)

| Проверка | Ожидание |
|----------|----------|
| Публичный URL подписки | **HTTP 200** |
| **`ops/panel_api.py`** или UI панели | нет массовых **401** |
| **`ru-monitor`** (один цикл) | нет серии **`401`** |
| При наличии SSH | **`python ops/drift-check.py`** — всё **OK** |

### F. Закрытие

Строка в **`docs/COMMERCIAL-BACKLOG.md` §12** — что изменено (AMS / LV / оба), дата, smoke OK.

---

## Автоматизация в репозитории

| Скрипт | Назначение |
|--------|------------|
| **`ops/remna_api_token_rollout.sh`** | Справка **`help`**, **`dry-run`**, **`verify-ams`**, **`sync-ams-sub`** |
| **`ops/sync-sub-token-ams.sh`** | SSH AMS → **`fix-ams-subscription-api-token.sh`** |
| **`ops/check-ams-subscription-token-layout.sh`** | На AMS: регресс-детектор YAML vs **`.env`** |
| **`ops/extract_vault.py`** | Собирает **`REMNA_API_TOKEN_AMS`** / **`LV`** в **`.secrets/vault.env`** из **`prod-compose`**, после SCP с прода |

Если перевыпуск вызван сменой **`JWT_API_TOKENS_SECRET`** — это **шире**: **`docs/RUNBOOK-P0-SEC04-SEC05.md`** + **`ops/rotate_ams_panel_core_secrets.py`**, затем выпуск новых machine-token'ов по этому runbook для **AMS** и **LV** как положено вашему решению.
