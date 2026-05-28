# Аудит BenderVPN — post-gen=30 (Claude, 2026-05-28)

**Основание:** запрос полного аудита по трём критериям — надёжность, скорость, простота — после Cursor-фиксов gen=29/30.  
**Исполнение задач:** [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md) (статусы и gate).  
**Сверка с продом:** владелец подтвердил факты gen=30; уточнения в §0.

---

## §0. Уточнения по сверке владельца

| Тезис в аудите | Реальность |
|----------------|------------|
| «Phase 8–10 + VPN-AUD-001..251 закрыты» | VPN-AUD-001..011, 101..250 DONE; VPN-AUD-103, 160, 201+ — TODO (owner/blocker) |
| «Пользователь видит 11 пунктов меню в Happ» | Happ показывает **1 профиль** «🚀 BenderVPN Auto»; 11 outbound внутри JSON; Append custom count=1. Риск ручного выбора ниже — аргумент U-001 другой (упростить конфиг для нового пользователя) |
| «Custom remarks убрали proxy-N» | Правили subscription-page `customRemarks` (gen=28), не injectHosts; U-003 — отдельная проверка что видит пользователь |
| «Bot circuit breaker + payment DLQ на проде» | В `git/main` — да; YooKassa/balance — WIP локально, не на AMS |
| «Redis без AOF» | Гипотеза для аудита (VPN-AUD-340), не подтверждённый инцидент |

---

## I. НАДЁЖНОСТЬ

### Работает хорошо (gen=30)

- Circuit breaker (3 fail → 30s backoff) + tenacity retry × 4 на все Remna API
- SQLite WAL + busy_timeout=5000
- HA sub-page split-host :3010/:3011 + AMS 2G swap
- docker events → TG (die/oom remnanode/panel) — VPN-AUD-140
- ru-monitor anti-flap на LV
- balancer.sh / watchdog.sh на продах — drift OK
- RELAY-NL :9443 убраны из injectHosts (gen=30, `a82c4f7`)

### Открытые проблемы

**[BLOCKER] N-001 — Единственный relay IP**  
`proxy-5..7` = один IP `72.56.0.145`. Блокировка IP → все три RELAY пути умирают одновременно. Аналогично LV direct — `proxy-1..4` = `176.126.162.158`. Единственный fix — **Q120 / VPN-AUD-201** (второй relay VPS, другой AS). **Задача владельца.**

**[P1] N-002 — relay_failover_template.py**  
ru-monitor обнаруживает отказ relay, но не патчит selector автоматически. MTTR при relay failure: ручной (~30–90 мин). Нужен `ops/relay_failover_template.py` — при N fail удаляет relay proxy-5..7 из `Super_Balancer` selector; при recovery возвращает. VPN-AUD-202.

**[P1] N-003 — Caddy upstream health-check** (новый, VPN-AUD-152)  
При падении одного из контейнеров sub-page (:3010 или :3011) Caddy получает 502 и не переключает на второй. Нужен `health_poll` в Caddy upstream config на `/api/sub/health` или просто `/`.

**[P1] N-004 — Fragment per-ISP (МТС/Билайн)**  
`patch_remove_fragment_defaults.py` убрал fragment. При жёстком DPI (МТС/Билайн) Reality-handshake может резаться. Нужен второй Response Rule или отдельный шаблон с `fragment_on`. VPN-AUD-320 (среднесрок — до появления второго relay или второго IP).

**[P2] N-005 — Redis AOF audit**  
Гипотеза: если Valkey используется для rate-limit при оплате, restart без AOF сбрасывает state. Нужен аудит use-case: что хранится в Redis, критично ли это. VPN-AUD-340.

---

## II. СКОРОСТЬ

### Работает хорошо (gen=30)

- DNS port 53 → direct (`a82c4f7`) — убрал 50–200ms на каждый hostname resolve через random proxy
- bufferSize 128 (gen=28) — video burst буфер
- RELAY-NL :9443 убраны — 22% трафика больше не уходит на dead paths
- Intl IP CIDR (TG/Meta/OpenAI) в R1 — iOS background
- policy 30/30 (было 2/5)

### Открытые проблемы

**[P1] S-001 — Sub-page cache** (новый, VPN-AUD-153)  
p95=4.5s при baseline 120 rps (VPN-AUD-240). Цель: <2s. Sub меняется только при смене gen (редко). Решение: Caddy `cache` directive или Redis-кэш в sub-page с TTL=5–10 min. Инвалидация — при bump gen + broadcast.

**[P1] S-002 — Random без latency-awareness**  
Random при 11 путях → ~9% коннектов могут попасть на деградировавший outbound. Это главный разрыв с AmnesiaVPN/Outline (там health-based routing). Решение: server-side latency probe per-outbound из RU → PATCH selector. VPN-AUD-310. **Не включать observatory на прод без staging A/B** (closed-pipe риск).

**[P2] S-003 — Observatory staging A/B**  
gstatic-probe (не hicloud) + Happ A/B: проверить есть ли `closed pipe` на RU-сетях. Если нет — добавить leastLoad/observatory. VPN-AUD-430.

