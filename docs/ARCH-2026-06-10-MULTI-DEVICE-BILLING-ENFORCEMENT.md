# ARCH — Multi-Device Billing & Enforcement Model

**ID:** DEVICE-ARCH-001  
**Date:** 2026-06-10  
**Mode:** architecture audit + decision design · no implementation · no prod mutation  
**Branch:** `product-referral-cabinet-ui-v1`  
**Repo HEAD:** `5865aa0` (1 commit ahead of `origin` @ `c5f5062`)  
**Parent:** [`AUDIT-2026-06-10-USER-LIFECYCLE-SCENARIOS.md`](AUDIT-2026-06-10-USER-LIFECYCLE-SCENARIOS.md), [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md)  
**Owner premise:** Each physical device loads infrastructure like a full user — vague «support-only replacement» is **insufficient** for launch architecture.

**Evidence method:** code + docs + postdeploy only. No Remna PATCH, no config create/revoke, no billing mutation. Status: **CONFIRMED** / **PARTIAL** / **BLOCKED** / **UNKNOWN**.

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **MODEL A** (one tracked config per device, billing × N) | **FEASIBLE** with schema + Remna provisioning refactor + billing change — **not implemented** |
| **MODEL B** (one sub, up to N devices/sessions, block 8th) | **NOT READY** — no proof of per-user device/session enforcement in bot; HWID hints in panel schema only |
| **MODEL C** (unlimited devices, one price) | **REJECTED** — contradicts owner premise and abuse risk |
| **MODEL D** (concurrent session limit only) | **UNKNOWN** — requires Remna/Xray proof; ≠ unique device limit |

**MVP recommendation:** **MODEL A** as **target architecture**. **Immediate stopgap:** one active tracked config, honest copy, support/admin **tracked** replace — then build MODEL A in ordered gates. **Do not** launch paid multi-device on MODEL B without DEVICE-SMOKE Remna proof.

**Billing today:** `6.67 ₽/account/day` fixed — **cannot** accumulate per device. **Target (MODEL A):** `6.67 ₽ × active_billable_device_count/day` after owner approval + BILL-SMOKE pass.

---

## 2. Owner premise

> Each physical device effectively loads infrastructure like a full user.

**Implications:**

| Requirement | Current stack | Gap |
|-------------|---------------|-----|
| Economic honesty | Account-level flat rate | No per-device coefficient |
| Abuse control | Copy-only «one device» | Same sub URL can be imported on many devices undetected |
| Support clarity | «Support-only» without tracked revoke | No admin device tool; manual Remna breaks accounting |
| Launch enforcement | **L0** (policy/copy) | **L0 unacceptable** for paid/open per USER-LIFECYCLE-001 |

---

## 3. Current stack capability (Phase 2 answers)

### 3.1 What is a «config» today?

| Layer | What it is | Evidence |
|-------|------------|----------|
| **App DB `vpn_keys` row** | Tracked config record: `key_id`, `user_id`, `vless_uuid`, `key_email`, `expiry_date` | `database.py` L56–66 |
| **Remna panel user** | Authoritative VPN identity; has `uuid`, `subscriptionUrl`, `expireAt`, `telegramId` | `remnawave_api.create_or_extend_user` |
| **`key_email`** | Unique panel email identifier per row | UNIQUE constraint |
| **Subscription URL** | Panel-derived link imported into Happ | `resolve_subscription_url`, `provision_key` |
| **Physical device** | **Not stored** | No device_id, platform, HWID in shop DB |

**Verdict:** «Config» = **`vpn_keys` row + linked Remna user**. Not the same as physical device unless 1:1 enforced.

### 3.2 Phase 2 checklist

