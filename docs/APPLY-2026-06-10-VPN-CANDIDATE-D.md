# APPLY — Candidate D VPN Stability Rollout

**Date:** 2026-06-10  
**Approval:** owner «approve global Candidate D»  
**Mode:** controlled global template apply · no deploy · no broadcast · no mass-refresh  
**Branch:** `product-referral-cabinet-ui-v1` @ `f27e87b` (+ local apply artifacts)  
**Script:** `ops/patch_restore_6relay_stealth.py`  
**Prior audits:** [`AUDIT-2026-06-10-VPN-READONLY-PROBES.md`](AUDIT-2026-06-10-VPN-READONLY-PROBES.md), [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md)

---

## 1. Pre-apply confirmation

| Check | Result |
|-------|--------|
| Branch | `product-referral-cabinet-ui-v1` |
| HEAD includes audit docs | `f27e87b` docs(audit): compare VPN clients and final read-only probes |
| Working tree | Dirty: `.cursor/skills/…` only; apply artifacts in `.secrets/snapshots/` (not committed) |
| Owner approval | **Received** |

---

## 2. Rollback snapshots (local, not in git)

| Artifact | Path |
|----------|------|
| **Template (pre-apply, full API response)** | `.secrets/snapshots/template-pre-candidate-d-apply-20260609_150128.json` |
| **Template (apply-time snapshot from patch script)** | `.secrets/snapshots/template-pre-candidate-d-apply-20260609_150159.json` |
| **Live sub sample (pre, Happ UA)** | `.secrets/snapshots/sub-pre-candidate-d-apply-20260609_150128.json` |
| **Pre state summary** | `.secrets/snapshots/candidate-d-pre-state-20260609_150128.json` |
| **Live sub sample (post, Happ UA)** | `.secrets/snapshots/sub-post-candidate-d-apply-20260609_150212.json` |
| **Post state summary** | `.secrets/snapshots/candidate-d-post-state-20260609_150212.json` |

### Pre-apply baseline

