# AUDIT — Consolidated Risk Map

**Date:** 2026-06-10  
**Mode:** AUDIT-FIRST · read-only synthesis · no prod mutation in this pass  
**Branch:** `product-referral-cabinet-ui-v1`  
**Inputs:** Waves 1–10 audits, live probes 2026-06-10, prior artifacts AUDIT-001/002, APPLY Candidate D

---

## 1. Executive risk posture

| Layer | Posture | One-line |
|-------|---------|----------|
| **VPN profile (Happ)** | **Improved, unproven in field** | Candidate D fixed 6/6 parity + DoH; owner 48h soak pending |
| **VPN (non-Happ clients)** | **Critical gap** | Karing/Clash/v2rayN still LV-direct strip — not Auto-equivalent |
| **Subscription generator** | **High drift risk** | `singbox.generator` off-repo; verify gate had blind spot |
| **Infra edge** | **High SPOF** | LV HTTPS edge; sub-page Caddy health gap; 3010/3011 exposure |
| **Product/backend** | **Pilot-soft OK, scale-red** | Web ref drop, cabinet API gaps, no hard invite/cap/device |
| **Security/CI** | **Manual discipline** | No CI, no gitleaks/pre-commit; snapshots correctly gitignored |
| **Portal UX/copy** | **Mostly safe** | Happ-first truths aligned; referral email claim false |
| **Docs** | **Split canon** | Policy v1 fresh; FAQ/ONBOARDING stale |

---

## 2. Risk register (consolidated)

| ID | Domain | Finding | Severity | Status | Blocks |
|----|--------|---------|----------|--------|--------|
| **R-VPN-01** | VPN soak | Candidate D applied; **manual Happ 48h soak not done** | **P0** | Open | Declaring instability fixed |
| **R-VPN-02** | VPN (was) | 6-selector / 3-outbound skew → reconnect roulette | **P0** | **Mitigated** (D) | — if soak passes |
| **R-VPN-03** | Verify gate | `verify_vpn_balancer_profile.py` green-lit 3-proxy + broken DNS pre-D | **High** | Open | Blind trust in gate alone |
| **R-VPN-04** | Generator | Non-Happ UA → LV direct / no stealth / no DoH parity | **Critical** | Open | Karing primary, multi-client promise |
| **R-VPN-05** | Generator | `singbox.generator.service.js` not in git (AMS mount only) | **High** | Open | Reproducible generator changes |
| **R-VPN-06** | Infra | LV edge HTTPS SPOF; NL jurisdiction ≠ sub edge fix | **High** | Known | Partner/public scale |
| **R-VPN-07** | Infra | Caddy may 502 if one sub-page container dies (no upstream health) | **High** | Open | HA confidence |
| **R-VPN-08** | Infra | Sub backends `0.0.0.0:3010/3011` in compose (CR-01) | **High** | Partial mit | Firewall drift |
| **R-VPN-09** | Autotrim | Selector-only trim; injectHosts shrink is separate ops failure mode | **Medium** | Open | Repeat of pre-D regression |
| **R-VPN-10** | TSPU | Probes green 2026-06-10; ongoing score ~5/10 in backlog | **Low–Med** | Monitor | — |
| **R-PROD-01** | Referral | Web `ref_code` dropped before `issue_web_trial` | **P0** | Open | Honest referral growth |
| **R-PROD-02** | Cabinet | `billing_profile` missing from cabinet API | **P1** | Open | Mini App trial/wallet UX |
| **R-PROD-03** | Policy | Invite-only / 30k cap — copy stronger than enforcement | **P1** | Pilot OK | Public scale |
| **R-PROD-04** | Device | One device = support-only; no HWID enforcement | **P1** | Pilot OK | Fair-use at scale |
| **R-PROD-05** | Referral | Hidden +3d on first legacy purchase if `referred_by` | **P2** | Open | Policy PT-07 |
| **R-PROD-06** | Billing | 6.67 ₽/day core implemented | **Low** | OK | — |
| **R-PROD-07** | Trial | TG 90d / email 1d implemented | **Low** | OK | — |
| **R-SEC-01** | CI | No GitHub Actions / automated checks | **Critical** | Open | Multi-contributor scale |
| **R-SEC-02** | Secrets | No gitleaks/detect-secrets/pre-commit | **High** | Open | Secret leak prevention |
| **R-SEC-03** | Secrets | `vault.env.example` drift (single token vs AMS+LV) | **Medium** | Open | Onboarding |
| **R-SEC-04** | Edge | LV Caddyfile not versioned in repo | **Medium** | Open | Edge change review |
| **R-SEC-05** | Snapshots | `.secrets/snapshots/` gitignored correctly | **Low** | OK | Local disk only |
| **R-UX-01** | Copy | “Referral preserved on email signup” — false | **P0** | Open | Trust |
| **R-UX-02** | Errors route | Was broken (start shell); fixed in repo | **P1** | Fixed | Keep in smoke |
| **R-UX-03** | Docs | FAQ/ONBOARDING pre–policy v1 | **P1** | Open | Support consistency |
| **R-OPS-01** | Support | RUNBOOK-001 support intake open | **P2** | Open | Ops consistency |
| **R-OPS-02** | Admin | No per-user lookup by TG/email/BVPN-ID | **P1** | Open | Support scale |
| **R-OPS-03** | Patch ops | 52 `patch_*` scripts; classification doc-only | **Medium** | Open | Incident repeat |

