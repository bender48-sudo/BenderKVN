# База знаний BenderVPN (операционный контур)

Цель этого файла — **единая точка входа**: куда складываем находки, как работаем, чего избегать. Детальный бэклог и журнал решений остаются в **`docs/COMMERCIAL-BACKLOG.md`** (особенно **§12**).

---

## 1. Где что лежит

| Что нужно | Документ / артефакт |
|-----------|---------------------|
| Очередь задач по приоритетам | **`docs/COMMERCIAL-BACKLOG.md`** |
| Журнал «что уже сделали на проде» | тот же файл, **§12** |
| Очередь capacity (users/nodes vs §10.1) | `python ops/capacity_snapshot.py` (токен в `.secrets/panel-token.txt`) |
| Деплой, drift, рендер vault | **`docs/DEPLOY.md`** |
| Порядок спринтов (продукт → UX) | **`docs/POLICY-BACKLOG-ORDER.md`** |
| Алерты в Telegram (метаданные) | **`docs/POLICY-TELEGRAM-ALERTS.md`** |
| SSH known_hosts / `StrictHostKeyChecking` | **`docs/SSH-HOST-KEY-PRACTICE.md`** |
| Утечка секрета в чат / скриншот | **`docs/POLICY-SECRET-LEAK-RESPONSE.md`** |
| Drift прод↔репо после P0 / смены панели | **`docs/DRIFT-POST-P0.md`** |
| Реестр секретов и путей на хостах | **`docs/SECRETS.md`** |
| Инциденты (роли, первый ответ) | **`docs/RUNBOOK-INCIDENT.md`** |
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

2. **Один источник правды по machine JWT.** Активный **`REMNA_API_TOKEN`** задаётся в панели и раскладывается согласно **`docs/SECRETS.md` §3**. Не брать значение со **старого LV `/opt/remnawave`** (legacy закрыт **P0-SEC-04**).

3. **Subscription-page без инлайна JWT.** В **`/opt/remnawave/sub/docker-compose.yml`** только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**; строка **`eyJ…`** там — регрессия → клиентские **502** и **401** на краю саба. Контроль: **`bash ops/remna_api_token_rollout.sh verify-ams`** (или **`check-ams-subscription-token-layout.sh`** на AMS).

4. **Два параллельных мониторинга на LV.** После любых изменений платформы (drain AMS, **`isHidden`/`isDisabled`**, подмена таргетов) синхронно обновлять и **`monitor.sh`**, и **`ru-monitor.py`** (и при необходимости **selfsteal**). Чеклист зафиксирован в журнале **COMMERCIAL-BACKLOG §12** (**2026-05-14**).

5. **Дрейф прод ↔ репо.** После ручных правок или ротаций — **`python ops/drift-check.py`** с рабочей машины/бастиона с SSH; **`TIMEOUT`** на **`/etc/bvpn/*.env`** — см. **`P2-ENG-DRIFT-CHECK-01`** в бэклоге.

6. **Коммиты только по явной просьбе владельца репозитория** — по договорённости в этом проекте; агент не коммитит «между делом».

---

## 3. Типичные ошибки прошлых спринтов (кратко)

| Симптом | Частая причина | Куда смотреть |
|---------|----------------|----------------|
| Клиенты **502**/битый sub при живой панели | JWT зашит в **`sub/docker-compose.yml`**, не подтягивается из **`.env`** | **`RUNBOOK-REMNA-API-TOKEN`**, **`fix-ams-subscription-api-token`** |
| **401** от **`ru-monitor`** / balancer после ротации | Обновили токен не везде (**LVBalancer + ru-monitor + shop + sub**) | **`SECRETS.md`**, runbook по токену |
| **USERS=0 NODES=0** в balancer | **`PANEL_URL`** / токен бьют в **`localhost:3000`** вместо публичной панели | **`balancer.env.tmpl`**, **`P2-MON-BALANCER-PANEL-URL`** (закрыт) |
| Шум после drain AMS только в одном алертере | Обновили **`monitor.sh`**, забыли **`ru-monitor`** (или наоборот) или selfsteal | журнал §12 **2026-05-14** |
| **Total** в TG daily report = **25**, в панели больше | **`GET /api/users`** без **`size`/`start`** — только первая страница ответа API | Пагинация как в **`grandfather_panel_users_expire.py`** / текущий **`daily-report.sh`** |
| DRIFT по **`tmpl`** сразу на нескольких `.env` / compose | Рендер из vault не совпадает с продом: vault устарел **или** на проде правили вручную | **`docs/DRIFT-POST-P0.md`** (порядок: vault → файлы → tmpl → перепроверка); **`docs/DEPLOY.md` §7.3** |
| **`python ops/drift-check.py`** exit **1**, много **DRIFT (file)** | Скрипты на проде уехали от репо (патч на сервере без git) | Деплой из репо по **`docs/DEPLOY.md` §3**, не заполнять waive «чтобы отмазаться» |
| Контрабанда локальных правил Claude в Git | Коммит **`.claude/settings.local.json`** содержит пути и не должен быть публичным | **`.gitignore`**, раздел KNOWLEDGE-BASE §2 |

---

## 4. Связка с аудитами

- После закрытия **P1** и **P0-SEC-04/05**: **`docs/P1-POST-AUDIT.md`**.
- «ТПСУ / red team» не смешиваем с операционкой по подписке — они в одном **`COMMERCIAL-BACKLOG` §5.1**, но исполняются отдельным потоком.

---

## 5. Обновление этого файла

Добавляйте строки в **§3** только когда найден новый класс ошибки с понятным сигналом и фиксацией. Рутинные задачи без обобщённого урока — только журнал **§12** основного бэклога.
