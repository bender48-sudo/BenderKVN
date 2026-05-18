# Запасной домен bootstrap (P3-FLOW-11)

**Связь:** **P2-RED-SUB-01** (multi-origin подписки), **P2-RED-EDGE-PORT-01** (edge **8443**).

## Когда включать

- Основной хост **`k9x2m1.conntest.xyz`** недоступен с RU-сети (DNS или блок), при живых **p4n7q** / AMS.
- Tabletop раз в квартал + после инцидента в **`RUNBOOK-TSPU-VLESS-INCIDENT.md`**.

## План (tabletop)

1. Зарегистрировать **второе имя** (другой registrar — **P1-RED-DNS-01**).
2. DNS **A** → тот же **bvpn-lv** IP.
3. Caddy: клон блока **`k9x2m1:8443`** на `bootstrap-alt.example:8443` → те же `file_server` / `reverse_proxy`.
4. **`ops/site.env`:** `PUBLIC_BOOTSTRAP_URL`, `PUBLIC_PORTAL_ORIGIN` — не менять канон без коммуникации; alt только в рекламе/зеркале.
5. Probe: `curl -fsSI https://bootstrap-alt.example:8443/portal/` → **200**.
6. Сообщение пользователям: «если не открывается основная ссылка — зеркало …».

## Откат

Удалить server block alt; DNS TTL 300.

## Verify

**`BACKUP_BOOTSTRAP_DOMAIN_OK`** — runbook + ссылка из **`RUNBOOK-INCIDENT.md`**.
