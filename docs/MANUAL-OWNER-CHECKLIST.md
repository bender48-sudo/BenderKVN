# Чеклист владельца (ручные доработки)

Задачи, которые **не автоматизируются** в репо или требуют действий вне Cursor. Отмечай `[x]` по мере выполнения.

---

## Критично (безопасность / доступ)

- [ ] **LUKS Postgres AMS** — сохранить passphrase в Bitwarden **`BenderVPN/ams/postgres-luks-key`** + офлайн-копия (показан один раз при `deploy-postgres-luks-ams.ps1 -Enable`; если потерян — см. runbook откат/новый ключ).
- [ ] После **перезагрузки AMS** — unlock тома: `pwsh -File ops/deploy-postgres-luks-ams.ps1 -ProbeOnly` (если FAIL → `ssh bvpn-ams 'bash /opt/scripts/ams_postgres_luks_unlock.sh'` с ключом из Bitwarden).
- [ ] **`%USERPROFILE%\.ssh\config`** — уже обновлён на `bvpn_lv_ed25519` / `bvpn_ams_ed25519`; проверить: `.\scripts\ssh-smoke-test.ps1`.
- [ ] **Crypto webhook** (если включён) — `CRYPTO_WEBHOOK_SECRET` в `/opt/remna-shop/.env` + callback у провайдера (`docs/RUNBOOK-COMMERCE-GO-LIVE.md` §2).

---

## DNS (P1-RED-DNS-01)

- [ ] Bitwarden: recovery-коды **Dynadot** → `BenderVPN/dns/dynadot-recovery-codes` (+ офлайн).
- [ ] Завести **второй регистратор** (reserve) и item `BenderVPN/dns/reserve-registrar-recovery-codes`.
- [ ] Включить **DNSSEC** для `conntest.xyz` в Dynadot → обновить `ops/dns_critical_inventory.json` (`dnssec_enabled: true`).
- [ ] До массового GTM: **backup apex** на втором регистраторе (`docs/RUNBOOK-DNS-RED-TEAM.md` §3).

---

## Postgres / AMS ops

- [ ] Удалить архивный Docker volume (после 7 дней стабильной работы):  
  `ssh bvpn-ams 'du -sh /var/lib/docker/volumes/remnawave_remnawave-db-data/_data'` → backup off-box → `docker volume rm` (опционально).
- [ ] Накат **compose tmpl** на прод при следующем safe-deploy (`connection_limit`, bind mount уже на проде).

---

## Мониторинг (по желанию)

- [ ] Cron на LV: `dns_delegation_probe.py` раз в час (`docs/RUNBOOK-DNS-RED-TEAM.md` §5).
- [ ] Cron на LV: `remna_credential_broker.py refresh` каждые 30 мин (`docs/RUNBOOK-SHORT-LIVED-CREDS.md`).
- [ ] Telegram-алерт при `DNS_DELEGATION_FAIL` / `POSTGRES_CRYPT_FAIL` (сейчас — ручной smoke).

---

## Продукт / очередь (следующие Q в бэклоге)

| Q | ID | Статус в репо |
|---|-----|----------------|
| 028 | P1-RED-SEC-01 | ✅ broker на LV |
| 029 | P3-RED-MIN-01 | data minimization |
| 030 | P3-RED-JURIS-01 | jurisdiction failover runbook |
| 031 | P5-COM-01 | public status page |

Параллельно (не NEXT): **P4-DNS-01…06** mobile bootstrap.

---

## Быстрые smoke (здоровье)

```powershell
cd d:\Va\projects\VPN
python ops/ssh_audit.py
pwsh -File ops/ssh_audit_from_ams.ps1
ssh bvpn-lv 'python3 /opt/scripts/dns_delegation_probe.py'
ssh bvpn-lv 'python3 /opt/scripts/smoke_short_lived_token_lv.py'
ssh bvpn-ams 'python3 /opt/scripts/ams_postgres_crypt_probe.py'
python ops/smoke_ams_safe_deploy.py
```

Ожидаемые маркеры: **`SSH_AUDIT_OK`**, **`DNS_DELEGATION_OK`**, **`POSTGRES_CRYPT_OK`**, **`AMS_SAFE_DEPLOY_OK`**.
