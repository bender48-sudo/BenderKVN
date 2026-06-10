# INCIDENT-004 — Browser SaaS Long-Session Disconnects (Happ + BenderVPN)

**Date opened:** 2026-06-10  
**Mode:** incident analysis + diagnostic protocol only · no prod mutation  
**Branch:** `product-referral-cabinet-ui-v1`  
**Extends:** INCIDENT-002 (active failure capture), INCIDENT-003 (sleep/resume) — **does not replace**  
**Prior:** [`INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md`](INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md) (INCIDENT-001)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| **New signal** | Owner: browser **SaaS app** (e.g. Claude) shows **connection failure banner** while **page stays loaded**; message send **intermittent** |
| **Failure type** | **Long-lived session instability** — WebSocket/SSE/HTTP2/HTTP3/QUIC/TLS — **not necessarily full internet outage** |
| **Server/profile regression** | **Still not confirmed** — INCIDENT-001/002 short TCP/subscription probes **green**; probes **cannot prove** long-session stability |
| **Relation to INCIDENT-003** | May share root cause (Happ false-connected / TUN-route-DNS / VLESS layer) or be **distinct** active-work failure mode |
| **Commercial impact** | **Critical** — blocks desktop/browser SaaS positioning; **G1 remains PARTIAL/BLOCKED** |
| **Partial diagnostic evidence** | **INCIDENT-DIAG-003-004** — mail/Google DNS **~3m40s** degraded, **~25ms** after VPN reconnect; **CLIENT-STABILITY-001** — Track B: Bender Proxy fails while other VPN Proxy works (separate from TUN) — see [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md), [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) |
| **Prod fix justified now?** | **NO** — need correlated timestamps, browser diagnostics, comparison VPN, optional Hiddify A/B |

---

## 2. Owner evidence

### 2.1 Reported pattern

| Field | Owner report |
|-------|----------------|
| **Context** | Working in a **browser SaaS document/chat app** (Claude cited) |
| **Symptom** | In-app banner: *«We couldn't connect to Claude. Please check your network connection and try again.»* |
| **Page state** | **Page remains loaded** — not a full browser crash or tab unload |
| **Messaging** | **Sometimes sends**, sometimes reports network failure |
| **Frequency** | **Typical during document work** — not one-off |
| **VPN** | BenderVPN via **Happ** |
| **Screenshot** | Owner provided (private) — **not committed to repo** |

### 2.2 What this is **not** (yet)

- Not proven as **total internet loss** (other tabs may still work)
- Not reproduced by **short subscription fetch** or **relay TCP probes** alone
- Not confirmed as **server-side Candidate D regression**

### 2.3 What this **may** be

- **Long-lived connection** drops (WebSocket, SSE, EventSource, HTTP/2 stream, QUIC)
- **Happ false-connected** — UI shows connected while tunnel/path degraded
- **DNS/TUN stale state** — short requests OK, persistent channels fail
- **VLESS/Reality intermittent** layer — TCP handshake OK ≠ long-flow stability
- **Browser connection pool** behavior over VPN TUN

---

## 3. Failure classification

| Dimension | Classification |
|-----------|----------------|
| **Layer** | Application/session (browser SaaS) over VPN |
| **Duration** | **Long session** (20–30+ min active work) |
| **Scope** | May be **app-specific** or **system-wide** — must be tested at failure time |
| **Probe gap** | **INCIDENT-004 class** — missed by 7353 B fetch + relay TCP checks |
| **Desktop gate** | Same family as INCIDENT-003 but **active typing** vs **post-sleep** |

---

## 4. Relation to prior incidents

| Incident | Link |
|----------|------|
| **INCIDENT-001** | Candidate D active; 7353 B / 6 paths / DoH / parity OK — **does not disprove** long-session drops |
| **INCIDENT-002** | Interim stable after fresh import for **short active browsing** — **compatible** with long-session failures |
| **INCIDENT-003** | Sleep/resume breaks networking; another VPN survives — **may share** Happ TUN lifecycle root cause (Track A) |
| **CLIENT-STABILITY-001 Track B** | Bender **Proxy mode** reported failing while other VPN Proxy works — **distinct** from TUN daemon failure; long-session drops may occur in either mode |
| **Happ UX** | **One Auto host** expected — not a regression |

**Hypothesis convergence:** INCIDENT-003 (idle/sleep) + INCIDENT-004 (active long session) both point to **Happ desktop tunnel lifecycle** and/or **VLESS long-flow** — server short probes insufficient.

---

## 5. Primary hypotheses