**[P2] S-004 — regexp:.*\.ru$ → geosite:ru**  
Слишком широкий direct rule. Часть .ru CDN может оптимальнее идти через proxy. Замена на `geosite:ru` с exceptions для TG/IG. Риск регрессии — только после A/B. VPN-AUD-210.

---

## III. ПРОСТОТА

### Работает хорошо

- Пользователь не видит кнопок «выберите LV/NL» — constraint соблюдён
- Happ показывает 1 профиль «BenderVPN Auto» — не 11 отдельных серверов
- customRemarks добавлены (gen=28) — убраны технические proxy-N в JSON
- Wizard + Mini App работают (P3-FLOW-04 DONE)
- Auto-renew + expiry notify (days≤1, hours≤6) работают
- bot topup_button_label показывает «≈N дн.» рядом с суммой

### Открытые проблемы

**[P1] U-001 — Trial sub-template** (VPN-AUD-410)  
Новый пользователь получает тот же шаблон что и платный — 11 outbounds, relay, NL. Для первого опыта достаточно 3–4 LV outbounds + leastLoad, interval=60s. Упрощает JSON, снижает вероятность edge-case ошибок при первом import.

**[P1] U-002 — /help_connect recovery URL при TSPU** (VPN-AUD-370)  
При LTE (МТС/Билайн + жёсткий DPI) стандартная sub может не коннектиться. Нет пути: бот-команда `/help_connect` → пользователь получает alt sub URL (xhttp-only или fragment-on). Без этого пользователь просто уходит.

**[P1] U-003 — Remarks quality verify**  
Проверить что видит пользователь в Happ: `customRemarks` из subscription-page. Цель: «BenderVPN 🇱🇻», «BenderVPN 🇱🇻 Reserve», «BenderVPN 🇳🇱» — не технические proxy-N. Если Happ показывает только один профиль «Auto» — дополнительно убедиться что UX-текст не создаёт confusion.

**[P2] U-004 — Payment UX: «≈N дней» везде**  
`topup_button_label` уже показывает «≈N дн.». Проверить экраны: профиль, история пополнений, уведомление о низком балансе — везде ли есть дни рядом с суммой в рублях.

---

## Сводная таблица приоритетов

| ID | Критерий | Задача | P | Исполнитель | Бэклог ID |
|----|----------|--------|---|-------------|-----------|
| N-001 | Надёжность | 2-й relay VPS (другой AS/DC) | **P0** | Владелец | Q120 / VPN-AUD-201 / O-VPN-001 |
| N-002 | Надёжность | relay_failover_template.py — auto PATCH selector | **P1** | Агент | VPN-AUD-202 |
| N-003 | Надёжность | Caddy upstream health-check sub-page | **P1** | Агент | VPN-AUD-152 (новый) |
| N-004 | Надёжность | Fragment per-ISP profile (МТС/Билайн) | **P1** | Агент | VPN-AUD-320 |
| N-005 | Надёжность | Redis AOF use-case audit | **P2** | Агент | VPN-AUD-340 |
| S-001 | Скорость | Sub-page cache TTL 5–10 min → p95 < 2s | **P1** | Агент | VPN-AUD-153 (новый) |
| S-002 | Скорость | Server-side latency probe → PATCH selector | **P1** | Агент | VPN-AUD-310 |
| S-003 | Скорость | Observatory staging A/B (gstatic) | **P2** | Агент | VPN-AUD-430 |
| S-004 | Скорость | regexp:.*\.ru$ → geosite:ru с A/B | **P2** | Агент | VPN-AUD-210 |
| U-001 | Простота | Trial sub-template (3–4 outbounds) | **P1** | Агент | VPN-AUD-410 |
| U-002 | Простота | Bot /help_connect → recovery sub URL | **P1** | Агент | VPN-AUD-370 |
| U-003 | Простота | Remarks quality verify в Happ | **P1** | Агент | — |
| U-004 | Простота | Payment UX «≈N дней» во всех экранах | **P2** | Агент | — |

---

## Рекомендуемая очередь агента (без владельца, без observatory risk)

```
S-001  sub-page cache (dry-run → load probe до/после)
N-003  Caddy upstream health-check :3010/:3011
U-002  bot /help_connect recovery URL (только бот, без template PATCH)
U-001  trial sub-template (staging → prod)
```

**Не трогать без owner / A/B:**
- Observatory на прод (VPN-AUD-430)
- regexp:.*\.ru$ → geosite:ru (VPN-AUD-210)
- relay_failover_template.py apply на прод без 2-го relay (N-002)

---

## Главный вывод

Продукт технически надёжен на уровне бота и базовой инфраструктуры. Три архитектурных разрыва vs AmnesiaVPN:

1. **SPOF по IP** — один relay IP + один LV IP. Не фиксируется кодом — нужны новые сервера (владелец).
2. **Random без latency-awareness** — ~9% попаданий на деградировавший outbound без авто-переключения. Ключевой разрыв с AmnesiaVPN.
3. **Sub latency p95=4.5s** — кэш на sub-page закрывает за один day.

---

*Исполнение: [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md). Предыдущий аудит той же сессии: [`AUDIT-2026-05-28-VPN-FULL-CLAUDE.md`](AUDIT-2026-05-28-VPN-FULL-CLAUDE.md).*
