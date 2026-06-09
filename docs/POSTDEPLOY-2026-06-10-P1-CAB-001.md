# POSTDEPLOY — P1-CAB-001 Cabinet billing_profile

**Date:** 2026-06-09 ~16:26–16:29 UTC (AMS `20260609-162628`, LV `20260609-162858`)  
**Target:** AMS `168.100.11.140` · **`remna-shop-bot`** · LV **`bvpn-lv`** `/var/www/bvpn-portal/`  
**Approval:** Owner — `approve deploy P1-CAB-001 billing_profile`  
**Repo commit deployed:** `27a39d5` — `feat(cabinet): expose billing profile access state`  
**Rollback:** Not used (backups available)  
**Related:** [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md), [`AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md`](AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md)

---

## 1. Deploy scope (actual)

| File | Host | Action |
|------|------|--------|
| `bot_src/portal_cabinet.py` | AMS host + `remna-shop-bot` container | Updated (`build_billing_fields`) |
| `web/portal/assets/portal.js` | LV `/var/www/bvpn-portal/assets/` | Updated (legacy/trial/wallet/expired render) |
| `web/portal/content/ru.json` | LV `/var/www/bvpn-portal/content/` | Updated (`access_legacy`) |
| `web/portal/cabinet.html` | LV `/var/www/bvpn-portal/` | Updated (cache bust `v=27`) |

**Not touched:** Remna panel/users, Caddy config, template PATCH, broadcast, mass-refresh, billing job, DB migration, other bot modules, setup/guide copy outside cabinet block.

---

## 2. Backups / rollback

| Asset | Backup path |
|-------|-------------|
| Backend (host) | `/opt/remna-shop/src/shop_bot/portal_cabinet.py.before-p1-cab-001-20260609-162628` |
| Portal JS | `/var/www/bvpn-portal/assets/portal.js.before-p1-cab-001-20260609-162858` |
| Portal ru.json | `/var/www/bvpn-portal/content/ru.json.before-p1-cab-001-20260609-162858` |
| Portal cabinet.html | `/var/www/bvpn-portal/cabinet.html.before-p1-cab-001-20260609-162858` |

**Rollback (manual):**

```bash
# AMS
cp /opt/remna-shop/src/shop_bot/portal_cabinet.py.before-p1-cab-001-20260609-162628 \
   /opt/remna-shop/src/shop_bot/portal_cabinet.py
docker cp /opt/remna-shop/src/shop_bot/portal_cabinet.py \
   remna-shop-bot:/app/src/shop_bot/portal_cabinet.py
docker restart remna-shop-bot

# LV
cp /var/www/bvpn-portal/assets/portal.js.before-p1-cab-001-20260609-162858 \
   /var/www/bvpn-portal/assets/portal.js
cp /var/www/bvpn-portal/content/ru.json.before-p1-cab-001-20260609-162858 \
   /var/www/bvpn-portal/content/ru.json
cp /var/www/bvpn-portal/cabinet.html.before-p1-cab-001-20260609-162858 \
   /var/www/bvpn-portal/cabinet.html
```

---

## 3. Container / startup

| Check | Result |
|-------|--------|
| `remna-shop-bot` after restart | **running** |
| Flask webhook | **1488** — startup OK |
| Import / traceback in tail logs | **None** |
| `build_billing_fields` in container file | **Present** |

---

## 4. API smoke (`POST /portal-cabinet` on AMS localhost)

Required fields verified on successful responses:

`billing_profile`, `access_profile`, `is_billable_now`, `next_charge_applicable`, `access_expires_at`, `access_expires_at_iso`, `billing_note_code`, `billing_note`, `billing_note_text`, `active_config_count`, `billable_config_count`, `legacy_manual_access`, plus legacy fields `balance_rub`, `days_left`, `daily_rate`.

Smoke helper: `ops/smoke_p1_cab_001_ams.py` → **`P1_CAB_SMOKE_OK`**

---

## 5. Profile smoke (read-only, no balance/key mutation)

| Profile | Test | Result | Notes |
|---------|------|--------|-------|
| **Legacy / manual** | TG users with 2099 expiry | **PASS** | `billing_profile=legacy`; note includes «Баланс сохранён и сейчас не списывается»; e.g. tid `924498094`, `165870920` |
| **Trial** | Active `-trial@` keys, TG id > 0 | **PASS** | `billing_profile=trial`; note «Пробный доступ активен до …»; e.g. tid `704254538`, `1141323331` |
| **Wallet** | Non-legacy paid user | **NOT TESTED** | Only wallet-balance candidate in sample was owner legacy account (correctly `legacy`, not `wallet`) |
| **Expired** | Expired `vpn_keys` row | **NOT TESTED** | No expired keys returned by safe DB sample query at deploy time |

**No balances or keys mutated during smoke.**

---

## 6. Portal / Mini App static smoke

| Check | Result |
|-------|--------|
| `GET …/portal/cabinet.html` | **200**; contains `portal.js?v=27` |
| `GET …/portal/assets/portal.js` | **200**; contains `billing_note_text`, `billing_profile` handling |
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

- **Wallet profile UI** not live-verified on a non-legacy paying user (classification code deployed; await real wallet account or owner spot-check after top-up user opens cabinet).
- **Expired profile UI** not live-verified (no expired-key sample in DB at deploy time).
- **Mini App** cache: users may need hard refresh / reopen from bot to pick up `v=27`.
- **G2-A TG bind** remains separate gate (unchanged by this deploy).

---

## 9. Out of scope (unchanged)

- P1-DEV-001 — `active_configs[]` / masked URLs
- Device revoke/delete
- Multi-device billing (6.67 × N)
- Setup copy truth (P2-COPY-DEVICE-001)
- Guide layout (P2-UX-GUIDE-001)

---

## 10. Verdict

**DEPLOY SUCCESS** — P1-CAB-001 live on AMS + LV portal static. Rollback paths documented; not used.

**Next recommended surface (do not start without approval):** **P1-DEV-001** — read-only active config count/list.
