# CLIENT-SMOKE-002 — Bender Proxy vs Control VPN Proxy (diagnostic capture)

**Task:** CLIENT-SMOKE-002-PROXY-CAPTURE-001  
**Parent:** [CLIENT-STABILITY-001](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) Track B  
**Prerequisite design:** CLIENT-SMOKE-002-PROXY-VARIANT-READINESS-001  
**Mode:** owner-run diagnostics · no prod mutation · no deploy

**Do not commit:** `report.zip`, screenshots, `.secrets/diagnostics/*`, subscription URLs, tokens, UUIDs.

---

## 1. Purpose

Capture **Track B** evidence: BenderVPN Auto in **Happ Proxy mode** fails while **another VPN profile in Proxy mode** works on the same Windows laptop and network.

This bundle blocks Proxy-native implementation until classified (see §8).

---

## 2. Preconditions (same session)

| # | Requirement |
|---|---------------|
| 1 | **Same laptop** (Windows 11 preferred; note build in checklist) |
| 2 | **Same network** (Wi‑Fi or Ethernet — note which; no VPN change between A/B) |
| 3 | **Same browser** for site tests (Chrome or Edge — note version) |
| 4 | **Same time window** (~30–60 min) if possible |
| 5 | **TUN disabled** in Happ → Settings → Advanced (Proxy test only) |
| 6 | **Only one VPN profile connected at a time** |
| 7 | **Bender first**, then disconnect → **control VPN Proxy** (order reduces cross-contamination) |
| 8 | No reboot between Bender fail and control pass unless unavoidable (note if reboot occurred) |

---

## 3. Owner checklist (print or copy)

### 3.1 Meta (fill once)

| Field | Value |
|-------|-------|
| Date / local time | |
| Windows build | Settings → System → About |
| Happ version | Happ → About |
| Browser + version | |
| Network | Wi‑Fi / Ethernet / other |
| Bender profile name | **BenderVPN Auto** (only name — no sub URL) |
| Control VPN product name | e.g. SafeVPN / other (no sub URL) |
| Routing profile in Happ | e.g. **BenderVPN RU** Y/N |
| TUN enabled during Proxy test | must be **No** |

### 3.2 Bender Proxy test

**Setup**

1. Happ → disable **TUN** (Advanced).
2. Select **BenderVPN Auto**.
3. Enable **Proxy mode** (not TUN).
4. Connect and wait ~30 s.

**Record in Happ UI (no secrets in shared notes)**

| Check | Y / N / N/A | Notes |
|-------|-------------|-------|
| Shows connected / proxy active | | |
| «0 servers» or import error | | |
| Local proxy port visible (e.g. 127.0.0.1:xxxx) | | port: _____ |
| System proxy auto-set by Happ | | |
| Works in **TUN** but **not Proxy** (optional A/B) | | run only after Proxy capture |

**Site matrix** (Y = loads/works, N = fail, P = partial)

| Site | Bender Proxy | DNS symptom (timeout / wrong IP / ERR_*) |
|------|--------------|------------------------------------------|
| https://www.google.com | | |
| https://mail.google.com | | |
| Telegram (web or desktop) | | |
| Instagram / Meta (if feasible) | | |
| https://ya.ru | | |
| https://vk.com | | |
| Public IP check page (2ip.ru / ifconfig.me — no login) | | expected vs actual country |

**On failure — immediately**

1. Screenshot Happ: mode = Proxy, profile name, error text (crop sub URL / QR).
2. Screenshot browser error page (one failing site).
3. Optional: Windows Settings → Network → Proxy screenshot.
4. Happ → **Export report.zip** → save to `.secrets/diagnostics/` or private folder — **do not commit**.
5. Run (optional helper):

```powershell
pwsh -File ops/diagnose_windows_proxy_smoke.ps1 -Phase BenderProxyFail -ProfileLabel BenderVPN-Auto
```

Output: `.secrets/diagnostics/proxy-smoke-<timestamp>-BenderProxyFail.txt` (gitignored).

### 3.3 Control VPN Proxy test

1. **Disconnect** Bender completely (Happ off or profile switched).
2. Wait ~15 s (or reboot if Bender left system proxy stuck — **note this**).
3. Connect **control VPN** in **Proxy mode** only (TUN off).
4. Repeat **same site matrix** and record pass/fail.

Optional:

```powershell
pwsh -File ops/diagnose_windows_proxy_smoke.ps1 -Phase ControlProxyPass -ProfileLabel ControlVPN
```

### 3.4 Safe command bundle (after each phase)

Run only if comfortable; paste **redacted** output to support (script auto-redacts sub URLs):

```powershell
pwsh -File ops/diagnose_windows_proxy_smoke.ps1 -Phase BenderProxyFail -ProfileLabel BenderVPN-Auto
# … after control test …
pwsh -File ops/diagnose_windows_proxy_smoke.ps1 -Phase ControlProxyPass -ProfileLabel ControlVPN
```

Manual (if script unavailable):

```text
ipconfig /all
nslookup google.com
nslookup mail.google.com
curl -I https://www.google.com
curl -I https://mail.google.com
```

**Never paste:** subscription URLs, `vless://`, full Happ config export, tokens, HWID, raw `selected_server.json`.

---

## 4. Evidence package for ops/agent

Share privately (Telegram / ticket — not git):

