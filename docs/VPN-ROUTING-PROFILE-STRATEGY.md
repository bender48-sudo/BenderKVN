# VPN Routing Profile Strategy (BenderVPN)

**ID:** ROUTING-PROFILE-RU-DIRECT-001 (strategy **DONE** · implementation **OPEN**)  
**Date:** 2026-06-15  
**Purpose:** Convert external routing references (e.g. SafeVPN) into **BenderVPN-safe** Happ/Xray routing decisions without copying foreign infrastructure.

**Related:** [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) · `ops/happ_routing_profile_ru.json` · `ops/happ_routing_directip_guard.py` · [`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md)

---

## 1. What SafeVPN proves (reference only)

SafeVPN is useful as a **routing pattern reference**, not as architecture to clone.

| Block | Useful for BenderVPN |
|-------|----------------------|
| `queryStrategy: UseIPv4` | Test variant for Happ/Windows/mobile — avoids IPv6 oddities |
| Split DNS (RU vs intl resolvers) | Predictable domestic resolution under TUN |
| Private/system CIDR → direct | Correct — matches fixed Happ routing direction |
| Sniffing `http` / `tls` / `quic` | Domain-based routing under TUN |
| Curated RU/domestic direct domain list | Base for **reviewed** routing pack — not blind import |
| Simple single VLESS Reality outbound | Good **lab** pattern — not 30k capacity model |

---

## 2. What SafeVPN does NOT prove

| Cannot use as evidence | Why |
|------------------------|-----|
| Their UUID / publicKey / shortId / serverName / domain | Foreign credentials and infra |
| Full domain list without review | Privacy, product expectations, maintenance burden |
| `bittorrent → direct` without product decision | User surprise: “VPN on but torrent direct” |
| Single-proxy architecture | Does not scale to 30k; no N+1 |
| “It works on their server” | Different capacity, routing, and exit geography |
| Post-switch export state | Invalid for Bender analysis ([`CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md`](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md)) |

---

## 3. Bender routing principles (Happ / Xray)

Xray routing rules evaluate **top to bottom** — **order is part of the spec**. Any change requires ordered regression tests, not “append domains at the end.”

### 3.1 Fixed decisions (do not regress)

| Rule | Status |
|------|--------|
| Private + system CIDR → **direct** | **Required** |
| **`geoip:ru` must NOT appear in DirectIp** | **Required** — fixed prod happRouting (`0258d00`); **do not rollback** |
| Proxy server IPs must NOT be in DirectIp | Guard: `happ_routing_directip_guard.py` |
| Relay endpoints must NOT be Happ-direct-routed | Guard + generator (`0258d00`) |
| Import **BenderVPN RU** routing in setup flow | User-facing requirement |

### 3.2 Curated RU / domestic direct pack

| Principle | Implementation note |
|-----------|---------------------|
| RU banking, gov, CDN, major domestic services → direct | Maintain **reviewed** list in repo — versioned |
| Intl / blocked apps → proxy selectors | TG/IG/Meta via **Intl_Stealth** (backend template) |
| No user-facing NL/LV/relay pick | Policy PT-11 |
| List changes = routing pack version bump | Test matrix §6 |

### 3.3 DNS strategy

| Mode | Use |
|------|-----|
| Split DNS | Domestic domains → domestic resolver; intl → DoH/remote as designed |
| Happ `DomesticDNSIP` / DoH fields | Align with [`happ_routing_profile_ru.json`](../ops/happ_routing_profile_ru.json) |
| Test variant: dedicated RU resolver block | Document in routing pack changelog |

### 3.4 UseIPv4 test variant

| Item | Guidance |
|------|----------|
| `queryStrategy: UseIPv4` | **Test cohort only** first — desktop Happ + mobile |
| Rollout | Owner smoke → canary → default only if PASS |
| Rollback | Revert routing pack version in generator |

### 3.5 Sniffing

Enable `http`, `tls`, `quic` sniffing where Happ/TUN supports it for domain routing — verify no conflict with DirectIp guards.

### 3.6 BitTorrent policy — **owner decision required**

| Option | User expectation |
|--------|------------------|
| **block** | “All traffic through VPN when on” |
| **direct** | Faster local peers; leak risk disclosure |
| **proxy** | Full tunnel including torrent |

**Status:** **UNDECIDED** — do not copy SafeVPN default without product sign-off.

---

## 4. Backend vs client routing split

| Layer | Owns |
|-------|------|
| **Remna template / sub generator** | Outbounds, selectors, injectHosts, stealth split, cohort assignment |
| **Happ routing profile (RU)** | DirectIp, DNS, domestic domain direct, private CIDR |
| **Client (Happ)** | TUN, leastLoad among **issued** outbounds — not capacity planning |

**Target:** stop relying on “6 outbounds in JSON” as architecture. See **SUB-GEN-SELECTOR-STRATEGY-001**.

---

## 5. Client-specific strategy

### 5.1 Happ (primary — desktop + mobile)

| Topic | Strategy |
|-------|----------|
| Launch client | **Primary** for acquisition |
| Routing import | Mandatory **BenderVPN RU** deeplink in setup |
| Lab profiles | `LAB_OWNER` — relay2-only; **do not refresh** mass sub |
| Sleep/wake | Track CLIENT-SMOKE-001 — routing pack does not replace soak |
| Regression tests | `happ_routing_directip_guard.py`; import smoke |

### 5.2 v2rayN (Windows fallback)

| Topic | Strategy |
|-------|----------|
| Role | Support fallback — [`CLIENT-STABILITY-DESKTOP-FALLBACK.md`](CLIENT-STABILITY-DESKTOP-FALLBACK.md) |
| Parity | **Not** Auto-equivalent — LV-direct style emit |
| Routing pack | Simplified — document limitations in support scripts |

### 5.3 sing-box / Karing (exploratory)

| Topic | Strategy |
|-------|----------|
| Role | Diagnostic / second opinion — **not launch default** |
| `urltest` | Candidate for **mobile fallback profile** — probe URL picks outbound tag |
| Capacity | Does **not** replace node registry or multi-node delivery |

---

## 6. Routing test matrix (implementation for ROUTING-PROFILE-RU-DIRECT-001)

| # | Test | Pass criteria |
|---|------|---------------|
| T1 | `happ_routing_directip_guard.py` | Exit 0; no geoip:ru in DirectIp; no proxy IPs in direct |
| T2 | JSON schema valid | `python -m json.tool ops/happ_routing_profile_ru.json` |
| T3 | Private CIDR direct | 10/8, 172.16/12, 192.168/16, link-local → direct |
| T4 | Sample RU domain direct | yandex.ru, sberbank.ru (examples) → direct in Happ |
| T5 | Sample intl via proxy | google.com → not direct leak |
| T6 | TG/IG | Still via stealth selector in **subscription** — not routing pack alone |
| T7 | Generator idempotency | Regenerate profile — only `LastUpdated` changes if inputs unchanged |
| T8 | Prod apply gate | dry-run → owner approval → post-apply owner smoke |

---

## 7. SafeVPN → Bender mapping (conceptual)

| SafeVPN concept | Bender action |
|-----------------|---------------|
| UseIPv4 | Optional test flag in routing pack v2 |
| Split DNS | Already partially in happ profile — document + test |
| private CIDR direct | Keep |
| RU domain list | New curated `routing/domestic-direct-v1.txt` (future) — reviewed |
| sniffing | Evaluate Happ compatibility |
| single Reality outbound | Lab only |
| bittorrent direct | **Block until OD decision** |

---

## 8. Explicit non-goals

- Copying SafeVPN credentials or endpoints into repo or prod.
- Using SafeVPN export as PASS/FAIL evidence for Bender prod.
- Replacing multi-node architecture with a prettier client JSON.
- Rolling back fixed happRouting to restore `geoip:ru` in DirectIp.

---

## 9. Next implementation tasks

1. **ROUTING-PROFILE-RU-DIRECT-001** — versioned domestic direct list + generator integration.
2. **Owner decision** — bittorrent policy (§3.6).
3. **UseIPv4 cohort test** — owner desktop + one mobile device.
4. Wire T1–T8 into CI / pre-apply gate alongside `vpn_verify_gate.py`.
