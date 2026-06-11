# INCIDENT-DIAG — Happ TUN Active Failure + Relay Direct-Route Storm (Windows)

**Task:** CLIENT-STABILITY-ACTIVE-FAILURE-CAPTURE-001  
**Date:** 2026-06-12  
**Mode:** read-only analysis + owner mitigation plan · no prod mutation · no deploy  
**Client:** Happ desktop **2.16.2** · sing-box tun **1.12.12** · Xray core **26.3.27** · Windows 11  
**Sources:** owner `report(1).zip` (prior unstable session) + `report(2).zip` (active failure) — **not committed**

**Not in scope:** CLIENT-SMOKE-002 Proxy capture — owner uses **TUN only** because Bender Proxy mode does not work on this PC.

**Related:** [CLIENT-STABILITY-001](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) · [INCIDENT-DIAG-003-004](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md) · [CLIENT-SMOKE-002](CLIENT-SMOKE-002-PROXY-CAPTURE.md) (separate Track B)

---

## 1. Executive summary

| Report | Session | TUN lifecycle | Active connectivity | Primary class |
|--------|---------|---------------|---------------------|---------------|
| **report(1)** | 2026-06-11 (multiple) | **FAIL** — `sing-box-tun` exit 1; `happ-tun` not UP ~10s; Cannot set DNS | Not primary evidence | **Track A** |
| **report(2)** | 2026-06-12 **00:12–00:19** local (+0300) | **PASS** — interface UP ~682ms; DNS set OK | **FAIL** — ~3616 errors in ~7 min | **Track D + H** (mixed) |

**Practical answer for owner desktop use now:**

1. **Track A days:** full reboot → reconnect Happ TUN (no sleep/resume before critical use).
2. **Track D/H active failure:** **disable Happ routing profile `BenderVPN RU` for one test session** (or use alt client with JSON-only routing) — relay server IPs appear in routing `directIp`, forcing `outbound/direct` TCP to relays instead of VLESS `proxy` outbounds; under TUN this produces timeout/reset storms.
3. **Parallel:** CLIENT-SMOKE-003 alt client (Karing / v2rayN) as temporary lab path until routing profile is corrected or Proxy mode fixed.

**Commercial blocker:** **Yes** — CLIENT-STABILITY-001 remains a **desktop launch gate** (Track A + active TUN unusability).

---

## 2. report(1) vs report(2) comparison

