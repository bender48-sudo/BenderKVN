# Runbook: второй RU relay VPS (P2-DOC-RU-RELAY-02-01 / Q120)

**Владелец:** **Q120** `P2-OPS-RU-RELAY-02-VPS-01` — агент не блокирует очередь.

## Цель

Два независимых RU egress для `tspu_block_probe` и template Relay — снижение единой точки отказа **72.56.0.145**.

## Шаги (владелец)

1. Поднять 2-й VPS в RU (другой ASN/DC по возможности).
2. SSH: LV → relay#1 **3344**, relay#2 — отдельный ключ в `docs/SSH-KEY-INVENTORY.md`.
3. Скопировать `ops/tspu_block_probe_ru.py` + cron по образцу `ops/install_tspu_ru_probe_cron.sh`.
4. Probe с LV: `python ops/smoke_tspu_block_probe_ru.py` — **2× OK**.
5. После стабильных probe — добавить 3-й Relay host в panel (отдельный Q, не смешивать с routing patch).

## Verify

**2× `TSPU_BLOCK_PROBE_RU_OK`**; журнал §12; **Q120** → DONE в `docs/BACKLOG-QUEUE.md`.
