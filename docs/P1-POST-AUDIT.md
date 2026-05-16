# Плотный аудит после закрытия P1 (gate перед P2/P6)

Запускать **только когда все пункты блока P1 в `docs/COMMERCIAL-BACKLOG.md` выполнены**
(или явно задокументировано как «отложено с риском»). Цель — зафиксировать
состояние «конфигурация + продуктовая оболочка P1» перед углублением в P2
(надёжность) и P6 (ёмкость).

---

## 1. Конфигурация и Source of Truth

- [x] **`python ops/drift-check.py`** — норматив: **0 DRIFT / MISSING** по всем парам при заполненном `.secrets/vault.env` для `tmpl` **после синхронизации прода** с обновлёнными шаблонами (NL/AMS `remnanode` теперь `env_file` + отдельный `node.env`; до наката на хосты возможен ожидаемый DRIFT).
- [x] **`docs/DEPLOY.md` §1 и §7** отражают пути, `daily-report`, `count_users_with_ams_sub.py`, vault/render.
- [x] Публичные URL/UUID: **`ops/site_urls.py`** + **`ops/site.env.example`**; исключения (bash `monitor.sh`) зафиксированы как техдолг → **P2-CHORE-SUB-ENV** в бэклоге.
- [x] **`daily-report.sh`**: smoke URL подписки через **`SUB_PUBLIC_ORIGIN`** / **`SUB_MONITOR_PROBE_URL`** (fallback как в `site.env.example`).

## 2. Подписка и шаблон Happ / Xray

- [x] **`ops/probe_routing.py`**: критерий `degenerate routing rules = 0` (последняя проверка на проде 2026-05-15, RU-bypass + strip-degenerate).
- [x] **`docs/RU-BYPASS.md`**: процедура + **`ops/ru_bypass_routing.py`** + снапшоты `.secrets/snapshots/`.
- [x] Smoke **GET** подписки: логика совпадает с `SUB_MONITOR_PROBE_URL` в `daily-report.sh` (проверка на проде при деплое).

## 3. Безопасность (наследие и открытые P0)

- [ ] **`P0-SEC-04`** / **`P0-SEC-05`**: закрываются **операционно** по **`docs/RUNBOOK-P0-SEC04-SEC05.md`** (`ops/archive_lv_remnawave_legacy.sh`, `ops/rotate_ams_panel_core_secrets.py`). После выполнения на проде — отметить **`docs/COMMERCIAL-BACKLOG.md` §12** (строка **P0-SEC-04/05 DONE**).
- [x] «Живые» JWT в дереве: **`ops/redact_bvpn_artifacts.py`**; выборочный поиск `eyJ` — в прикладном коде/compose плейсхолдеров нет; встречается в архивных markdown/снапшотах как **описание формата**, не как значение секрета.

## 4. Архитектура нод и compose

- [x] **`P1-ARCH-NODE-UNIFY`**: NL и AMS `remnanode` в репо — **`ghcr.io/remnawave/node@sha256:9d57375a8168d00252f4debe7a6ac29debd8449af60467ab26b4ee212b047525`**, стиль **`env_file` + `node.env.tmpl`**, см. `compose/*/remnanode/`.
- [x] **AMS decom**: метрика **`ops/count_users_with_ams_sub.py`** + строка в **`daily-report.sh`** (ACTIVE с AMS outbound по факту Happ-sub). Rollback xray — см. журнал бэклога 2026-05-14 (`docker compose start remnanode` на AMS).

## 5. Продукт P1 (PRO-01…04)

- [x] **P1-PRO-01** — **`docs/FAQ.md`**
- [x] **P1-PRO-02** — **`docs/RUNBOOK-INCIDENT.md`**
- [x] **P1-PRO-03** — **`docs/HAPP-MATRIX.md`** + `site_urls`
- [x] **P1-PRO-04** — **`docs/POLICY-SNI-MONITORING.md`**

## 6. Инвентаризация и версии

- [x] Критичный digest **`remnanode`**: см. строка `image:` в **`compose/lv|nl|ams/remnanode/docker-compose.yml.tmpl`** (**`sha256:9d5737…`**).
- [x] **`docs/COMMERCIAL-BACKLOG.md` §1**: текст среза обновлён **2026-05-15** (состояние после AMS drain; точные счётчики БД переснять при SSH-ревизии).

## 7. Выходной артефакт

- [x] Краткий отчёт перенесён в **§8** ниже + строка журнала **`docs/COMMERCIAL-BACKLOG.md` §12**.

---

## 8. Отчёт аудита **2026-05-15** — **PASS (P1 / go на P2 с оговорками)**

Закрытие **блока P1** подтверждено документально и кодом репозитория: продуктовый пакет (FAQ, runbook, Happ-matrix, SNI-policy), ENG (site_urls, архив **`tmp_*.py`** → **`archive/tmp-remna-shop-bot-patches/`**, RU-bypass tooling), ARCH (унификация compose нод NL/AMS, метрика «users-touching-AMS-sub» для decom).

**Оговорки (не блокируют go на P2, но критичны по приоритету):**

1. **`P0-SEC-04` / `P0-SEC-05`**: процедура и скрипты в **`docs/RUNBOOK-P0-SEC04-SEC05.md`** — выполнить на проде; затем считать критичный секретный трек закрытым и обновить журнал бэклога §12.
2. **Деплой на прод после merge**: **`daily-report.sh`**, **`count_users_with_ams_sub.py`**, возможное разнесение секрета AMS/NL **`remnanode`** на **`docker-compose.yml` + `.env`** — иначе **`drift-check`** будет показывать расхождение до наката.
3. **`monitor.sh`**: smoke URL подписки всё ещё захардкожен → задача **`P2-CHORE-SUB-ENV`** в бэклоге.

**Вердикт:** **go на P2** (надёжность, мониторинг Xray-vs-grep, бэкапы) после выполнения **`docs/RUNBOOK-P0-SEC04-SEC05.md`** на проде (или параллельно держать контроль до окна работ).

---

*Документ: gate после закрытия спринтов P1.*
