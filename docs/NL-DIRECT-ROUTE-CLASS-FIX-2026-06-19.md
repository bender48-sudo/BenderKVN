# NL Direct Route-Class Fix — 2026-06-19

**Task:** NL-DIRECT-ROUTE-CLASS-FIX-001  
**Status:** **PATH A — DONE (repo) / WAITING_OWNER_NL_DIRECT_BASIC_ROUTE_CLASS_SMOKE**  
**Companions:**
[`NL-DIRECT-PATH-SERVER-PROFILE-FIX-2026-06-18.md`](NL-DIRECT-PATH-SERVER-PROFILE-FIX-2026-06-18.md) ·
[`NL-INDEPENDENT-EXIT-FIX-2026-06-18.md`](NL-INDEPENDENT-EXIT-FIX-2026-06-18.md)

> Repo-side route-class/profile/validator fix only. No prod apply, no registry
> promotion, no server mutation.

---

## 1. Owner report(14) — recorded

| Field | Value |
|-------|-------|
| Active profile | `BenderVPN NL Split Stealth Canary — owner only` |
| Happ external routing overlay | **OFF** — `useRouting=false` |
| TUN startup | healthy (~1.45 s) |
| DNS set | OK |
| relay1 | absent |
| REALITY fragment | absent (count 0) |
| Telegram / relay2 stealth | **alive** |
| Normal non-blocked sites | worked (likely **direct bypass**) |
| Blocked intl sites | **failed** |
| NL direct endpoint | reset/closed errors (~611 lines / ~1 min) |

Local copy: `.secrets/diagnostics/report-14-nl-split-partial.zip` (not committed).  
Synthetic regression fixture: `tests/fixtures/nl_smoke_report14_fixture.py`.

### Classification

- `SPLIT_STEALTH_PARTIAL` — stealth branch carried Telegram; NL-direct/blocked path failed.
- `TELEGRAM_STEALTH_ALIVE` — relay2/stealth path functional.
- `NL_DIRECT_OR_ROUTE_CLASS_FAIL` — blocked intl sites (Google/YouTube/etc.) hit NL direct and reset.
- `DIRECT_BYPASS_MASKS_SMOKE` — normal RU/local sites working does **not** prove NL egress.
- **NOT an NL PASS.** Registry promotion forbidden.

---

## 2. Route classes (explicit)

| Class | Purpose | Examples | Proves NL? |
|-------|---------|----------|------------|
| `DIRECT_BYPASS_ALLOWED` | RU/local traffic may go direct | yandex.ru, vk.com, geoip:ru | **NO** |
| `NL_DIRECT_VALIDATION` | Blocked intl sites must use NL direct | google, youtube, x.com, openai | **YES** |
| `STEALTH_VALIDATION` | TG/Meta/IG must use relay2 stealth | telegram, instagram, facebook | Proves stealth only |
| `BLOCKED_SITE_NL_DIRECT` | RU-blocked → NL path | google.com, youtube.com, x.com | **YES** |
| `BLOCKED_SITE_STEALTH` | RU-blocked → stealth path | telegram, instagram, meta | Proves stealth only |

Owner must never guess “ordinary vs blocked” — runbook smoke targets are explicit.

---

## 3. Repo corrections

| Component | Change |
|-----------|--------|
| `ops/nl_canary_route_classes.py` | **NEW** — route taxonomy, resolver, static validator |
| `ops/nl_canary_profile_builder.py` | Explicit NL validation rule in SPLIT_STEALTH (google/youtube/twitter/x/openai → Intl_Direct) |
| `ops/validate_happ_importable_profile.py` | Fails if route-class expectations violated |
| `ops/nl_canary_smoke_guard.py` | Split-stealth PARTIAL/FAIL classification; direct-bypass mask detection |
| `ops/generate_independent_exit_canary.py` | Route-class smoke checklist + metadata |
| `tests/fixtures/nl_smoke_report14_fixture.py` | report(14)-class regression |
| `tests/test_nl_canary_route_classes.py` | Route-class unit tests |

Prior artifact bugs remain fixed: no legacy profile, no overlay, no fragment, no relay1.

---

## 4. Owner test sequence (mandatory order)

1. Regenerate locally: `python ops/generate_independent_exit_canary.py`
2. Validate both profiles with route-class guards
3. **Phase 1 — DIRECT_BASIC:** NL proof targets only (Google/Gmail/YouTube); **not** Yandex/VK
4. On DIRECT_BASIC PASS → Phase 2 SPLIT_STEALTH with per-class proof
5. Analyze reports: `python ops/analyze_nl_canary_smoke.py --report <zip> --variant <variant> --evaluate`

---

## 5. Gate update

| Gate | Status |
|------|--------|
| NL Direct Basic smoke | **WAITING_OWNER_NL_DIRECT_BASIC_ROUTE_CLASS_SMOKE** |
| NL Split Stealth | **PARTIAL** (report 14 — stealth alive, NL direct fail) |
| Registry promotion | **NO** |
| PUBLIC_PROD | **NO-GO** |
| 300 / 30k | **NO-GO** |

---

## 6. Next owner action

**RUN OWNER NL DIRECT BASIC ROUTE-CLASS SMOKE** — Phase 1 with corrected DIRECT_BASIC profile; use explicit NL proof targets from runbook.

If DIRECT_BASIC still shows NL-direct reset storm with clean input → **APPROVE NL DIRECT SERVER FIX** (server-side REALITY/remnanode check; separate approval).

---

## 7. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Deploy/reload | **NO** |
| Remna/Caddy/template/subscription | **NO** |
| Live routing changes | **NO** |
| Registry promotion | **NO** |
| Secrets committed | **NO** |
| NL PASS claimed | **NO** |
| 300/30k GO | **NO** |
