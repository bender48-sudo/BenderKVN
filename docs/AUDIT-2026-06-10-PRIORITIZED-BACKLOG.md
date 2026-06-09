# AUDIT — Prioritized Development Backlog (post-audit)

**Date:** 2026-06-10  
**Mode:** AUDIT-FIRST · planning only — no implementation in this pass  
**Gates:** [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md)  
**Risk map:** [`AUDIT-2026-06-10-CONSOLIDATED-RISK-MAP.md`](AUDIT-2026-06-10-CONSOLIDATED-RISK-MAP.md)

---

## 1. Priority tiers

| Tier | When | Theme |
|------|------|-------|
| **T0** | Now (owner) | G1 Happ soak + soak log |
| **T1** | Immediately after G1 pass | Product truth fixes (G2) |
| **T2** | Parallel after G1 | Dev hygiene (G3) |
| **T3** | After G2 stable | QA automation + docs sync |
| **T4** | After soak + metrics | VPN hardening (verify gate, generator in repo) |
| **T5** | Pre-scale (~300 configs) | Invite/cap/admin (G4) |
| **T6** | Deferred | Karing generator, REG-001, native app |
| **T-ROLL** | If G1 fails | Candidate D rollback |

---

## 2. Backlog items (prioritized)

### T0 — Owner verification (not dev)

| ID | Task | Owner | Done when |
|----|------|-------|-----------|
| **SOAK-001** | Happ refresh + 15–30 min active test per platform | Owner | Checklist §G1.2 complete |
| **SOAK-002** | 48h watch: disconnect/stall/support tickets | Owner | Log in APPLY doc or ticket note |
| **SOAK-003** | Decision: D solved primary instability Y/N | Owner | Signed note in APPLY §9 |

### T-ROLL — Rollback (only if G1 fails)

| ID | Task | Surface | Done when |
|----|------|---------|-----------|
| **ROLL-001** | Restore `template-pre-candidate-d-apply-20260609_150159.json` | VPN template | 5896 B / 3-proxy verify |
| **ROLL-002** | Document rollback reason + symptom persistence | docs | APPLY addendum |

### T1 — Phase 1 product truth (first development)

| ID | Maps to | Task | Surface | Effort |
|----|---------|------|---------|--------|
| **P1-REF-001** | PROD-003, R-PROD-01 | Wire `ref_code` webhook → `issue_web_trial` → `link_referral` | bot + webhook | S |
| **P1-CAB-001** | R-PROD-02 | Add `billing_profile`, trial expiry to `portal_cabinet.py` | bot API | S |
| **P1-REF-002** | R-PROD-05 | Remove or gate +3d referral purchase bonus | bot billing | S |
| **P1-ADM-001** | DEC-IMPL-007 | Admin lookup: TG ID → user/keys/balance/referrer | bot admin | M |
| **P1-ADM-002** | DEC-IMPL-006 | Referral ledger admin view or export | bot admin | M |
| **P1-COPY-001** | R-UX-01 | Fix setup copy until P1-REF-001 ships | portal ru.json | S |

**Commit rule:** one ID per commit; no VPN template in same commit.

### T2 — Dev infrastructure (parallel)

| ID | Maps to | Task | Surface | Effort |
|----|---------|------|---------|--------|
| **P2-CI-001** | R-SEC-01 | Minimal `.github/workflows/ci.yml` | ops | M |
| **P2-CI-002** | R-SEC-02 | gitleaks or detect-secrets in CI | ops | S |
| **P2-CI-003** | R-SEC-02 | pip-audit on bot requirements | ops | S |
| **P2-SEC-001** | R-SEC-03 | Fix `.secrets/vault.env.example` (AMS+LV tokens) | docs/secrets | S |
| **P2-OPS-001** | R-OPS-03 | Publish `ops/SCRIPT-SAFETY.md` from audit taxonomy | docs | S |
| **P2-OPS-002** | R-VPN-03 | Harden `verify_vpn_balancer_profile`: fail on inject≠proxy count | ops | S |

### T3 — QA + docs (after T1 starts)

