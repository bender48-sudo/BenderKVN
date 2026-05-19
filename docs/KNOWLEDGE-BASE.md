# База знаний BenderVPN (операционный контур)

Цель этого файла — **единая точка входа**: куда складываем находки, как работаем, чего избегать. Детальный бэклог и журнал решений остаются в **`docs/COMMERCIAL-BACKLOG.md`** (особенно **§12**).

---

## 1. Где что лежит

| Что нужно | Документ / артефакт |
|-----------|---------------------|
| **Карта бэклога (начать здесь)** | **`docs/BACKLOG-MAP.md`** |
| **Что делать сейчас (один NEXT)** | **`docs/BACKLOG-QUEUE.md`** — фаза 4 **DONE**; владелец: **`MANUAL-OWNER-CHECKLIST.md`** (BotFather **:8443**, Q032) |
| **Флоу (после Q062)** | **`docs/AGENT-FLOW-BACKLOG.md`** |
| **ТСПУ — 12 наблюдений → бэклог** | **`docs/TSPU-OBSERVATIONS.md`** |
| **Порт вместо 2053** | **`docs/EDGE-PORT-RECOMMENDATION.md`** |
| **Тиры подписки (turbo / WL)** | **`docs/PRODUCT-TIER-PROFILES.md`** |
| Своё iOS/Android app (долгий горизонт) | **`docs/NATIVE-APP-BACKLOG.md`** (**P5-PROD-NATIVE-APP-01**, **Q053**) |
| Очередь задач по приоритетам | **`docs/COMMERCIAL-BACKLOG.md`** (§7.1, **§12**) |
| Бэклог флоу / бабушка-тест | **`docs/USER-FLOW-BACKLOG.md`**, **`docs/USER-FLOW-JOURNEY.md`** |
| Инструкции агента (Q032–050) | **`docs/AGENT-FLOW-BACKLOG.md`** |
| Portal (сайт + Mini App) | **`web/portal/`**, **`RUNBOOK-USER-BOOTSTRAP-SITE`**, **`RUNBOOK-TELEGRAM-MINIAPP`** |
| Правило: одна задача → коммит → стоп | **`docs/POLICY-SEQUENTIAL-WORK.md`** |
| Журнал «что уже сделали на проде» | тот же файл, **§12** |
| Очередь capacity (users/nodes vs §10.1) | `python ops/capacity_snapshot.py` (токен в `.secrets/panel-token.txt`) |
| Деплой, drift, рендер vault | **`docs/DEPLOY.md`** |
| Порядок спринтов (продукт → UX) | **`docs/POLICY-BACKLOG-ORDER.md`** |
| Тексты ошибок бота / карта для поддержки | **`bot_src/user_messages.py`**, **`docs/support/USER-FACING-ERRORS.md`** |
| Черновик рассылки при инциденте | **`docs/templates/USER-INCIDENT-BROADCAST.md`** |
| Черновик политики логов (внутр.) | **`docs/POLICY-LOGS-DATA.md`** |
| LV/NL распределение нагрузки / soft cap / 3-я нода | **`docs/NODE-POLICY-LV-NL.md`** (**P6-SCALE-02**) |
| Регрессия `ops/load_env_file` (`site.env`) | `python -m unittest discover -s tests` из корня репо |
| Хотфикс бота (handlers/user_messages на AMS) | **`pwsh -File ops/deploy-bot-handlers-ams.ps1`** (см. **`docs/DEPLOY.md` §4.3.1**) |
| Авто-уведомление «обновите подписку» после PATCH шаблона | **`ops/subscription_config_notify.py`** → бот scheduler; деплой **`pwsh -File ops/deploy-bot-sub-refresh-ams.ps1`** |
| Sub-page HA (split-host :3010 / :3011) | **`docs/RUNBOOK-P6-SUBSCRIPTION-HA.md`**, **`ops/deploy-sub-page-ha-ams.ps1`**, **`ops/patch-caddy-sub-split-host-lv.sh`** |
| Postgres панели (аудит / pg_stat / окно бэкапа) | **`docs/RUNBOOK-P6-POSTGRES-MAINTENANCE.md`**, **`ops/pg_remnawave_audit.py`** |
| Digest pin образов (postgres, valkey, adguard) | **`docs/IMAGE-PINS.md`**, **`python ops/check_compose_image_pins.py`** |
| Алерты в Telegram (метаданные) | **`docs/POLICY-TELEGRAM-ALERTS.md`** |
| SSH known_hosts / `StrictHostKeyChecking` | **`docs/SSH-HOST-KEY-PRACTICE.md`** |
| Утечка секрета в чат / скриншот | **`docs/POLICY-SECRET-LEAK-RESPONSE.md`** |
| Drift прод↔репо после P0 / смены панели | **`docs/DRIFT-POST-P0.md`** |
| Накат AMS compose/env (gate) | **`docs/RUNBOOK-AMS-SAFE-DEPLOY.md`** |
| Go-live оплаты в боте | **`docs/RUNBOOK-COMMERCE-GO-LIVE.md`** |
| GTM / рост 10k–30k | **`docs/GTM-GROWTH-OUTLINE.md`**, wiki-шаблон **`docs/templates/GTM-WIKI-PAGE.md`**, реестр URL **`docs/GTM-WIKI.md`** |
| Edge подписки (P6-SCALE-04) | **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`** |
| Правила репозитория (secrets, sanitize, drift) | **`docs/POLICY-REPO-WORKFLOW.md`** |
| Онбординг пользователя / поддержка первого коннекта | **`docs/ONBOARDING.md`**, полный флоу-бэклог **`docs/USER-FLOW-BACKLOG.md`** |
| Реестр секретов и путей на хостах | **`docs/SECRETS.md`** |
| Инциденты (роли, первый ответ) | **`docs/RUNBOOK-INCIDENT.md`** |
| VPS / платёжка / DNS отключили за день (P3-RED-JURIS) | **`docs/JURISDICTION-FAILOVER-WIKI.md`**, **`docs/RUNBOOK-JURISDICTION-FAILOVER.md`**, tabletop **`docs/TABLETOP-JURISDICTION-EXERCISE.md`** |
| Публичный статус для пользователей (P5-COM-01) | **`https://k9x2m1.conntest.xyz:8443/status`**, **`docs/RUNBOOK-PUBLIC-STATUS-PAGE.md`** |
| Карта пути пользователя (P3-FLOW-00) | **`docs/USER-FLOW-JOURNEY.md`**, **`docs/USER-FLOW-BACKLOG.md`**, **`docs/AGENT-FLOW-BACKLOG.md`** |
| Портал / Mini App (P3-FLOW-14) | **`web/portal/`**, **`ops/site_urls.py`** (`public_portal_url`) |
| Bootstrap без VPN (P3-FLOW-01) | **`https://k9x2m1.conntest.xyz:8443/start/`**, **`docs/RUNBOOK-USER-BOOTSTRAP-SITE.md`** |
| Ротация панели + LV legacy архив | **`docs/RUNBOOK-P0-SEC04-SEC05.md`** |
| Смена **`REMNA_API_TOKEN`** без 502 | **`docs/RUNBOOK-REMNA-API-TOKEN.md`** |
| Логи Caddy без сырого **`/api/sub/`** в access-log | **`docs/RUNBOOK-CADDY-SUBSCRIPTION-LOGS.md`** |
| Бэкап Postgres панели (AMS → LV, restore test) | **`docs/RUNBOOK-BACKUP-REMNAWAVE.md`** |
| Пик подписки / edge (rate limit, тест нагрузки) | **`docs/RUNBOOK-P6-SUBSCRIPTION-EDGE.md`** |
| Git / ветки / что в репо | **`docs/VCS-WHERE-IS-GIT.md`** |
| FAQ для пользователя | **`docs/FAQ.md`** |

