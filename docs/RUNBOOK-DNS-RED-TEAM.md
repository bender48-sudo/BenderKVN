# Runbook: DNS red team (P1-RED-DNS-01)

Цель: снизить blast radius при компрометации одного регистратора / DNS-оператора.

## 1. Текущий прод (2026-05-17)

- Зона **`conntest.xyz`**: Dynadot, NS **`ns1/ns2.dyna-ns.net`**
- Критичные имена: **`k9x2m1`**, **`p4n7q`** → A **176.126.162.158** (LV Caddy)
- DNSSEC: **выключен** (зафиксировать включение ниже)

Инвентарь: **`docs/DNS-CRITICAL-NAMES.md`**, **`ops/dns_critical_inventory.json`**.

## 2. DNSSEC

1. В панели Dynadot для **`conntest.xyz`**: включить DNSSEC (или DNSSEC + DS в parent).
2. Проверка с LV:
   ```bash
   dig +short DNSKEY conntest.xyz @8.8.8.8
   dig +short DS conntest.xyz @8.8.8.8
   ```
3. Обновить **`dns_critical_inventory.json`**: `"dnssec_enabled": true`.
4. **`python ops/dns_delegation_probe.py`** → без `NOTE: DNSSEC not enabled`.

Откат: отключить DNSSEC в регистраторе; дождаться TTL DS (до 48 ч).

## 3. Второй регистратор (backup apex)

До массового GTM:

1. Завести **второй** аккаунт у другого регистратора (не Dynadot).
2. Зарегистрировать резервный apex (например `*.conntest` альтернатива — имя в wiki/Bitwarden).
3. Записать recovery-коды в Bitwarden **`BenderVPN/dns/reserve-registrar-recovery-codes`** + **офлайн** копия.
4. Обновить **`backup_apex.apex`** в **`ops/dns_critical_inventory.json`**.
5. Держать минимальную делегированную зону (NS + placeholder A) — проверка **`dns_delegation_probe`**.

Критичные **prod**-имена можно оставить на **`conntest.xyz`**; backup apex — для аварийного переключения Caddy/DNS (см. **P4-DNS-05**).

## 4. Recovery-коды (офлайн)

| Item Bitwarden | Что хранить | Где офлайн |
|----------------|-------------|------------|
| `BenderVPN/dns/dynadot-recovery-codes` | Dynadot 2FA recovery | Сейф / hardware |
| `BenderVPN/dns/reserve-registrar-recovery-codes` | Второй регистратор | Сейф / hardware |

**Не** хранить только на VPS-провайдере (Hetzner/FriendHosting email ≠ регистратор домена).

## 5. Мониторинг (P4-DNS-04)

Cron на **LV** (рядом с `monitor.sh`, раз в час):

```bash
python3 /opt/scripts/dns_delegation_probe.py || logger -t bvpn-dns 'DNS delegation probe FAIL'
```

Деплой: **`ops/deploy-dns-delegation-probe-lv.ps1`**.

Алерт: при FAIL — Telegram через существующий ops-канал (расширить `monitor.sh` при необходимости; сейчас — лог + ручной smoke).

## 6. Smoke

```bash
ssh bvpn-lv 'python3 /opt/scripts/dns_delegation_probe.py'
# → DNS_DELEGATION_OK
```