| ID | Task | Surface | Effort |
|----|------|---------|--------|
| **P3-QA-001** | Playwright: errors route regression | portal | S |
| **P3-QA-002** | Playwright: email signup + ref preservation (post P1-REF-001) | portal+bot | M |
| **P3-QA-003** | Playwright: Mini App cabinet billing_profile (post P1-CAB-001) | portal | M |
| **P3-DOC-001** | Sync FAQ + ONBOARDING from PRODUCT-POLICY §2 | docs | M |
| **P3-DOC-002** | RUNBOOK-001 support intake | docs | M |
| **P3-DOC-003** | README links to June 2026 product canon | docs | S |
| **P3-DOC-004** | User-safe claims sheet for support (from policy PT-*) | docs | S |

### T4 — VPN ops hardening (after G1 pass)

| ID | Maps to | Task | Surface | Effort |
|----|---------|------|---------|--------|
| **P4-VPN-001** | R-VPN-05 | Vendor `singbox.generator` patch into repo + AMS sync doc | ops+AMS | M |
| **P4-VPN-002** | R-VPN-09 | Document injectHosts vs autotrim separation in runbook | docs | S |
| **P4-VPN-003** | — | Commit `ops/patch_restore_6relay_stealth.py` (was apply-only local) | ops | S |
| **P4-VPN-004** | R-VPN-09 | Multi-UA subscription probe script (Happ/Karing/Clash/v2rayN) | ops | M |

### T5 — Scale (before invite push)

| ID | Maps to | Task | Effort |
|----|---------|------|--------|
| **P5-SCL-001** | PROD-002 | Capacity read API + honest badge | M |
| **P5-SCL-002** | DEC-IMPL-015 | Invite gate (phase 4) | L |
| **P5-SCL-003** | DEC-IMPL-008 | Waitlist + admin approve | L |
| **P5-SCL-004** | PROD-004 | Device limit enforcement research + implement | L |
| **P5-SCL-005** | DEC-IMPL-010 | Trial 90→30 switch at ~300 configs | M |

### T6 — Explicitly deferred (owner ban in audit pass)

| ID | Task | Blocker |
|----|------|---------|
| **P6-KAR-001** | Karing sing-box generator parity | G1 + product decision + G5-G |
| **P6-KAR-002** | Portal Karing download/copy | P6-KAR-001 |
| **P6-REG-001** | REG-001 phone/email bot onboarding | AUDIT-004 design |
| **P6-NAT-001** | Native app (Q053) | Owner go/no-go |

---

## 3. Recommended commit order

| Order | Commit scope | Gate |
|-------|--------------|------|
| 0 | `docs/audit: consolidate product readiness and development gates` | G0 ✅ |
| — | **Wait for owner G1 soak** | G1 |
| 1 | `fix(bot): wire web ref_code to referral attribution` (P1-REF-001) | G2-A |
| 2 | `fix(bot): expose billing_profile in cabinet API` (P1-CAB-001) | G2-B |
| 3 | `fix(bot): remove hidden referral purchase bonus` (P1-REF-002) | G2-C |
| 4 | `feat(bot): admin user lookup by telegram id` (P1-ADM-001) | G2-D |
| 5 | `feat(bot): admin referral ledger view` (P1-ADM-002) | G2-E |
| 6 | `fix(portal): honest referral copy after backend fix` (P1-COPY-001) | G2-F |
| 7 | `ci: minimal lint and secret scan` (P2-CI-001…003) | G3 |
| 8 | `fix(ops): fail verify gate on inject/outbound skew` (P2-OPS-002) | G3 |
| 9 | `ops: add patch_restore_6relay_stealth to repo` (P4-VPN-003) | G1 pass |
| 10 | `docs: sync FAQ and onboarding to policy v1` (P3-DOC-001) | After T1 |
| 11 | `test(portal): journey Playwright smoke` (P3-QA-*) | After T1 |

**Never mix:** portal + bot + VPN template + docs in one commit.

---

## 4. Recommended first development surface

**After G1 pass:** **`bot_src/` + `webhook_server/`** — **P1-REF-001** (web referral attribution).

**Why first:**

- P0 product-promise breach (R-PROD-01)
- Smallest blast radius vs VPN infra
- Unblocks honest portal copy and referral cabinet work later
- No schema migration required

**Second:** **`portal_cabinet.py` API** — P1-CAB-001 (Mini App trust).

**Do not start with:** Karing generator, portal marketing, VPN template, billing schema, referral UI polish before P1-REF-001.

---

## 5. Final audit answers (deliverable checklist)

