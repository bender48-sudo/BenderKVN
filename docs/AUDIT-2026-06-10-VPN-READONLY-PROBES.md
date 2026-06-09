# AUDIT-001B — Final Read-Only Probes (pre–Candidate D)

**Date:** 2026-06-10  
**Mode:** read-only · no `--apply` · no prod mutation  
**Host:** probes executed on **bvpn-lv** (`/opt/scripts`) + local panel-token probes from admin workstation  
**Branch:** `product-referral-cabinet-ui-v1` @ `f203d62`  
**Prior:** [`AUDIT-2026-06-09-VPN-RELIABILITY.md`](AUDIT-2026-06-09-VPN-RELIABILITY.md), [`AUDIT-2026-06-09-VPN-ARCHITECTURE-DRYRUN.md`](AUDIT-2026-06-09-VPN-ARCHITECTURE-DRYRUN.md), [`AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md`](AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md)

---

## 1. Executive summary

Mandatory **LV-vantage** probes that failed on Windows (2026-06-09) were re-run on **bvpn-lv**. **All relay and TSPU probes passed.** Both RU relays are TCP-reachable on `:443` from cross-probe vantage; subscription edge is TLS-reachable from both relays.

Live subscription probes **confirm AUDIT-001/002 findings unchanged:**

- **5896 B**, **3 VLESS outbounds**, **relay#2 only** (`46.173.28.252`)
- Balancers reference **`proxy`…`proxy-6`** but only **`proxy`…`proxy-3`** exist
- Live DNS verify: **BROKEN** (DoH entry missing on emitted sub)
- `injectHosts`: **3** (parity OK — broken but consistent)

**Candidate D pre-apply gate:** relay/TSPU **no-go conditions in test plan §10.6 are NOT triggered.** Owner **global apply approval** remains the only blocker.

---

## 2. Safety constraints

| Constraint | Status |
|------------|--------|
| No `patch_*`, `--apply`, template PATCH | Honored |
| No deploy / restart / broadcast / mass refresh | Honored |
| No Remna/Caddy/routing/DNS mutation | Honored |
| Probes: SSH read-only + GET sub/panel only | Honored |
| Secrets / sub URLs redacted in this doc | Honored |

---

## 3. Probe results table