| # | Question | Status | Evidence | Launch implication |
|---|----------|--------|----------|-------------------|
| 1 | Config definition | **CONFIRMED** | §3.1 | Architecture must name all three layers |
| 2 | Store physical devices? | **CONFIRMED NO** | No device table/columns | MODEL A needs schema |
| 3 | Device type (iOS/Android/…)? | **CONFIRMED NO** | Portal device grid = UX only | Optional label in MODEL A |
| 4 | Count same URL imports? | **CONFIRMED NO** | No telemetry in bot | MODEL B/D need Remna proof |
| 5 | Active simultaneous connections? | **PARTIAL** | Panel `onlineAt` / `userTraffic` in `daily-report.sh` — **not in bot** | Cannot show in cabinet today |
| 6 | Remna online in bot code? | **PARTIAL** | Ops scripts only | DEVICE-SMOKE needed |
| 7 | HWID / fingerprint? | **PARTIAL** | `HWIDMaxDevicesExceeded` remark in `patch_subscription_custom_remarks.py` — panel **schema** exists; **bot never sets** `hwidSettings` | MODEL B unproven |
| 8 | Max-device limit configured? | **CONFIRMED NO** in bot | `create_or_extend_user` body has no `deviceLimit` | MODEL B not wired |
| 9 | Block 8th device today? | **CONFIRMED NO** | No enforcement path | MODEL B NOT READY |
| 10 | Message user on block? | **PARTIAL** | Copy exists for HWID exceed in **subscription-settings remarks** — only if panel enforces | Not active |
| 11 | Support revoke single config? | **BLOCKED** | No admin revoke API; `update_key_status_from_server` DELETE on sync miss only | Support-only manual |
| 12 | Support issue tracked new config? | **PARTIAL** | `provision_key` + `add_new_key` exist — **no admin UI**; second device path **not exposed** | Orphan risk if manual Remna |
| 13 | Manual Remna without app DB? | **CONFIRMED BREAKS** | Cabinet uses `vpn_keys`; resolve uses panel TG then keys; orphan = invisible/wrong billing | **Prohibit** manual-only configs |
| 14 | Cabinet multiple keys? | **CONFIRMED** (P1-DEV-001) | `configurations[]`, `multiple_configs_anomaly` | Read-only; no revoke |
| 15 | Billing unit? | **CONFIRMED** per **account** | `charge_daily_balance_if_due(user_id, DAILY_RATE)` once/day; `billable_config_count` max **1** | Not per device |

### 3.3 Critical Remna coupling (MODEL A blocker detail)

`create_or_extend_user` (`remnawave_api.py` L378–408):

- If `telegram_id` is passed and panel user exists → **PATCH existing user** (extend expiry).
- Does **not** create a second panel user for the same Telegram account.

**Implication:** Multiple `vpn_keys` rows with the same `telegram_id` on panel likely share **one** `subscriptionUrl`. True MODEL A needs **one Remna panel user per device config**, with explicit rules:

- Primary device: `telegramId` set.
- Secondary devices: separate `key_email` + panel user; `telegramId` **omitted** or use panel multi-user pattern — **requires Remna API proof** (DEVICE-SMOKE-001).

### 3.4 Same subscription on several devices — today

| Action | What happens |
|--------|--------------|
| User imports same `subscriptionUrl` on phone + laptop | **Both work** — no bot/panel limit in code |
| Backend detects second device | **No** |
| Billing increases | **No** — still 6.67/account/day |
| User notified | **No** |
| 8th device blocked | **No** |

**Status:** **CONFIRMED** — unlimited import of same URL is **de facto allowed**.

---

## 4. Model evaluation

### 4.1 MODEL A — one tracked config per device

**Definition:** Each device gets its own Remna user + `vpn_keys` row; cabinet lists all; billing = `6.67 × active_billable_devices`; support/admin revoke/replace per device; no untracked manual configs.

| Area | Current gap | MVP slice |
|------|-------------|-----------|
| DB schema | No `device_label`, `status`, `billing_enabled`, `revoked_at` | Extend `vpn_keys` or `user_devices` table |
| Remna provision | TG-id merge prevents multi-user | `provision_device_config()` — new panel user per device |
| Cabinet | List read-only (P1-DEV-001) | Add/revoke/replace UX |
| Billing | Account flat rate | `DAILY_RATE × billable_count` — **after BILL-SMOKE + owner approval** |
| Notifications | None for device add | Price impact before confirm |
| Admin | No lookup/revoke | DEVICE-ADMIN-001 |
| Migration | Existing multi-key anomalies | DEVICE-MIGRATE-001 classify |
| Copy/legal | `device_rule` false promise | DEVICE-COPY-001 first |

**Can implement safely now?** **PARTIAL** — design yes; **billing change NO** until BILL-SMOKE; **Remna multi-user per account** needs smoke proof.

**Smallest MVP slice:**

