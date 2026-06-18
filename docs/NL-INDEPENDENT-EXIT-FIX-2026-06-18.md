# NL Independent Exit Fix — 2026-06-18

**Task:** NL-INDEPENDENT-EXIT-FIX-001  
**Status:** **FAIL_PROFILE_ROUTING_PROTOCOL → WAITING_RETEST** (corrected profiles generated locally)  
**Companion:** [`NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md`](NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md)

> Repo-side generator/routing/validation fix only. No prod apply, no registry promotion.

---

## 1. Owner smoke FAIL (recorded)

| Field | Value |
|-------|-------|
| Profile used (report 11) | Legacy `BenderVPN NL Independent Exit Canary — owner only` (single importable) |
| Verdict (report 11) | **FAIL_PROFILE_ROUTING_PROTOCOL** |
| Profile used (report 12) | Same legacy profile + Happ **BenderVPN RU** overlay + Telegram opened |
| Verdict (report 12) | **NOT_TESTED_INVALID_SMOKE** — not NL Direct Basic failure |
| Analyzer | `ops/analyze_nl_canary_smoke.py` (guard NL-DIRECT-BASIC-SMOKE-GUARD-001) |
| Registry promotion | **Not performed** |

---

## 2. Root cause classification

**Primary: A — Generator/routing mismatch**

- Legacy single profile routed `geosite:google` via **Intl_Stealth** (relay-2), not NL **Intl_Direct**.
- Smoke checklist used Gmail/Google as NL proof → **invalid** (Gmail success did not prove NL egress).

**Contributing: E — Happ routing overlay**

- Report showed external Happ routing profile **BenderVPN RU** active (`use_routing=true`), which can override JSON-embedded rules.

**Possible secondary: C — Relay/stealth path stress**

- Error storm dominated relay-class endpoint bucket (~60% of endpoint errors); NL direct vs stealth not separable until DIRECT_BASIC retest.

---

## 3. Repo corrections (DESIGN 1 — two profiles)

| Profile | Happ label | Purpose |
|---------|------------|---------|
| **DIRECT_BASIC** | `BenderVPN NL Direct Basic Canary — owner only` | NL outbounds only; Google/youtube + catch-all → Intl_Direct |
| **SPLIT_STEALTH** | `BenderVPN NL Split Stealth Canary — owner only` | NL Intl_Direct + relay-2 Intl_Stealth for TG/Meta/IG only |

**Files (`.local` only — not committed):**

- `.local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json`
- `.local/independent_exit_nl_SPLIT_STEALTH_IMPORTABLE_PROFILE.json`
- `.local/independent_exit_nl_canary_RUNBOOK.md`
- `.local/independent_exit_nl_canary_METADATA.json`

**Deprecated:** `.local/independent_exit_nl_canary_IMPORTABLE_PROFILE.json` (google→stealth bug)

**Code:**

- `ops/nl_canary_profile_builder.py` — two-profile builder
- `ops/generate_independent_exit_canary.py` — generates both variants + updated runbook
- `ops/validate_happ_importable_profile.py` — `validate_nl_canary_variant()` smoke/routing guards
- `ops/nl_canary_smoke_guard.py` + `ops/analyze_nl_canary_smoke.py` — fail-fast invalid smoke detection (report 12)

---

## 3b. report(12) — invalid Direct Basic attempt (2026-06-18)

| Check | Finding |
|-------|---------|
| Active profile | Legacy Independent Exit Canary (not Direct Basic) |
| Happ overlay | `useRouting=true`, `selectedRoutingRule=BenderVPN RU` |
| Forbidden app | Telegram opened during Direct Basic phase |
| TUN / DNS | Healthy (~1.5s startup, DNS set OK) |
| Errors | ~700 lines / ~2 min — relay/stealth class, not isolated NL direct |
| Classification | **NOT_TESTED_INVALID_SMOKE** — do not score as NL PASS/FAIL |

Local copy: `.secrets/diagnostics/report-12-invalid-nl-smoke.zip` (not committed).

## 4. Owner test sequence (mandatory order)

1. Regenerate locally: `python ops/generate_independent_exit_canary.py`
2. Validate:  
   `python ops/validate_happ_importable_profile.py .local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json --variant direct_basic`
3. **Phase 1 — DIRECT_BASIC only:** new Happ profile, auto-refresh OFF, **disable external routing profile overlay**
4. Smoke: Google search + Gmail (NL proof); 10–15 min session; **no Telegram/Meta in this phase**
5. On **PASS only** → Phase 2: import SPLIT_STEALTH, validate stealth split
6. On both PASS → report `overall_verdict` for promotion task (still no PUBLIC_PROD apply)

---

## 5. Gate update

| Gate | Status |
|------|--------|
| NL traffic smoke | **WAITING_CLEAN_DIRECT_BASIC_SMOKE** (report 12 = invalid, not tested) |
| Registry promotion | **NO** |
| PUBLIC_PROD | **NO-GO** |
| 300 / 30k | **NO-GO** |

---

## 6. Next owner action

**RUN CLEAN OWNER NL DIRECT BASIC SMOKE** — preflight checklist in runbook; analyze with `ops/analyze_nl_canary_smoke.py`.

If DIRECT_BASIC still FAILs with clean routing → escalate **APPREVE NL SERVER-SIDE FIX** (separate approval).

---

## 7. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Deploy/reload | **NO** |
| Remna/Caddy/template/subscription | **NO** |
| Live routing changes | **NO** |
| Registry promotion | **NO** |
| NL PASS claimed | **NO** |
| 300/30k GO claimed | **NO** |