| Probe | Target | Result | Interpretation | Candidate D impact |
|-------|--------|--------|----------------|-------------------|
| **`relay_latency_probe.py`** (bvpn-lv) | relay#1 `72.56.0.145:443` via relay#2 vantage | **OK** tcp **13.4 ms** | relay#1 VPN port reachable from RU cross-probe | Safe to restore **relay#1 ×3** in injectHosts |
| **`relay_latency_probe.py`** (bvpn-lv) | relay#2 `46.173.28.252:443` via relay#1 vantage | **OK** tcp **8.5 ms** | relay#2 healthy; current sole relay path is up | Adding relay#1 removes SPOF without dead path risk |
| **`relay_latency_probe.py`** | Exit code | **`RELAY_LATENCY_PROBE_OK`** | Both relays alive — not a false Windows “missing SSH key” fail | §10.6 no-go **not** triggered |
| **`tspu_block_probe_ru.py`** (bvpn-lv) | Edge `k9x2m1.conntest.xyz` via **relay#1** | tcp `:2053` **39.4 ms**, tls `:8443` **26.2 ms** | No TSPU hard-block on sub edge from relay#1 RU vantage | No red flag against global apply |
| **`tspu_block_probe_ru.py`** (bvpn-lv) | Edge via **relay#2** | tcp `:2053` **111.3 ms**, tls `:8443` **30.7 ms** | Edge reachable; relay#2 slower but OK | Both relay pools can reach panel/sub edge |
| **`tspu_block_probe_ru.py`** | Exit code | **`TSPU_BLOCK_PROBE_RU_OK`** | TSPU probe green from LV | §10.6 no-go **not** triggered |
| **`nl_reachability_probe_ru.py`** (bvpn-lv) | NL `91.90.192.17:443` | **OK** tcp **52.1 ms** (best via relay#2) | NL exit reachable from RU; not in current injectHosts | Informational only — Candidate D phase 1 keeps **LV/NL direct out** |
| **`probe_subscription.py`** (local) | Happ UA live sub | HTTP **200**, **5896 B**, **3** tcp vless, **LV=0 NL=0**, all **relay#2** | Profile still collapsed vs stealth design | After D: expect **~7–8 KB**, **6** proxies, relay#1+#2 |
| **`verify_vpn_balancer_profile.py`** (local) | Balancer + DNS gate | **`VPN_BALANCER_PROFILE_OK`**, relay-only×6 policy, **vless_proxy=3**, **dns=BROKEN** | Gate accepts broken 3-proxy skew; DNS issue persists | D fixes selector parity + DoH on emitted sub |
| **`diagnose_happ_import.py`** (local) | Happ batch simulate | **batch_risk=LOW**, xhttp=0, observatory=NO, **3** parseable proxies | Not an xhttp / “0 servers” regression | Instability is routing/balancer/DNS, not Happ import |
| **`diagnose_speed.py`** (local) | Template vs live | **WARN:** random **6-path** balancers on **3** injectHosts; **missing DoH** on live | Direct mechanism for ~1/min connect roulette | **Primary fix target** for Candidate D |
| **`probe_injecthosts_sub_parity.py`** (local) | Template vs sub | **injectHosts=3**, live **3** proxies, **`INJECT_SUB_PARITY_OK`** | Broken state is **consistent**, not drift | Apply must raise injectHosts **3→6** atomically with selectors |
| **`probe_routing.py`** (local, 3 users) | Routing rules | **7** rules, catch-all → `Intl_Direct`, stealth domain list intact, **0** degenerate rules | Stealth split architecture present but undermined by missing outbounds | D preserves rules; fixes outbound pool |
| **`transport_mux_audit.py`** (local, n=20) | primary+alt mux | **0%** users with primary+alt (all relay-only) | Expected while injectHosts trimmed; not mux regression | Post-D: mux audit again before NL/LV direct phase 2 |
| **Autotrim log** (`/var/log/bvpn-latency-autotrim.log`, bvpn-lv tail) | `latency_selector_autotrim.py` | Both relays probed OK; **target selector 6 paths**; **`[autotrim] no selector change`** | Cron is **not** shrinking injectHosts now; 3-host state likely from prior manual/ops trim | D restore should not fight live autotrim (selectors already want ×6) |
| **Happ user logs** | Device `access_log` / `error_log` | **Not collected** | Requires affected user export; server has no Happ telemetry | Optional post-apply if symptoms persist after D |

---

## 4. Relay health detail (2026-06-10, bvpn-lv)

```
relay2 → 72.56.0.145:443  tcp=13.4ms   (relay#1 from relay#2 vantage)
relay1 → 46.173.28.252:443 tcp=8.5ms   (relay#2 from relay#1 vantage)
RELAY_LATENCY_PROBE_OK
```

Cross-probe design avoids hairpin on same host and matches RU user → relay RTT semantics (`ops/relay_latency_probe.py`).

---

## 5. TSPU / edge detail (2026-06-10, bvpn-lv)

| Vantage | tcp `:2053` | tls `:8443` |
|---------|-------------|-------------|
| relay#1 `72.56.0.145` | OK 39.4 ms | OK 26.2 ms |
| relay#2 `46.173.28.252` | OK 111.3 ms | OK 30.7 ms |

**Verdict:** no evidence that TSPU currently hard-blocks subscription edge from either relay. relay#2 legacy port latency is higher but within probe pass criteria.

---

## 6. Live profile snapshot (unchanged from AUDIT-001B prep)

| Field | Value |
|-------|-------|
| Sub size (Happ UA) | **5896 B** |
| VLESS proxies | **3** (`proxy`, `proxy-2`, `proxy-3`) |
| Node mix | **relay#2 only** (`46.173.28.252:443`) |
| Balancer selectors | **6 tags** each (`Intl_Direct`, `Intl_Stealth`) |
| Missing outbound tags | **`proxy-4`, `proxy-5`, `proxy-6`** |
| Catch-all | Present → `Intl_Direct` |
| Observatory | Absent (correct for closed-pipe guard) |
| Template DNS | OK in templateJson |
| Live sub DNS | **BROKEN** — DoH entry missing |
| injectHosts | **3** (relay#2 only) |

---

## 7. Candidate D pre-apply checklist (§10.6 mapping)

| No-go condition | Probe evidence | Status |
|-----------------|----------------|--------|
| Both relays fail latency probe | Both OK | **PASS** |
| Both relays fail TSPU probe | `TSPU_BLOCK_PROBE_RU_OK` | **PASS** |
| `happ_geosite_guard.py` would fail | Not re-run here; unchanged template geo policy | **Defer at apply time** |
| Dry-run would enable observatory | Not executed (no apply) | **N/A** |
| injectHosts / selector mismatch after dry-run | Current mismatch documented; D designed to fix | **PASS intent** |
| Owner global approval | Pending | **BLOCKER** |

---

## 8. Recommended next step

1. Owner reply: **«approve global Candidate D»** (test-user-only impossible — single `REMNA_TEMPLATE_UUID`).
2. On approval only: snapshot → author/run `patch_restore_6relay_stealth.py` dry-run → `--apply` once on bvpn-lv → verify gate → owner device 48h soak (see test plan §9).
3. **No broadcast.** Optional single-user notify only if owner asks.

**Related:** client compatibility audit — [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md).

---

**AUDIT-001B status:** complete (read-only probes) · **Candidate D apply:** NOT APPROVED · **Push:** not requested