1. DEVICE-COPY-001 — honest copy (no self-service lie).
2. DEVICE-SMOKE-001 — prove Remna can hold N panel users per account.
3. DEVICE-DATA-001 — schema + status enum.
4. DEVICE-ADMIN-001 — support create/revoke/replace **tracked** only.
5. DEVICE-REPLACE-001 — replace = revoke old + create new, same-day no double count.
6. DEVICE-ADD-001 — user add flow **disabled** until DEVICE-BILL-001 approved.
7. DEVICE-BILL-001 — per-device debit (owner + BILL-SMOKE gate).

**Blocked until BILL-SMOKE:** any live per-device charge. **Blocked until owner approval:** pricing coefficient change.

---

### 4.2 MODEL B — one subscription, up to N devices (e.g. 7)

| Proof required | Status | Evidence |
|----------------|--------|----------|
| Remna per-user device limit | **UNKNOWN** | Not in `create_or_extend_user` body |
| HWID per device identity | **PARTIAL** | `hwidSettings` in subscription-settings (archive patch); `HWIDMaxDevicesExceeded` remark | Not configured in prod via bot |
| Happ passes device ID server sees | **UNKNOWN** | Needs DEVICE-SMOKE |
| Distinguish devices with same URL | **UNKNOWN** | Core MODEL B requirement |
| Block 8th **unique** device | **UNKNOWN** | Not proven |
| Block concurrent sessions only | **UNKNOWN** | Different from unique device count |
| Backend query device count | **CONFIRMED NO** | — |
| Cabinet show count | **CONFIRMED NO** | — |
| User notify on block | **PARTIAL** | Remark strings exist if panel enforces |
| Support reset slots | **UNKNOWN** | — |

**Verdict:** **MODEL B — NOT READY / REQUIRES REMNA PROOF.**

Do **not** recommend for launch. If owner insists, run **DEVICE-SMOKE-001** first:

1. Read live `subscription-settings.hwidSettings`.
2. Read sample panel user HWID list API (if exists).
3. Import same sub on 2 lab devices → check panel telemetry.
4. Attempt 8th device on test user with limit=7.

---

### 4.3 MODEL C — unlimited devices, one price

| Criterion | Assessment |
|-----------|------------|
| Owner premise | **Violates** «each device = full user load» |
| Abuse | **High** — subscription sharing |
| Billing | No coefficient |
| Enforcement | L0 only |

**Verdict:** **REJECTED** for paid/open launch.

---

### 4.4 MODEL D — concurrent session limit only

| Criterion | Assessment |
|-----------|------------|
| Feasibility | **UNKNOWN** — Remna/Xray concurrent connection limits not proven in bot |
| vs unique devices | Limiting 2 simultaneous ≠ limiting 7 devices |
| Interim value | Could reduce abuse if proven |
| Launch fit | **Interim only** if MODEL A delayed |

**Verdict:** **PARTIAL / UNKNOWN** — not a substitute for MODEL A; optional add-on after smoke.

---

## 5. Billing architecture (Phase 6)

### 5.1 Current formula

```
daily_charge = DAILY_RATE  (6.67 ₽)  once per UTC day per user_id
if access_profile == "wallet" and BOT_PAYMENTS_LIVE
billable_config_count = 1 iff exactly one active config else 0
panel sync uses keys[0] only
```

**Evidence:** `balance_billing.py`, `portal_cabinet.py` L180–182, L211.

### 5.2 Target formula (MODEL A)

```
daily_rate_per_device = DAILY_RATE  (6.67 ₽)  # owner may revise OD-03
billable_device_count = count(configs where status=active AND billing_enabled=true)
daily_charge = daily_rate_per_device × billable_device_count
idempotency key: daily_balance:{YYYY-MM-DD}  # still one action per account per day, amount = sum
panel sync: per device OR primary device + aggregate expiry policy (TBD)
```

### 5.3 MODEL A billing rules (proposed)

| Case | Rule |
|------|------|
| **Trial** | **Recommend Option 3:** no extra devices during trial; first device only until wallet |
| **Wallet** | Charge per active billable device |
| **Legacy** | `billing_enabled=false` on all configs |
| **Replace same day** | Revoke old + create new → **no net +1** device for that UTC day (owner confirm) |
| **Add mid-day** | **Recommend:** billing_enabled from next UTC day OR prorated from confirm time (owner pick) |
| **Insufficient balance** | **Recommend Option A:** all billable devices suspend together (simpler); partial suspend = Phase 2 |
| **Max devices** | Cap e.g. 5 billable (owner OD-03); over = support |