| Metric | Value |
|--------|-------|
| Sub size | **5896 B** |
| injectHosts | **3** (relay#2 only) |
| vless proxies | **3** |
| Balancer selectors | **6 tags** each (`proxy`…`proxy-6`) |
| Missing outbound tags | **`proxy-4`, `proxy-5`, `proxy-6`** |
| Live DNS | **BROKEN** (DoH missing) |

---

## 3. Pre-apply gates (read-only)

| Gate | Result |
|------|--------|
| `happ_geosite_guard.py` | **HAPP_GEOSITE_GUARD_OK** |
| `relay_latency_probe.py` (bvpn-lv) | **RELAY_LATENCY_PROBE_OK** |
| `tspu_block_probe_ru.py` (bvpn-lv) | **TSPU_BLOCK_PROBE_RU_OK** |

---

## 4. Dry-run summary

**Command:** `python ops/patch_restore_6relay_stealth.py`

| Change | Before | After |
|--------|--------|-------|
| injectHosts | 3 | **6** (relay#1×3 + relay#2×3) |
| Intl_Stealth selector | 6 tags (3 dead) | **RELAY6** aligned |
| Intl_Direct selector | 6 tags (3 dead) | **RELAY6** aligned |
| DNS | template partial / live broken | **split DoH** (`build_split_dns_config`) |
| Observatory | off | **off** (unchanged) |
| Super_Balancer | absent | **absent** |
| LV/NL direct inject | out | **out** |
| Routing rules | 7 stealth split rules | **unchanged** |

**Relay pick (3 per IP, :443):**

| UUID (prefix) | Host | IP |
|---------------|------|-----|
| `131c6720…` | Relay LV · Ozon | 72.56.0.145 |
| `1ae0b3e4…` | Relay LV · VK | 72.56.0.145 |
| `88f34942…` | Relay LV · X5 | 72.56.0.145 |
| `dbe9c16a…` | Relay2 LV · Ozon | 46.173.28.252 |
| `6edf3aef…` | Relay2 LV · VK | 46.173.28.252 |
| `52645dd4…` | Relay2 LV · X5 | 46.173.28.252 |

**Dry-run verify:** inject=6, selectors=RELAY6, DoH, stealth split, no observatory — **OK**

---

## 5. Apply

**Command:** `python ops/patch_restore_6relay_stealth.py --apply`  
**When:** 2026-06-09 ~15:01 UTC (local admin workstation, panel API PATCH)  
**Target:** global `REMNA_TEMPLATE_UUID` subscription template  
**Sub-config generation:** bumped to **102** (`patch_restore_6relay_stealth`) — **AMS notify skipped** (no Telegram broadcast)

**Output:** `CANDIDATE_D_APPLY_OK` · post-verify `VPN_BALANCER_PROFILE_OK`

---

## 6. Post-apply verification (automated)

| Probe | Result |
|-------|--------|
| `probe_subscription.py` | HTTP 200, **7353 B** (+1457 B vs baseline), **6** vless tcp, relay#1×3 + relay#2×3 |
| `diagnose_happ_import.py` | batch_risk=**LOW**, 6 parseable proxies, observatory=NO |
| `probe_injecthosts_sub_parity.py` | injectHosts=**6**, live=**6**, **INJECT_SUB_PARITY_OK** |
| `verify_vpn_balancer_profile.py` | relay-only×6, vless_proxy=**6**, dns=**yes**, **VPN_BALANCER_PROFILE_OK** |
| `probe_users_sub_sample.py --sample 5` | all **7353 B / 6 proxy**, **SUB_SAMPLE_VERIFY_OK** |
| `diagnose_speed.py` | injectHosts=**6**, split DNS OK, observatory absent; 1 benign WARN (catch-all detector false positive — `probe_routing` confirms R6 → Intl_Direct) |
| `happ_geosite_guard.py` | **HAPP_GEOSITE_GUARD_OK** |
| `probe_routing.py` | 7 rules, catch-all R6 → Intl_Direct, 6 proxy outbounds, split DNS 4 servers |

### Live sub parity (post)

| Field | Value |
|-------|-------|
| Sub size | **7353 B** (was 5896 B) |
| VLESS proxies | **6** |
| relay#1 `72.56.0.145` | **3** (`proxy`, `proxy-2`, `proxy-3`) |
| relay#2 `46.173.28.252` | **3** (`proxy-4`, `proxy-5`, `proxy-6`) |
| Intl_Stealth selector | `proxy`…`proxy-6` — **all exist** |
| Intl_Direct selector | `proxy`…`proxy-6` — **all exist** |
| DoH | **present** (dns_errors=[]) |
| 6-selector/3-outbound skew | **resolved** |
| Observatory | absent |
| LV/NL direct in inject | **0** (unchanged) |

---

## 7. Manual Happ test plan (15–30 min)

**Agent environment:** automated probes only — **no physical iOS/Android/Windows/macOS Happ session** in this apply pass.

| # | Test | Status | Notes |
|---|------|--------|-------|
| 1 | Refresh Happ sub once | **Owner PASS** (verbal, pre–P1-REF deploy) | Owner refreshed **BenderVPN Auto** before AMS bot deploy 2026-06-09 |
| 2 | Confirm ~7353 B sub size | **Auto-verified** | Live fetch post-apply; remained healthy at deploy time |
| 3 | General browsing 15–30 min | **Owner PASS** (verbal) | Wi‑Fi + LTE per owner sign-off; no severe regression reported |
| 4 | Telegram + non-TG traffic | **Owner PASS** (verbal) | No connected-but-need-refresh symptom reported |
| 5 | Sleep/lock/resume (desktop) | **Owner PASS** (verbal, where tested) | Primary symptom area — no reboot-required reported |
| 6 | No minute-cycle refresh loop | **Owner PASS** (verbal, at deploy gate) | Full **48h** metric log not written in repo at deploy time |

### G1 closure note (2026-06-09)

- **Gate:** Owner approved **G1 Candidate D soak PASS** verbally before AMS deploy **P1-REF-001** (phrase: `G1 Candidate D soak PASS. approve AMS deploy P1-REF-001`).
- **Automated Candidate D health at deploy:** sub **7353 B**, **6** proxies (relay#1 + relay#2), **INJECT_SUB_PARITY_OK**, **dns=yes**, no broadcast, no mass-refresh.
- **Limitation:** Per-device soak log (platform, exact durations, disconnect counts) was **not fully written in repo** at deploy time. Treat as **owner-approved PASS with monitoring continuation**, not a closed 48h field soak.
- **Follow-up:** Continue **24–48h** watch for reconnect loops, sleep/resume stalls, and “connected but sites need refresh” regressions. Append detailed device rows here if issues appear.

**Owner action (ongoing):** On each device → Happ → refresh 🔄 on **BenderVPN Auto** if sub size drifts; see §9 checklist in [`AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md`](AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md).

---

## 8. Rollback

### Restore pre-apply template

1. Use snapshot: `.secrets/snapshots/template-pre-candidate-d-apply-20260609_150159.json`
2. PATCH `/api/subscription-templates` with full template body (same pattern as patch scripts — `templateJson` from snapshot).
3. Verify baseline returns: **5896 B**, 3 proxy, dns=BROKEN skew state.
4. **Do not** run `broadcast_refresh_sub.py` unless owner explicitly orders.

Example (from repo root, with panel token):

```bash
# Dry-run inspect only — use panel_client or dedicated restore script with owner approval
python -c "
import json, sys
from pathlib import Path
sys.path.insert(0,'ops')
from panel_client import PanelClient
import site_urls
snap = Path('.secrets/snapshots/template-pre-candidate-d-apply-20260609_150159.json')
tpl = json.loads(snap.read_text(encoding='utf-8'))
c = PanelClient(timeout=120)
body = {'uuid': tpl['uuid'], 'templateJson': tpl['templateJson'],
        'viewPosition': tpl.get('viewPosition'), 'templateType': tpl.get('templateType')}
# code, _ = c.patch('/api/subscription-templates', body=body)  # uncomment only for rollback
print('rollback payload ready from', snap)
"
```

---

## 9. 48h soak

| Criterion | Status |
|-----------|--------|
| Automated verify gate | **PASS** |
| Global template applied | **YES** |
| Broadcast / mass refresh | **NO** (generation 102 local only) |
| Owner device manual test | **Owner PASS (verbal, 2026-06-09)** — **48h field soak log incomplete**; continue monitoring per §7 |

---

## 10. Scope honored

| Constraint | Status |
|------------|--------|
| 6 relay injectHosts (3+3) | Applied |
| Selectors aligned RELAY6 | Applied |
| DoH restored on live sub | Verified |
| Observatory off | Verified |
| LV/NL direct out | Verified |
| geosite:ru unchanged | Verified (geosite guard OK) |
| No Super_Balancer | Verified |
| No 14-host restore | Verified |
| No deploy | Honored |
| No broadcast | Honored (AMS notify skipped) |
| No mass-refresh | Honored |
| No guide/Karing copy changes | Honored |

---

## 11. Files touched (this apply pass)

| File | Action |
|------|--------|
| `ops/patch_restore_6relay_stealth.py` | **Created** (local; implement script for Candidate D) |
| Remna global template (`REMNA_TEMPLATE_UUID`) | **PATCH applied** |
| `.secrets/sub_config_generation.json` | generation → 102 |
| `.secrets/snapshots/*candidate-d*` | Pre/post snapshots |
| `docs/APPLY-2026-06-10-VPN-CANDIDATE-D.md` | This report |

---

**Apply status:** **COMPLETE (automated verify)** · **Manual soak:** pending owner devices · **Push:** not requested