---

## 2. Правила работы (не обсуждаются в пылу инцидента)

1. **Секреты не в Git.** В репозитории только шаблоны (`*.tmpl`), примеры (`*.example`) и ссылки «куда записать на проде». Перед **`git push`** проверять **`git status`** на предмет случайных **`.env`**, **`.secrets/`**, токенов в diff. Локальные настройки агентов с путём к паролям (**`.claude/settings.local.json`** и аналоги) — **игнорируются** и не пересылать в общие каналы.

2. **Machine JWT для API панели (два вида значений на проде).** В переменной окружения на хостах она **`REMNA_API_TOKEN=`**, но в vault для drift два ключа шаблонов — **`REMNA_API_TOKEN_AMS`** (AMS shop + **`sub/.env`**) и **`REMNA_API_TOKEN_LV`** (LV **`balancer.env`** / **`ru-monitor.env`**). Карта файлов и ротации — **`docs/SECRETS.md` §1**. Не брать значение со **старого LV `/opt/remnawave`** (legacy закрыт **P0-SEC-04**).

3. **Subscription-page без инлайна JWT.** В **`/opt/remnawave/sub/docker-compose.yml`** только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**; строка **`eyJ…`** там — регрессия → клиентские **502** и **401** на краю саба. Контроль: **`bash ops/remna_api_token_rollout.sh verify-ams`** (или **`check-ams-subscription-token-layout.sh`** на AMS).

