# AUDIT — VPN Client App Compatibility (pre–Candidate D)

**Date:** 2026-06-10  
**Mode:** read-only · UA matrix via live `GET /api/sub/{shortUuid}` · no prod mutation  
**Branch:** `product-referral-cabinet-ui-v1` @ `f203d62`  
**Prior:** [`AUDIT-2026-06-10-VPN-READONLY-PROBES.md`](AUDIT-2026-06-10-VPN-READONLY-PROBES.md), [`AUDIT-2026-06-09-VPN-ARCHITECTURE-DRYRUN.md`](AUDIT-2026-06-09-VPN-ARCHITECTURE-DRYRUN.md)

---

## 1. Executive summary

BenderVPN’s subscription edge returns **different profiles per User-Agent**. Only **Happ-class Xray JSON** (Happ, Hiddify, Streisand) receives the full **stealth split** config: routing rules, random balancers, relay pool, catch-all → `Intl_Direct`.

**Karing, Clash Meta, sing-box official, and v2rayN do not receive equivalent “BenderVPN Auto” behavior today.** They get stripped sing-box JSON, Clash YAML in **global** mode, or a **single VLESS link to LV direct** — bypassing relay stealth architecture and RU-oriented routing policy.

**Recommendation:**

| Decision | Answer |
|----------|--------|
| Candidate D still right global fix? | **Yes** — server-side integrity bug; client-agnostic |
| Add Karing before Candidate D? | **No** — fix profile first; Karing needs separate generator work |
| Client strategy | **Happ primary** on all platforms; **v2rayN** documented Windows fallback with caveats; **Karing not primary** until sing-box/routing parity is engineered |
| Owner approval for global Candidate D? | **Yes — request explicitly** |

---

## 2. How subscription generation works (relevant to all clients)

```
Client GET /api/sub/{shortUuid} + User-Agent
        ↓
Caddy → subscription-page HA → Remna sing-box/Xray generator
        ↓
UA-specific format (JSON Xray | sing-box | Clash YAML | base64 vless://)
```

Canonical product path: **Happ** → full Xray JSON → **BenderVPN Auto** (no manual server pick). Documented in portal, bot, [`docs/FAQ.md`](FAQ.md), [`docs/HAPP-MATRIX.md`](HAPP-MATRIX.md).

---

## 3. Live UA matrix (2026-06-10, sample active user)

| Client UA | HTTP | Size | Content-Type | Outbounds / nodes | Routing / balancers | BenderVPN Auto equivalent? |
|-----------|------|------|--------------|-------------------|---------------------|----------------------------|
| **Happ/1.9.4 (iOS)** | 200 | **5896 B** | `application/json` | **3** VLESS → relay#2 `46.173.28.252:443` | **7** rules, **2** balancers (`Intl_Direct`, `Intl_Stealth`) | **Yes** (intended primary) |
| **Hiddify/2.5.0 (iOS)** | 200 | **5896 B** | `application/json` | Same as Happ | Same as Happ | **Yes** (Xray JSON path) |
| **Streisand/1.6.50 (iOS)** | 200 | **5896 B** | `application/json` | Same as Happ | Same as Happ | **Yes** (Xray JSON path) |
| **Karing/1.0.38 (iOS)** | 200 | **2036 B** | `application/json` | **1** VLESS → **LV direct** `176.126.162.158:443` + selector shell | **3** basic sing-box rules (sniff/DNS/private); **no** stealth split | **No** |
| **ClashMeta/1.18.0** | 200 | **1583 B** | `text/yaml` | **1** proxy → **LV direct**; mode **`global`** | No domain split / no relay balancers | **No** |
| **sing-box/1.8.0** | 200 | **344 B** | `text/plain` | **1** base64 `vless://…@176.126.162.158:443` | None | **No** |
| **v2rayN/7.3.6** | 200 | **344 B** | `text/plain` | **1** base64 VLESS → **LV direct** | None | **No** |
| **Mozilla/5.0** | 502 | 0 | — | — | — | N/A |

**Note:** Current broken 3-proxy / 6-selector skew affects **Happ-class** clients most (random dead picks). Karing/Clash bypass that bug by not using balancers at all — but connect via **LV direct**, which is **not** the intended RU stealth path.

---

## 4. Per-client evaluation

### 4.1 Happ (primary today)

| Criterion | Assessment |
|-----------|------------|
| Subscription format | Full **Xray JSON** via Happ UA filter (xhttp stripped) |
| Routing / balancers / DNS | **Receives** stealth rules + `Intl_*` balancers + split DNS block (DoH broken on live emit) |
| Sleep / resume | Known weak spot on desktop; **may improve** with Candidate D multipath — not proven until post-apply soak |
| Platform stability | **iOS, Android, Windows, Mac** — product-tested; portal + bot copy aligned |
| Auto routing | **Yes** — «BenderVPN Auto», no manual node pick |
| Beginner-friendly | **Best** — deep links, QR, store links in portal |
| Install source | App Store, Google Play, GitHub desktop builds ([`ru.json`](../web/portal/content/ru.json)) |
| Trust / recommend | **Default recommendation**; some user distrust (RU store presence) noted in [`NATIVE-APP-BACKLOG.md`](NATIVE-APP-BACKLOG.md) |
| Candidate D | **Direct beneficiary** — 6 aligned outbounds + DoH restore |

