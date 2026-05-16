# BenderVPN — коммерческий бэклог

**Версия документа:** 2026-05-15 — ~~P2-MON-01~~ / ~~P2-MON-02~~, P2.monitor/drift-check, ~~P1-RED-LOG-01~~ (репозиторий).
**Цель:** стабильный **8–9/10** (нишевый коммерческий VPN в РФ); измеримый рост к максимально достижимому качеству.  
**Определение «готово»:** по каждой задаче выполнен критерий в колонке **Done when** + при необходимости запись в трекере (статусы `TODO` / `DOING` / `DONE`).

---

## 1. Срез продакшена (зафиксировано по SSH, AMS + LV)

Используйте как **baseline** для порогов ниже; обновляйте строку даты после каждого замера.

| Объект | Факт (снимок после P1-close **2026-05-15**; счётчики БД/TRaffic переснять при SSH-ревизии) |
|--------|----------------|
| **Роль AMS** | Панель + подписка (`remnawave`, postgres, redis, subscription-page, бот, AdGuard, Caddy-selfsteal). **`remnanode` AMS** — **stopped (drain, P1-ARCH-AMS-DECOM 4a)**; не running в `docker ps`. |
| **Роль LV** | Production-нода (`remnanode` + AdGuard); `/opt/scripts/*`. |
| **Роль NL** | Production-нода (`remnanode`). |
| **Пользователи в БД** (`users`) | **≈58** (ориентир; см. журнал §12) |
| **Ноды в панели** | **3 записи**; prod **online: LV + NL**; Amsterdam-01 — **decom**, `connected=false` до шага 4c. |
| **Inject / AMS hosts** | Не входят в `injectHosts`; целевые `hosts`: `isHidden` + `isDisabled` (зафиксировано **2026-05-14**). |
| **Размер БД Postgres** | **~11 MB** (ориентир) |
| **RAM хоста AMS** | **~2 GiB** — панель + edge без prod VPN после drain |
| **Вывод** | Модель роста: **2 prod-ноды (LV+NL) + панель AMS**. Контроль «кто всё ещё видит AMS IP в Happ-sub»: **`daily-report.sh`** вызывает **`count_users_with_ams_sub.py`**. Узкие места: RAM/API панели, публичная подписка (**P6**). |

---

## 2. Легенда приоритетов

| Метка | Что закрывает |
|-------|----------------|
| **P0** | Безопасность, целостность, компрометация = конец доверия |
| **P1** | Продукт, РФ‑выживаемость, конфигурация матрицы |
| **P2** | Надёжность, мониторинг, бэкапы, SSH‑дисциплина |
| **P3** | Юзерфлоу, поддержка, коммуникация инцидентов |
| **P4** | DNS‑bootstrap / белые списки (**не** основной VPN) |
| **P5** | Полировка после «восьмёрки» |
| **P6** | Ёмкость: метрики, пороги, ноды, подписка, рост до **10k–30k+** |

---

## 3. Очередь по спринтам (чёткий порядок)

Выполнять **сверху вниз**. Параллельно: только **P4-DNS** при отдельном человеке (не блокирует P0–P2).

| # | Спринт‑кусок | ID |
|---|----------------|-----|
| 1 | TLS + секреты + argv | **P0-SEC-01** ✅, **P0-SEC-02** ✅, **P0-OPS-01** ✅ |
| 2 | Подписка `:3010` + UFW + compose | **P0-SEC-03** ✅ |
| 3 | Digest образов | **P0-OPS-02** ✅ |
| 4 | **Архитектура**: AMS = только панель | ~~**P1-ARCH-AMS-DECOM**~~ ✅ *(drain выполнен 2026-05-14; шаг **4c** опционально — удалить запись ноды в UI)* |
| 5 | **Прод ↔ репо**: синхронизация `/opt/scripts/` + compose/env templates | **P1-OPS-DRIFT-01** ✅, **P1-OPS-DRIFT-02** ✅ |
| 5b | **После P0‑SEC‑05 / миграции панели**: снять DRIFT и починить мониторинг вместимости (`balancer` → публичный `PANEL_URL`) | **P2-OPS-DRIFT-POST-P0**, **P2-MON-BALANCER-PANEL-URL** ✅ (см. §12), ~~**P2-ENG-DRIFT-CHECK-01**~~ ✅ |
| 6 | Конфиг в одном месте + ru-monitor хосты + чистка артефактов | **P1-ENG-01** ✅ (`ops/site_urls.py` + `deploy-node.sh`), **P1-ENG-02** ✅, ~~**P1-ENG-03**~~ ✅ (`archive/tmp-remna-shop-bot-patches/` + `redact_bvpn_artifacts`) |
| 7 | Мониторинг «Xray реально жив» + state dirs | ~~**P2-MON-01**~~ ✅, ~~**P2-MON-02**~~ ✅ |
| 8 | Бэкапы (off-host + restore test) + patches | **P2-BAK-01**, **P2-BAK-02** |
| 9 | Метрики ёмкости (**старт P6 до роста базы**) | **P6-SCALE-01**, **P6-SCALE-04** (минимум) |
| 10 | Продуктовая линия + онбординг + тексты ошибок | ~~**P1-PRO-01…04**~~ ✅ (см. **`docs/FAQ.md`**, **`docs/RUNBOOK-INCIDENT.md`**, **`docs/HAPP-MATRIX.md`**, **`docs/POLICY-SNI-MONITORING.md`**), **P3-UX-01**, **P3-UX-02** |
| 11 | DNS PoC → FAQ (по ресурсу) | **P4-DNS-01** → **P4-DNS-02** → **P4-DNS-03** |
| 12 | **Red team / ТПСУ** (устойчивость к наблюдению, blast radius, рост до 30k) — см. **§5.1 → §10.2** | **P1-RED-DATA-01** … **P1-RED-LOG-01** → **P2-RED-*** → **P6-RED-*** → **P3-RED-*** → **P5-RED-RD-01** |

---

## 4. P0 — Критично

| ID | Задача | Done when |
|----|--------|-----------|
| **P0-SEC-01** | Убрать **`curl -sk`** / **`CERT_NONE`** там, где **Bearer** или **изменение состояния** панели. | Все такие вызовы → проверка TLS (CA или pin); read‑only health вынесен и помечен. |
| **P0-SEC-02** | Переписать **`ops/sync-sub-token-ams.sh`**: секрет **не** в `ssh "…${VAL}…"`. | Передача через stdin/heredoc/base64; review без shell‑инъекции. |
| **P0-SEC-03** | Решение по **`0.0.0.0:3010`**: зачем, кто достучится, UFW / reverse proxy. | Wiki + `ss`/ufw проверены; нет лишнего exposed surface. |
| ~~**P0-SEC-04**~~ ✅ | **`/opt/remnawave/` на LV**: legacy дерево с **копиями** JWT/Postgres/API-секретов активного AMS. | **DONE 2026‑05‑15** (журнал §12): архив **`/opt/_archive/remnawave-legacy-*`**, **`chattr +i`** по runbook; живого **`/opt/remnawave/`** на LV нет. |
| ~~**P0-SEC-05**~~ ✅ | После **P0-SEC-04**: ротация `JWT_AUTH_SECRET`, `JWT_API_TOKENS_SECRET`, `POSTGRES_PASSWORD` на AMS + перевыпуск и раскладка **`REMNA_API_TOKEN`** в 4 местах. | **DONE 2026‑05‑15** (журнал §12): фаза A **`rotate_ams_panel_core_secrets.py --apply`** + **`--force-recreate remnawave`**; фаза B новый API‑токен → AMS shop/sub + LV **`balancer.env`** / **`ru-monitor.env`**; smoke входа в панель / sub / мониторов. |
| **P0-OPS-01** | **`deploy-node.sh`**: токен панели **не** в argv. | `ps` на машине деплоя не показывает токен целиком. |
| **P0-OPS-02** | Образы Docker: **`:latest` → digest** для критичных сервисов. | Compose/скрипты воспроизводят тот же образ по digest. |

