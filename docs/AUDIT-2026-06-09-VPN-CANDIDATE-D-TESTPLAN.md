# AUDIT — Candidate D VPN Stability Test Plan

**Date:** 2026-06-09
**Status:** **STOPPED — global apply approval required** (test-user-only not possible)
**Prior:** [`AUDIT-2026-06-09-VPN-RELIABILITY.md`](AUDIT-2026-06-09-VPN-RELIABILITY.md), [`AUDIT-2026-06-09-VPN-ARCHITECTURE-DRYRUN.md`](AUDIT-2026-06-09-VPN-ARCHITECTURE-DRYRUN.md)
**Branch:** `product-referral-cabinet-ui-v1` @ `6abdda6` (pushed to origin)

---

## 1. Symptom update (owner report)

| Signal | Detail |
|--------|--------|
| Platforms | **iOS, Android, Windows, Mac** — all affected |
| Networks | **Wi‑Fi and LTE**, different providers |
| Traffic scope | **All traffic** through VPN unstable — not Telegram-only |
| UX pattern | Happ often **shows connected**; pages fail first, work after refresh/retry |
| Frequency | **~once per minute** |
| Sleep/resume | After lock/sleep (especially desktop), network **unusable until reboot** |
| User behavior | Refreshes subscription **constantly** |
| Conflicts | No old VPN / second Happ profile |

### Interpretation

Cross-platform + multi-network + all-traffic + ~1/min retry strongly indicates **service/profile/routing/DNS/outbound defect**, not one bad client.

Aligns with AUDIT-001/002:

- **Selector/outbound mismatch** (`proxy-4`…`proxy-6` referenced, only 3 outbounds) → random picks dead paths → minute-scale failures.
- **relay#2-only SPOF** → no healthy alternate when one path degrades.
- **Missing DoH on live sub** (per verify) → DNS stalls mistaken as disconnect.
- **Sleep/resume** worsens without alternate paths — client resumes into same broken pool.

**Candidate D not applied** — awaiting owner **global template apply** approval.

---

## 2. STEP 0 — Audit docs push

| Check | Result |
|-------|--------|
| `git status` | Only dirty: `.cursor/skills/…`; untracked QA screenshots |
| Audit commits clean | `4d837f1`, `6abdda6` on branch |
| `git push origin product-referral-cabinet-ui-v1` | **Success** `3a9fa73..6abdda6` |

---

## 3. Test-user-only feasibility

### Verdict: **NOT POSSIBLE**

| Evidence | Source |
|----------|--------|
| Single subscription template `REMNA_TEMPLATE_UUID` for all users | `ops/site_urls.py`, all `patch_*` scripts |
| `injectHosts` lives in **global** `templateJson` | Panel API `/api/subscription-templates` |
| One squad; **no per-user host filter** | `BenderVPN_Documentation_v2_5.md` §2 — «Фильтрации хостов по пользователям нет» |
| `probe_users_sub_sample.py` — all sampled users share same proxy count | Verified 2026-06-09 |

**Implication:** Any `--apply` on subscription template changes profile for **every** user on next sub fetch. Cannot isolate one Telegram ID.

**Action taken:** **STOP before apply.** See §10 Global Apply Approval Request.

---

## 4. Pre-apply snapshot (read-only)

**Local snapshot:** `.secrets/snapshots/template-pre-candidate-d-20260609_014010.json` (not committed — contains panel structure)

### Template (current broken state)

| Field | Value |
|-------|-------|
| injectHosts | **3** |
| relay#1 / relay#2 / LV / NL | **0 / 3 / 0 / 0** |
| stealth_split | **true** |
| Intl_Direct selector | 6 tags (`proxy`…`proxy-6`) |
| Intl_Stealth selector | 6 tags |
| catch-all | **Present** → `Intl_Direct` |
| observatory | **false** |
| template DNS | **OK** (no warnings) |

### Live sub (sample user)

| Field | Value |
|-------|-------|
| Size | **5896 B** |
| proxy count | **3** |
| tags present | `proxy`, `proxy-2`, `proxy-3` |
| relay#1 / relay#2 | **0 / 3** |
| **missing selector tags** | **`proxy-4`, `proxy-5`, `proxy-6`** |
| catch-all | `Intl_Direct` |
| live DNS (verify) | **BROKEN** — missing DoH entry |

### Panel capacity (for restore)

| Resource | Count |
|----------|-------|
| relay#1 hosts :443 | **6** available |
| relay#2 hosts :443 | **6** available |
| Pick for Candidate D | **3 + 3** (not all 12) |

---

## 5. Probes run (read-only)

