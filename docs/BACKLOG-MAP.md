# Карта бэклога BenderVPN

**Назначение:** одна страница «куда смотреть». **Исполнять** только по **`BACKLOG-QUEUE.md`** (строка **`NEXT`**).

---

## Иерархия документов

| Уровень | Файл | Роль |
|---------|------|------|
| **1. Исполнение** | **`docs/BACKLOG-QUEUE.md`** | Линейная очередь **Q001…**; единственный **`NEXT`** |
| **2. Задачи и журнал** | **`docs/COMMERCIAL-BACKLOG.md`** | ID, Done when, §7.1 P3-FLOW, **§12** прогресс на проде |
| **3. Флоу (продукт)** | **`docs/USER-FLOW-BACKLOG.md`** | Принципы, MVP/Comfort, бабушка-тест |
| **4. Агент (как делать)** | **`docs/AGENT-FLOW-BACKLOG.md`** | Пошагово по Q, файлы, smoke, commit |
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
| **3** | 032–050 | **В работе** | Флоу, portal, Mini App, GTM-хвосты, веб-ЛК |

**Сейчас:** **`NEXT = Q042`** (**P3-FLOW-06** — видео/GIF на portal).

---

## Фаза 3 — блоки (логика, не менять Q-номера)

```
[LEGAL]     Q032  P5-COM-02 возвраты — TODO, до GTM (пропущен при старте фазы 3)
[MVP DONE]  Q033–038  journey, portal, /start, /setup, Mini App, bot links
[DONE]      Q039  мастер «Подключить VPN» в боте
[DONE]      Q040  FAQ / оплата live (PAYMENT_COPY_SYNC_OK)
[DONE]      Q041  QR подписки (бот + portal)
[CURRENT]   Q042  NEXT → видео/GIF на portal
[POLISH]    Q043–047  ошибки, a11y, метрики, запасной домен
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

*Обновлять эту карту при смене фазы или добавлении Q051+.*