| # | Hypothesis | Code |
|---|------------|------|
| 1 | Happ desktop breaks **long-lived TCP/TLS** sessions | A |
| 2 | **QUIC/HTTP3** unstable over VPN TUN | A/C |
| 3 | **HTTP/2 / WebSocket / SSE** resets through VLESS/Reality | D |
| 4 | Browser or OS **DNS cache** stuck on VPN interface | C |
| 5 | **TUN route** valid for short requests but tunnel drops long flows | A |
| 6 | Happ **false-connected** state | A |
| 7 | Server path healthy for **short** requests, unstable for **long** flows | D/F |
| 8 | SaaS-specific sensitivity to **IP/route change** mid-session | A/D |
| 9 | Coincides with **idle** within active session (micro-sleep, tab background) | A (INCIDENT-003 overlap) |
| 10 | BenderVPN profile structure triggers Happ long-session bug | 8 |

---

## 6. Owner diagnostic protocol

### A. BenderVPN / Happ (primary)

**Prerequisites:** Fresh import **BenderVPN Auto** if not done recently; note browser, OS, Happ version.

| Step | Action |
|------|--------|
| 1 | Connect Happ; confirm normal short browsing (Google, 2–3 sites) |
| 2 | Open **in separate tabs**: Claude or ChatGPT; Google Docs or similar; Gmail/webmail; 2–3 normal sites |
| 3 | **Work 20–30 minutes** in SaaS app (document/chat) — active typing, not just idle tab |
| 4 | When banner/error appears — **do not refresh immediately** |

**At failure moment, record:**

| Field | Record |
|-------|--------|
| Local time + UTC | Required |
| Happ status | Connected / error text |
| SaaS app name | e.g. Claude |
| Other tabs | Do they load? (Google, Telegram web, normal sites) |
| Telegram app | Works? |
| Google search | Opens? |
| Page refresh | Fixes SaaS only? |
| VPN off/on | Fixes without reboot? |
| Happ disconnect only | Restores SaaS? |
| After idle vs active typing | Was failure during typing or after pause? |
| Screenshot | Error banner (private — do not commit unless approved) |
| Windows laptop | `ops/diagnose_windows_vpn_resume.ps1 -Phase AfterBroken` (route/DNS) |
| Happ | `report.zip` export if available |

**Notify ops:** planned start time + device/OS for **Watch Window** (§8).

### B. Comparison VPN (same laptop)

| Step | Action |
|------|--------|
| 1 | Same browser, same Wi‑Fi, same SaaS app |
| 2 | Same **20–30 min** active work duration |
| 3 | Record whether connection banner appears |
| 4 | Note Happ-equivalent client status at failure time |

### C. Optional Hiddify A/B

- Same BenderVPN subscription URL, same browser/network
- Same SaaS app + duration
- **Diagnostic only** — do not change public Happ recommendation
- If Hiddify stable, Happ long-session specific; if both fail, server/profile/VLESS more likely

---

## 7. Browser / client diagnostics (no secrets)

### 7.1 Capture checklist

| Item | Safe to record |
|------|----------------|
| Browser name + version | Yes |
| OS version | Yes |
| Happ desktop version | Yes |
| Network (Wi‑Fi / LTE) | Yes |
| Time of error (local + UTC) | Yes |
| Happ shows connected? | Yes |
| All sites fail or only SaaS? | Yes |
| During active typing vs after idle? | Yes |
| Coincides with Happ reconnect? | Yes |
| DevTools Network summary | **Status/error names only** — see §7.2 |

**Do not capture:** auth tokens, cookies, request headers, subscription URLs, API keys, full HAR with credentials.

### 7.2 DevTools (optional, owner-comfortable)

Open DevTools → **Network** tab (before or right after failure):

| Column | Record |
|--------|--------|
| Time | Relative to error |
| Type | `websocket`, `fetch`, `eventsource`, `xhr` |
| Status | e.g. failed, (canceled), 502, 503 |
| Error | e.g. `ERR_NETWORK_CHANGED`, `ERR_CONNECTION_RESET`, `ERR_TIMED_OUT`, `ERR_NAME_NOT_RESOLVED`, `ERR_QUIC_PROTOCOL_ERROR` |

**Export:** screenshot of **Name + Status + Type** columns only — redact domain if needed; **no** cookie/header panel.

### 7.3 Windows route/DNS (laptop)

Reuse INCIDENT-003 script at failure time:

```powershell
pwsh -File ops/diagnose_windows_vpn_resume.ps1 -Phase AfterBroken
```

Output: `.secrets/diagnostics/` — **gitignored; do not commit**

---

## 8. Ops watch enhancements (when owner announces window)

Run read-only at correlated timestamp — **no prod mutation**.

| Check | Command / source | Pass does **not** prove SaaS stability |
|-------|------------------|----------------------------------------|
| Subscription size | `probe_subscription.py` | **Yes** — short fetch only |
| injectHosts parity | `probe_injecthosts_sub_parity.py` | **Yes** |
| Balancer profile | `verify_vpn_balancer_profile.py` | **Yes** |
| Relay TCP | `relay_latency_probe.py` on LV | **Yes** |
| DoH in profile | `verify_vpn_balancer_profile.py` dns=yes | **Yes** |
| Sub edge HTTP 200 | subscription-page logs / curl Happ UA | **Yes** |
| Remna/container health | `docker ps`, restart counts | Partial |
| Caddy 5xx around T | AMS/LV logs grep window | Partial |
| Repeated HTTPS to stable endpoints | curl/google/1.1.1.1 from ops host | **Yes** — not through owner TUN |
| HTTP/2 / HTTP/3 probe | If tooling exists — document result | **Yes** — edge only |