| Artifact | Required | Notes |
|----------|----------|-------|
| Filled checklist §3.1–3.3 | **Yes** | Text table OK |
| Happ **report.zip** (Bender Proxy fail) | **Yes** | Primary |
| Happ report.zip (control pass) | Optional | Helps contrast |
| Screenshots (Happ + browser + proxy settings) | **Yes** | Redact URLs |
| `proxy-smoke-*.txt` from helper script | Optional | Gitignored path |
| TUN vs Proxy comparison | Optional | Strengthens DNS/inbound hypothesis |

**Control VPN — high-level only:** «full Xray JSON with local SOCKS» / «link list» / «Happ routing profile only» — **no** endpoints, keys, or sub URL.

---

## 5. Repo-side analysis (after owner delivers report.zip)

### 5.1 Safe local workflow

```bash
# Owner places zip outside repo, e.g. ~/Downloads/bender-proxy-fail-report.zip
python ops/analyze_happ_report_proxy.py ~/Downloads/bender-proxy-fail-report.zip
python ops/analyze_happ_report_proxy.py ~/Downloads/bender-proxy-fail-report.zip --json
```

- Parser **redacts** by default (`vless://`, `/api/sub/`, JWT-like strings, common UUID patterns).
- **Do not** copy report into repo or commit parser output containing raw endpoints.
- Write human summary to a **new** incident note (docs only) — quote patterns, not secrets.

Optional control contrast:

```bash
python ops/analyze_happ_report_proxy.py ~/Downloads/control-proxy-pass-report.zip --json
```

### 5.2 Log files to inspect (same as INCIDENT-DIAG-003-004)

| File | Proxy-track signals |
|------|---------------------|
| `subscription_log.txt` | `UnknownContentType`, `0 servers`, batch import count |
| `application_log.txt` | Proxy vs TUN mode, connect/disconnect, routing profile |
| `happd.log` | Local SOCKS/HTTP listen, DNS set failures, service stop |
| `tun_log.txt` / `access_log.txt` | `[socks -> direct]`, `[socks >> proxy]`, outbound tags, DNS timing |
| `error_log.txt` | geosite.dat, Reality/TLS, core start failures |
| `routing.json` / `settings.json` | **Analyze locally** — do not commit; check GlobalProxy, DNS type |
| `versions.txt` | Happ / Xray / sing-box versions |

### 5.3 Pattern checklist (agent)

| Pattern | Points to class |
|---------|-----------------|
| `localhost` DNS / `127.0.0.1:53` / «no such host» on RU resolve | **A** |
| No SOCKS/HTTP inbound lines; only outbound-only core | **B** |
| `ImportResult(count=0`, `0 servers`, `UnknownContentType` | **C** |
| Routing profile missing / `GlobalProxy` false / embedded routing ignored | **D** |
| `REALITY`, `TLS`, `connection refused` to relay IPs, all proxy timeout | **E** |
| Bender fail + control pass with clean Happ logs on same PC | **F** unlikely; prefer B–E |
| report captured after reconnect / no fail window | **G** |

Also compare with [INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md) parsing style (timeline tables, redacted inventory).

---

## 6. Root-cause classification (Track B)

| Code | Class | Meaning |
|------|-------|---------|
| **A** | DNS localhost / Proxy DNS | Template or Happ routing uses localhost/DoU for RU; breaks without TUN DNS path |
| **B** | Missing local inbound / sniffing | Outbound-only JSON; Happ Proxy wrapper insufficient for routing rules |
| **C** | Happ import / profile integrity | Batch import fail, single custom host, balancers dead |
| **D** | Routing profile not applied in Proxy | Dual-layer split (JSON + `happRouting`) fails in Proxy mode |
| **E** | Relay / VLESS connection | Server/path issue (less likely if control VPN works) |
| **F** | Generic Windows / system proxy | Stuck system proxy, wrong port — control test usually rules out |
| **G** | Insufficient evidence | Re-run capture §3 with fresh fail window + report.zip |

**Multiple codes allowed.** Primary code drives Proxy-variant design (see readiness audit).

---

## 7. Pass / fail for CLIENT-SMOKE-002

| Outcome | Criteria |
|---------|----------|
| **Capture complete** | Checklist + Bender report.zip + site matrix + classification A–G |
| **Track B confirmed** | Bender Proxy **FAIL** + control Proxy **PASS** + classification ≠ G only |
| **Blocks implementation** | Until capture complete; Proxy-native variant stays **design-only** |

---

## 8. References

- Track A/B runbook: [INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md)
- TUN sleep capture: [INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md), `ops/diagnose_windows_vpn_resume.ps1`
- Proxy readiness audit: CLIENT-SMOKE-002-PROXY-VARIANT-READINESS-001 (chat/report)
- Parser: `ops/analyze_happ_report_proxy.py`
- Helper: `ops/diagnose_windows_proxy_smoke.ps1`

---

## 9. Support intake (copy for users)

> Windows desktop, Happ [version], **Proxy mode** (TUN off), profile **BenderVPN Auto**.  
> Another VPN in Proxy mode on the same PC **works / fails**.  
> Sites: Google [Y/N], Gmail [Y/N], Telegram [Y/N], ya.ru [Y/N].  
> Attach: filled checklist + Happ report.zip (export after failure).  
> Do **not** send subscription link in chat — use /id or support token only.