### 5.4 Why 6.67/account is insufficient

If user adds 3 devices under MODEL A without coefficient change:

- Infra cost ≈ 3× user load.
- Revenue stays 1× → **unsustainable** and **dishonest** if copy promises per-device pricing.

**Silent billing change forbidden** — DEVICE-BILL-001 requires explicit owner approval + user notification + copy update.

---

## 6. Recommended architecture decision (Phase 7)

### Primary: **MODEL A MVP**

**Target state:**

> One **tracked** config per physical device; each config = one Remna panel user + `vpn_keys`/device row; cabinet lists devices with daily cost; billing = **6.67 ₽ × active billable devices**; add/replace/revoke via app only; **no** untracked manual Remna configs; trial = **one device** until wallet proven.

### Stopgap (until MODEL A shipped)

| Item | Action |
|------|--------|
| Enforcement | **One active billable config** per account (policy + code path) |
| Multi-device | **No self-service add** |
| Replace | Support/admin **tracked** revoke + create via DEVICE-ADMIN-001 |
| Copy | DEVICE-COPY-001 **immediately** — remove false self-service |
| Same URL sharing | Document risk; DEVICE-SMOKE measures abuse |

### MODEL B

**Do not implement** until DEVICE-SMOKE proves HWID/device limits on live panel.

---

## 7. Data model proposal (Phase 8)

### 7.1 Option: extend `vpn_keys` → device-aware config

```text
vpn_keys (extended) OR user_devices:
  device_id          → key_id (PK) or new UUID
  user_id            → telegram_id (FK users)
  remna_uuid         → vless_uuid
  key_email          → panel email (unique)
  device_label       → "iPhone", "Ноутбук" (user or support)
  device_type        → enum optional: ios|android|windows|macos|other
  config_status      → active|revoked|replaced|expired|suspended
  billing_enabled    → bool (default true for wallet devices)
  billable_from      → timestamp UTC
  revoked_at         → nullable
  replaced_by_device_id → nullable FK
  created_by         → user|support|system|trial|web_trial
  is_primary         → bool (one primary for TG resolve)
  last_seen_at       → nullable (from panel if available)
  subscription_url_cached → never expose full in cabinet API
```

### 7.2 Source of truth

| Field | Source of truth |
|-------|-----------------|
| Device count / billable | **App DB** `config_status` + `billing_enabled` |
| VPN access | **Remna** `expireAt` per panel user |
| Subscription URL | **Remna** `subscriptionUrl` per panel user |
| Balance | **App DB** `users.balance` |
| Legacy classification | `subscription_profile.is_legacy_manual_panel` |

### 7.3 Migration (design only)

| Cohort | Treatment |
|--------|-----------|
| Single active key | → primary device, `billing_enabled` per profile |
| Multi-key anomaly | → flag `multiple_configs_anomaly`; support classifies; only one `billing_enabled=true` until owner review |
| Legacy long expiry | → `billing_enabled=false` |
| Orphan Remna users | → inventory script (read-only); link or revoke |

---

## 8. UX / API / bot flows (Phase 9)

| Flow | MODEL A behavior | Prerequisite |
|------|------------------|--------------|
| **First device** | Trial/web issues **one** tracked config; cabinet «Устройство 1» | Current trial path + schema |
| **Add device** | «Добавить устройство» → price «+6,67 ₽/день» → confirm → `provision_device` → new row | DEVICE-ADD-001 + DEVICE-BILL-001 |
| **Replace** | «Заменить» → revoke old → new config → no +1 billable if replace not add | DEVICE-REPLACE-001 |
| **Remove** | Revoke → `billing_enabled=false` from next period | DEVICE-REVOKE-001 |
| **Limit reached** | Block add; «Лимит устройств. Удалите старое или напишите в поддержку.» | `max_devices` OD-03 |
| **Same URL copied** | Document: MODEL A = separate configs per device; sharing one URL = policy violation; detection **UNKNOWN** | DEVICE-SMOKE |
| **Trial extra device** | **Block** — «Сначала пополните баланс» | Recommended |
| **Expired** | Block add; existing configs expire with panel | Current |
| **Legacy** | List devices; `billing_enabled=false`; support replace only | Current + schema |

**Bot changes (future):** `menu_get_setup` must distinguish **open existing device setup** vs **add device** (separate callbacks).