---

## 5. P1 — Продукт и инженерия

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P1-PRO-01**~~ ✅ | Линия продукта: основной VPN vs аварийный режим (в т.ч. DNS). | **2026-05-15**: пользовательский **`docs/FAQ.md`** (основной VPN vs DNS/bootstrap; ссылка на **`P4-DNS-02`** в бэклоге). Юридическая оферта — вне репо. |
| ~~**P1-PRO-02**~~ ✅ | Внутренний SLA + runbook инцидента (1 стр.). | **2026-05-15**: **`docs/RUNBOOK-INCIDENT.md`** (роли, рекомендация первого ответа ≤60 мин, проверки, эскалация; имена — в частной базе не в git). |
| ~~**P1-PRO-03**~~ ✅ | Матрица Happ: один источник `TEMPLATE_UUID`, URL панели, правила нод; **rollback** после PATCH. | **2026-05-15**: **`docs/HAPP-MATRIX.md`** + **`ops/site_urls.py`** / **`ops/site.env.example`**; процедуры **`ru_bypass_routing`** / **`freeze_ams_node`**, снапшоты **`.secrets/snapshots/`**. |
| ~~**P1-PRO-04**~~ ✅ | Политика probe‑SNI / снижение сигнатуры мониторинга. | **2026-05-15**: **`docs/POLICY-SNI-MONITORING.md`** (принципы + журнал согласований; код без обязательных правок). |
| ~~**P1-PRO-RU-BYPASS-01**~~ ✅ | **Split-tunneling** RU-приложений/сайтов: direct в Happ-template; список и процесс в **`docs/RU-BYPASS.md`**. | **2026-05-15 DONE**: журнал §12; **`ops/ru_bypass_routing.py`**, **`ops/probe_routing.py`**. |
| ~~**P1-OPS-SELFSTEAL-01**~~ ✅ | **Selfsteal fingerprint `EXPECTATIONS`** vs актуальные upstream'ы. | **2026-05-15 DONE**: шапка у `EXPECTATIONS` в **`selfsteal-monitor.py`**; **`ads.x5.ru` → HTTP 302** + tolerate (журнал §12). |
| ~~**P1-ENG-01**~~ ✅ | Один конфиг **без секретов** для публичных URL/UUID (панель, подписка, ru‑relay для ops). | **`ops/site_urls.py`**, **`ops/site.env.example`**, **`deploy-node.sh`** (опц. source), wiring в ключевые `ops/*.py`. |
| ~~**P1-ENG-02**~~ ✅ | **`ru-monitor.py`**: не «ровно N» таргетов; устойчивость к смене числа хостов. | Закрыто **Monitor-block D (2026-05-14)**: предупреждение если **<4** целей; нет жёсткого «expected 16». |
| ~~**P1-ENG-03**~~ ✅ | `tmp_*.py` → архив; **`bvpn-artifacts`** без сохранённых живых JWT. | **`archive/tmp-remna-shop-bot-patches/`** + README; **`ops/redact_bvpn_artifacts.py`**. |
| ~~**P1-OPS-DRIFT-01**~~ ✅ | Синхронизация прод ↔ репо для `/opt/scripts/{monitor.sh,daily-report.sh,ru-monitor.py,…}`. Закрыта 2026-05-14: репо ← прод для всех 10 управляющих файлов (LV/AMS/NL), `ops/drift-check.py` сравнивает md5 в один SSH-вызов на хост, `docs/DEPLOY.md` — процедура и карта SoT. |
| ~~**P1-OPS-DRIFT-02**~~ ✅ | Sanitized **`compose/**/*.tmpl`**, **`docs/SECRETS.md`**, **`python .secrets/sanitize-compose.py`** + **`extract-vault.py`**, рендер **`ops/render_compose.py`** (`--only` / `--none` для compose), **`ops/drift-check.py`** с `tmpl_only_keys` и нормализацией CRLF. Закрыто 2026-05-15. |
| ~~**P1-ARCH-NODE-UNIFY**~~ ✅ | Единый стиль **`remnanode`**: **`env_file` + `node.env.tmpl`**, digest pin (**`sha256:9d57375a8168d…`**), образ **`ghcr.io/remnawave/node`**. | **`compose/lv|nl|ams/remnanode/`** нормализовано в репо; **`drift-check`** зелёный после деплоя **`.env`** на NL/(AMS legacy). |
| ~~**P1-ARCH-AMS-DECOM**~~ ✅ | **AMS VPN drained** (`remnanode` stopped): freeze inject + hosts hidden/disabled → drain → daily metric «sub still resolves AMS IPs». | **2026-05-14**: шаги **1**, **2**, **4a** (журнал). **2026-05-15**: метрика в **`daily-report.sh`** через **`ops/count_users_with_ams_sub.py`**. Опционально **4c** — удалить Amsterdam-01 в панели. Детальный план шагов 1–5 — записи журнала **2026-05-14**. |

### 5.1 Red team / ТПСУ — конкретные доработки (приоритет: критичные → мелкие)

Источник: аудит «чёрного оппонента» + дорожная карта смягчения (sing-box/USENIX DPI‑литература, Vault/SPIFFE, Snowflake‑подобный bootstrap). Выполнять в порядке **P1‑RED → P2‑RED → P6‑RED → P3‑RED → P5‑RED**.

