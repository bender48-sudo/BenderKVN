# CLIENT-STABILITY-HAPP-RECOVERY-001 — Clean Bender Capture + Lab Variants

**Task:** CLIENT-STABILITY-HAPP-RECOVERY-001  
**Date:** 2026-06-13  
**Mode:** owner-led diagnosis · no prod mutation by default  
**Parent:** [INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) · CLIENT-STABILITY-001

**Goal:** Recover Happ Windows TUN as a supported path. Do **not** rollback fixed `happRouting` (`geoip:ru` removed from Happ `DirectIp`).

---

## 1. Clean Bender-only report capture (required next)

Export **before** switching to SafeVPN or any other VPN. Otherwise `selected_server.json` / `settings.json` in the zip are **not** valid Bender profile evidence.

### Steps (owner)

1. **Fully quit Happ** — tray icon → Exit (not just disconnect).
2. Wait **10 seconds**.
3. Reopen Happ.
4. **Refresh subscription** (pull latest BenderVPN Auto JSON).
5. **Refresh routing** — confirm profile **BenderVPN RU** is active (`useRouting=true`).
6. Mode: **TUN ON**, system proxy **OFF**.
7. Connect **BenderVPN Auto** in TUN.
8. Confirm TUN comes up quickly (interface UP, DNS set) — this is **not** the current blocker.
9. Test for **3–5 minutes**:
   - Google Docs or Gmail (long-lived tab)
   - Telegram Web or app
   - `https://ipinfo.io` or `https://ifconfig.me` (not check.ru — RU direct by design)
10. **If anything fails:** Happ → Help / Settings → **Export diagnostic report** → save `report.zip`.
11. **Only after export succeeds:** disconnect or switch to SafeVPN if you need a working VPN.
12. Send zip to analysis path (local only — **do not commit** to git).

### PASS capture quality

| Check | Expected in zip |
|-------|-----------------|
| `selected_server.json` name | **BenderVPN Auto** (not SafeVPN) |
| `settings.json` | `tun=true`, `systemProxy=false` |
| `routing.json` | BenderVPN RU; `directIp` = private CIDRs only; **no** `geoip:ru` |
| Analyzer | `final_state_guard.usable_as_bender_profile_evidence=true` |

```bash
python ops/analyze_happ_report_tun.py path/to/report.zip
python ops/happ_routing_directip_guard.py
```

---

## 2. report(5) — what we know (Bender segment only)

**report(5) not in repo.** Owner context + prior reports:

| Dimension | report(5) Bender segment (inferred) | Must NOT use as Bender evidence |
|-----------|--------------------------------------|----------------------------------|
| TUN startup | **Fast** — not Track A | — |
| Routing | **BenderVPN RU** ON; fixed DirectIp (no `geoip:ru`) | — |
| DirectIp leak | **Not primary** — fix retained | — |
| Import | **Not** 0 servers | — |
| Active failure | **Relay #1/#2 timeout/reset** under TUN | — |
| Final zip state | — | **SafeVPN Proxy** in `selected_server` / proxy mode settings |

**Why final SafeVPN state is invalid for Bender analysis:** Happ export captures **current** selection and mode. After manual switch, profile integrity, routing overlap, and error attribution reflect SafeVPN — not the failing Bender session.

**Analyzer:** `ops/analyze_happ_report_tun.py` → `final_state_guard`, `bender_segment` fields flag overwritten exports.

---

## 3. Previously working vs current — delta hypotheses