4. **Два параллельных мониторинга на LV.** После любых изменений платформы (drain AMS, **`isHidden`/`isDisabled`**, подмена таргетов) синхронно обновлять и **`monitor.sh`**, и **`ru-monitor.py`** (и при необходимости **selfsteal**). Чеклист зафиксирован в журнале **COMMERCIAL-BACKLOG §12** (**2026-05-14**).

5. **Дрейф прод ↔ репо.** После ручных правок или ротаций — **`python ops/drift-check.py`** с рабочей машины/бастиона с SSH; **`TIMEOUT`** на **`/etc/bvpn/*.env`** — см. **`P2-ENG-DRIFT-CHECK-01`** в бэклоге.

6. **Коммиты только по явной просьбе владельца репозитория** — по договорённости в этом проекте; агент не коммитит «между делом».

---

## 3. Типичные ошибки прошлых спринтов (кратко)

| Симптом | Частая причина | Куда смотреть |
|---------|----------------|----------------|
| Клиенты **502**/битый sub при живой панели | JWT зашит в **`sub/docker-compose.yml`**, не подтягивается из **`.env`** | **`RUNBOOK-REMNA-API-TOKEN`**, **`fix-ams-subscription-api-token`** |
| **401** от **`ru-monitor`** / balancer после ротации | На LV обновили не **`balancer.env`** + **`ru-monitor.env`** **или** на AMS не shop+sub (**два JWT могут отличаться**, см. **`SECRETS.md`**) | **`SECRETS.md`**, **`RUNBOOK-REMNA-API-TOKEN`** |
| **USERS=0 NODES=0** в balancer | **`PANEL_URL`** / токен бьют в **`localhost:3000`** вместо публичной панели | **`balancer.env.tmpl`**, **`P2-MON-BALANCER-PANEL-URL`** (закрыт) |
| Шум после drain AMS только в одном алертере | Обновили **`monitor.sh`**, забыли **`ru-monitor`** (или наоборот) или selfsteal | журнал §12 **2026-05-14** |
| **Total** в TG daily report = **25**, в панели больше | **`GET /api/users`** без **`size`/`start`** — только первая страница ответа API | Пагинация как в **`grandfather_panel_users_expire.py`** / текущий **`daily-report.sh`** |
| DRIFT по **`tmpl`** сразу на нескольких `.env` / compose | Рендер из vault не совпадает с продом: vault устарел **или** на проде правили вручную | **`docs/DRIFT-POST-P0.md`** (порядок: vault → файлы → tmpl → перепроверка); **`docs/DEPLOY.md` §7.3** |
| **`python ops/drift-check.py`** exit **1**, много **DRIFT (file)** | Скрипты на проде уехали от репо (патч на сервере без git) | Деплой из репо по **`docs/DEPLOY.md` §3**, не заполнять waive «чтобы отмазаться» |
| Контрабанда локальных правил Claude в Git | Коммит **`.claude/settings.local.json`** содержит пути и не должен быть публичным | **`.gitignore`**, раздел KNOWLEDGE-BASE §2 |
| Crash loop **`remnawave`**, Prisma **P1000**, **502** на панели/sub | Накат **`panel.env`** из vault: **`DATABASE_URL`** не совпадает с живым **`remnawave-db`** | Откат **`/opt/remnawave/.env`** с прода-бэка + **`python ops/extract_vault.py`** |
| **502** на sub, **401** у subscription-page к панели | Рендер **`sub/docker-compose.yml`**: неверный **`REMNA_API_TOKEN`** | Откат compose с бэкапа; **`RUNBOOK-REMNA-API-TOKEN`** |

---

## 4. Связка с аудитами

- После закрытия **P1** и **P0-SEC-04/05**: **`docs/P1-POST-AUDIT.md`**.
- «ТПСУ / red team» не смешиваем с операционкой по подписке — они в одном **`COMMERCIAL-BACKLOG` §5.1**, но исполняются отдельным потоком.

---

## 5. Обновление этого файла

Добавляйте строки в **§3** только когда найден новый класс ошибки с понятным сигналом и фиксацией. Рутинные задачи без обобщённого урока — только журнал **§12** основного бэклога.
