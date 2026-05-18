# DNS на VPN-нодах (не провайдерский резолвер)

**ID:** P1-RED-NODE-DNS-01 (Q061).

## Политика

- **Xray/remnanode** на LV/NL использует **локальный** DNS (AdGuard/unbound на том же VPS или loopback).
- **Не** полагаться на resolver хостера — ТСПУ может подменять/удалять записи (наблюдение п.11).

## Настройка

1. AdGuard из `compose/lv/adguard` — слушает **127.0.0.1:53** (или documented port).
2. В inbound / routing template — `dns.servers` → **127.0.0.1** (или docker bridge к AdGuard).
3. Документировать в node `.env` на каждой ноде.

## Мониторинг

```bash
# На ноде: сравнить dig @127.0.0.1 vs @8.8.8.8 для заблокированного домена (тестовый)
dig @127.0.0.1 +short example-blocked.test
```

Probe: расхождение → алерт в `monitor.sh` (хвост).

## Verify

**`NODE_DNS_RESOLVER_OK`** — runbook + smoke file.
