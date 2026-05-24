# Матрица Happ / подписка (единый источник правды операций)

**P1-PRO-03**. Описывает «где живёт конфиг клиента», как его менять и как откатиться.

## Публичные URL и UUID (не секреты)

| Что | Где задано | Примечание |
|-----|-------------|------------|
| База панели API | **`ops/site_urls.py`** (`PANEL_URL`), опционально **`ops/site.env`** | Тот же источник у **`PanelClient`** / большинства `ops/*.py`. |
| База HTTP подписки | **`SUB_PUBLIC_ORIGIN`** | Без финального slash в коде добавляются пути вида `/api/sub/…`. |
| UUID шаблона подписки | **`REMNA_TEMPLATE_UUID`** | По умолчанию совпадает с переменными в **`site_urls`**. |

Образец для локальной машины админа: **`ops/site.env.example`**.

## Операции, затрагивающие шаблон

| Задача | Скрипт | Снимок перед изменением |
|--------|--------|-------------------------|
| RU‑bypass / прямые домены | **`ops/ru_bypass_routing.py`** | `.secrets/snapshots/template-before-ru-bypass-*.json` |
| Заморозка / trimming inject на AMS‑ноду | **`ops/freeze_ams_node.py`** | `.secrets/snapshots/template-before-freeze-*.json` |
| Hotfix вырожденных `routing.rules` | **`ops/ru_bypass_routing.py --strip-degenerate-only --apply`** | `template-before-strip-degenerate-*.json` |
| burstObservatory interval/destination | **`ops/patch_burst_observatory.py --apply`** | `template-before-observatory-*.json` |

**Happ / XHTTP:** verify **`ops/diagnose_happ_import.py`** → `batch_risk=LOW`.

**Обязательный verify loop после любого PATCH шаблона или sub-page** (Q-VPN-STAB-018):

```bash
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
python ops/transport_mux_audit.py
bash ops/smoke_sub_page_ha.sh
```

Процесс добавления домена в bypass: **`docs/RU-BYPASS.md`**.

## Rollback после PATCH шаблона

1. Взять последний актуальный JSON из **`.secrets/snapshots/`** с префиксом, соответствующим операции.
2. Из снимка извлечь объект **template** в формате, который ожидает API (как в скриптах: поле **`templateJson`** и метаданные шаблона).
3. Выполнить PATCH **`/api/subscription-templates`** с полным телом (как делает **`panel_client.patch`** в скриптах) **или** восстановить через UI панели, если доступен импорт/редактор.
4. Проверка: **`python ops/probe_routing.py`**, **`python ops/probe_users_subs.py`** (по необходимости).

## Ноды и outbounds

Количество и набор outbounds в выдаче зависят от **injectHosts** и состава нод в панели.
Регрессии ловятся **`ops/probe_users_subs.py`** (выборка пользователей).

## Транспортные профили (P2-RED-MUX-01)

Матрица **primary / alt** (порты 443 vs 9443/8443, LV+NL): **`docs/TRANSPORT-MUX-MATRIX.md`**.  
Аудит доли alt в подписке: **`python ops/transport_mux_audit.py`**.

Нет «магии в чате» — только снапшот + скрипт + проверка.

## TLS / sing-box (P2-RED-TLS-01)

Квартальный обзор **Xray / sing-box / uTLS / ECH**: **`docs/TLS-CLIENT-STACK-REVIEW.md`**, **`ops/tls_client_stack_audit.py`**.