---

## 3. SPOF and failover map

```
[User RU]
    │
    ▼
[Caddy @ bvpn-lv :8443]  ← R-VPN-06 SPOF
    │
    ├── :3010 sub-page-a ──┐
    └── :3011 sub-page-b ──┤  ← R-VPN-07 (Caddy health gap)
                           ▼
              [Remna panel + templateJson @ AMS]
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   relay#1 ×3       relay#2 ×3         LV/NL exits
   72.56.0.145       46.173.28.252     (out of phase-1 inject)
         │                 │
         └────────┬────────┘
                  ▼
           [Happ Xray client]
           BenderVPN Auto (6 paths post-D)
```

**Non-Happ path (parallel, inferior):** same sub URL → generator strips to **1× LV direct** (R-VPN-04).

---

## 4. Wave summary scores

| Wave | Topic | Grade | Top residual |
|------|-------|-------|--------------|
| **1** | Post-apply stability | **Yellow** | Soak pending; rollback ready |
| **2** | Generator / profile | **Red** (non-Happ) / **Green** (Happ post-D) | UA parity, off-repo JS |
| **3** | Infra / routing | **Yellow** | Edge SPOF, Caddy HA |
| **4** | Security / secrets | **Red** (automation) / **Green** (gitignore) | No CI/scanners |
| **5** | CI/CD supply chain | **Red** | No workflows, no pip-audit gate |
| **6** | Product/backend | **Yellow** | Ref drop, soft enforcement |
| **7** | Admin/support | **Red** | Lookup, ledger, RUNBOOK-001 |
| **8** | QA / journey | **Yellow** | Semantic OK; E2E gaps |
| **9** | Client strategy | **Yellow** | Happ OK post-D; Karing blocked |
| **10** | Docs / release | **Yellow** | Policy fresh; user docs stale |

---

## 5. Candidate D — stability verdict (audit-only)

| Question | Answer |
|----------|--------|
| Did D fix the **known config bug**? | **Yes** (automated): 7353 B, 6 proxies, selector parity, DoH |
| Did D fix **user-reported instability**? | **Unknown** — needs owner Happ soak |
| Rollback ready? | **Yes** — snapshot at `.secrets/snapshots/template-pre-candidate-d-apply-20260609_150159.json` |
| Safe to tell users “refresh Happ”? | **Yes**, after owner confirms soak on at least one device |
| Safe to promise “fixed for everyone”? | **No** — until 48h soak + support ticket trend |

**Live probe 2026-06-10:** `7353 B`, relay#1×3 + relay#2×3, `INJECT_SUB_PARITY_OK`, `dns=yes`.

---

## 6. What is safe / broken / tolerable (summary)

### Safe now (tell users / ops)

- Happ + BenderVPN Auto as primary path; refresh subscription after template change
- Telegram trial ~90 days; email `/setup/` 1 day; 6.67 ₽/day from balance
- Public status URL; support via bot + `/id`
- No referral bonus at MVP
- Candidate D profile shape for **Happ-class clients** (automated verify)

### Broken (do not promise / fix before scale)

- Web referral attribution on email path (R-PROD-01, R-UX-01)
- Cabinet `billing_profile` for Mini App trial/wallet clarity (R-PROD-02)
- Karing/Clash/v2rayN as Auto-equivalent (R-VPN-04)
- FAQ/ONBOARDING vs policy v1 (R-UX-03)

### Risky but tolerable (pilot phase)

- Soft invite-only (organic `/start` allowed per policy)
- 30k badge without enforcement API
- One device = policy/support, not technical block
- Manual deploy/verify gates without CI
- Observatory off (closed-pipe guard)

### Blocks development

- **Hard block:** declaring VPN fixed without soak (R-VPN-01)
- **Hard block:** referral Phase 1 without ref_code fix (R-PROD-01)
- **Hard block:** Karing generator work before audit sign-off (owner constraint)
- **Soft block:** CI absence for multi-agent/multi-dev (R-SEC-01)

### Blocks public / partner scale

- No CI + secret scanning (R-SEC-01/02)
- Admin lookup + referral ledger (R-OPS-02, R-PROD-01)
- Hard invite/cap/device enforcement (R-PROD-03/04)
- Edge SPOF + sub-page HA gap (R-VPN-06/07)
- Support runbook (R-OPS-01)

---

## 7. Related artifacts

| Doc | Role |
|-----|------|
| [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md) | Apply record |
| [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md) | Wave 9 detail |
| [`AUDIT-2026-06-10-VPN-READONLY-PROBES.md`](AUDIT-2026-06-10-VPN-READONLY-PROBES.md) | Wave 3 probes |
| [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) | ID catalog |
| [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) | Policy canon |

---

**Status:** consolidated read-only · **Next:** [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md)
