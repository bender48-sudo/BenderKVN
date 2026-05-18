# Карта бэклога BenderVPN

**Назначение:** одна страница «куда смотреть». **Исполнять** только по **`BACKLOG-QUEUE.md`** (строка **`NEXT`**).

---

## Иерархия документов

| Уровень | Файл | Роль |
|---------|------|------|
| **1. Исполнение** | **`docs/BACKLOG-QUEUE.md`** | Линейная очередь **Q001…**; единственный **`NEXT`** |
| **2. Задачи и журнал** | **`docs/COMMERCIAL-BACKLOG.md`** | ID, Done when, §7.1 P3-FLOW, **§12** прогресс на проде |
| **3. Флоу (продукт)** | **`docs/USER-FLOW-BACKLOG.md`** | Принципы, MVP/Comfort, бабушка-тест |
| **4. Агент — продукт (критично)** | **`docs/AGENT-PRODUCT-BACKLOG.md`** | Q051–062: что / зачем / почему |
| **4b. Агент — флоу** | **`docs/AGENT-FLOW-BACKLOG.md`** | Q044–050 после продукта |
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
| **3** | 032–062 | **В работе** | Продукт/ТСПУ **Q051–062**, затем флоу **Q044–050** |

**Сейчас:** **`NEXT = Q051`** (edge **:8443**). **Флоу Q044–050** — после **Q062**.

---

## Фаза 3 — блоки (логика, не менять Q-номера)

```
[LEGAL]     Q032  P5-COM-02 возвраты — TODO, до GTM (пропущен при старте фазы 3)
[MVP DONE]  Q033–038  journey, portal, /start, /setup, Mini App, bot links
[DONE]      Q039  мастер «Подключить VPN» в боте
[DONE]      Q040  FAQ / оплата live (PAYMENT_COPY_SYNC_OK)
[DONE]      Q041  QR подписки (бот + portal)
[DONE]      Q042  видео/GIF guide на portal
[DONE]      Q043  ошибки /start/help/errors/
[CURRENT]   Q051  NEXT → edge :8443 (см. EDGE-PORT-RECOMMENDATION)
[BETA]      Q052–061  v2rayN, VLESS, SNI, …
[TIER]      Q062  turbo / wl-direct / wl-routed
[FLOW]      Q044–050  после продукта
[NATIVE]    Q053  brief своего iOS/Android app
[TSPU]      Q054–059  VLESS, probe, VPN port, selfsteal, SNI, threat model
[P4 TSPU]   Q060  RF egress + whitelist IP (параллельно P4)
[TSPU]      Q061  DNS на нодах
[POLISH]    Q045–047  a11y, метрики, запасной домен
[WEB LK]    Q048–050  баланс в ЛК, bind TG, notify без TG
```

**Gate:** накат AMS — **`RUNBOOK-AMS-SAFE-DEPLOY`** (не Q).

---

## Публичные URL продукта (после Q035–037)

| URL | Назначение |
|-----|------------|
| `https://k9x2m1.conntest.xyz:2053/start/` | Bootstrap (браузер, без VPN) |
| `https://k9x2m1.conntest.xyz:2053/portal/` | Тот же портал; **URL Mini App** в BotFather |
| `https://k9x2m1.conntest.xyz:2053/setup/?t=…` | Персональная выдача конфига |
| `https://k9x2m1.conntest.xyz:2053/status` | Публичный статус |

Код: **`web/portal/`**, **`ops/site_urls.py`**.

---

## Открыто вне очереди

| ID | Где | Комментарий |
|----|-----|-------------|
| **P4-DNS-01…06** | §8 | Mobile bootstrap SKU |
| **P5-ENG-01** | §9 | Общий HTTP-клиент ops |
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

*Обновлять эту карту при смене фазы или добавлении Q062+.*
