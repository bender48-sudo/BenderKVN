# Смена inbound-порта VPN-ноды (≠ 443)

**ID:** P2-RED-VPN-INBOUND-PORT-01 (Q056).  
**Не путать с** edge **2053→8443** ([`RUNBOOK-P6-EDGE-PORT-MIGRATION.md`](RUNBOOK-P6-EDGE-PORT-MIGRATION.md)).

## Когда

- Хостер/ТСПУ заблокировал **443** на IP ноды.
- Пользователи на vision+443 не коннектятся, alt **9443/8443** в sub не помогает на их ISP.

## Подготовка

1. Snapshot панели / template (`ops/freeze_ams_node.py` или runbook Remnawave).
2. Выбрать новый порт (напр. **8443**, **9443**, **47xxx**) — не конфликт с edge LV Caddy.
3. Обновить **injectHosts** / subscription template.

## Шаги (tabletop на тестовой ноде)

1. Remnawave → inbound → сменить **port** + `listen`.
2. Перезапуск remnanode на LV/NL (`docker compose` на ноде).
3. Проверка: `xray` health, probe с внешней сети.
4. Дождаться обновления sub у тестового пользователя (Happ refresh).
5. Массово — только после 24h стабильности на тесте.

## Откат

- Восстановить inbound port из snapshot; redeploy node.

## Verify

**`VPN_INBOUND_PORT_OK`** — runbook + smoke file check.
