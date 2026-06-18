# NL Automated Connectivity Smoke — 2026-06-19

**Task:** NL-AUTOMATED-CONNECTIVITY-SMOKE-001  
**Status:** **PATH A — AUTOMATED DIRECT_BASIC SMOKE PASS**  
**Companions:**
[`NL-DIRECT-ROUTE-CLASS-FIX-2026-06-19.md`](NL-DIRECT-ROUTE-CLASS-FIX-2026-06-19.md) ·
[`NL-DIRECT-PATH-SERVER-PROFILE-FIX-2026-06-18.md`](NL-DIRECT-PATH-SERVER-PROFILE-FIX-2026-06-18.md)

> Local automated smoke only. No prod apply, no registry promotion, no NL capacity PASS.

---

## 1. Owner direction

Owner asked Cursor to validate site opening through the generated profile **before** another manual retest.

---

## 2. Harness

| Item | Value |
|------|-------|
| Script | `ops/run_nl_direct_connectivity_smoke.py` |
| Profile | `.local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json` |
| Core | Happ `xray.exe` (local, `XRAY_BIN` override supported) |
| Assets | `XRAY_LOCATION_ASSET` → Happ core dir (`geosite.dat`) |
| Inbound | SOCKS `127.0.0.1:10808` (`socks5h` for remote DNS) |
| Probe | `curl` through local proxy |

### NL_DIRECT_VALIDATION targets (proof)

| Target | Host | Result |
|--------|------|--------|
| google_generate_204 | www.google.com | **204** OK |
| gmail | mail.google.com | **301** OK |
| youtube_generate_204 | www.youtube.com | **204** OK |
| x_com | x.com | **200** OK |
| openai | openai.com | **403** OK (reachable) |

### Control (not NL proof)

| Target | Host | Result |
|--------|------|--------|
| yandex_ru_control | yandex.ru | **302** OK (direct-bypass sanity only) |

---

## 3. Automated result

| Field | Value |
|-------|-------|
| Static validation | **PASS** |
| Core start | **OK** |
| SOCKS ready | **OK** |
| NL proof | **5/5** |
| Reset-like errors | **0** |
| Endpoint roles | NL ×4 |
| **Verdict** | **PASS** |

**Interpretation:** Generated DIRECT_BASIC profile routes NL validation targets successfully through local Xray. This does **not** close Split Stealth owner report(14) or registry promotion.

---

## 4. Usage

```bash
python ops/generate_independent_exit_canary.py
python ops/validate_happ_importable_profile.py .local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json --variant direct_basic
python ops/run_nl_direct_connectivity_smoke.py --profile .local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json
python ops/run_nl_direct_connectivity_smoke.py --json
python ops/run_nl_direct_connectivity_smoke.py --static-only
```

Exit codes: `0=PASS`, `1=FAIL`, `2=BLOCKED_LOCAL_ENV`, `3=PARTIAL`.

### Local env blockers

If `BLOCKED_LOCAL_ENV`:

- Install/set `XRAY_BIN` (Happ core xray or standalone xray)
- Ensure `XRAY_LOCATION_ASSET` dir contains `geosite.dat` / `geoip.dat`
- `curl` on PATH

---

## 5. Gate update

| Gate | Status |
|------|--------|
| NL Direct Basic automated smoke | **PASS** (local xray, 2026-06-19) |
| NL Direct Basic owner Happ smoke | **WAITING_OWNER_NL_DIRECT_BASIC_ROUTE_CLASS_SMOKE** |
| NL Split Stealth | **PARTIAL** (report 14 — unchanged) |
| Registry promotion | **NO** |
| PUBLIC_PROD | **NO-GO** |
| 300 / 30k | **NO-GO** |

---

## 6. Next owner action

**RUN OWNER NL DIRECT BASIC ROUTE-CLASS SMOKE**

1. Import regenerated `.local/independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json`
2. Overlay OFF, auto-refresh OFF, no Telegram
3. Test NL proof targets from runbook (not Yandex/VK)
4. Export report.zip on fail → `ops/analyze_nl_canary_smoke.py --variant direct_basic --evaluate`

Only if automated + owner Direct Basic PASS → consider Split Stealth phase.

---

## 7. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Registry promotion | **NO** |
| NL capacity PASS | **NO** (automated client smoke only) |
| Secrets committed | **NO** |
| 300/30k GO | **NO** |