### 4.2 Karing ([karing.app/ru/download](https://karing.app/ru/download))

| Criterion | Assessment |
|-----------|------------|
| Subscription format | **sing-box JSON** (not Clash YAML) from current generator |
| Routing / balancers | **Stripped** — 1 LV node, no `Intl_Stealth` / `Intl_Direct`, no relay pool |
| Sleep / resume | sing-box-based; anecdotal reports vary; **no BenderVPN soak data** |
| Platform stability | iOS ≥15, Android ≥8, Windows ≥10, macOS ≥12, Linux, tvOS — broad install surface |
| Auto routing | **No** with current sub URL — user gets single LV outbound |
| Beginner-friendly | Good UI, but **wrong profile** for BenderVPN without docs/engineering |
| Install source | Official site + App Store (region caveats on download page) + GitHub mirrors |
| Trust | Active Flutter/sing-box project; smaller audit trail in BenderVPN ops than Happ |
| **Import current sub URL?** | **Yes**, but **not equivalent** to Happ |
| **Separate Clash/sing-box profile?** | Today: auto sing-box; **would need** engineered sing-box route rules mirroring stealth split + relay outbounds |
| Parallel with Happ? | Possible for power users **after** generator parity; **not** for mass recommendation now |

### 4.3 Hiddify

| Criterion | Assessment |
|-----------|------------|
| Format | **Same Xray JSON as Happ** (5896 B in probe) |
| Routing | Full stealth split **when** JSON path used |
| Platforms | iOS/Android/desktop variants |
| Store RU | **Limited** — [`NATIVE-APP-BACKLOG.md`](NATIVE-APP-BACKLOG.md) notes foreign clients hard for mass RU |
| Recommend | **Secondary** for technical users who already have the app |

### 4.4 Streisand

| Criterion | Assessment |
|-----------|------------|
| Format | **Same Xray JSON as Happ** |
| Routing | Full stealth split |
| iOS | App Store availability **region-dependent** |
| Recommend | **Fallback** only where installed; CIDR routing patches documented in [`RU-BYPASS.md`](RU-BYPASS.md) |

### 4.5 v2rayN (Windows)

| Criterion | Assessment |
|-----------|------------|
| Format | **Single base64 VLESS** → LV `:443` |
| Routing | **None** — manual node; [`CLIENT-V2RAYN.md`](CLIENT-V2RAYN.md) mentions tier pick (outdated vs stealth Auto) |
| Auto routing | **No** |
| Recommend | **Windows fallback** with explicit caveats; not a fix for current instability |

### 4.6 Clash Verge Rev / Mihomo / Clash Meta family

| Criterion | Assessment |
|-----------|------------|
| Format | **Clash YAML**, `mode: global`, **1 LV proxy** |
| Routing | **No** RU bypass / stealth split conversion in current emit |
| Recommend | **Not supported** for BenderVPN Auto without Clash rule pack + multi-node YAML work |

### 4.7 sing-box official / SFA

| Criterion | Assessment |
|-----------|------------|
| Format | **Plain base64 vless://** (same as v2rayN-style strip) |
| Recommend | **Not** for default users |

### 4.8 Shadowrocket / Stash / FoXray

| Criterion | Assessment |
|-----------|------------|
| Likely emit | iOS proxy clients often get **link-list** or minimal JSON (not probed individually; same generator family as sing-box strip) |
| Recommend | **Not** in current support matrix; Streisand/Hiddify cover Xray JSON niche better |

---

## 5. Answers to audit questions (1–15)

| # | Question | Answer |
|---|----------|--------|
| 1 | Clients supporting **current** BenderVPN sub format? | **Happ, Hiddify, Streisand** — full JSON. **Karing** — sing-box subset. **Clash*** — YAML. **v2rayN/sing-box** — single link. |
| 2 | Clients supporting **routing/balancer/DNS profile** correctly? | **Only Happ-class Xray JSON** path. All others **partial or none**. |
| 3 | Sleep/resume handling? | **Unknown winner**; Happ reported weak on desktop sleep. Candidate D multipath may help Happ; **no evidence** Karing fixes sleep without routing parity. |
| 4 | Stable iOS/Android/Windows/macOS? | **Happ** — production default. Others — untested at scale in BenderVPN. |
| 5 | Auto routing without manual node pick? | **Happ (+ Hiddify/Streisand JSON path)** only. |
| 6 | Beginner-friendly? | **Happ** >> all others given portal integration. |
| 7 | Official stores/sites? | Happ + Karing + v2rayN + Clash forks — see §4; portal only documents Happ (+ v2rayN note on Windows). |
| 8 | Safe enough to recommend? | **Happ: yes (default).** Karing: **only after** profile engineering. v2rayN: **qualified.** Clash/sing-box link: **no** for Auto promise. |
| 9 | UX if switching Happ → Karing? | Rewrite setup/guide: no Happ deep link; import URL manually; **no «BenderVPN Auto»**; explain LV vs relay; TUN/VPN permissions differ; lose routing profile link workflow. |
| 10 | Happ + Karing in parallel? | **Technically yes**, same sub URL — but **different effective paths** today (relay pool vs LV direct). Risk of confused support tickets. |
| 11 | Format changes for Karing? | Need **UA-specific sing-box emit**: relay outbounds ×6, route rules mirroring stealth split, DoH DNS — likely `singbox.generator` / template work **outside** Candidate D scope. |
| 12 | Karing import current URL directly? | **Yes** (200 OK, sing-box JSON). |
| 13 | Karing need separate Clash/sing-box profile? | **Needs proper sing-box profile from server**, not a second manual file — unless ops ships static routing pack (not recommended). |
| 14 | Default app per platform? | **Happ** on iOS, Android, Windows, Mac (unchanged). |
| 15 | Karing primary or fallback? | **Fallback / future** — **not primary** before Candidate D **and** generator parity. |

