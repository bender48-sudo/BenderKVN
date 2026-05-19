# Инцидент: «спалили VLESS» / бан ~15 дней на ТСПУ

**ID:** P2-RED-TSPU-VLESS-01 (Q054).  
**Связь:** [`RUNBOOK-INCIDENT.md`](RUNBOOK-INCIDENT.md), [`TSPU-OBSERVATIONS.md`](TSPU-OBSERVATIONS.md).

## Симптомы

- Массовые жалобы: **не коннектится** на LTE/Wi‑Fi при живой панели.
- С RU-сети: обрыв **TLS handshake** на edge/sub; режут порты **>990** (см. **Q055** probe).
- Локально на одном ISP — работает; на другом — нет.

## Не делать

- Не крутить **весь** шаблон подписки для всех пользователей без сегментации.
- Не менять **SNI/порт** на проде без snapshot Remnawave (`freeze_ams_node.py` стиль).
- Не публиковать «рабочий» URI в открытый чат.

## Действия (порядок)

1. **Статус:** `https://k9x2m1.conntest.xyz:8443/status` + зеркало JSON ops.
2. **Подтвердить scope:** `ru-monitor`, `tspu_block_probe.py`, **`tspu_block_probe_ru.py`** (RU relay), жалобы по ISP/городу.
3. **Сегмент:** затронут один транспорт (vision+443) или весь VLESS?
4. **Пользователю (2026, первая линия):**
   - Обновить подписку в Happ.
   - Выбрать узел **XHTTP** (порт **8443**, LV) — SplitHTTP обходит часть поведенческого DPI ([Habr 1009542](https://habr.com/ru/articles/1009542/)).
   - Если не помогло — **NL** или **9443** (alt Reality), не крутить всех на один outbound.
5. **Мягкие меры:** alt origin подписки **p4n7q** vs **k9x2m1** (оба **:8443**).
6. **Транспорт:** [`TRANSPORT-MUX-MATRIX.md`](TRANSPORT-MUX-MATRIX.md) — MUX считает Reality; **XHTTP проверять отдельно** (`python ops/smoke_live_sub_sni.py` после Q102).
7. **SNI:** live sub **не должен** содержать `api.github.com` / microsoft / bing — иначе **P0 Q102** (панель → `www.yandex.ru`).
8. **Режим whitelist (мобильный интернет):** см. **`RUNBOOK-TSPU-WHITELIST-L3.md`** (Q105) — portal с NL IP может быть недоступен; RF egress / DNS bootstrap.
9. **Коммуникация:** «временное ухудшение на части сетей; пробуем XHTTP → alt порт → другой origin».

## Эскалация

- >30% active users fail probe → incident P1; владелец + runbook jurisdiction (**P3-RED-JURIS-01**).

## Verify

Smoke **`TSPU_VLESS_PLAYBOOK_OK`** — файл существует + ссылка из `RUNBOOK-INCIDENT.md`.
