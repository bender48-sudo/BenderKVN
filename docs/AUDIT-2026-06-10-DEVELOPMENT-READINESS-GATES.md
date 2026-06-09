# AUDIT — Development Readiness Gates

**Date:** 2026-06-10  
**Mode:** AUDIT-FIRST · gates only — no implementation  
**Purpose:** Define **go/no-go** conditions before feature development resumes  
**Risk map:** [`AUDIT-2026-06-10-CONSOLIDATED-RISK-MAP.md`](AUDIT-2026-06-10-CONSOLIDATED-RISK-MAP.md)

---

## 1. Gate hierarchy

```
G0  Audit complete (this pass)
G1  Candidate D post-apply verification (owner soak)
G2  Phase 1 product truth (backend matches copy)
G3  Dev infrastructure minimum (CI + secrets scan)
G4  Scale gates (invite/cap/admin/support)
G5  Public/partner scale
```

**Development go/no-go (§10):** **NO-GO** for feature work until **G0 + G1** complete. **Conditional GO** for **G2-scoped** fixes after G1.

---

## 2. G0 — Audit complete ✅

| Check | Status |
|-------|--------|
| Waves 1–10 synthesized | ✅ this pass |
| Consolidated risk map | ✅ |
| Prioritized backlog | ✅ |
| No prod mutation in audit pass | ✅ |
| Candidate D treated as verification, not new dev | ✅ |

---

## 3. G1 — Candidate D post-apply verification

**Status:** **Owner-approved PASS (verbal, 2026-06-09)** before P1-REF-001 AMS deploy. Automated verify PASS. Full per-device 48h soak log **incomplete in repo** — monitoring continues per [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md) §7.

### G1.1 Automated (done — re-run anytime)

| Probe | Pass criteria | Last run |
|-------|---------------|----------|
| `probe_subscription.py` | 7353 B, 6 vless, relay#1+#2 | 2026-06-10 ✅ |
| `probe_injecthosts_sub_parity.py` | injectHosts=6, live=6 | ✅ |
| `verify_vpn_balancer_profile.py` | vless_proxy=6, dns=yes | ✅ |
| `diagnose_happ_import.py` | batch_risk=LOW | ✅ |
| `happ_geosite_guard.py` | OK | ✅ |

### G1.2 Manual Happ checklist (owner)

| # | Test | Pass | Log field |
|---|------|------|-----------|
| 1 | Refresh Happ sub once per device | ☑ (verbal) | sub_bytes ~7353 |
| 2 | Browsing 10–15 min Wi‑Fi | ☑ (verbal) | disconnect_count |
| 3 | LTE 10–15 min (if available) | ☑ (verbal) | |
| 4 | Telegram + Instagram/Google (non-TG only) | ☑ (verbal) | |
| 5 | Sleep/lock/resume desktop | ☑ (verbal) | reboot_required Y/N |
| 6 | No ~1/min retry-without-refresh | ☑ (verbal) | stall_episodes |

**Soak log:** [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md) §7 (verbal PASS; 48h detailed log pending).

### G1.3 Rollback readiness

| Check | Status |
|-------|--------|
| Snapshot exists | ✅ `template-pre-candidate-d-apply-20260609_150159.json` |
| Rollback procedure documented | ✅ APPLY doc §8 |
| No broadcast on rollback | Policy ✅ |

### G1.4 Regression symptoms to watch

- Happ shows connected but pages stall until refresh
- Constant subscription refresh by user
- Minute-scale failure cycle
- Post-sleep network dead until reboot
- DNS errors in Happ log

**G1 pass criteria:** manual checklist complete on ≥1 iOS + ≥1 Android or desktop; disconnect/stall rate **materially lower** than pre-D report; OR explicit owner sign-off to proceed despite residual issues (documented).

---

## 4. G2 — Phase 1 product truth (development unlock)

**May start after G1 pass.** No hard invite gate, no REG-001 schema, no Karing generator.

| Gate | Deliverable | Verify |
|------|-------------|--------|
| **G2-A** | Web `ref_code` → `referred_by` end-to-end | E2E web trial **PASS**; TG bind **FAIL** — `p1bind2-` retest NOT_BOUND; `funnel_bot_start bind:*` = 0 (POSTDEPLOY §9, [`AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md`](AUDIT-2026-06-10-TELEGRAM-BIND-FLOW.md)) |
| **G2-B** | Cabinet API `billing_profile` + trial fields | **P1-CAB-001 deployed 2026-06-09** — [`POSTDEPLOY-2026-06-10-P1-CAB-001.md`](POSTDEPLOY-2026-06-10-P1-CAB-001.md); legacy+trial API PASS; wallet/expired UI spot-check pending |
| **G2-C** | Remove/gate hidden +3d referral purchase bonus | Policy PT-07 |
| **G2-D** | Admin user lookup (TG ID / email hint) | Admin command smoke |
| **G2-E** | Referral ledger export or admin view | Query `referrals` table |
| **G2-F** | Copy honesty sweep | No “ref preserved on email” until G2-A |