**Classification rule:** Short subscription fetch **PASS** + owner SaaS failure **both true** ⇒ evidence supports **client/long-flow** hypothesis, **not** server regression from probes alone.

**Load:** light probes only; no mass-refresh, no billing, no template PATCH.

---

## 9. Root cause decision matrix

| Observation | Likely cause |
|-------------|--------------|
| Other VPN keeps Claude/GDocs connected; BenderVPN drops | Happ or profile×Happ |
| Hiddify + same sub stable; Happ drops | **Happ-specific** |
| Happ + Hiddify both drop | Server/profile/VLESS |
| **Only Claude/SaaS drops**; other tabs work | SaaS long-session or app-specific — **not** full outage |
| **All sites fail** while Happ says connected | Tunnel/route/DNS false-connected |
| VPN off/on fixes without reboot | Happ tunnel lifecycle |
| Only reboot fixes | OS adapter/route/DNS stuck (INCIDENT-003 overlap) |
| Failure after tab background / micro-idle | Sleep/resume family (INCIDENT-003) |
| DevTools: WebSocket `ERR_CONNECTION_RESET` | Long-flow reset — VLESS or middlebox |
| DevTools: `ERR_NETWORK_CHANGED` | Route/TUN change mid-session |
| DevTools: DNS errors only | DNS stuck on dead tunnel |

---

## 10. Commercial readiness impact

| Launch type | Impact |
|-------------|--------|
| **G1 VPN stability** | **PARTIAL / BLOCKED** for desktop + browser SaaS until long-session evidence |
| **Closed soft launch** | **Mobile-first / manual support** — do not promise desktop document work |
| **Paid / open launch** | **NO-GO** until G1 improves |
| **Copy** | Do not claim stable desktop VPN for document/chat SaaS |

See [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) — G1 update in §11.

---

## 11. Stabilization options (evaluate only — not applied)

| Option | Blast radius |
|--------|--------------|
| Disconnect Happ before long SaaS sessions | User habit |
| Document VPN off/on recovery for SaaS banner | Docs only |
| **Proxy mode as desktop fallback** | **Not until CLIENT-SMOKE-002** — Bender Proxy currently reported failing |
| Collect `report.zip` + DevTools error names at failure | Diagnostic |
| Hiddify comparison same sub | Diagnostic only |
| Profile simplification canary | Requires `approve INCIDENT-003 desktop profile canary` |
| Emergency prod change | **Not justified** without correlated evidence + approval phrase |

---

## 12. Approval phrases

| Scenario | Phrase |
|----------|--------|
| Desktop profile canary | `approve INCIDENT-003 desktop profile canary` |
| Relay bias (from RST evidence) | `approve INCIDENT-002 relay bias relay#1` or `relay#2` |
| Rollback Candidate D | `approve rollback Candidate D template` — only if D proven harmful |

---

## 13. Prod fix justified?

**NO** — until owner supplies:

1. Failure timestamp (local + UTC) + ops watch correlation
2. Scope at failure: SaaS-only vs all tabs
3. Recovery test: refresh / VPN off/on / disconnect Happ
4. Comparison VPN same SaaS session (or waiver documented)
5. Optional: DevTools error names (no secrets), `report.zip`, route/DNS snapshot

---

## 14. What remains unknown

- Whether failure is **SaaS-only** or system-wide at banner time
- WebSocket/SSE/QUIC error class (DevTools at failure)
- Controlled **20–30 min SaaS soak** with timestamped failure
- Whether failure occurs without any idle (pure active 30 min)
- Hiddify A/B on same sub for long SaaS session

**Partially known (INCIDENT-DIAG-003-004):** Happ **2.16.2** / Chrome; mail/Google degradation + reconnect fix; tunnel connection-closed burst at manual stop (~13:10). **Not** Claude/ChatGPT banner reproduction. Details: [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md).

---

## 15. References

- **INCIDENT-DIAG-003-004:** [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md) — mail/Google tunnel evidence (partial)
- **CLIENT-STABILITY-001:** [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) — Track A/B split, Proxy smoke, workarounds
- INCIDENT-002: [`INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md`](INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md)
- INCIDENT-003: [`INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md`](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md)
- Route/DNS script: [`ops/diagnose_windows_vpn_resume.ps1`](../ops/diagnose_windows_vpn_resume.ps1)
- Skill: `vpn-incident-tg-only-ru` — RST / routing analysis
- Gates: [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md)
- Launch audit: [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md)

**Owner screenshot:** private evidence — referenced but **not embedded** in repo.
