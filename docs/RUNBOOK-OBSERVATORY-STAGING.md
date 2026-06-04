# Runbook: observatory staging (VPN-AUD-430-staging)

**NO-GO на прод:** `--apply` без staging A/B и без go/no-go владельца.  
**Probe:** `https://www.gstatic.com/generate_204` (не hicloud — closed-pipe риск).

---

## Scope

- Только **Intl_Stealth** / relay pool (TG/Meta/video).
- **Не** трогать Intl_Direct multipath без отдельного A/B.
- **Не** включать observatory на Happ batch sub без staging.

---

## Dry-run (prod template read-only)

```bash
python ops/patch_observatory_staging.py
```

Ожидание: diff preview или `OBSERVATORY_STAGING_NO_CHANGE`.

---

## Staging A/B (перед prod)

1. Snapshot template: `.secrets/snapshots/template-before-observatory-*`.
2. Patch staging UUID или `--staging-template` copy.
3. 5 users Happ + TG video upload 5 min — нет «closed pipe» / disconnect storm.
4. Rollback snapshot если fail.

---

## Prod apply (только после green staging)

```bash
python ops/patch_observatory_staging.py --apply --confirm-prod
```

Затем: `subscription_config_notify` + gate LV.

---

## Verify

- `python ops/vpn_verify_gate.sh` on LV
- Owner **O-VPN-002**: TG video on LTE
