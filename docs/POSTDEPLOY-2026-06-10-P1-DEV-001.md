# POSTDEPLOY — P1-DEV-001 Active config summary

**Date:** 2026-06-09 ~20:07–20:11 UTC (AMS `20260609-200759`, LV `20260609-201012`)  
**Target:** AMS `168.100.11.140` · **`remna-shop-bot`** · LV **`bvpn-lv`** `/var/www/bvpn-portal/`  
**Approval:** Owner — `approve deploy P1-DEV-001 active config summary`  
**Repo commit deployed:** `2be02f0` — `feat(cabinet): expose active config summary`  
**Branch:** `product-referral-cabinet-ui-v1`  
**Rollback:** Not used (backups available)  
**Related:** [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md) §14.6, [`POSTDEPLOY-2026-06-10-P1-CAB-001.md`](POSTDEPLOY-2026-06-10-P1-CAB-001.md)

---

## 1. Deploy scope (actual)

| File | Host | Action |
|------|------|--------|
| `bot_src/portal_cabinet.py` | AMS host + `remna-shop-bot` container | Updated (`build_configuration_fields`); **restart** after LF normalize |
| `web/portal/assets/portal.js` | LV `/var/www/bvpn-portal/assets/` | Updated (config list render, anomaly/MVP note) |
| `web/portal/content/ru.json` | LV `/var/www/bvpn-portal/content/` | Updated (`configs_*` copy) |
| `web/portal/cabinet.html` | LV `/var/www/bvpn-portal/` | Updated (cache bust `v=28`; unchanged from pre-deploy) |

**Not touched:** Remna panel/users, Caddy config, template PATCH, broadcast, mass-refresh, billing job, DB migration, other bot modules, setup/guide copy outside cabinet block, Semgrep.

---

## 2. Backups / rollback

| Asset | Backup path |
|-------|-------------|
| Backend (host) | `/opt/remna-shop/src/shop_bot/portal_cabinet.py.before-p1-dev-001-20260609-200759` |
| Portal JS | `/var/www/bvpn-portal/assets/portal.js.before-p1-dev-001-20260609-201012` |
| Portal ru.json | `/var/www/bvpn-portal/content/ru.json.before-p1-dev-001-20260609-201012` |
| Portal cabinet.html | `/var/www/bvpn-portal/cabinet.html.before-p1-dev-001-20260609-201012` |

**Rollback (manual):**

```bash
# AMS
cp /opt/remna-shop/src/shop_bot/portal_cabinet.py.before-p1-dev-001-20260609-200759 \
   /opt/remna-shop/src/shop_bot/portal_cabinet.py
docker cp /opt/remna-shop/src/shop_bot/portal_cabinet.py \
   remna-shop-bot:/app/src/shop_bot/portal_cabinet.py
docker restart remna-shop-bot

# LV
cp /var/www/bvpn-portal/assets/portal.js.before-p1-dev-001-20260609-201012 \
   /var/www/bvpn-portal/assets/portal.js
cp /var/www/bvpn-portal/content/ru.json.before-p1-dev-001-20260609-201012 \
   /var/www/bvpn-portal/content/ru.json
cp /var/www/bvpn-portal/cabinet.html.before-p1-dev-001-20260609-201012 \
   /var/www/bvpn-portal/cabinet.html
```

---

## 3. Container / startup

| Check | Result |
|-------|--------|
| `remna-shop-bot` after restart | **running** |
| Flask webhook | **1488** — startup OK |
| Import / traceback in tail logs | **None** |
| `build_configuration_fields` in container file | **Present** |

---

## 4. API smoke (`POST /portal-cabinet` on AMS localhost)

Required fields verified on successful responses:

`billing_profile`, `access_profile`, `is_billable_now`, `next_charge_applicable`, `active_config_count`, `billable_config_count`, `configurations`, `multiple_configs_anomaly`, `support_required_for_extra_configs`, `billing_note_code`, `billing_note`, plus legacy fields from P1-CAB-001.

Per-config safety checks:

- `has_subscription_url` boolean only
- `subscription_url_masked` null
- no full `subscription_url` in list
- `key_id` / `CFG-{id}` label safe for display
- `status` active/expired; `is_primary` / `is_current` on newest active key
- `billable` true only under wallet + single-active rule

Smoke helper: `ops/smoke_p1_dev_001_ams.py` → **`P1_DEV_SMOKE_OK`**

---

## 5. Profile smoke (read-only, no balance/key mutation)

| Profile | Test | Result | Notes |
|---------|------|--------|-------|
| **Legacy / manual** | TG user with 2099 expiry | **PASS** | `billing_profile=legacy`; `active_config_count=1`; primary badge fields; e.g. tid `924498094` |
| **Trial** | Active `-trial@` key | **PASS** | `billing_profile=trial`; `active_config_count=1`; expiry visible; e.g. tid `704254538` |
| **Wallet** | Non-legacy paid user with balance ≥ 6.67 | **NOT TESTED** | No safe wallet candidate in DB sample at deploy time |
| **Expired** | Expired `vpn_keys` row | **NOT TESTED** | No expired-key sample returned by safe query |
| **Multi-key anomaly** | User with >1 active key | **NOT TESTED** | No multi-active sample in DB at deploy time |

**No balances or keys mutated during smoke.**

---

## 6. Portal / Mini App static smoke

| Check | Result |
|-------|--------|
| `GET …/portal/cabinet.html` | **200**; contains `portal.js?v=28` |
| `GET …/portal/assets/portal.js` | **200**; contains `active_config_count`, `configurations`, `configs_mvp_note` |
| `GET …/portal/content/ru.json` | **200**; contains `configs_active_count` |
| No revoke/delete config UI in `portal.js` | **PASS** |
| Interactive Mini App session | **NOT TESTED** (owner visual confirm recommended) |

Public origin checked: `https://k9x2m1.conntest.xyz:8443/portal/…`

---

## 7. Logs / secrets

| Check | Result |
|-------|--------|
| Recent bot logs | No stack traces; no secret values printed |
| Billing job run | **Not run** |
| Remna mutation | **None** |

---

## 8. Residual risks

- **Wallet profile** config list + `billable_config_count` not live-verified on a non-legacy paying user.
- **Expired profile** config list not live-verified (no expired-key sample).
- **Multi-key anomaly UI** not live-verified (no multi-active sample in DB).
- **Mini App** cache: users may need hard refresh / reopen from bot to pick up config panel.
- **`btn-new-device`** remains a bot link (not self-service revoke); aligns with Option A MVP.

---

## 9. Out of scope (unchanged)

- Device revoke/delete (P1-DEV-002)
- Self-service replace device (P1-DEV-003)
- Multi-device billing 6.67 × N (P1-BILL-002)
- Setup copy truth (P2-COPY-DEVICE-001)
- Guide layout (P2-UX-GUIDE-001)
- G2-A TG bind retest

---

## 10. Verdict

**DEPLOY SUCCESS** — P1-DEV-001 live on AMS + LV portal static. Rollback paths documented; not used.

**Next recommended surface (do not start without approval):** **P1-DEV-002 + PROD-004** — support/admin revoke + one-config enforcement.
