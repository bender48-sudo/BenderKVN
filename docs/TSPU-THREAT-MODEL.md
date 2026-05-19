# Модель угроз ТСПУ (бета BenderVPN)

**ID:** P1-RED-TSPU-THREAT-MODEL-01 (Q059), дополнено **P2-RED-TSPU-AUDIT-04** (Q102, 2026-05-19).  
**Источник наблюдений:** [`TSPU-OBSERVATIONS.md`](TSPU-OBSERVATIONS.md), [`AUDIT-2026-05-TSPU-REDTEAM-04.md`](AUDIT-2026-05-TSPU-REDTEAM-04.md).

## Предпосылки

1. **ТСПУ независимы по регионам** — бан на МСК ≠ бан на СПб; **один** RU relay (`72.56.0.145`) **недостаточен** (Q106).
2. **Бан часто временный (~15 дней)** на конкретном fingerprint, не «навсегда».
3. **Массовые автоматические баны** редки при **<100** users; при **GTM** риск **T24-02** — один шаблон vision+443+github SNI на всю базу.
4. **Малый сервер** реже в массовых списках, чем бренды; **не отменяет** слои JA3/поведение ([Habr 1009542](https://habr.com/ru/articles/1009542/)).
5. **Апрель 2026 — whitelist L3** (~75k корпоративных IP): VPS **вне списка** уязвимы при режиме «только разрешённые IP» ([Habr 1027276](https://habr.com/ru/articles/1027276/)).

## Слои ТСПУ (2026, внешние источники)

| Слой | Что ломает | Наша линия защиты |
|------|------------|-------------------|
| **L3 CIDR** | Пакеты не в whitelist IP | RF egress / DNS bootstrap (**Q060**, **Q105**); не обещать portal с NL IP в WL-режиме |
| **L7 SNI/DPI** | ClientHello, blacklist SNI | **www.yandex.ru** на проде (**Q102**), не github/microsoft |
| **JA3/JA4** | Не-браузерный TLS стек | uTLS на клиенте; audit нод (**Q107**) |
| **Активное зондирование** | Ответ сервера ≠ легенда SNI | Selfsteal review (**Q104**), не палить github :9443 |
| **Поведение** | vision uplink/downlink ≠ HTTPS | **XHTTP** SplitHTTP (**Q103**), не только Reality MUX |
| **Скан портов** | **:2053** 3X-UI | **:8443** + 301 grace (закрыть **T24-08**) |

## Векторы

| Вектор | Сигнал | Митигация в бэклоге |
|--------|--------|---------------------|
| Скан **:2053** | access-log шум | **Q051** → **:8443** |
| VLESS+vision **:443** | bbs#546, волна 2025–26 | Alt **9443**, **XHTTP 8443** (**Q103**) |
| SNI github-кластер | live sub audit **T24-01** | **Q102** panel template + `smoke_live_sub_sni.py` |
| VLESS+Reality «в целом» | Habr 969618, BlockPulse | XHTTP-first UX; не один outbound |
| Subscription URL в логах | утечка shortId | **log_skip** ✅ |
| WL mobile routing | App Store / NE 15MB | **Q062** tiers, native brief **Q053** |
| ECH | drop ClientHello | **не использовать** (corpus Lantern) |

## Роли

| Роль | Действие при инциденте |
|------|------------------------|
| **Support** | [`RUNBOOK-TSPU-VLESS-INCIDENT.md`](RUNBOOK-TSPU-VLESS-INCIDENT.md) |
| **Ops** | `tspu_block_probe.py`, `ru-monitor`, edge status |
| **Владелец** | BotFather URL, RF VPS go/no-go (**Q060**) |

## Шпаргалка (1 строка)

**Не менять всем сразу** — сегмент, alt tier, alt origin, потом template.