| Dimension | report(1) — unstable / daemon | report(2) — active failure |
|-----------|------------------------------|----------------------------|
| **Mode** | TUN (`tun=true`, `systemProxy=false`) | Same |
| **Happ / core / tun** | 2.16.2 / 26.3.27 / 1.12.12 | Same |
| **TUN daemon crash** | **Yes** — multiple `sing-box-tun` exit 1 on 2026-06-11 | **No** in active window |
| **Interface UP** | **No** — not UP after ~10s; DNS set failed | **Yes** — UP ~682ms; DNS OK |
| **Profile import** | Full JSON (6 proxy + direct + block) | Same — **OK**, not 0 servers |
| **Candidate D shape** | 6× `proxy` outbounds; Intl_Direct / Intl_Stealth random | Same |
| **Error storm** | Not primary in export window | **~3616 ERROR** in ~7 min |
| **Error type** | Daemon / interface lifecycle | **2243** i/o timeout + **1338** remote reset via **`outbound/direct`** |
| **Relay asymmetry** | N/A | 6 timeout endpoint buckets; top-2 ≈ **55% / 44%** (relay #1 worse) |
| **Local clues** | Check Point adapter; Npcap; stale proxy backup in app log | Same |
| **Proxy mode** | **Not tested** — owner states Proxy unusable | **Not tested** |

---

## 3. report(2) mode & profile integrity

| Check | Result |
|-------|--------|
| TUN vs Proxy | **TUN** — `AdvancedSettings.tun=true`, `systemProxy=false` |
| Profile name | BenderVPN Auto (full JSON / VLESS REALITY) |
| Import | **OK** — 8 outbounds: `proxy`…`proxy-6` + `direct` + `block` |
| Candidate D | **Yes** — 6 relay-only proxies; NL=0; LV direct=0 |
| Balancers | Intl_Direct + Intl_Stealth (random) |
| DNS | UseIP; 4 servers in JSON |
| Local inbounds | SOCKS **10808**, HTTP **10809**, sniffing, routeOnly=true |
| Happ routing | **BenderVPN RU** active, `useRouting=true`, `globalProxy=true` |

**Track C verdict:** **Not broken** — import integrity OK.

---

## 4. report(2) error storm (redacted counts)

**Active window:** 2026-06-12 00:12:48 connect → errors through **00:19** (~7 minutes).

| Metric | Count |
|--------|------:|
| Total ERROR-like lines | **3616** |
| i/o timeout | **2243** |
| forcibly closed by remote host | **1338** |
| upload closed | **224** |
| route-related | **2** |
| Errors via **`outbound/direct`** tag | **100%** of typed outbound errors |
| Unique timeout destination buckets | **6** (matches 6 proxy outbounds) |
| Docker / 172.18.x errors | **~259** |

**By minute (local):**

| Minute | Errors |
|--------|-------:|
| 00:13 | 208 |
| 00:14 | 402 |
| 00:15 | 389 |
| 00:16 | 656 |
| 00:17 | 460 |
| 00:18 | 911 |
| 00:19 | 590 |

**Sample pattern (redacted):**

```text
ERROR connection: open connection to [IP] using outbound/direct[direct]: dial tcp [IP]: i/o timeout
ERROR connection upload closed: ... forcibly closed by the remote host
```

**Interpretation:** Xray core attempts **plain TCP** to relay endpoints through **`direct` outbound**, not through **`proxy` VLESS outbounds**. Under Happ TUN, user traffic and core egress share the tunnel stack — consistent with **Track D** (routing profile sends relay IPs to direct) amplified by **Track H** (Happ TUN wrapper).

**Critical finding:** **Both relay server IPs appear in Happ routing profile `directIp` list** (`overlap_count=2`). This explains 100% `outbound/direct` errors to relay endpoints.

---

## 5. Server-side correlation (read-only)

**Owner window:** 2026-06-12 00:12–00:19 **+0300** ≈ **2026-06-11 21:12–21:19 UTC**.

| Check | Result |
|-------|--------|
| LV `bvpn-monitor.log` | Normal monitor checks at 21:10 and 21:15 UTC — **no mass outage signal** |
| Relay Caddy journal (local `bvpn-relay`) | **0 lines** in window (journal may not capture access) |
| Relay2 via LV jump SSH | **Not completed** — key denied from LV in this session |

**Conclusion:** **Inconclusive** whether packets reached relays. Timeout-via-`direct` pattern suggests many attempts may **never complete VLESS handshakes** — server logs may show few or no successful client sessions even if SYNs arrive.

**Needed for confirmation (read-only, no mutation):** relay #1/#2 Caddy or Xray access logs filtered to UTC window; compare attempt counts vs owner error counts.

---

## 6. Local Windows / Happ conflict (evidence strength)

| Factor | Present | Strength | Notes |
|--------|---------|----------|-------|
| Check Point VPN adapter | Yes (media disconnected) | **Medium** | Secondary; disable if possible |
| Npcap | Yes | **Low** | Common; 172.18.x noise in logs |
| Stale proxy backup (localhost:1080 PAC) | App log only | **Low** | `systemProxy=false`; not active |
| Wi‑Fi + happ-tun dual default routes | Yes | **Low–Medium** | Metric 0 on happ-tun; may add flakiness |
| UrbanVPN / extension | Not seen | — | — |

---

## 7. Classification

| Track | report(1) | report(2) | Confidence |
|-------|-----------|-----------|------------|
| **A** — TUN daemon / interface | **Primary** | Historical in same `happd.log`, not active window | **High** (A) |
| **B** — Proxy mode | N/A — not Proxy capture | N/A | Owner statement only |
| **C** — Import / 0 servers | **No** | **No** | **High** |
| **D** — Routing / DNS profile | Possible contributor | **Primary** — relay IPs in `directIp` | **High** |
| **E** — Relay / VLESS / server | Secondary (resets) | Possible partial — needs server logs | **Low–Medium** |
| **F** — Local Windows conflict | Secondary | Secondary | **Medium** |
| **H** — TUN route-to-relay / wrapper | Possible | **Co-primary** with D | **High** |
| **G** — Insufficient evidence | No | No | — |

**Overall report(2):** **Mixed Track D + H** (routing directIp leak + TUN wrapper), with **Track A** on other days. **Not CLIENT-SMOKE-002.**

---

## 8. Answers to specific questions

| Question | Answer |
|----------|--------|
| Primarily A, E, or mixed? | **Mixed D+H** for report(2) active failure; **A** for report(1) daemon crashes |
| CLIENT-STABILITY-001 still desktop blocker? | **Yes** |
| Change NL A2/A4 smoke plan? | **No change** — desktop Happ issue is orthogonal; continue NL smoke after owner desktop path stable |
| Relay #1 vs #2? | **Both fail**; **relay #1 ~55%** of timeout buckets vs relay #2 ~44% |
| Profile integrity? | **OK** — full Candidate D JSON |
| localhost RU DNS relevant? | **Not primary** here — UseIP + 1.1.1.1 on TUN; no localhost DNS failure in report(2) window |
| Proxy-mode issue? | **No** — explicitly **not** this capture; separate Track B |

---

## 9. Immediate owner workaround (prioritized)

### A. Fast recovery (Track A)

1. Fully **quit Happ** (tray → exit).
2. Optional: `services.msc` → restart **HappService** if TUN stuck.
3. **Reboot** if `happ-tun` stale / “Failed to start TUN process via daemon”.
4. Reconnect **BenderVPN Auto** in **TUN** only.

### B. Active failure test (Track D — do today)

1. Happ → Routing → **turn OFF `BenderVPN RU`** (or disable `useRouting`) for **one test session**.
2. Reconnect TUN; retry Google / Telegram / ya.ru for **5 minutes**.
3. If stable → root cause confirmed as **routing directIp leak**; capture short note + optional second report.zip.
4. Re-enable routing only after profile fix is planned.

### C. Local cleanup

- Disconnect / uninstall **Check Point VPN** if not needed.
- Windows Settings → Network → Proxy → **Off** (unless Happ intentionally sets).
- `ipconfig /flushdns`
- **Avoid sleep/resume** with VPN on before important use.
- Only one VPN active.

### D. Safer client path (CLIENT-SMOKE-003)

- Test **Karing** or **v2rayN** with same subscription (JSON profile).
- If alt client works with routing OFF or without Happ dual-layer → supports Track D/H, not server outage.

### E. Lab-only (needs owner approval — not prod default)

- Relay #2-only stripped profile for owner A/B — **do not deploy** without explicit approval.

---

## 10. Recommended next fix surfaces

| Option | Action | Prod mutation? |
|--------|--------|----------------|
| **1 — Client workaround now** | Routing OFF test + alt client smoke | **No** |
| **2 — Repo fix** | This doc + `ops/analyze_happ_report_tun.py` | **No** |
| **3 — Infra read-only** | Relay #1/#2 access log audit for UTC window | **No** |
| **4 — Controlled experiment** | Fix `BenderVPN RU` directIp (remove relay server IPs); owner-only validate | **Requires approval** — routing asset change |

**Product fix candidate (approval required):** Audit Happ routing profile **`BenderVPN RU`** — **remove relay endpoint /32 entries from `directIp`**; keep private RFC1918 ranges only. Re-test TUN + routing ON.

---

## 11. Tooling

```bash
python ops/analyze_happ_report_tun.py ~/Downloads/report.zip
python ops/analyze_happ_report_tun.py ~/Downloads/report.zip --json
```

Redacts secrets; reports TUN lifecycle, error storm, `directIp` overlap, track hints.

---

## 12. References

- Parser: `ops/analyze_happ_report_tun.py`
- Proxy capture (separate): `ops/analyze_happ_report_proxy.py`, `docs/CLIENT-SMOKE-002-PROXY-CAPTURE.md`
- Resume helper: `ops/diagnose_windows_vpn_resume.ps1`
- Backlog: CLIENT-STABILITY-001, CLIENT-SMOKE-001..003, VPN-ARCH-001
