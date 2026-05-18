# Модель угроз ТСПУ (бета BenderVPN)

**ID:** P1-RED-TSPU-THREAT-MODEL-01 (Q059).  
**Источник наблюдений:** [`TSPU-OBSERVATIONS.md`](TSPU-OBSERVATIONS.md).

## Предпосылки

1. **ТСПУ независимы по регионам** — бан на МСК ≠ бан на СПб; мониторинг один RU relay недостаточен.
2. **Бан часто временный (~15 дней)** на конкретном fingerprint, не «навсегда».
3. **Массовые автоматические баны** редки при **<100** активных users; риск растёт при публичном URI и дефолтных портах (**2053**).
4. **Малый сервер** реже попадает в массовые списки, чем известные VPN-бренды.

## Векторы

| Вектор | Сигнал | Митигация в бэклоге |
|--------|--------|---------------------|
| Скан **:2053** | access-log шум | **Q051** → **:8443** |
| VLESS+vision **:443** | bbs#546, бета | Alt inbound **Q056**, MUX |
| SNI github-кластер | DPI fingerprint | **Q058** yandex.ru |
| Subscription URL в логах | утечка shortId | **log_skip** ✅ |
| WL mobile routing | App Store / NE 15MB | **Q062** tiers, native brief **Q053** |

## Роли

| Роль | Действие при инциденте |
|------|------------------------|
| **Support** | [`RUNBOOK-TSPU-VLESS-INCIDENT.md`](RUNBOOK-TSPU-VLESS-INCIDENT.md) |
| **Ops** | `tspu_block_probe.py`, `ru-monitor`, edge status |
| **Владелец** | BotFather URL, RF VPS go/no-go (**Q060**) |

## Шпаргалка (1 строка)

**Не менять всем сразу** — сегмент, alt tier, alt origin, потом template.