**Cabinet API fields (future):**

```text
daily_charge_estimate_rub = DAILY_RATE * billable_device_count
can_add_device: bool
can_replace_device: bool (per row)
can_revoke_device: bool
max_devices: int
devices[]: extended configurations
```

---

## 9. Enforcement levels L0–L5 (Phase 10)

| Level | Description | Current | MODEL A target | MODEL B need |
|-------|-------------|---------|----------------|--------------|
| **L0** | Copy/policy only | **YES** | Insufficient paid | Insufficient |
| **L1** | One tracked config; same URL reuse undetected | **YES** | Stopgap only | — |
| **L2** | Tracked configs + support revoke | **PARTIAL** (list yes, revoke no) | **MVP minimum** | — |
| **L3** | + Remna session/online monitoring | **NO** | Recommended | Optional |
| **L4** | Hard session/device limit | **NO** | Optional add-on | **Required** |
| **L5** | Full unique device identity | **NO** | Ideal long-term | MODEL B core |

**Launch minimum (owner premise):**

| Launch type | Minimum level |
|-------------|---------------|
| F&F | L1 + honest copy |
| Soft launch | **L2** + DEVICE-COPY-001 |
| Paid pilot | **L2** + DEVICE-ADMIN-001 + DEVICE-BILL-001 (if multi-device enabled) |
| Open launch | **L3** + billing proof + abuse monitoring |

**Paid/open with only L0–L1:** **NO-GO**.

---

## 10. Gate matrix (Phase 11)

| Gate | Status | F&F | Soft | Paid | Open | Action |
|------|--------|-----|------|------|------|--------|
| **DEVICE-ARCH-001** | **DONE** (this doc) | — | — | — | — | Owner confirm MODEL A |
| **DEVICE-DATA-001** | **NOT_STARTED** | No | No | Yes | Yes | Schema design |
| **DEVICE-BILL-001** | **BLOCKED** | No | No | **Yes** | **Yes** | After BILL-SMOKE + owner |
| **DEVICE-ADD-001** | **BLOCKED** | No | No | Yes | Yes | After DEVICE-BILL-001 |
| **DEVICE-REPLACE-001** | **NOT_STARTED** | No | **Yes** | Yes | Yes | Admin path first |
| **DEVICE-REVOKE-001** | **NOT_STARTED** | No | Yes | Yes | Yes | With REPLACE |
| **DEVICE-LIMIT-001** | **UNKNOWN** | No | No | Partial | Yes | Remna smoke |
| **DEVICE-ADMIN-001** | **BLOCKED** | No | **Yes** | **Yes** | **Yes** | P1-ADM + device ops |
| **DEVICE-COPY-001** | **NOT_STARTED** | No | **Yes** | **Yes** | **Yes** | COPY-TRUTH-001 |
| **DEVICE-SMOKE-001** | **NOT_STARTED** | No | **Yes** | **Yes** | **Yes** | Same-sub multi-device lab |
| **DEVICE-MIGRATE-001** | **NOT_STARTED** | No | No | Yes | Yes | Classify existing keys |
| **DEVICE-UX-001** | **NOT_STARTED** | No | Partial | Yes | Yes | Cabinet charge display |

---

## 11. Implementation roadmap (Phase 12)