### 1. What is safe now

- Happ primary path; BenderVPN Auto; refresh sub after global template change
- Automated Candidate D profile for Happ (6 relay, DoH, parity) — live probes 2026-06-10
- Telegram 90d trial; email 1d; 6.67 ₽/day billing core
- Portal primary copy (90d/1d, Auto, Happ-first) on live semantic audit
- Rollback snapshot ready; no broadcast applied
- Infra probes green (relay + TSPU from LV)

### 2. What is broken

- Web email referral attribution (ref_code dropped)
- Cabinet API missing `billing_profile` for trial/wallet UI
- Non-Happ clients (Karing/Clash/v2rayN) not Auto-equivalent
- FAQ/ONBOARDING vs policy v1
- No CI / automated secret scanning
- Admin user lookup + referral ledger missing
- “Referral preserved on email signup” copy false

### 3. What is risky but tolerable (pilot)

- Candidate D stability unconfirmed until owner soak
- Soft invite-only; 30k badge without enforcement
- One device = policy not HWID
- Manual deploy gates without CI
- verify gate historically permissive (mitigate with parity probe)
- Observatory off by design
- Hidden +3d referral bonus in legacy purchase path

### 4. What blocks development

- **G1:** owner Happ soak not complete → **NO-GO all feature dev**
- Owner explicit ban: Karing generator, guide copy, portal product changes during audit-first mode

### 5. What blocks public/partner scale

- G4/G5 gates: invite/cap enforcement, admin tooling, support runbook
- CI + branch protection absent
- Edge SPOF + sub HA gaps
- Legal final review deferred
- Multi-client generator parity

### 6. What can be developed only after soak

- Any claim that VPN instability is fixed
- Referral/cabinet **marketing** expansion
- NL/LV phase-2 injectHosts
- Karing strategy implementation
- Mass sub refresh notify (even optional)

### 7. What can be developed immediately after audit (after G1)

- P1-REF-001 … P1-ADM-002 (G2 product truth)
- P2-CI-* (G3 hygiene) in parallel
- P2-OPS-002 verify gate hardening
- P4-VPN-003 commit patch script to repo

### 8. Recommended commit order

See §3 above.

### 9. Recommended first development surface

**Bot webhook + `portal_web_trial.py` + `web_referral.py`** — web referral attribution (P1-REF-001).
**AMS deploy (after G1 + approval):** `ops/deploy-portal-web-trial-ams.ps1` — see [`DEPLOY-P1-REF-001.md`](DEPLOY-P1-REF-001.md).

### 10. Explicit go/no-go for development

| Verdict | Scope |
|---------|--------|
| **NO-GO** | All feature development until **G1 owner Happ soak** complete |
| **NO-GO** | Karing generator, user-facing guide changes, portal copy expansion (current owner constraints) |
| **CONDITIONAL GO** | After G1: **G2-only** backend fixes (referral, cabinet API, admin lookup) — one surface per commit |
| **NO-GO** | Public/partner scale until G4–G5 |

---

## 6. Audit wave completion status

| Wave | Status | Artifact |
|------|--------|----------|
| 1 Post-apply stability | **Complete (auto); soak pending** | APPLY doc, risk map §5 |
| 2 Generator | **Complete** | CLIENT-APP-COMPATIBILITY, risk R-VPN-04/05 |
| 3 Infra routing | **Complete** | READONLY-PROBES, risk map §3 |
| 4 Security | **Complete** | risk R-SEC-* |
| 5 CI/CD | **Complete** | gates G3 |
| 6 Product/backend | **Complete** | backlog T1 |
| 7 Admin/support | **Complete** | backlog P1-ADM-* |
| 8 QA journey | **Complete** | backlog P3-QA-* |
| 9 Client strategy | **Complete** | CLIENT-APP-COMPATIBILITY |
| 10 Docs release | **Complete** | backlog P3-DOC-* |

---

## 7. Suggested owner next actions

1. Run **G1.2 manual Happ checklist** on phone + desktop; log results.
2. If stable → approve **CONDITIONAL GO** for P1-REF-001.
3. If unstable → **ROLL-001** and capture Happ logs before re-architecting.
4. Do **not** start Karing or guide work until explicit new scope.

---

**Status:** backlog prioritized · **Commit:** docs only with risk map + gates trio
