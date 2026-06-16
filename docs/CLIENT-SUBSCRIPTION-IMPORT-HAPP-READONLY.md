# CLIENT-SUBSCRIPTION-IMPORT-HAPP-001 — Read-only import investigation

**Task:** CLIENT-SUBSCRIPTION-IMPORT-HAPP-001  
**Status:** **DONE (read-only review)** — staging experiment **NOT STARTED**  
**Mode:** no prod mutation · no template change  
**Parent:** [CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md](CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md)

---

## 1. Observed Happ import pattern (mobile logs)

**BenderVPN (every auto-update):**

```
HTTP 200 → Batch ImportResult count=0 (UnknownContentType×2) → Append custom count=1 OK
```

**SafeVPN (control, behavior only):**

```
HTTP 200 → Batch count=0 (UnknownContentType×2) → Append custom count=5 OK
```

**Geofile/provider (routing profile, not subscription body):**

```
Google file failed / Happ file failed → Required value was null
```

Occurs in **bursts** separate from some traffic windows; **not correlated** with access gaps during 19:19–19:40 (0 sub events).

---

## 2. What Bender subscription likely returns (repo evidence)

| Aspect | Finding | Source |
|--------|---------|--------|
| Format | **Xray JSON** for Happ UA | `probe_fallback_client_sub.py`, `CLIENT-STABILITY-MOBILE-SMOKE.md` |
| Content-Type | `application/json; charset=utf-8` on live sub | `AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md` |
| Outbounds | 6× relay proxy tags + balancers (`Intl_Direct`, `Intl_Stealth`) | Candidate D emit |
| Batch parse | **xhttp** network outbounds → `UnknownContentType` in Happ batch importer | `ops/subscription_fetch.py` `happ_batch_parseable()` |
| Fallback | **Append custom** path imports full profile when batch fails | Mobile `subscription_log` |

**Not vless plain list** for Happ Auto path — full JSON document.

---

## 3. Why UnknownContentType then Append custom OK

Happ mobile import **stages** (from logs + repo simulator):

1. **Config manager batch import** — parses each outbound; **xhttp** (and other non-whitelisted networks) → `UnknownContentType` → **count=0**.
2. UI may flash **«0 servers»** briefly (19 occurrences in owner log file — transient).
3. **Append custom result** — separate code path loads **full BenderVPN Auto** JSON → **count=1** (expected for Auto UI).
4. Tunnel uses appended profile; **access_log shows accepted flows** when connected.

Repo simulator (`simulate_happ_batch`): `HAPP_BATCH_NETWORKS = {tcp, ws, grpc, http, h2, kcp, quic}` — **xhttp excluded** → batch_risk HIGH if xhttp present.

Historical prod note: **VPN-STAB-005 DONE** — xhttp risk documented; Happ-only filter was product direction, **not applied in this session**.

---

## 4. Geofile / Google / Happ file failed

| Hypothesis | Verdict |
|------------|---------|
| Happ fetching **routing provider** files (geosite/geoip CDN) | **LIKELY** |
| Subscription HTTP failure | **NOT SUPPORTED** — HTTP 200 on updates |
| Blocks tunnel by itself | **NOT PROVEN** — traffic active during access window without concurrent geofile burst |
| Explains slow sleep reconnect | **POSSIBLE** if reconnect triggers geofile fetch + delay — **NOT PROVEN** without wake timestamps |

`Required value was null` = Java/Kotlin parse error on empty provider response — **client-side noise**, not Bender server down.

---

## 5. Bender vs SafeVPN (structural only)

| | BenderVPN Auto | SafeVPN (control) |
|--|----------------|-------------------|
| Append custom count | **1** | **5** |
| UnknownContentType batch | Yes | Yes |
| Geofile failures | Yes (shared app) | Yes |
| Config shape | 6-way Auto JSON | Different provider (do not copy) |

Shared **Happ client behavior** → import noise is **not Bender-specific outage**.

---

## 6. Reconnect after sleep — causality

| Claim | Verdict |
|-------|---------|
| Import noise breaks tunnel while connected | **NOT SUPPORTED** — 766 flows, 0 errors in access window |
| Import delay on wake **possible** | **POSSIBLE** — if wake triggers sub refresh + geofile fetch |
| Proven root cause | **NOT PROVEN** |

---

## 7. What remains unknown

- Exact **Content-Type header** on owner’s live mobile fetch (not in subscription_log).
- Whether **xhttp** outbounds still present in current emit (needs owner-approved `probe_fallback_client_sub.py` or staging — **not run this session** to avoid live token use without explicit ask).
- Happ mobile **access_log retention policy** (full-day export method).

---

## 8. Safe next surfaces (no prod change)

| Priority | Surface | Scope |
|----------|---------|-------|
| **1** | [CLIENT-MOBILE-OBSERVABILITY-001](CLIENT-MOBILE-OBSERVABILITY-PLAN.md) | Full-day access export |
| **2** | **CLIENT-SUBSCRIPTION-IMPORT-HAPP-STAGING-001** (proposed) | Owner-approved staging fetch + `diagnose_happ_import.py --json` redacted summary |
| **3** | **CLIENT-STABILITY-MOBILE-SLEEPWAKE-001** | Timed lock/unlock if logs stay partial |
| **4** | Profile comparison | Only if full-day logs show route-specific gaps |

**Explicitly NOT approved now:** template trim, xhttp filter deploy, happRouting change, relay2 default.

---

## 9. Read-only tools (reference)

```powershell
# Shape probe (needs panel token — owner/local only)
python ops/probe_fallback_client_sub.py --json

# Happ batch simulator (live sub — needs token)
python ops/diagnose_happ_import.py --json

# Log analysis only (no network)
python ops/analyze_mobile_logs.py --fullday --correlate ...
```

---

## 10. Task closure

| Item | Status |
|------|--------|
| Read-only pattern documented | **DONE** |
| Prod/template change | **NOT DONE / NOT APPROVED** |
| Staging A/B (xhttp strip) | **OPEN** — separate owner gate |
| Mobile PASS | **NOT CLAIMED** |
