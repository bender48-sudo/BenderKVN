# Карта бэклога BenderVPN

**Назначение:** одна страница «куда смотреть». **Исполнять** только по **`BACKLOG-QUEUE.md`** (строка **`NEXT`**).

---

## Иерархия документов

| Уровень | Файл | Роль |
|---------|------|------|
| **1. Исполнение** | **`docs/BACKLOG-QUEUE.md`** | Линейная очередь **Q001…**; единственный **`NEXT`** |
| **2. Задачи и журнал** | **`docs/COMMERCIAL-BACKLOG.md`** | ID, Done when, §7.1 P3-FLOW, **§12** прогресс на проде |
| **3. Флоу (продукт)** | **`docs/USER-FLOW-BACKLOG.md`** | Принципы, MVP/Comfort, бабушка-тест |
| **4. Агент — прод (сейчас)** | **`docs/AGENT-PROD-DEPLOY-BACKLOG.md`** | Q079–Q084 |
| **4b. Владелец** | **`docs/MANUAL-OWNER-CHECKLIST.md`** | Q032, BotFather, DNSSEC, видео |
| Закрыто (репо) | AUDIT / PRODUCT / FLOW backlogs | Q063–050 |
| **5. Карта пути** | **`docs/USER-FLOW-JOURNEY.md`** | Персоны, сценарии (закрыт **P3-FLOW-00**) |
| **6. Владелец (ручное)** | **`docs/MANUAL-OWNER-CHECKLIST.md`** | Bitwarden, BotFather, DNSSEC — не в очереди Q |
| **7. Политики** | **`POLICY-SEQUENTIAL-WORK.md`**, **`POLICY-BACKLOG-ORDER.md`** | Один Q → коммит; продукт → UX |

**Параллельно (не NEXT):** **P4-DNS** — §8 бэклога, отдельный владелец.

---

## Фазы очереди (сводка)

| Фаза | Q | Статус | Тема |
|------|---|--------|------|
| **1** | 001–022 | **Закрыта** | Scale, monetize, P6-RED (sub/mux/pg), GTM wiki |
| **2** | 023–031 | **Закрыта** | Safe-deploy, P1-RED, публичный `/status` |
| **3** | 033–050, 063–078, 051–062 | **Репо закрыто** | Код/docs: security → продукт → флоу |
| **4** | 079–084 | **В работе** | Накат LV/AMS (агент + SSH) |

**Сейчас:** **`NEXT = Q080`**. **`docs/AGENT-PROD-DEPLOY-BACKLOG.md`**. Владелец: **`MANUAL-OWNER-CHECKLIST.md`**.

---

## Фазы 3–4 (логика)

```
[DONE репо] Q033–050, Q063–078, Q051–062
[CURRENT]   Q079–084  prod deploy (агент+SSH)
[OWNER]     Q032 + MANUAL-OWNER-CHECKLIST
```

**Gate:** накат AMS — **`RUNBOOK-AMS-SAFE-DEPLOY`** (не Q).

---

## Публичные URL продукта (после Q035–037)

| URL | Назначение |
|-----|------------|
| `https://k9x2m1.conntest.xyz:8443/start/` | Bootstrap (целевой порт после **Q080**) |
| `https://k9x2m1.conntest.xyz:8443/portal/` | Portal + **Mini App** (BotFather после Q080) |
| `https://k9x2m1.conntest.xyz:8443/setup/?t=…` | Персональная выдача |
| `https://k9x2m1.conntest.xyz:8443/status` | Публичный статус |
| `:2053` | Grace period (снять после миграции пользователей) |

Код: **`web/portal/`**, **`ops/site_urls.py`**.

---

## Открыто вне очереди

| ID | Где | Комментарий |
|----|-----|-------------|
| **P4-DNS-01…06** | §8 | Mobile bootstrap SKU |
| **P5-ENG-01** | §9 | Общий HTTP-клиент **ops** |
| **Q063–Q078** | **`AUDIT-2026-05-SECURITY.md`** | Pre-GTM security (CodeRabbit) |
| **P5-PROD-NATIVE-APP-01** | §9, **Q053** | Своё iOS/Android (замена Happ) |
| **TSPU (12 пунктов)** | **`TSPU-OBSERVATIONS.md`**, §5.1 | Матрица наблюдений → **Q051–061** |
| **P2-RED-EDGE-PORT-01** | §5.1, **Q051** | Уход с **:2053** (ТСПУ) |
| **P1-PRO-CLIENT-V2RAYN-01** | §5.1, **Q052** | v2rayN на Windows |
| **P4-DNS-07/08** | §8, **Q060** | RF egress, whitelist IP |
| **P5-RED-RD-01** | §5.1 | R&D Snowflake PoC |
| **§1 срез продакшена** | §1 | Переснять users/RAM при SSH |

---

## Smoke для агента (фаза 3)

```powershell
python ops/portal_bundle_audit.py      # PORTAL_BUNDLE_OK
python ops/smoke_public_bootstrap.py   # PUBLIC_BOOTSTRAP_OK
python ops/smoke_portal_setup_page.py  # PORTAL_SETUP_PAGE_OK  # если есть
python ops/smoke_telegram_miniapp.py   # TELEGRAM_MINIAPP_PORTAL_OK
```

---

*Обновлять эту карту при смене фазы или добавлении Q078+.*
