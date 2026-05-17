# Runbook: short-lived machine credentials (P1-RED-SEC-01)

## Пилот (LV)

| Компонент | Роль |
|-----------|------|
| **`/etc/bvpn/remna-credential-source.env`** | Master JWT (root `600`), единственный «долгий» токен на хосте |
| **`ops/remna_credential_broker.py`** | Кэш per-consumer с **TTL** (default **3600 s**) |
| **`/var/lib/bvpn/credentials/*.json`** | Кэш (`600`), не в git |
| **`/var/log/bvpn-credential-audit.log`** | JSON audit: `issue`, `cache_hit`, `refresh` |
| **Consumers** | **`ru-monitor.py`**, **`balancer.sh`** |

Remnawave пока выдаёт **long-lived API JWT** в UI — пилот **не** создаёт новый тип токена в панели, а **ограничивает экспозицию**: процессы читают кэш с TTL + аудит; ротация master — по **`RUNBOOK-REMNA-API-TOKEN.md`**.

## Деплой

```powershell
pwsh -File ops/deploy-remna-credential-broker-lv.ps1
```

Создаёт `remna-credential-source.env` из `ru-monitor.env` (если нет).

## Cron (опционально)

```cron
# /etc/cron.d/bvpn-credential-refresh — каждые 30 мин
*/30 * * * * root python3 /opt/scripts/remna_credential_broker.py refresh --consumers ru-monitor,balancer >>/var/log/bvpn-credential-refresh.log 2>&1
```

## Smoke

```bash
ssh bvpn-lv 'python3 /opt/scripts/smoke_short_lived_token_lv.py'
# SHORT_LIVED_TOKEN_OK
```

## Фаза 2 (вне пилота)

- HashiCorp **Vault** + **SPIFFE** ([`philips-labs/spiffe-vault`](https://github.com/philips-labs/spiffe-vault))
- Отдельные API-токены per-service в UI панели
- AMS shop/sub — отдельный broker или sidecar

## Связанные документы

- **`docs/SECRETS.md`** — `REMNA_API_TOKEN_LV`
- **`docs/RUNBOOK-REMNA-API-TOKEN.md`** — ротация master JWT