| Change | When | Happ TUN impact |
|--------|------|-----------------|
| **Candidate D** — 6 relay injectHosts, random balancers | 2026-06-10 apply | More relay endpoints; random selector may hit weaker path; **likely** |
| **Second relay restored** (relay#1 ×3 + relay#2 ×3) | Candidate D | Asymmetric relay quality; report(2) relay#1 ~55% dial errors pre-fix |
| **Happ routing profile** (`BenderVPN RU`) + bundled geosite | 2026-05+ onboarding | Layer on top of core JSON; DirectIp leak **fixed** — do not revert |
| **`geoip:ru` in Happ DirectIp** | until `0258d00` | Caused dial/open storm — **fixed**; report(5) past this |
| **Split DoH DNS** in subscription | Candidate D | UseIP + 1.1.1.1 / 8.8.8.8 — minor latency class |
| **xhttp removed** from Happ batch | earlier | Reduced 0-servers import risk — **positive** |
| **Mux off** in core JSON | stable | Unlikely primary |
| **In-core relay `/32` → direct** rules | always (anti-loop) | **Expected** — not same as Happ DirectIp leak |

**Most likely for current report(5) class:** Track **E** — VLESS/REALITY egress to relay #1/#2 resets/timeouts under Happ TUN wrapper, **after** DirectIp fix. Contributing: random 6-way balancer, Happ long-connection handling (Docs/WebSocket), possible relay#1 bias.

**Less likely now:** Track A (TUN daemon), Track D (DirectIp leak), Track C (broken import).

---

## 4. Controlled lab variants (owner-only; no prod default)

| Variant | Setup | Expected if hypothesis true | PASS | FAIL | Rollback | Owner approval |
|---------|-------|----------------------------|------|------|----------|----------------|
| **A — clean baseline** | Quit Happ → refresh sub+routing → TUN → Bender Auto | Relay errors reproduce on Docs/TG | Sites usable 5+ min; analyzer: no DirectIp leak; low dial/open | Same relay timeout/reset storm | None — disconnect | No |
| **B — routing OFF** | Happ routing **disabled** one session; core JSON only | If RU routing layer still contributes | Intl sites work; RU `.ru` may split-tunnel differently | No improvement | Re-enable routing | No |
| **C — relay #2-only** | Owner support profile: proxy-4/5/6 only | relay#1 is worse | Stable on relay#2 paths | Still fails | Delete test profile | **Yes** — support profile |
| **D — single-relay deterministic** | One outbound, no random balancer | Happ+balancer instability | Stable single path | Still fails | Remove test profile | **Yes** |

**Runbook (Option A — local JSON, no prod):** [CLIENT-STABILITY-HAPP-RELAY2-LAB.md](CLIENT-STABILITY-HAPP-RELAY2-LAB.md) · `ops/generate_happ_relay2_lab_profile.py`
| **E — DNS / UseIPv4** | Test profile: `queryStrategy=UseIPv4` or simplified DNS | DNS v6/latency class | Faster resolve; fewer resets | No change | Remove test profile | **Yes** |
| **F — workload split** | Docs-heavy 10 min vs light browsing | Track E long-connection | Light OK, Docs fail | Both fail | None | No |

**Order after clean capture:** **A** → **B** → **C** or **D** (if relay-tagged errors) → **F** → **E**.

---

## 5. Core relay direct rules — do not remove blindly

| Layer | Purpose |
|-------|---------|
| **In-core Xray** `routing.rules` relay IP → `outboundTag: direct` | Dial relay VLESS endpoints on **physical** NIC; prevents routing loop |
| **Happ `DirectIp`** (fixed) | Private CIDRs only — must **not** include `geoip:ru` or relay `/32` |

Removing in-core relay direct without lab proof risks failed handshakes or TUN capture loops. Only test alternatives in **owner-only** profiles after clean capture confirms Track E.

---

## 6. Immediate recommendation

1. **Now:** Clean Bender-only capture (§1) — **before any config experiments**.
2. **Then:** Run analyzer on new zip; if relay #1/#2 pattern persists → **Variant C** (relay #2-only owner profile) with owner approval.
3. **Do not:** rollback prod `happRouting`; do not remove in-core relay direct from prod template.

---

## 7. Fallback track (parallel, not abandoned)

| Path | Role |
|------|------|
| **Karing / v2rayN** (CLIENT-SMOKE-003) | Launch safety if Happ TUN remains flaky |
| **Happ recovery** | **Active** — primary commercial desktop client target |

---

## 8. Tooling

```bash
python ops/analyze_happ_report_tun.py report.zip
python ops/happ_routing_directip_guard.py
python ops/generate_happ_relay2_lab_profile.py --from-json owner_sub.json --write-json .local/lab_relay2.json
python -m pytest tests/test_analyze_happ_report_tun.py tests/test_generate_happ_relay2_lab_profile.py -q
```

Redacts secrets. Flags `final_state_guard` when export was taken after switching VPN.