| Command | Result |
|---------|--------|
| `probe_subscription.py` | 5896 B, 3 tcp, relay#2 only, batch OK |
| `diagnose_happ_import.py` | batch_risk=LOW, observatory=NO |
| `probe_injecthosts_sub_parity.py` | injectHosts=3, parity OK (broken but consistent) |
| `verify_vpn_balancer_profile.py` | VPN_BALANCER_PROFILE_OK, **dns=BROKEN**, vless_proxy=3 |
| `probe_users_sub_sample.py --sample 3` | All users 5896 B / 3 proxy |
| `diagnose_speed.py` | WARN: 6-selector random on 3 hosts; dns DoH missing on emitted sub |
| `relay_latency_probe.py` | **FAIL** — SSH keys missing (Windows vantage; **must run from bvpn-lv before apply**) |
| `tspu_block_probe_ru.py` | **Not run** — requires LV SSH; mandatory pre-apply on LV |

---

## 6. Candidate D — exact target profile

| Parameter | Target |
|-----------|--------|
| injectHosts | **6** (relay#1 ×3 + relay#2 ×3, :443 relay LV paths) |
| Live proxies | **6** (`proxy`…`proxy-6`) |
| relay#1 + relay#2 | **Both present** |
| LV/NL direct | **Out** (phase 1) |
| Intl_Stealth selector | `RELAY6_SELECTOR` |
| Intl_Direct selector | `RELAY6_SELECTOR` |
| catch-all | `tcp,udp` → `Intl_Direct` (keep) |
| observatory | **Absent** |
| DNS | `build_split_dns_config()` in templateJson.dns |
| Super_Balancer | **Not restored** (stealth split architecture) |
| Est. sub size | ~7–8 KB |

---

## 7. Patch plan (NOT APPLIED)

### Scripts / approach

| Item | Detail |
|------|--------|
| **New script (to author on approval)** | `ops/patch_restore_6relay_stealth.py` — stealth-safe; does **not** use `patch_trim_injecthosts_relay_only.py` (aborts on stealth split) |
| **Reuse logic from** | `patch_trim_injecthosts_relay_only.py` — `pick_relay_uuids`, `is_relay_lv_host`, `apply_patch` (inject + balancer alignment) |
| **DNS from** | `dns_split_config.build_split_dns_config()` |
| **Guards** | `happ_geosite_guard.py` before/after; `is_stealth_split_profile` must remain true |
| **Writes to** | Remna panel **global** template via `PATCH /api/subscription-templates` |
| **Does NOT touch** | Per-user records, billing, bot, portal, Caddy, Remna users, broadcast |

### Pick logic (dry-run verified)

From full panel hosts (not current 3-host inject):

- Available: 6 relay#1 + 6 relay#2 at :443
- **Target pick: 3 relay#1 + 3 relay#2** (first 3 per IP after sort — same as trim script intent)
- Dry-run full pick returned 12 — apply script **must cap at 3 per relay IP**

### Exact apply command (after owner approval + LV probes)

```bash
# ON bvpn-lv only, after snapshot:
python ops/happ_geosite_guard.py
python ops/relay_latency_probe.py
python ops/tspu_block_probe_ru.py   # or run_tspu_block_probe_ru.sh

python ops/patch_restore_6relay_stealth.py          # dry-run first
python ops/patch_restore_6relay_stealth.py --apply  # owner-approved global apply only
```

*Script `patch_restore_6relay_stealth.py` does not exist yet — create in implementation pass after approval.*

### Post-apply verify

```bash
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
python ops/probe_injecthosts_sub_parity.py
python ops/verify_vpn_balancer_profile.py   # expect vless_proxy=6, dns≠BROKEN
python ops/probe_users_sub_sample.py --sample 5
```

### Rollback

| Step | Command / action |
|------|------------------|
| 1 | Restore `.secrets/snapshots/template-pre-candidate-d-20260609_014010.json` via panel PATCH |
| 2 | Verify 5896 B / 3-proxy state returns |
| 3 | **No** `broadcast_refresh_sub.py` unless owner explicitly orders |
| 4 | Optional: `sub_config_generation` notify only after rollback verified |

---

## 8. Apply status

| Status | Detail |
|--------|--------|
| **Candidate D applied** | **NO** |
| **Reason** | Template patch is **global** — affects all users |
| **Test-user-only** | **Not technically possible** |
| **Next gate** | Owner **GLOBAL APPLY APPROVAL** (§10) |

---

## 9. Test checklist (after global apply + owner refresh)

Use on **owner device first**, then monitor support channel.

### Setup

1. Happ → **Refresh subscription** once (after global template apply propagates).
2. Connect **BenderVPN Auto** only.
3. Confirm sub size ~7–8 KB (not 5896 B).

### 10–15 minute active test

| # | Test | Pass criteria |
|---|------|---------------|
| 1 | General browsing (3–5 sites) | No minute-cycle failures |
| 2 | Telegram (messages + media) | Stable send/receive |
| 3 | Page reload behavior | First load works without retry loop |
| 4 | Wi‑Fi | 10 min stable |
| 5 | LTE (if available) | 10 min stable |
| 6 | Lock/unlock or sleep/resume (desktop) | Traffic resumes **without reboot** |

### Record

- Disconnect count
- «Connected but no traffic» episodes
- DNS errors in Happ log
- Whether reboot still required after sleep
- Sample `access_log` outbound tag changes (flap rate)

### Do not

- Ask user to pick NL/LV manually
- Mass broadcast refresh
- Change billing / registration / referral

---

## 10. GLOBAL APPLY APPROVAL REQUEST

**Required before any `--apply`.**

### 1. Current broken evidence

- All platforms, all traffic, ~1/min failure pattern
- **3 outbounds** vs **6 selector tags** — `proxy-4/5/6` missing on every sampled user
- **relay#2-only** — relay#1 absent despite 6 panel hosts available
- Live DNS verify: **BROKEN** (DoH missing on emitted sub)
- User constant sub refresh — likely chasing profile churn without fix

### 2. Why Candidate D is lowest-risk fix

- **Smallest** change that fixes integrity bug (parity) + SPOF
- Preserves **stealth split** (no gen=20 revert)
- **No observatory** (avoids E1 closed-pipe)
- **No LV/NL direct** (avoids RU direct + ping noise)
- **No 14-host** blast radius

### 3. Exact changes (global template)

1. injectHosts: 3 → **6** (relay#1×3 + relay#2×3)
2. Intl_Stealth + Intl_Direct selectors → **RELAY6_SELECTOR** (aligned)
3. templateJson.dns → **split DoH** (`dns_split_config`)
4. observatory: remain **off**
5. No Super_Balancer, no geosite:ru changes

### 4. Expected impact

| Aspect | Impact |
|--------|--------|
| All users on next sub fetch | New ~7–8 KB profile, 6 relay paths |
| Reconnect / page retry | **Should decrease** if root cause is selector mismatch + SPOF |
| Ping display in Happ | Slightly higher than 1-path (6 relay pings) but **honest** |
| Sleep/resume | **Should improve** with relay#1 fallback |

### 5. Rollback plan

Restore snapshot `template-pre-candidate-d-20260609_014010.json` via panel PATCH. Verify 5896 B profile returns. No broadcast unless ordered.

### 6. No-go conditions (abort apply)

- `happ_geosite_guard.py` fails
- Both relays fail `tspu_block_probe_ru` from LV
- `relay_latency_probe.py` shows both relays dead
- Dry-run would enable observatory
- injectHosts / selector counts still mismatched after dry-run
- Owner does not approve global impact

### 7. Verification plan

1. LV pre-probes (relay + TSPU)
2. Snapshot template
3. Dry-run → owner review diff
4. `--apply` once
5. Verify gate scripts (§7)
6. Owner device 48h soak (§9)
7. Only then consider optional sub refresh notify (not broadcast)

### 8. Why not alternatives

| Alternative | Why not now |
|-------------|-------------|
| **14-host restore (B)** | Reverts stealth split; LV/NL direct RU risk; larger ping noise |
| **Observatory / leastLoad** | E1 closed-pipe history; ~1/min may worsen |
| **NL/LV direct in inject** | NODE-POLICY: verify NL first; increases TSPU exposure |
| **Do nothing** | Profile internally inconsistent; cross-platform symptoms continue |

---

## 11. Next decision

| Option | Owner action |
|--------|--------------|
| **A — Approve global Candidate D** | Reply «approve global Candidate D» → implement `patch_restore_6relay_stealth.py` on **bvpn-lv** with full verify |
| **B — Defer** | Gather Happ logs from affected user first |
| **C — Reject** | Document alternative; remain on broken 3-host profile |

---

## 12. Exact next implementation prompt (after approval only)

> **Global Candidate D apply on bvpn-lv (owner-approved)**
>
> 1. SSH/session on **bvpn-lv** with relay SSH keys.
> 2. `relay_latency_probe.py` + `tspu_block_probe_ru.py` — both relays OK.
> 3. Snapshot template (new timestamp).
> 4. Author + dry-run `ops/patch_restore_6relay_stealth.py`:
>    - 6 injectHosts (3 relay#1 + 3 relay#2)
>    - RELAY6_SELECTOR on Intl_Stealth + Intl_Direct
>    - build_split_dns_config()
>    - observatory off; stealth rules preserved
> 5. `happ_geosite_guard.py` → `--apply` → verify gate.
> 6. Owner device test §9 — 48h.
> 7. **No broadcast.** Optional single-user notify only if owner asks.
>
> **STOP if:** any no-go in §10.6.

---

**Apply status:** NOT APPLIED · **Approval:** PENDING global owner consent
