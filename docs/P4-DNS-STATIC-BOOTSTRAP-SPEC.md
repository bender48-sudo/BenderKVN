# P4-DNS-06: спецификация статического DNS bootstrap

**Назначение:** что **разрешено** и **запрещено** для опционального режима «только DNS» (без динамического туннеля).

---

## Разрешено

| Элемент | Описание |
|---------|----------|
| **A/AAAA** | Статические записи на **bootstrap apex** (не prod panel IP без rate-limit). |
| **TXT** | Служебные метки версии / incident (короткий JSON ≤255 B). |
| **HTTPS/SVCB** | Только если клиент PoC явно поддерживает (не Happ). |
| **TTL** | 300–3600 s; смена IP — через runbook jurisdiction, не silent. |

---

## Запрещено

1. Публиковать **полный VPN config** в DNS TXT (секреты, UUID, private keys).
2. Обещать пользователю «весь интернет через DNS» в маркетинге основного SKU.
3. GitHub seed-lists для whitelist IP (**P4-DNS-08** — свой источник).
4. Подмена **prod** `k9x2m1` / `p4n7q` A-записей без safe-deploy и §12.

---

## Мониторинг

- **`ops/dns_delegation_probe.py`** — делегирование и critical hosts (**P4-DNS-04**).
- Cron LV: **`ops/install_dns_delegation_cron.sh`**.

---

## Связь

- **P4-DNS-01** — dnstt/slipstream PoC (динамический путь).
- **P4-DNS-05** — plan B domain (владелец + legal).
- **`RUNBOOK-DNS-RED-TEAM.md`**