| Order | ID | Objective | Files likely | Deploy? | Prod risk | Prerequisite | Approval |
|-------|-----|-----------|--------------|---------|-----------|--------------|----------|
| 1 | DEVICE-ARCH-001 | Architecture decision | docs | No | None | — | Owner: «approve MODEL A target» |
| 2 | DEVICE-COPY-001 | Honest device copy | `ru.json`, `subscription_resolve.py` | Yes | Low | — | approve deploy COPY-TRUTH-001 |
| 3 | DEVICE-SMOKE-001 | Remna multi-device proof | `ops/smoke_device_*` read-only | AMS/LV read | Low | — | approve DEVICE-SMOKE-001 lab |
| 4 | DEVICE-DATA-001 | Schema + status enum | `database.py`, `schema_migrations.py` | Yes | Medium | ARCH approved | approve DEVICE-DATA-001 schema |
| 5 | DEVICE-ADMIN-001 | Support lookup/revoke/create | `admin_handlers.py`, `remnawave_api.py` | Yes AMS | Medium | DATA-001 | approve DEVICE-ADMIN-001 |
| 6 | DEVICE-REPLACE-001 | Tracked replace flow | handlers, admin | Yes | Medium | ADMIN-001 | approve DEVICE-REPLACE-001 |
| 7 | DEVICE-REVOKE-001 | User/support revoke | portal API, bot | Yes | Medium | REPLACE | approve DEVICE-REVOKE-001 |
| 8 | DEVICE-BILL-001 | Per-device debit | `balance_billing.py`, `portal_cabinet.py` | Yes | **High money** | BILL-SMOKE + owner | approve DEVICE-BILL-001 coefficient |
| 9 | DEVICE-ADD-001 | Self-service add (gated) | handlers, portal, cabinet | Yes | **High** | BILL-001 | approve DEVICE-ADD-001 |
| 10 | DEVICE-UX-001 | Cabinet daily charge UI | `portal.js`, `ru.json` | Yes LV | Low | BILL-001 | approve deploy DEVICE-UX-001 |
| 11 | DEVICE-LIMIT-001 | HWID/session cap | Remna settings, panel | Yes | High | SMOKE proof | approve DEVICE-LIMIT-001 |
| 12 | DEVICE-MIGRATE-001 | Existing key classification | ops script read-only → apply | AMS | Medium | DATA-001 | approve DEVICE-MIGRATE-001 |

**Rollback:** each deploy keeps `.before-device-*` backups per AMS safe deploy pattern.

---

## 12. Owner decisions required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Target model** | A / B / stopgap-only | **MODEL A** target + L2 stopgap |
| 2 | **OD-03 pricing** | 6.67/device vs bundle tiers | **6.67 × N** aligns with current rate |
| 3 | **Trial multi-device** | Allow / block | **Block** until wallet |
| 4 | **Replace vs add billing** | Same-day free replace | **Yes** for replace |
| 5 | **Insufficient balance** | All suspend vs partial | **All suspend** (MVP) |
| 6 | **Max devices cap** | e.g. 3 / 5 / 7 | Owner pick before ADD-001 |
| 7 | **MODEL B investment** | Run DEVICE-SMOKE or abandon | **Smoke first** if B considered |
| 8 | **Manual Remna policy** | Ban untracked configs | **Mandatory** — support runbook |

---

## 13. Explicit NO-GO items

- Enable multi-device **self-service** without DEVICE-BILL-001 + copy update.
- Change billing coefficient **silently**.
- Promise MODEL B «7 devices» in copy before DEVICE-SMOKE PASS.
- Claim HWID enforcement in product UI (PT-06 / policy §6.2).
- Manual Remna user creation without `vpn_keys` row.
- DEVICE-BILL-001 before BILL-SMOKE-001..004.
- Per-device billing during **trial** without owner approval.

---

## 14. What can be done immediately (no money mutation)

1. **DEVICE-COPY-001** — fix `setup.device_rule`, ghost labels.
2. **DEVICE-SMOKE-001** — read-only Remna: `hwidSettings`, same-sub 2-device lab, panel user list fields.
3. **DEVICE-ARCH-001** — owner sign-off on MODEL A (this document).
4. **Support runbook draft** — «manual Remna forbidden; use admin device tool when ready».

---

## 15. What requires prod / Remna proof

| Proof | Test |
|-------|------|
| Second panel user per Telegram account | Create test user with 2 `key_email`, TG id rules |
| HWID limit active | Read `GET /api/subscription-settings` → `hwidSettings` |
| 8th device block | Lab import with limit=7 |
| `onlineAt` per user | Panel API sample → cabinet `last_seen_at` |
| Same URL on 2 phones | Traffic/online indicators differ or not |

---

## 16. References

| Artifact | Role |
|----------|------|
| `bot_src/portal_cabinet.py` | `build_configuration_fields`, `billable_config_count` |
| `bot_src/balance_billing.py` | Daily debit |
| `bot_src/remnawave_api.py` | `provision_key`, TG merge behavior |
| `bot_src/database.py` | `vpn_keys`, `add_new_key` |
| `tests/test_portal_cabinet_billing.py` | billable rules |
| `ops/patch_subscription_custom_remarks.py` | HWID remark strings |
| `POSTDEPLOY-2026-06-10-P1-DEV-001.md` | Config list deployed |

---

**Architecture audit complete.** No implementation. No prod mutation.