---

## 6. Phase 3 — Decision matrix

### 6.1 Does Candidate D still look like the right global fix?

**Yes.** Probes show both relays healthy; live profile has **selector/outbound skew** and **missing DoH**. Symptoms (all platforms, ~1/min retry, connected-but-stalls) match **server profile defect**, not a single bad client. Candidate D fixes integrity with lowest blast radius (6 relay injectHosts, no observatory, no 14-host restore).

### 6.2 relay#1 / TSPU red flags?

| Check | Result |
|-------|--------|
| relay#1 TCP `:443` cross-probe | **OK** ~13 ms |
| relay#2 TCP `:443` cross-probe | **OK** ~8 ms |
| TSPU edge via relay#1 | **OK** |
| TSPU edge via relay#2 | **OK** (higher legacy-port latency) |
| NL reachability (informational) | **OK** ~52 ms — not in phase-1 inject |

**No red flag** blocking Candidate D on relay#1 reintroduction.

### 6.3 Karing before or after Candidate D?

| Order | Rationale |
|-------|-----------|
| **After Candidate D** ✓ | Fix global Happ profile first (helps majority). Karing needs **separate** sing-box routing emit — orthogonal workstream. |
| Before Candidate D ✗ | Karing users don’t consume broken balancers today (LV shortcut) — fixing D doesn’t help Karing; delaying D hurts Happ majority. |

### 6.4 Recommended client strategy

**Selected: Happ primary + Karing fallback (future / power users only)**

| Strategy | Verdict |
|----------|---------|
| Happ only | Safe short-term; matches portal |
| Karing only | **Reject** — wrong profile today |
| Happ primary + Karing fallback | **Accept** with «Karing = experimental, not Auto-equivalent» until generator work |
| Karing primary + Happ fallback | **Reject** |
| Per-platform split | **Defer** — unnecessary complexity before D |

### 6.5 Guide / docs changes needed later (not in this read-only pass)

| Area | Change |
|------|--------|
| Portal [`ru.json`](../web/portal/content/ru.json) | Keep Happ primary; if Karing added: new download block + «не то же самое, что Auto» warning |
| [`docs/FAQ.md`](FAQ.md) | Karing row only after sing-box routing parity + owner sign-off |
| New doc | `docs/CLIENT-KARING.md` — import steps, limitations vs Happ, TUN, refresh |
| [`docs/CLIENT-V2RAYN.md`](CLIENT-V2RAYN.md) | Update tier language → stealth Auto; note single-LV link emit |
| Bot / Mini App | No change until owner approves client expansion |
| Happ routing profile link | Remains Happ-specific (`ops/happ_routing_profile_ru.json`); no Karing equivalent yet |

### 6.6 Owner approval request

> **Request:** Owner explicit consent for **global Candidate D** template apply on bvpn-lv.  
> Reply: **«approve global Candidate D»**  
> **Not approved:** Karing primary switch, broadcast, mass refresh, or observatory enable.

---

## 7. Candidate D impact on client matrix (expected)

After Candidate D (Happ-class JSON path):

| Aspect | Expected change |
|--------|-----------------|
| Happ / Hiddify / Streisand | **6** relay outbounds; selectors aligned; DoH restored → **lower reconnect / DNS stall rate** |
| Karing / Clash / v2rayN | **Unchanged emit shape** unless separate generator work — still LV-centric strip |
| Client strategy | **Still Happ-first** |

---

## 8. Testing recommendations (post-apply, owner devices)

1. **Happ** iOS + Android + Windows: refresh sub once → 48h soak (web + TG + sleep/resume on desktop).
2. Optional: **Hiddify/Streisand** on one iOS device — confirm 6 proxies + rules present.
3. **Karing:** only exploratory — expect **1 LV node** until generator updated; do not use as success criterion for Candidate D.

---

**Status:** complete (read-only) · **Next:** owner **«approve global Candidate D»** → implement per [`AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md`](AUDIT-2026-06-09-VPN-CANDIDATE-D-TESTPLAN.md)
