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
2. **Подтвердить scope:** `ru-monitor`, `tspu_block_probe.py`, жалобы по ISP.
3. **Сегмент:** затронут один транспорт (vision+443) или весь VLESS?
4. **Мягкие меры:** напомнить пользователям **turbo** tier / обновить sub; alt origin **p4n7q** vs **k9x2m1**.
5. **Транспорт:** по [`RUNBOOK-P6-TRANSPORT-MATRIX.md`](RUNBOOK-P6-TRANSPORT-MATRIX.md) — MUX уже включён; рассмотреть alt inbound **≠443** (**Q056**).
6. **SNI:** если fingerprint github-кластера — **Q058** (`www.yandex.ru`).
7. **Коммуникация:** шаблон в support — «временное ухудшение на части сетей, пробуем alt профиль».

## Эскалация

- >30% active users fail probe → incident P1; владелец + runbook jurisdiction (**P3-RED-JURIS-01**).

## Verify

Smoke **`TSPU_VLESS_PLAYBOOK_OK`** — файл существует + ссылка из `RUNBOOK-INCIDENT.md`.
