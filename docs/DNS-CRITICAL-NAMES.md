# Критичные DNS-имена (P1-RED-DNS-01)

Инвентарь публичных имён BenderVPN. Секреты (recovery-коды регистратора) — только в Bitwarden, не в git.

## Регистраторы (≥2 учётки)

| ID | Регистратор | Recovery (Bitwarden) | Назначение |
|----|-------------|----------------------|------------|
| **dynadot** | Dynadot | `BenderVPN/dns/dynadot-recovery-codes` | Основная зона **`conntest.xyz`** |
| **reserve** | Резервный (второй аккаунт) | `BenderVPN/dns/reserve-registrar-recovery-codes` | Backup apex / новые зоны до GTM |

**Правило:** recovery-коды — **офлайн** (бумага / hardware vault), дубликат в Bitwarden — не единственная копия.

## Зоны

| Apex | Registrar | DNS operator | NS (prod) | DNSSEC |
|------|-----------|--------------|-----------|--------|
| **conntest.xyz** | dynadot | Dynadot (`dyna-ns.net`) | `ns1.dyna-ns.net`, `ns2.dyna-ns.net` | ❌ → включить по **`RUNBOOK-DNS-RED-TEAM.md`** |

Машиночитаемо: **`ops/dns_critical_inventory.json`**.

## Критичные FQDN

| FQDN | Роль | Origin (HTTPS) |
|------|------|----------------|
| **k9x2m1.conntest.xyz** | Панель, alternate sub, status JSON | AMS panel / LV Caddy → **176.126.162.158** |
| **p4n7q.conntest.xyz** | Primary subscription | LV Caddy → AMS sub **:3010** |

Источник URL: **`ops/site_urls.py`**, **`ops/site.env.example`**.

## Backup apex (план Б)

| Поле | Значение |
|------|----------|
| Registrar | **reserve** (второй регистратор) |
| Apex | *не заведён* — до массового GTM |
| Runbook | **`docs/RUNBOOK-DNS-RED-TEAM.md` §3** |

## Мониторинг делегирования (P4-DNS-04)

Не дублирует RU SNI-пробы (`ru-monitor`). Только **NS / A / DNSSEC** критичных имён:

```bash
# На LV (есть dig):
ssh bvpn-lv 'python3 /tmp/dns_delegation_probe.py'
# Или с workstation:
python ops/dns_delegation_probe.py   # если локальный dig доступен
pwsh -File ops/deploy-dns-delegation-probe-lv.ps1   # деплой + smoke
```

Ожидается **`DNS_DELEGATION_OK`**.

## Связанные документы

- **`docs/RUNBOOK-DNS-RED-TEAM.md`** — DNSSEC, второй регистратор, делегирование
- **`docs/SECRETS.md`** — публичные домены в panel.env
- **P4-DNS-01…06** — mobile bootstrap (параллельный поток)
