# Аудит: нестабильный Instagram / связь с патчами Q132 (2026-05-27)

**Запрос владельца:** «до последних патчей было ок», Instagram то грузит, то нет; сверка с [AUDIT-2026-05-VPN-STABILITY-CLAUDE.md](AUDIT-2026-05-VPN-STABILITY-CLAUDE.md).

---

## Executive summary

| Вопрос | Ответ |
|--------|--------|
| Ноды LV/NL упали? | **Нет** — remnanode up, 71 ACTIVE, нагрузка ~0 |
| xhttp ломает Happ сейчас? | **Нет** — live sub 16 outbounds, 0× xhttp, `batch_risk=LOW` |
| Почему Instagram флапает? | **Маршрутизация:** `geosite:instagram` → `Intl_Direct` → **только** `proxy-5..7` (RU relay `72.56.0.145:443`) |
| Relay реально нестабилен? | **Да** — ru-monitor: TCP OK, TLS timeout/recover каждые 5–15 мин |
| Регрессия от патчей? | **Да (routing)** — коммиты `f7583a6`, `7429daf`, `e497c52` (25.05) перевели Intl/catch-all на RELAY-only |
| Фикс | **Применён 27.05:** `Intl_Direct` → LV Direct + RELAY + NL Direct (11 путей, random); catch-all по-прежнему RELAY-only |

---

## Сверка с аудитом Claude (25.05)

| Гипотеза Claude | Актуальность 27.05 |
|-----------------|-------------------|
| **P0-A xhttp → batch-import 0** | **Снято** на prod: xhttp нет в выдаче, observatory нет |
| **P0-B 194.221.250.50 retry** | По-прежнему **destination** (CDN), не outbound VPN |
| **P1-A leastLoad флап proxy-6/7/8** | **Нет** burstObservatory в template — балансировка `random` на 3 relay |
| **P1-B AMS OOM** | Не наблюдалось в этом инциденте |
| **Новое** | **Intl → relay-only** — в Claude-аудите не было; появилось после Q132 |

**Вывод:** жалоба «как в аудите Claude» частично совпадает (нестабильность через балансировщик), но **корневая причина сегодня — не xhttp**, а **узкий selector Intl_Direct = relay-only** при флапающем RU relay.

---

## Live routing (до фикса 27.05)

```
geosite:instagram, facebook, telegram, …
    → balancerTag: Intl_Direct
    → selector: [proxy-5, proxy-6, proxy-7]   # 72.56.0.145:443 only
    → strategy: random

tcp,udp catch-all
    → Super_Balancer
    → selector: [proxy-5, proxy-6, proxy-7]   # тот же relay
```

Outbounds в подписке (16 vless/tcp):

| Тег | Путь |
|-----|------|
| proxy … proxy-4 | LV Direct :443 |
| proxy-5 … proxy-7 | RELAY→LV :443 |
| proxy-8 … proxy-11 | NL Direct :443 |
| proxy-12 … proxy-14 | RELAY→NL :9443 |

Instagram **не использовал** LV/NL Direct — только relay.

---

## Доказательства нестабильности relay

`ru-monitor` (LV, cron */5), 27.05 вечер:

- `72.56.0.145:443` + SNI `eh.vk.com`, `ir-3.ozone.ru`, `ads.x5.ru`
- Паттерн: **TCP 0.1ms**, **TLS timeout** → через 4–5 мин **TLS OK** → снова DOWN
- Совпадает с UX: «то грузит, то нет»

TSPU probe с relay: панель `:8443` OK; это **не** отменяет флап TLS к сторонним SNI на :443 relay.

---

## Хронология патчей (git)

| Коммит | Смысл | Влияние на IG |
|--------|--------|----------------|
| `f7583a6` | P1-PRO-VPN-SPEED-01, gen=21 | Intl через отдельный балансировщик |
| `42c6468` | split Intl_Direct / Super_Balancer | Иначе random по 8 Direct — пинг ×3 |
| `e497c52` | TG/IG только RELAY-LV proxy-5..7 | **IG привязан к relay** |
| `7429daf` | catch-all тоже RELAY | Остальной трафик тоже через relay |

До Q132 Intl мог ходить через Direct — у владельца «было ок».

---

## Фикс 27.05

**Скрипт:** `python ops/patch_balancer_direct_first_intl.py --apply`

**Intl_Direct selector:**

`proxy … proxy-4` (LV) + `proxy-5 … proxy-7` (RELAY) + `proxy-8 … proxy-11` (NL)

**Super_Balancer** без изменений: `proxy-5..7` (игры/общий трафик — отдельный компромисс).

**Действие пользователям:** обновить подписку в Happ (pull), переподключить VPN.

---

## Остаточные риски

1. **RU relay** — по-прежнему SPOF для catch-all и части Intl; нужен **Q120** (2-й relay).
2. **random** без observatory — при нескольких живых путях может попасть на слабый; при необходимости → `leastPing` + лёгкий observatory (отдельная задача).
3. **TG через NL Direct** — исторически медленно; сейчас NL снова в Intl pool — мониторить access_log для `149.154.x`.

---

## Verify после apply

```bash
python ops/probe_subscription.py
python -c "… Intl_Direct selector …"   # 11 тегов
python ops/diagnose_happ_import.py      # batch_risk=LOW
```

---

## Мониторинг

- `ru-monitor.py` — антифлап TG (streak 3/2, batch alerts) — деплой 27.05.
- Не путать **SNI failure на relay** с падением LV/NL нод.
