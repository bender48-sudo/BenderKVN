# Smoke-пакет G1 + H1 — один заход (друг + iPhone)

**ID:** `G1-H1-SMOKE-001`  
**Для:** друга с iPhone (РФ, Wi‑Fi для первого прогона)  
**Режим:** read-only · **prod не меняем** · отдельные тестовые профили  
**Время:** ~60–90 мин

**Owner runbook после smoke:** [`G1-POST-SMOKE-RUNBOOK.md`](G1-POST-SMOKE-RUNBOOK.md)  
**Edge UA/HWID tail:** `ops/tail_owner_canary_ua_log.sh`

**Не трогать:** чужой рабочий VPN / «BenderVPN Auto», если установлен.

---

## 0. Установить приложения (один раз)

| # | Приложение | Зачем |
|---|------------|-------|
| 1 | **Happ** | H1 — NL smoke |
| 2 | **INCY** | G1 — основной iOS |
| 3 | **V2Ray Client+** | G1 — запасной |
| 4 | **Изи VPN** | G1 — запасной |

Запиши версии iOS и каждого приложения: _______________

---

## Часть A — H1 (NL exit smoke в Happ)

Два этапа подряд. **Сначала фаза 1, потом фаза 2.**

### Общие правила Happ (обе фазы)

- **Новый профиль** — не перезаписывать чужие.
- **Auto-update / auto-refresh: OFF**
- **Routing overlay OFF** — не включать «BenderVPN RU» поверх JSON.
- Импорт: **файл JSON** от владельца (не metadata).

---

### H1 — Фаза 1: NL Direct Basic (~15 мин)

**Файл от владельца:** `independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json`

**Имя профиля:** `BenderVPN NL Direct Basic — H1 smoke`

#### Импорт в Happ

1. Открой файл в Telegram → **Поделиться** → **Happ** (или сохрани в «Файлы» → Happ → Import).
2. Если Happ просит тип — **Import config** / **Импорт**, не Subscription URL.
3. Проверь: в списке **один** профиль с именем выше.

#### Preflight (обязательно)

- [ ] Auto-refresh **OFF**
- [ ] External routing / BenderVPN RU overlay **OFF**
- [ ] **Telegram и Instagram ЗАКРЫТЫ** на этом этапе

#### Smoke фаза 1

| # | Действие | Ожидание | PASS/FAIL |
|---|----------|----------|-----------|
| 1 | Connect | Connected < 30 с | |
| 2 | **google.com** / Gmail / YouTube | открывается | |
| 3 | Speedtest (опц.) | сервер **NL / Amsterdam** | |
| 4 | **НЕ открывать** Telegram / Instagram | — | |
| 5 | 5 мин на VPN | без отвалов | |

**Фаза 1 итог:** PASS / FAIL / PARTIAL

> FAIL фазы 1 → **не переходи** к фазе 2 и G1 NL-зависимым выводам; всё равно можно прогнать **G1** (часть B).

---

### H1 — Фаза 2: NL Split Stealth (~20 мин)

**Только если фаза 1 = PASS.**

**Файл от владельца:** `independent_exit_nl_SPLIT_STEALTH_IMPORTABLE_PROFILE.json`

**Имя профиля:** `BenderVPN NL Split Stealth — H1 smoke`

#### Импорт

1. **Новый** профиль в Happ (не обновлять Direct Basic).
2. Импорт JSON файла, как в фазе 1.
3. Auto-refresh **OFF**, routing overlay **OFF**.

#### Smoke фаза 2

| # | Действие | Ожидание | PASS/FAIL |
|---|----------|----------|-----------|
| 1 | Connect | Connected | |
| 2 | **Telegram** | работает (stealth/relay) | |
| 3 | **Instagram** | открывается (stealth) | |
| 4 | **Google / YouTube** | работают (**NL direct**) | |
| 5 | **ya.ru** (опц.) | может идти **мимо VPN** — это норма | |
| 6 | 5–10 мин mixed | стабильно | |

**Фаза 2 итог:** PASS / FAIL / PARTIAL

**H1 общий итог:** PASS только если **обе** фазы PASS.

---

## Часть B — G1 (три iOS-клиента, owner-canary URL)

**URL (одна строка, скопировать из сообщения владельца):**

```
https://p4n7q.conntest.xyz:8443/owner-canary/canary-PIzWk8ql30ipVHyvB8S58rlr0dxcCH1m.json
```

Если не открывается — замени `p4n7q` на `k9x2m1`, путь тот же.

**Не вставлять сырой JSON в буфер** — только https-строку.

Каждый клиент — **отдельный** тестовый профиль. После каждого клиента можно **отключить VPN** перед следующим.

---

### B1 — INCY (главный)

1. **+** → **Add Subscription** / Подписка.
2. Вставь URL canary.
3. Имя: `BenderVPN G1 Canary — INCY`
4. Connect → smoke:

| Проверка | PASS/FAIL/N/A |
|----------|---------------|
| Импорт: **1** профиль (не 7 серверов) | |
| Connect | |
| Telegram | |
| Instagram | |
| Google / YouTube | |
| ya.ru (RU direct) | |

#### B1b — INCY + боевой sub (только для HWID, ~1 мин)

Canary — статический файл; **панель не видит HWID** только от canary. Чтобы владелец проверил INCY автоматически:

1. Владелец пришлёт **отдельную** https-строку боевой подписки (не canary).
2. В INCY: **+** → подписка → вставь **боевой** URL.
3. Имя: `BenderVPN G1 HWID probe — INCY` (отдельно от canary).
4. Достаточно **импорта / обновления** — **подключать VPN не обязательно**.
5. Напиши владельцу: «HWID probe сделал» + время (МСК).

> Не пересылай sub URL никому, кроме владельца. Не публикуй в чатах.

---

### B2 — V2Ray Client+

1. **+** → Subscription / URL (если есть).
2. Тот же canary URL.
3. Зафиксируй:

| Вопрос | Ответ |
|--------|-------|
| Импорт OK? | |
| Формат | JSON / vless / ошибка |
| Профилей в списке | |
| Connect | |

Если Connect OK — Telegram, Google, ya.ru (stealth **не гарантирован**).

---

### B3 — Изи VPN

1. **+** → Subscription или из буфера.
2. Тот же canary URL.
3. Та же таблица, что B2.

**Fingerprint в Изи VPN не менять.**

---

## Сводная таблица (заполни и пришли владельцу)

**Устройство:** iPhone ___ · iOS ___ · сеть Wi‑Fi / LTE ___ · дата ___

### H1 (Happ)

| Фаза | Connect | Google/NL | TG | IG | Итог |
|------|---------|-----------|----|----|------|
| Direct Basic | | | N/A | N/A | |
| Split Stealth | | | | | |

### G1

| Клиент | Версия | Импорт | Формат | # профилей | Connect | TG | IG/Google | Комментарий |
|--------|--------|--------|--------|------------|---------|----|-----------|-------------|
| INCY | | | | | | | | |
| V2Ray Client+ | | | | | | | | |
| Изи VPN | | | | | | | | |

---

## Откат

- Удали тестовые профили в Happ / INCY / V2Ray / Изи.
- Чужие рабочие VPN-профили не трогали.

---

## Что владелец сделает после

- Снимет **User-Agent + x-hwid / x-device-*** с edge: `bash ops/tail_owner_canary_ua_log.sh --since-minutes 120 --verbose`
- Проверит **INCY → HWID** в панели (до/после шага B1b): `python ops/_device_smoke_owner_probe.py`
- Обновит UA-map.

**Спасибо!**