**Explicitly out of G2:** Karing generator, portal marketing expansion, billing schema, hard 30k stop.

---

## 5. G3 — Dev infrastructure minimum

**Parallel OK with G2; required before multi-agent default workflow.**

| Gate | Deliverable | Tool |
|------|-------------|------|
| **G3-A** | CI workflow | `.github/workflows/ci.yml` |
| **G3-B** | Secret scan on PR | gitleaks or detect-secrets |
| **G3-C** | Python deps audit | pip-audit on `bot_src/requirements-bot.txt` |
| **G3-D** | Portal static checks | py_compile, `json.tool ru.json`, node --check |
| **G3-E** | Fix `vault.env.example` | AMS + LV token keys |
| **G3-F** | `ops/SCRIPT-SAFETY.md` or generated registry | From AUDIT-001 §3 |

**No Semgrep** per project rule.

---

## 6. G4 — Scale gates (before invite push / 300 configs)

| Gate | Trigger | Deliverable |
|------|---------|-------------|
| **G4-A** | ~300 active configs | Capacity dashboard, organic flag review |
| **G4-B** | Invite push | Hard or soft invite gate implemented |
| **G4-C** | 30k approach | Issuance stop + waitlist UX |
| **G4-D** | Support volume | RUNBOOK-001 complete |
| **G4-E** | Device abuse | HWID or Remna deviceLimit policy |

---

## 7. G5 — Public / partner scale

| Gate | Deliverable |
|------|-------------|
| **G5-A** | CI required checks + branch protection doc |
| **G5-B** | CR-01 sub-port bind 127.0.0.1 + firewall smoke in deploy |
| **G5-C** | Caddy sub-page upstream health or documented failover test |
| **G5-D** | `singbox.generator` in repo or pinned artifact + bump verify |
| **G5-E** | Multi-UA subscription probe in CI |
| **G5-F** | Legal/privacy final review (OD-09) |
| **G5-G** | Karing/sing-box generator parity (if product decision) |

---

## 8. Surface-specific gates

| Surface | May develop after | Must not touch before |
|---------|-------------------|------------------------|
| **Portal copy/UX** | G1 + G2-A honesty | Karing primary copy (owner ban) |
| **Bot billing** | G1 | VPN template PATCH same commit |
| **Referral cabinet UI** | G2-A backend | Promising attribution without data |
| **VPN template** | G1 pass + owner approval | Autotrim/inject without snapshot |
| **Karing generator** | G1 + product decision + G5-G design | Now (explicit owner ban) |
| **Admin tools** | G2-D minimum | — |
| **CI/ops hygiene** | G3 (anytime) | — |

---

## 9. Verification commands (canonical)

```bash
# G1 VPN (read-only)
python ops/probe_subscription.py
python ops/probe_injecthosts_sub_parity.py
python ops/verify_vpn_balancer_profile.py
python ops/diagnose_happ_import.py
python ops/happ_geosite_guard.py

# G1 infra (on bvpn-lv)
python3 relay_latency_probe.py
python3 tspu_block_probe_ru.py

# G3 local (future CI)
python -m py_compile bot_src/*.py ops/*.py
python -m json.tool web/portal/content/ru.json
node --check web/portal/assets/*.js
```

---

## 10. Go / no-go decision matrix

| Decision | Condition |
|----------|-----------|
| **NO-GO — all feature development** | G1 manual soak not started |
| **NO-GO — Karing / generator / guide changes** | Always until G1 + explicit owner scope |
| **NO-GO — public scale marketing** | G4 not met |
| **CONDITIONAL GO — Phase 1 backend fixes** | G1 pass + G2 items only |
| **CONDITIONAL GO — portal polish (no new promises)** | G1 pass + copy honesty |
| **FULL GO — growth features** | G1 + G2 + G4 |
| **FULL GO — partner channel** | G1–G5 |

### Recommended decision (2026-06-10)

> **NO-GO for feature development** until owner completes **G1 manual Happ soak** (15–30 min × 48h watch).  
> **CONDITIONAL GO** immediately after G1 for **G2-A…E only** (referral fix, cabinet API, admin lookup) — single-surface commits, no VPN template changes, no Karing, no guide copy expansion.

---

## 11. Audit wave → gate mapping

| Wave | Primary gate |
|------|--------------|
| 1 Post-apply stability | **G1** |
| 2 Generator | G5-G (later); G1 verify companions |
| 3 Infra routing | G1 probes; G5-C/D |
| 4 Security | **G3** |
| 5 CI/CD | **G3**, G5-A |
| 6 Product/backend | **G2** |
| 7 Admin/support | G2-D/E, G4-D |
| 8 QA journey | G1 smoke + future Playwright |
| 9 Client strategy | After G1; Karing blocked |
| 10 Docs | G2-F; FAQ sync after G2 |

---

**Status:** gates defined · **Backlog:** [`AUDIT-2026-06-10-PRIORITIZED-BACKLOG.md`](AUDIT-2026-06-10-PRIORITIZED-BACKLOG.md)