| ID | Задача | Done when |
|----|--------|-----------|
| **P1-RED-DATA-01** | **AMS Postgres**: шифрование данных на диске (TDE/шифрование тома); **ключи шифрования не хранить на том же VPS**, что БД (KMS / **Vault** / провайдерский CMK). | Документированная схема + включено на проде + процедура rotate ключа без простоя пользователей VPN. |
| **P1-RED-SEC-01** | **Machine credentials**: короткоживущие секреты для скриптов/контейнеров (**SPIFFE + Vault** или аналог): TTL, аудит каждого чтения, нет «одного JWT на год» для всего автопарка. | Пилот на одном классе workload (напр. мониторинг → панель); runbook в **`docs/`**; референсы: HashiCorp SPIFFE auth, [`philips-labs/spiffe-vault`](https://github.com/philips-labs/spiffe-vault). |
| **P1-RED-SSH-01** | **Blast radius LV**: убрать сценарий «один root‑ключ ко всем хостам»; отдельные ключи per‑host/per‑роль; **jump‑host** с MFA где возможно; расширить практику **`command=`** restricted keys для узких задач. | Таблица ключей + wiki; **`ssh_audit`** / проверка что нет дубликата одного приватного ключа на все три машины. |
| **P1-RED-DNS-01** | **DNS / домены**: несколько регистраторов и DNS‑операторов для критичных имён (панель, подписка, bootstrap); **DNSSEC**; офлайн‑хранение **recovery‑кодов** регистратора (аппаратный секрет, не только облако VPS‑провайдера). | Запись в wiki + мониторинг делегирования (**P4-DNS-04** пересекается — не дублировать проверки). |
| **P1-RED-LOG-01** | **Логи edge подписки / Caddy**: **`log_skip`** для **`/api/sub/*`** на сайтах публичной подписки; **retention** + доступ к access-log. Репозиторий: **`Caddyfile-latvia-full.txt`**, **`docs/RUNBOOK-CADDY-SUBSCRIPTION-LOGS.md`**, **`ops/patch-caddy-logskip-inplace.sh`** / **`ops/fix-caddy-security.sh`**. | **DONE (репо):** эталон + runbook + скрипты. После каждого наката LV: smoke **grep**/`tail` **`sub-access.log`** — без свежего сырого **`/api/sub/`** после refresh подписки; новые публичные домены патчить так же. |
| **P2-RED-BOOT-01** | **Не только Telegram**: резервный канал статуса/операций (**HTTPS JSON mirror** на втором домене, опционально onion, почтовый алерт админам), чтобы блок TG API из РФ не обнулял инцидент‑коммуникации. | Два независимых канала проверены в **`RUNBOOK-INCIDENT`**; quarterly drill «TG недоступен». |
| **P2-RED-SUB-01** | **Подписка — несколько origin**: ≥2 независимых имени/CDN‑края на синхронизированную версию конфига; сценарий «один домен в реестре блокировок» не режет всю базу. | Wiki + мониторинг расхождения версий; связано с **P6-SCALE-04**, но это **обязательное** разнесение имён. |
| **P2-RED-MUX-01** | **Не один транспорт для всех**: продуктовая матрица **≥2 независимых транспортных профиля** (разные инбаунды/порты/узлы), чтобы DPI не кластеризовал всю аудиторию по одному JA3/Reality‑шаблону. | Документ **`docs/`** + доля пользователей на «альтернативном» профиле измерима (метрика панели или выборка). |
| **P2-RED-TLS-01** | **Клиентский стек**: процесс пересмотра раз в квартал возможностей **sing-box / uTLS / ECH / multiplexing** ([`SagerNet/sing-box`](https://github.com/SagerNet/sing-box)) и внедрение в шаблон подписки при выходе критичных фиксов fingerprinting. | Чеклист в wiki + запись в журнале §12 после каждого ревью. |
| **P6-RED-SUBHA-01** | **Горизонталь subscription-page**: несколько инстансов за LB + кэш на edge для «утреннего stampede» обновления подписок (дополняет **P6-SCALE-04**). | Нагрузочный тест N параллельных refresh без деградации p95. |
| **P6-RED-PG-01** | **Postgres**: read‑реплики (или managed Postgres при переносе), явный **pool limit** приложений, нагрузочный тест «массовое обновление клиентов за 1 ч». | Отчёт теста + пороги в **§10.1**. |
| **P6-RED-PAY-01** | **Очередь платежей бота**: webhook **idempotency**, DLQ, чтобы TG‑бот не был узким горлышком при всплеске продаж. | Очередь задеплоена + тест повторной доставки webhook. |
| **P3-RED-MIN-01** | **Минимизация данных пользователя**: где юридически возможно — развязать платёжный след и тех‑UUID; явная политика «что не собираем». | Страница политики + внутренний чеклист полей БД. |
| **P3-RED-JURIS-01** | **Гео‑ и провайнер‑диверсификация**: runbook «нас отключил один VPS/агентство платежей за день» — перенос DNS/IP без зависимости от одной юрисдикции. | Wiki + tabletop exercise раз в год. |
| **P5-RED-RD-01** | **R&D**: PoC канала bootstrap по модели **эфемерных посредников** (идеология [**Snowflake**](https://github.com/cohosh/snowflake)) — только для получения статуса/нового endpoint’а, не замена нодам. | Внутренний doc go/no-go + оценка стоимости поддержки. |

### 5.2 Смена `REMNA_API_TOKEN` без регресса (после остального бэклога)

**Порядок:** выполнять **после** приоритетных P2 / P6 / §5.1 — на проде уже есть guardrails (**`ops/sync-sub-token-ams.sh`**, **`ops/check-ams-subscription-token-layout.sh`**, **`ops/fix-ams-subscription-api-token.sh`**, **`docs/SECRETS.md`** §3). Задача ниже — **формализовать одноразовую процедуру** на случай **намеренной** смены токена (компрометация, смена `JWT_API_TOKENS_SECRET`, политика ротации), чтобы не повторять сбои **2026‑05‑16**.

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P1-OPS-REMNA-TOKEN-01**~~ ✅ | **Единый runbook + автоматизация смены `REMNA_API_TOKEN`** по всем потребителям (**`docs/SECRETS.md` §3**: shop; **`/opt/remnawave/sub/.env`**; в compose подписки только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**, без `eyJ…` в YAML; LV **`balancer.env`/`ru-monitor.env`**; **`.secrets/vault.env`** + **`python ops/render_compose.py`** где применимо; перезапуск контейнеров/сервисов). Инцидент **2026‑05‑16**: инлайн JWT в **`sub/docker-compose.yml`** → **502** клиентам; синхрон LV **`/opt/remnawave`** давал рассинхрон. **Документ:** **`docs/RUNBOOK-REMNA-API-TOKEN.md`**; **скрипт:** **`bash ops/remna_api_token_rollout.sh`** (**`dry-run`** / **`verify-ams`** / **`sync-ams-sub`**). **Запрет:** коммит и публичные каналы. | **DONE 2026‑05‑15 (репо):** формализация процедуры. **При первой реальной ротации только скриптом** — добавить строку §12 со smoke (**подписка 200**, бот/`panel_api`, **`drift-check`** или waive). |

---

## 6. P2 — Надёжность

| ID | Задача | Done when |
|----|--------|-----------|
| ~~**P2-MON-01**~~ ✅ | **`monitor.sh`** (LV): **`remnanode` + `docker exec … xray version` + порты**, не только `ss :443` (AMS xray после drain выключен). | **Репо 2026-05-15**: «контейнер up, Xray мёртв» → **`xray_lv_core`**; нет контейнера → **`xray_lv_remnanode`**. |
| ~~**P2-MON-02**~~ ✅ | Разные каталоги state: `ru-monitor` vs `monitor.sh`. | **2026-05-15**: комментарии в `monitor.sh` / `ru-monitor.py` + строка в примере crontab **`DEPLOY.md`** (§6 таблица уже была). |
| **P2-MON-03** | Политика: что уходит в Telegram (минимум метаданных). | Полстраницы wiki. |
| **P2-SSH-01** | Таблица: где `accept-new`, где pin `known_hosts`; меньше `StrictHostKeyChecking=no` в проде. | Таблица в wiki. |
| **P2-BAK-01** | Расписание: `ops/pg_dump_remnawave.sh` (AMS) + `ops/pull-latest-dump-ams-to-lv.sh`; квартальный **restore test**. | Календарь + один успешный тест восстановления. |
| ~~**P2-CHORE-SUB-ENV**~~ ✅ | **`monitor.sh`** — smoke подписки как **`daily-report.sh`**: **`SUB_PUBLIC_ORIGIN`**, **`SUB_MONITOR_PROBE_URL`**, **`PANEL_URL`** после **`source /etc/bvpn/balancer.env`** (fallback = дефолты как у daily-report/tmpl). | См. репозиторий **2026‑05‑15**; деплой на LV **`/opt/scripts/monitor.sh`**. |
| **P2-OPS-DRIFT-POST-P0** | После ротации секретов и смены URL панели: снять **DRIFT** прод ↔ репо (**`deploy-node.sh`**, **`selfsteal-monitor.py`**, AMS **`/opt/remnawave/docker-compose.yml`** и **`.env`**, **`/opt/remna-shop/.env`** и т.д.). | **`python ops/drift-check.py`**: OK по всем парам **или** явный waive в wiki с причиной по каждому файлу. |
| ~~**P2-ENG-DRIFT-CHECK-01**~~ ✅ | **`ops/drift-check.py`**: нестабильные **TIMEOUT** на LV. | Retry + растущий deadline на chunk (**4×** попытки для **`bvpn-lv`**, **2×** прочие) + backoff; см. **`docs/DEPLOY.md`** (§ drift-check примечание). Репо **2026‑05‑15**. |
| ~~**P2-MON-BALANCER-PANEL-URL**~~ ✅ | **`balancer.sh`** на LV после переноса панели на AMS всё ещё бил в **`http://localhost:3000`** → **`USERS=0 NODES=0`** в логе, алерты вместимости бессмысленны. | **DONE 2026‑05‑15**: **`PANEL_URL`** в **`/etc/bvpn/balancer.env`** + правка **`balancer.sh`** (репо **`compose/_shared/etc-bvpn-lv/balancer.env.tmpl`**); smoke **`HTTP 200`** на **`/api/users`** (журнал §12). |
| **P2-SEC-LOG-01** | Гигиена секретов: если **`BOT_TOKEN`** / JWT попали в **транскрипты Cursor**, скриншоты, общие логи — считать компрометацией до проверки. | Политика «rotate + redeploy всех потребителей» в wiki; точечный grep по типичным артефактам. |

---

## 7. P3 — Юзерфлоу и доверие

| ID | Задача | Done when |
|----|--------|-----------|
| **P3-UX-01** | Онбординг: подписка → клиент → первый коннект + FAQ при ошибке. | Одна страница без противоречий. |
| **P3-UX-02** | Тексты ошибок для людей (не «TLS timeout»). | Шаблоны поддержки = текст в продукте. |
| **P3-UX-03** | Шаблон сообщения пользователям при инциденте. | Файл/пост + dry‑run. |
| ~~**P3-OPS-SUPPORT-REMNA-LOGIN**~~ ✅ | Саппорт / операторы: панель Remnawave показывает **Forbidden + E000** не только из‑за прокси, но и при **неверном пароле** и др. политиках (**403**, не **401**). | Абзац **`docs/RUNBOOK-INCIDENT.md`** § «Логин в панель Remnawave» + отсылка к Rescue CLI. **2026‑05‑15** |
| **P3-TR-01** | Политика логов (что, сколько, кто читает). | Согласовано с публичной политикой. |

---

## 8. P4 — DNS / белые списки (отдельный SKU)

| ID | Задача | Done when |
|----|--------|-----------|
| **P4-DNS-01** | PoC: **dnstt** или **slipstream** + свой домен; замер через НСДИ и провайдера. | Внутренний doc с цифрами. |
| **P4-DNS-02** | Позиционирование: bootstrap **≠** полноценный VPN. | FAQ без обещания «как основной канал». |
| **P4-DNS-03** | Гайд пользователя (iOS/Android, DNS, ключ). | Прохождение без root. |
| **P4-DNS-04** | Мониторинг зоны/authoritative отдельно от RU SNI‑проб. | Отдельный алерт. |
| **P4-DNS-05** | План Б: второй домен/ключ; ToS хостинга; внутренняя юр. оценка. | Wiki + owner. |
| **P4-DNS-06** | (Опц.) Только статический bootstrap через DNS. | Спека «что разрешено». |

---

## 9. P5 — После «восьмёрки»

| ID | Задача | Done when |
|----|--------|-----------|
| **P5-COM-01** | Публичный статус инцидентов. | URL без доступа к админскому TG. |
| **P5-COM-02** | Правила возвратов при массовом дауне. | Текст в оферте. |
| **P5-ENG-01** | Общий HTTP‑клиент для Python ops (TLS, таймауты). | Новые скрипты без `CERT_NONE`. |
| **P5-ENG-02** | Общий `load_env` для мониторов. | Один модуль + тест кавычек. |

---

## 10. P6 — Ёмкость и пороги (рост базы)

### 10.1 Правило «AMS = панель, prod-нагрузка на LV+NL»

**Целевая архитектура**: AMS — **панель, подписка и edge**; прод-VPN там **не выполняется** (`remnanode` **stopped / drain**, **P1-ARCH-AMS-DECOM**). Полезная нагрузка — **LV + NL**.

Рост **пользователей в БД** и **пикового API / подписки** увеличивают риск **OOM и latency на AMS** без привязки к VPN-трафику ноды. Действия по порогам:

| Условие (любое из) | Действие |
|---------------------|----------|
| **Available RAM** на AMS **< 300 MiB** устойчиво 15+ мин | Вертикальный апгрейд RAM VPS или перенос тяжёлых сервисов (**P6**); `remnanode` на AMS уже не ключевой фактор. |
| **Контейнер `remnawave`** стабильно **> 700 MiB** RSS | Профилирование API; проверить утечки / кэш |
| **`users` в БД > 2 000** | Вертикальный апгрейд AMS-панели; рассмотреть split `panel ↔ db ↔ redis` по доке Remnawave |
| **`users` > 8 000** | Обязательный **нагрузочный тест** подписки + панели; **отдельный** хост для subscription edge |
| **Сессий на LV или NL > soft-cap** (`P6-SCALE-02`) | Добавление третьей prod-ноды; пересмотр распределения в `injectHosts` |
| **Ошибки / таймауты** на `p4n7q…/api/sub/*` при пике | **P6-SCALE-04**: CDN / rate limit / кэш (не откладывать) |
| **RU-monitor** > **4 мин** на цикл | **P6-SCALE-06**: батчи / меньше целей / параллель |

### 10.2 Задачи P6

| ID | Задача | Done when |
|----|--------|-----------|
| **P6-SCALE-01** | Метрики: сессии по нодам, RPS `/api/*`, Postgres latency/size, Redis, RPS подписки, RAM по контейнерам. | Дашборд или скрипт + алерты по таблице 10.1 |
| **P6-SCALE-02** | Soft cap пользователей на ноду + правило добавления ноды в матрицу. | Документ + настройка панели/Happ |
| **P6-SCALE-03** | Postgres: индексы, `pg_stat_statements`, окно бэкапа не в пик. | План обслуживания |
| **P6-SCALE-04** | Публичная подписка: edge/CDN, **rate limit** по IP, защита от абьюза. | Нагрузочный тест refresh |
| **P6-SCALE-05** | Рост API панели: вертикаль/горизонталь по доке; Redis eviction. | Прогон «refresh × N» |
| **P6-SCALE-06** | RU-monitor укладывается в cron **< 5 мин** при текущем числе хостов. | Лог с длительностью |
| **P6-SCALE-07** | Нагрузка на поддержку: шаблоны (P3) + при росте очереди — вторая линия / SLA ответа. | Метрика очереди |
| **P6-SCALE-NL-VERIFY** | Продукт / ёмкость: все активные пользователи на **LV** при живой **NL** — осознанная политика (**leastLoad**, squads, запасная нода) или ошибка конфигурации? | Запись в wiki + проверка **internal squads / inbound’ы** LV+NL в UI панели; критерий «когда NL должна брать долю». |

Задачи **P6‑RED‑SUBHA‑01**, **P6‑RED‑PG‑01**, **P6‑RED‑PAY‑01** дублируются в сводной таблице **§5.1** (единый порядок «критичные → мелкие» для ТПСУ).

### 10.3 Про «30k подписчиков»

- **30k платящих** при **пике 3–8k** сессий, **2 prod-ноды (LV + NL) + панель AMS**, **edge** у подписки и **апгрейде** панели — **реалистично** при закрытии P0–P2 и P6.
- **Базовая модель**: 2 prod-ноды + 1 панель. Третья prod-нода добавляется при превышении soft-cap (P6-SCALE-02).
- **30k одновременных** на **одной** ноде или **вся** нагрузка на **одном 2 GiB** без изменений — **нет**.
- **P4 (DNS)** не масштабируется как основной канал на десятки тысяч пользователей.

---

## 11. Связь с аудитом репозитория

Закрыты по коду/операциям: **P0-SEC-01…03** ✅, **P0-OPS** ✅, ~~**P0-SEC-04**~~ ✅, ~~**P0-SEC-05**~~ ✅ (**журнал §12**). Открытых задач уровня **P0** в таблице §4 на текущий срез **нет**. Блок **P1** ✅ по **`docs/P1-POST-AUDIT.md` (PASS 2026-05-15)** плюс **~~P1-OPS-REMNA-TOKEN-01~~**, **~~P1-RED-LOG-01~~** (в форме репо + патч-док). **Операционная память:** **`docs/KNOWLEDGE-BASE.md`**. Из **§5.1**: дальше **P1‑RED‑DATA/SEC/SSH/DNS**. Из **§6**: **P2-OPS-DRIFT-POST-P0**, **`P2-SEC-LOG-01`**, ~~**`P2-MON-01`/`P2-MON-02`**~~ ✅, бэкапы; ~~**`P2-ENG-DRIFT-CHECK-01`**~~ ✅, ~~**`P2-CHORE-SUB-ENV`**~~ ✅; затем **P6** (**P6‑RED‑***, **`P6-SCALE-NL-VERIFY`**).

**P4** — отдельный продуктовый слой, не смешивать с основным VPN SKU.

---

## 12. Журнал прогресса (заполнять вручную)

| Дата | Что сделано |
|------|-------------|
| 2026-05-16 | **~~P2-MON-01~~ / ~~P2-MON-02~~**: `monitor.sh` на LV — перед `ss :443/:8443` проверяются **`remnanode` running** и **`docker exec remnanode xray version`**; новые ключи **`xray_lv_remnanode`**, **`xray_lv_core`**. Комментарии «где state» в `monitor.sh`, `ru-monitor.py`, пример crontab в **`DEPLOY.md`**. Деплой: `pwsh -File ops/deploy-monitor-lv.ps1`. |
| 2026-05-16 | **Red team / ТПСУ → бэклог**: добавлен **§5.1** с ID **P1‑RED‑*** … **P5‑RED‑RD‑01** (шифрование БД, Vault/SPIFFE, SSH blast radius, DNS‑диверсификация, log_skip подписки, резерв без TG, multi‑origin подписки, multi‑transport, квартальный TLS‑ревью sing-box; **P6‑RED‑*** масштаб; **P3‑RED‑*** минимизация данных и юрис‑runbook; **P5‑RED‑RD‑01** Snowflake‑PoC). Спринт **§3 п.12**. |
| 2026-05-16 | **Разворот пробного тарифа (прод AMS):** `grandfather_panel_users_expire.py --apply` — **54/59** профилям Remnawave **`expireAt` → 2099** (до cut-off **16.05.2026 00:00 МСК**); **1** уже новее порога без изменения; **`/opt/remna-shop/.env`**: TRIAL/`REMNA_DEFAULT_DAYS`/ **`BOT_PAYMENTS_LIVE`**; **`bot_src`**: кнопка «Бесплатно 3 месяца», текст выдачи + HTML, scheduler без оплаты. Сценарий: **`ops/remote_ams_rollout_trials.sh`** + `scp` в **`/tmp/bvpn-rollout/`**. |
| 2026-05-15 | **`docs/KNOWLEDGE-BASE.md`** — точка входа (правила, типовые ошибки); **`README.md`** для GitHub. **~~`P1-OPS-REMNA-TOKEN-01`~~** оформлен как **`docs/RUNBOOK-REMNA-API-TOKEN.md`** + **`ops/remna_api_token_rollout.sh`**. **~~`P3-OPS-SUPPORT-REMNA-LOGIN`~~ ✅**: секция в **`RUNBOOK-INCIDENT`**. Зрелость: ~~**`P2-CHORE-SUB-ENV`**~~ (**`monitor.sh`** `SUB_*` + **`PANEL_URL`**), ~~**`P2-ENG-DRIFT-CHECK-01`**~~ (**`drift-check`** retries LV), ~~**`P1-RED-LOG-01`**~~ (**`RUNBOOK-CADDY-SUBSCRIPTION-LOGS`**, эталон **`Caddyfile-latvia-full.txt`** с **`log_skip /api/sub/*`**). |
| 2026-05-14 | **P0-pre**: pg_dump remnawave (`/var/backups/remnawave/`) + git snapshot (`.snapshots/pre-P0-…`), SHA256 зафиксированы |
| 2026-05-14 | **P0-SEC-03 DONE**: `0.0.0.0:3010` закрыт через iptables `DOCKER-USER` (только LV `176.126.162.158`); systemd-юнит `ams-docker-firewall.service`; `ENABLE_DEBUG_LOGS=false`; LV→AMS `200 OK`, прямой доступ снаружи отвергнут |
| 2026-05-14 | **P0-SEC-01 DONE**: убран `ssl.CERT_NONE` из 15 `ops/*.py`, добавлен общий `ops/panel_client.py` (strict TLS + retry); `monitor.sh` / `daily-report.sh` — `-sk → -s` для LE-эндпоинтов (selfsteal `127.0.0.1` остался `-sk` намеренно); `.secrets/*.sh` — то же; `check.py` оставлен `CERT_NONE` с явным комментарием (это relay-проба чужих SNI). Smoke: `panel_api.py nodes/inject-count` отвечают, `curl -fsS` к панели/подписке без `-k` → 200 |
| 2026-05-14 | **Новая находка → P1-OPS-DRIFT-01**: репо `monitor.sh` / `daily-report.sh` дрейфуют с продом (`/opt/scripts/`): на проде hardcode `ADMIN_CHAT_ID` / `TEST_SUB_KEY` / `id.x5.ru`, в репо — env-based + `ads.x5.ru` + UFW hints. P0-SEC-01 применён точечно к прод-baseline; нужен отдельный спринт «raise prod to repo». |
| 2026-05-14 | **P0-SEC-02 DONE**: `sync-sub-token-ams.sh` устарел/удалён после миграции панели на AMS (на серверах нет). Расширил задачу: убил shell-injection вектор в `selfsteal-monitor.py:ssh_batch_check` — был `f"for sni in {sni_str}; do"` (если SNI прилетит из API с метасимволами — RCE на AMS). Сделал defense-in-depth: (1) strict DNS-label whitelist на python-стороне, (2) here-doc payload вместо интерполяции, (3) `case` re-check внутри bash. Smoke: `total=24 ok=24 critical=0 warning=0`, ноды отвечают как ожидается. Hash прод совпадает с репо после деплоя. |
| 2026-05-14 | **P0-OPS-01 DONE**: `deploy-node.sh` — порядок резолва токена `env → /etc/bvpn/balancer.env → .secrets/panel-token.txt → interactive read -rs → legacy argv с loud WARN`; 5-й позиционный аргумент остаётся как deprecated с громким предупреждением. Дополнительно убран остаточный leak: все `curl -H "Authorization: Bearer …"` переписаны на `_curl_auth_config | curl --config -` (header читается из stdin, secret не виден в `ps -ef` / `/proc/$pid/cmdline`). Smoke на LV: `--config -` даёт байт-в-байт тот же ответ, что `-H Authorization`; `ps auxww` не содержит Bearer. Задеплоено на LV (`c130744…`) и AMS (`c130744…`) — hash идентичен репо. |
| 2026-05-14 | **P0-OPS-02 DONE**: 4 критичных образа закреплены через `image: tag@sha256:DIGEST` (supply-chain immutability). Бэкапы compose-файлов рядом с оригиналом (`.bak-YYYYMMDD-HHMMSS`). Pinning: LV `remnanode → ghcr.io/remnawave/node@sha256:9d5737…`, AMS `remnanode → remnawave/node@sha256:9d5737…`, AMS `remnawave-subscription-page → remnawave/subscription-page@sha256:37dd48…`, AMS `remnawave → remnawave/backend@sha256:a0e9a3…`. Контейнеры пересозданы; smoke: panel `nodes` → все 3 (LV/AMS/NL) `connected=True`, sub endpoint `HTTP 200`. **Перенесено в P1**: `adguard:latest`, `caddy:2.9`, `postgres:17.6`, `valkey/valkey:8.1-alpine` — также pinning через digest. |
| 2026-05-14 | **P0-audit DONE**: единый скрипт `ops/p0-audit.sh` (запускается на LV и AMS, выводит `OK / WARN / FAIL`). Финальный прогон по обоим хостам: контейнеры up, критичные образы pinned, sub endpoint 200, TLS panel/sub валидируется системным CA, `iptables DOCKER-USER` корректно фильтрует 3010 (LV ACCEPT + DROP остальных), нет Bearer-токенов в `ps auxww`, бэкапы скриптов и compose-файлов на местах, cron на LV (monitor/daily/ru-monitor/selfsteal) живой. **Все P0 закрыты — переход к P1.** |
| 2026-05-14 | **Архитектурное уточнение → P1-ARCH-AMS-DECOM**: AMS — **только панель/подписка**, нода `remnanode` на AMS оставлена временно для users, чей клиент ещё не пересохранил подписку. Сейчас к AMS-ноде привязано **5 «прямых» injectHosts** — естественного оттока нет, новые подписки садятся на AMS. Зафиксирован план декомиссии (freeze growth → метрика → коммуникация → drain → cleanup → удалить пины и AMS-xray алерты из `monitor.sh`). §1 «Срез продакшена» и §10 «P6 Capacity» пересчитаны на **2 prod-ноды (LV+NL) + 1 панель**. |
| 2026-05-14 | **Переоценка после P0**: ~7.2 → ~**7.8/10**. Существенный прогресс по безопасности и operational hygiene; до устойчивых 8.5+ нужны P1 (DRIFT, ARCH-AMS-DECOM, PRO, ENG-01..03) и P2 (мониторинг «Xray реально жив», off-host бэкапы, SSH-дисциплина). 30k-цель остаётся реалистичной при закрытии P0–P2 и P6. |
| 2026-05-14 | **P1-ARCH-AMS-DECOM шаги 1-2 — оказались уже фактически выполнены**. Pre-flight (pg_dump AMS `7bdf1350…` + panel snapshot) сделан, написан безопасный `ops/freeze_ams_node.py` (dry-run по умолчанию, на `panel_client.PanelClient`). Dry-run показал: на Amsterdam-01 8 хостов (5 «прямых AMS» + 3 «Relay AMS»), **все имеют `isHidden=True`**, и **ни одного нет в `injectHosts.values`** (16 UUIDs там — это LV+NL). `probe_users_subs.py` по 10 рандомным активным юзерам: **AMS=0 outbound** у каждого. На AMS xray прямо сейчас: `ss` 0 ESTABLISHED на :443 и :8443, `docker stats remnanode` 0 B NET I/O за 3+ часа, 0 уникальных source IP в xray-логах. → Шаг 1 (freeze growth) и шаг 2 (метрика «AMS=0») закрыты эмпирически. **Готовы к шагу 4 (drain & cleanup)** без шага 3 (коммуникация) — поскольку коммуницировать некому. |
| 2026-05-14 | **P1-ARCH-AMS-DECOM шаг 4a (drain) — DONE, soft-stop без удаления.** На LV `monitor.sh` пропатчен: CHECK 3-4 (XRay Amsterdam :443/:8443) закомментированы с пометкой «DISABLED — P1-ARCH-AMS-DECOM drain phase», бэкап `/opt/scripts/monitor.sh.before-ams-drain-20260514-204413`, `bash -n` OK. На AMS выполнен `docker compose stop remnanode` (Exited(0)), порты `:443/:8443/:2222` на 127.0.0.1 — closed. Все остальные сервисы AMS живы (panel healthy, sub-page, db healthy, redis healthy, бот, AdGuard, caddy-selfsteal). Панель: `Amsterdam-01 connected=False` (ожидаемо), LV+NL `connected=True`. Re-probe 10 user'ов: LV=8/NL=8/AMS=0 — подписки не сломались. `monitor.sh` отработал на LV: тишина (нет alert/нет recovery). **Rollback в 1 команду**: `ssh -p 3344 root@168.100.11.140 'cd /opt/remnanode && docker compose start remnanode'`. Compose-файл, ноду в БД панели и SSH-ключ — не трогали. Через 24-48h тишины в саппорте → шаг 4b (`docker compose down` + rm из compose), затем 4c (`DELETE /api/nodes/{uuid}` + чистка mon-secrets). |
| 2026-05-14 | **P1-ARCH-AMS-DECOM hotfix: ru-monitor.py поднял шум, потому что `monitor.sh` я заглушил, а второй мониторящий сервис — нет.** 23:46 MSK прилетели 8 алертов «SNI failure» (5 на AMS-направлениях, 3 на Relay-через-AMS). Причина: `ru-monitor.py` (LV, cron `*/5`) берёт таргеты из `/api/hosts` и фильтрует только `isDisabled` — но мы выключили AMS только через `isHidden`. Решение архитектурно чище: расширил `ops/freeze_ams_node.py` флагом `--disable` (PATCH с `isDisabled=true` + GET-back verify), применил к 8 целевым хостам. Антиспам `ru-monitor.py` подавил повторы внутри суток (1 alert на target — больше не повторится). Следующий cron-tick (`[2026-05-14T20:56:19Z] total=16 ok=16 fail=0 transitions=0`) подтвердил: 8 хостов выпали из проверки, остальные 16 зелёные. Бонус: тех-долг — WARNING `expected 16 targets, got 24` исчез сам (был зарождающийся, теперь снова 16). Дополнительный probe 10 user'ов: LV/NL/AMS = 8/8/0 — двойная защита (`isHidden + isDisabled`) ничего не сломала. |
| 2026-05-14 | **Усвоенный урок** добавлен в P1-OPS-DRIFT-01: «при изменениях платформы (drain/decom/freeze) обязателен чек-лист всех мониторов в edits» — у нас 2 параллельных monitor: `/opt/scripts/monitor.sh` (LV bash) и `/opt/scripts/ru-monitor.py` (LV python, через RU-relay). Оба должны быть синхронизированы при любых архитектурных правках. |
| 2026-05-14 | **Monitor-block (A+B+C+D) — DONE.** Закрыта тема «непонятно, тихо потому что ок vs монитор сдох». Изменения: **D**) `monitor.sh.STATE_DIR /tmp/bvpn_states → /var/lib/bvpn-monitor` + миграция маркеров; то же для `ru-monitor.py.ANTISPAM_DIR` (фиксит баг «recover не приходит после reboot» — `/tmp` чистится). Заодно ослабил `expected = 16` → `len(targets) < 4`. **B**) `daily-report.sh` теперь рисует AMS как `🟡 (decom)` вместо 🔴; в `ALERT_COUNT` читает оба пути (legacy/new) для миграционного периода. **C**) Watchdog на NL: `*/15 * * * *`, SSH NL→LV через выделенный ключ `/root/.ssh/lv_watchdog`, restricted `command="/usr/local/sbin/bvpn-watchdog-probe"` + `from="91.90.192.17"` + no-pty/no-forward, локальный antispam `/var/lib/bvpn-watchdog`. Алертит **только при stale >30 мин** (monitor.sh / ru-monitor.py) или потере SSH к LV; шлёт recovery когда оживает. **Молчит когда всё ок** — никаких пустых отбивок. **A**) `/status` admin-only команда в `remna-shop-bot`: показывает nodes (с decom-меткой), hosts (active/hidden/disabled), subscription HTTP code. Async через aiohttp+TLS, использует существующий `REMNA_API_TOKEN` из `/app/.env`. Деплой: host-edit + `docker cp` + restart; backup `admin_handlers.py.before-status-20260514-212813`. Полный rollback в одну команду. |
| 2026-05-14 | **Post-block findings**: (1) первый `/status` в боте показал `active=-7` из-за моей наивной формулы `total - hidden - disabled` (на 8 AMS-хостах оба флага одновременно). Поправлено: `visible = !hidden && !disabled`, остальные счётчики показываются как есть. Деплой через `docker cp` + restart, backup `admin_handlers.py.before-status-v2-…`. (2) `selfsteal-monitor.py` тоже зашумел из-за drain'а AMS — Caddy на AMS:9443 возвращает 500 на bing/etc, потому что reverse_proxy ходит через мёртвый remnanode. Решено симметрично остальным: закомментирована строка `("amsterdam", AMSTERDAM_HOST)` в `NODES`, ANTISPAM_DIR переехал в `/var/lib/bvpn-monitor`, маркеры мигрированы; backup `selfsteal-monitor.py.before-decom-20260514-213408`. (3) Поймал ортогональный сигнал: `latvia:ads.x5.ru` теперь отвечает 302 вместо ожидаемых 503/502/504 — это **не наш регресс**, а реальное изменение upstream'а x5.ru. Заведён `P1-OPS-SELFSTEAL-01` на пересмотр `EXPECTATIONS`. |
| 2026-05-14 | **Новая продуктовая задача от пользователя**: `P1-PRO-RU-BYPASS-01` — split-tunneling для российских приложений (Я.Маркет, Авито, WB, Ozon, Госуслуги, Сбер, T-Bank, MAX, ВК/ОК, Яндекс.*, банки, мобильные ЛК, доставка/еда) — трафик в RU-ресурсы идёт **напрямую**, в обход VPN, даже при включённом VPN. Реализация: `routing.rules[].outboundTag="direct"` в `templateJson.remnawave.routing` через PATCH `/api/subscription-templates` (атомарно, со снапшотом — как `freeze_ams_node.py`). Готовая инфра: `panel_client.PanelClient` уже умеет, нужен только список доменов + matcher (`domain:` + `geosite:category-ru` + `geoip:ru`). |
| 2026-05-15 | **P1-PRO-RU-BYPASS-01 DONE.** Split-tunneling для RU-приложений. Inspection текущего `templateJson.routing.rules` показал что **частично уже есть**: `geosite:category-ru` + regexp на `.ru/.рф/.рус/.орг.рус` + `geoip:ru` уже направляют RU-трафик в `direct`. Найдены 2 проблемы: (1) **`max.ru` и `oneme.ru` сидят в block-rule** — MAX-мессенджер VK блокируется xray-клиентом даже без VPN, противоречит запросу пользователя; (2) **`.com / .net / .online / .eu` российские домены НЕ покрыты** regexp'ом (VK на vk.com, Яндекс на yandex.com, Сбер на sber.com, Tinkoff/T-Bank на .com, маркетплейсы на .com/.eu — все шли через VPN). Решение: написан атомарный `ops/ru_bypass_routing.py` (dry-run по умолчанию, snapshot + verify, как `freeze_ams_node.py`) и `ops/probe_routing.py` для проверки рендера. Изменения: (a) из block-rule убраны `max.ru`/`oneme.ru` (rule стал `domain=[]`, legacy-entry); (b) в direct-rule добавлены 35 доменов: MAX (`max.ru`, `oneme.ru`, `mybridge.ru`), VK (`vk.com`/`vk.me`/`vk.link`/`vkuservideo.com`/`vkuservideo.net`/`vkuser.net`/`userapi.com`/`vkontakte.com`), Яндекс (`yandex.com`/`yandex.net`/`yandexcloud.net`/`yastatic.net`/`ya.com`), мобильные (`mts.com`/`megafon.com`/`beeline.com`/`tele2.com`), банки (`sber.com`/`sberbank.com`/`sberbank.online`/`sbermegamarket.com`/`tinkoff.com`/`tbank.com`/`vtb.com`/`alfabank.com`/`raiffeisen.com`), маркетплейсы (`avito.com`/`ozon.com`/`wildberries.eu`/`aliexpressru.com`), госуслуги (`gosuslugi.com`/`pochta.com`). Backup: `.secrets/snapshots/template-before-ru-bypass-20260515_112742.json`. PATCH + verify прошли. Probe 3 случайных активных user'ов через UA Happ/1.9.4 показал: `R0 block.domain=[]`, `R3 direct.domain=41 entries (6 starting + 35 new)`, `outbounds=18 (proxy*=16)` — рендеринг ОК. **Изменение касается всех 25 активных юзеров** при следующем refresh подписки (1-24 ч; Hiddify/Happ обычно обновляют каждый запуск, v2rayN/NekoBox — по требованию). Rollback в 1 PATCH через snapshot. Что **не покрыто** этим изменением — `geosite:category-ru` (общий список v2fly, обновляется upstream'ом) и `geoip:ru` (если RU-сервис на иностранном CDN). |
| 2026-05-15 | **P1-OPS-SELFSTEAL-01 DONE** (15 мин). Probe `ads.x5.ru` ×10 c LV: устойчиво **HTTP 302 → `Location: https://x5media.ru/`** (60-170ms), upstream X5 вынес ad-platform на отдельный домен. `id.x5.ru` (200) и `5post-gate.x5.ru` (404) — стабильны. Патч: `EXPECTATIONS["ads.x5.ru"] = {"expected": 302, "tolerate": [302, 301, 503, 502, 504]}` (старые 5xx оставлены в tolerate — если X5 вернёт сервис, не алертим). Деплой LV: backup `selfsteal-monitor.py.before-x5fix-20260515-081711`, install, syntax OK, md5 `72ed0c7f`. Cron-tick подтвердил: `state.json` показал `latvia:ads.x5.ru { status: ok, code: 302 }`, в логе `ALERT RECOVERED: latvia:ads.x5.ru` (после 130 retry'ев в `critical`). Sync репо ← прод выполнен (`selfsteal-monitor.py` уже был обновлён локально перед scp), `drift-check.py`: 11/11 OK. |
| 2026-05-15 | **P1-OPS-DRIFT-02 DONE**: `compose/**/*.tmpl`, `docs/SECRETS.md`, `sanitize-compose` / `extract-vault`, рендер **`ops/render_compose.py`** с `--only`/`--none`, оболочка **`ops/render-compose.sh`**, расширение **`ops/drift-check.py`** (`tmpl_only_keys`, CRLF-norm), **`docs/DEPLOY.md` §7** переписан. В бэклог занесены **P0-SEC-04/05**, **P1-ARCH-NODE-UNIFY**. **P1-ENG**: `ops/site.env.example`, ENG-02 отмечено закрытым Monitor-block D; ENG-03 — `ops/redact_bvpn_artifacts.py` + очистка типовых JWT в `bvpn-artifacts`. SSH **drift-check** с этой машины не прогонялся до конца (таймаут) — повторить с рабочего хоста с `bvpn-*` в `ssh_config`. |
| 2026-05-15 | **P1-ENG-01 (конфиг URL)**: добавлен **`ops/site_urls.py`** (опциональный **`ops/site.env`** по **`site.env.example`**), ключевые maintenance-скрипты переведены на него + **`deploy-node.sh`** может source'ить **`ops/site.env`** из репо; **`panel_client`/`panel_api`/`freeze_ams_node`/`ru_bypass_routing`**; **`ops/bot-admin-handlers`** — сборка `SUB_PROBE_URL` из **`SUB_PUBLIC_ORIGIN`** / **`SUB_MONITOR_PROBE_SUFFIX`**. Новые доки: **`docs/P1-POST-AUDIT.md`** (плотный аудит после полного закрытия P1), **`docs/RU-BYPASS.md`**. **`docs/DEPLOY.md`** §2 п.7 — указание на `site.env`. |
| 2026-05-15 | **P1-PRO-01…04 (продуктовая линия)**: **`docs/FAQ.md`** — позиционирование основного VPN vs DNS/bootstrap; **`docs/RUNBOOK-INCIDENT.md`** — внутренний инцидент-runbook + SLA ответа; **`docs/HAPP-MATRIX.md`** — матрица шаблона/URL/rollback; **`docs/POLICY-SNI-MONITORING.md`** — политика SNI-проб. Спринт-строка 10: блок PRO закрыт; остаются **P3-UX-01/02**. |
| 2026-05-15 | **P1 полностью закрыт + `docs/P1-POST-AUDIT.md` PASS (go P2 с оговорками).** Сделано в репозитории: **P1-ARCH-NODE-UNIFY** — `compose/{nl,ams}/remnanode/{docker-compose.yml,node.env}.tmpl`, digest pin **`ghcr.io/remnawave/node@sha256:9d5737…`**, **`ops/drift-check.py`** дополнен парами **`.env`**; **P1-ENG-03** — **`archive/tmp-remna-shop-bot-patches/`** (40× `tmp_*.py` из корня); **P1 AMS-decom метрика** — **`ops/count_users_with_ams_sub.py`** + интеграция в **`daily-report.sh`**, smoke sub через **`SUB_MONITOR_PROBE_URL`**; **selfsteal** — шапка-док к **`EXPECTATIONS`**; **P2-CHORE-SUB-ENV** добавлен (хардкод smoke в **`monitor.sh`**). **Критичное, не P1:** **`P0-SEC-04`/`P0-SEC-05`** остаются открытыми. **Деплой обязателен:** `daily-report.sh`, `count_users_with_ams_sub.py`, при необходимости split **`/opt/remnanode/.env`** на NL/(AMS) под новые шаблоны — иначе **`drift-check`** покажет расхождение до наката. |
| 2026-05-15 | **`python ops/drift-check.py`** повторён (`PYTHONUNBUFFERED=1`): **28** пар, **OK=13**, **problems=15**, exit **1**. Много **TIMEOUT** на батчах LV/AMS (латентность SSH/нагрузка), плюс **DRIFT**: `selfsteal-monitor.py`, `deploy-node.sh` (LV), `balancer.env`, AMS **`/opt/remnawave/docker-compose.yml`** и **`.env`**. **Репо под P0-SEC-04:** **`ops/fix-caddy-security.sh`** — chmod только для существующих путей (`remnanode`, опц. legacy/архив). **На LV:** завершить архив **`/opt/remnawave/`** → **`/opt/_archive/…`** (если **`chmod -R`** на огромном дереве «висит» — уменьшить бэкапы внутри или дождаться окончания), затем **`chattr +i`**. |
| 2026-05-15 | **P0-SEC-04 / P0-SEC-05 — процедура в репозитории:** **`docs/RUNBOOK-P0-SEC04-SEC05.md`**, скрипты **`ops/archive_lv_remnawave_legacy.sh`**, **`ops/rotate_ams_panel_core_secrets.py`**. Исполнение на LV/AMS — вручную; после успеха добавить строку **«P0-SEC-04/05 DONE»** с датой ниже. |
| 2026-05-15 | **P0-SEC-04 / P0-SEC-05 DONE (прод).** **LV:** **`/opt/remnawave/`** заархивирован в **`/opt/_archive/remnawave-legacy-*`**, **`chattr +i`** (наследие закрыто). **AMS:** фаза A — ротация JWT + Postgres **`rotate_ams_panel_core_secrets.py --apply`**, контейнер **`remnawave`** пересоздан (**`--force-recreate`**); фаза B — новый **`REMNA_API_TOKEN`** из UI → **`/opt/remna-shop/.env`**, **`/opt/remnawave/sub/.env`**, LV **`/etc/bvpn/balancer.env`** (**`PANEL_TOKEN`/`REMNA_API_TOKEN`**) и **`/etc/bvpn/ru-monitor.env`**; **`docker compose up -d`** / **`--force-recreate`** для shop и subscription-page. Супер‑админ восстановлен через **Rescue CLI** после потери входа. Добавлены вспомогательные патчи URL панели: **`FRONT_END_DOMAIN`** / **`PANEL_DOMAIN`**, Caddy **`header_up`** (журнал ops/thread). |
| 2026-05-15 | **Инцидент эксплуатации → задачи P2/P3.** **`ru-monitor.py`**: серия **`HTTP 401`** до обновления **`REMNA_API_TOKEN`** на LV; после фазы B тик **`total=16 ok=16`**. **`balancer.sh`**: до правки бил в **`localhost:3000`** → **`USERS=0 NODES=0`**; исправлено **`PANEL_URL=https://k9x2m1.conntest.xyz:2053`** + синхронизация **`balancer.sh`** с репо; проверка **`/api/users` → HTTP 200**. **`python ops/drift-check.py`**: exit **1**, **DRIFT** по нескольким файлам + **TIMEOUT** на чтении **`/etc/bvpn/*.env`** → занесено как **`P2-OPS-DRIFT-POST-P0`**, **`P2-ENG-DRIFT-CHECK-01`**. UX: **Forbidden/E000** при логине часто означает неверный пароль (**403**) → **`P3-OPS-SUPPORT-REMNA-LOGIN`**. Продукт: все ~58 пользователей на LV при живой NL — на усмотрение политики → **`P6-SCALE-NL-VERIFY`**. |