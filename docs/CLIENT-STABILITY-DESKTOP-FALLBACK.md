# CLIENT-STABILITY-DESKTOP-FALLBACK-001 — Windows desktop fallback path

**Task:** CLIENT-STABILITY-DESKTOP-FALLBACK-001  
**Date:** 2026-06-13  
**Mode:** launch/support readiness · **no prod mutation by default**  
**Parent:** [CLIENT-STABILITY-001](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) · [CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md)

**Do not disturb:** If the owner is actively working on **Happ TUN** now, do **not** reconnect, reimport, or switch clients for this task unless Happ fails and support needs a fallback.

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **Recommended alternate Windows client** | **v2rayN** with existing bot subscription URL |
| **Recommended within Happ (before leaving Happ)** | **relay #2 lab profile** (`.local/lab_relay2.json`) — best routing parity |
| **Karing with current sub URL** | **Exploratory second alternate** — may help if Happ wrapper is the issue; **not** Auto-equivalent |
| **Happ Proxy on Bender** | **Not a fallback** — owner reports it fails; SafeVPN Proxy works (control only) |
| **Prod mutation for fallback** | **No** for default smoke paths |

**Happ remains the active recovery path** (TUN fast, DirectIp fixed, long-session soak open). **Fallback is launch/support safety** when Happ TUN cannot sustain desktop work — not a replacement product promise.

---

## 2. What each client receives today (subscription edge)

Source: [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md) (UA matrix) · read-only probe: `ops/probe_fallback_client_sub.py`

| Client | UA class | Format | Typical emit | Candidate D / stealth split? |
|--------|----------|--------|--------------|------------------------------|
| **Happ** | `Happ/*` | Xray JSON | 6 relay outbounds + `Intl_Direct` / `Intl_Stealth` + rules + DNS | **Yes** — **BenderVPN Auto** |
| **Hiddify / Streisand** | same JSON path | Xray JSON | Same as Happ | **Yes** (diagnostic; not Windows default) |
| **Karing** | `Karing/*` | sing-box JSON | **1× VLESS → LV direct** `:443` + basic route shell | **No** — stripped |
| **v2rayN** | `v2rayN/*` | plain / base64 | **1× VLESS link → LV direct** `:443` | **No** — single link |
| **Clash Meta** | `ClashMeta/*` | YAML | 1 proxy, `mode: global` | **No** |

**Important:** Candidate D fixed Happ-class integrity (6 relay injectHosts, DoH, DirectIp). **Karing/v2rayN emit shape did not change** — they still bypass relay stealth architecture.

Verify live shape (no secrets printed):

```powershell
cd D:\Va\projects\VPN
python ops/probe_fallback_client_sub.py --short YOUR_SHORT_UUID
# or first active user:
python ops/probe_fallback_client_sub.py
```

---

## 3. Fallback priority ranking (Windows desktop)

Use **top available** path that matches the failure mode. Do **not** stack multiple VPN clients connected at once.

| Rank | Path | Expected stability | Routing parity | RU direct (ya.ru/vk) | TG/IG/Meta safety | Setup | Launch suitability |
|------|------|-------------------|----------------|----------------------|-------------------|-------|-------------------|
| **E** | **Happ relay2 lab** | High if relay #1 is culprit | **Best in Happ** — stealth rules + relay #2 pool | **Yes** — Happ `BenderVPN RU` routing | **Yes** — `Intl_Stealth` | Medium — manual JSON import; **no refresh** | **Best Happ-side fallback**; not public default |
| **C** | **v2rayN + existing sub URL** | Moderate — single LV path; no Happ TUN wrapper | **Low** — LV direct only | **No** — no Happ routing profile; RU sites may go via proxy | **Not guaranteed** — no stealth split | **Low** — documented; portal mentions | **Recommended alternate client** for support |
| **A** | **Karing + existing sub URL** | Moderate — native sing-box TUN | **Low** — LV direct sing-box shell | **No** | **Not guaranteed** | Medium — import URL | **Exploratory** second alternate |
| **D** | v2rayN + generated support profile | Unknown | Would need engineering | TBD | TBD | High | **Deferred** — no generator |
| **B** | Karing + generated support profile | Unknown | Needs sing-box stealth emit | TBD | TBD | High | **Deferred** — G5-G / generator work |
| — | Happ normal Auto TUN | Residual long-session risk | Full Auto | **Yes** | **Yes** | Lowest | **Primary product path** |

**When to use which:**

| Situation | Path |
|-----------|------|
| Happ TUN up but Cursor/Docs reset; suspect relay #1 | **E** — relay2 lab (same Happ) |
| Happ TUN wrapper / client instability; need to work today | **C** — v2rayN |
| v2rayN unsatisfactory; test sing-box stack | **A** — Karing smoke |
| Need full Auto parity | **Stay on Happ** (normal or lab) — alt clients cannot deliver today |

---

## 4. Safety requirements (all fallback paths)

| Rule | Happ / relay2 lab | v2rayN / Karing (current sub) |
|------|-------------------|-------------------------------|
| No prod template mutation | ✓ local lab JSON only | ✓ import existing URL |
| No `fallbackTag=direct` in core JSON | Validated on lab generator | Stripped emits typically none — probe confirms |
| TG/IG/Meta must not leak **direct** | **Yes** via `Intl_Stealth` | **Not product-guaranteed** — traffic follows client global/TUN rules |
| RU direct behavior | **Yes** via Happ routing profile | **Limitation:** no `BenderVPN RU` profile — `.ru` may route differently |
| Secrets in git | **Never** commit sub URLs, `.local/*.json`, reports | Same |

**Support must say:** v2rayN/Karing fallback is **«работает интернет, но это не BenderVPN Auto»** — different path, no relay stealth, no RU split-tunnel parity.

---

## 5. Recommended smoke — v2rayN (alternate client)

**When:** Happ TUN unusable for real work; owner approved leaving Happ for this session.  
**Duration:** 20–30 minutes active use.  
**Do not run** while a productive Happ session is stable unless testing is scheduled.

### 5.1 Install / import

1. Download **v2rayN 7.x** portable: [GitHub releases](https://github.com/2dust/v2rayN/releases).
2. Bot → **«Моя настройка»** (or setup page) → copy subscription URL (`https://…:8443/api/sub/…`). **Do not paste URL into git/tickets verbatim** — use «sub URL from bot».
3. v2rayN → **Subscriptions** → **Add** → paste URL → **Update subscription**.
4. Expect **one VLESS node** (LV `:443`) — not six relay outbounds. See [`CLIENT-V2RAYN.md`](CLIENT-V2RAYN.md) (tier language outdated vs current emit).
5. **Quit Happ completely** (tray → Exit) before connecting v2rayN.
6. v2rayN → select imported node → **System proxy** mode first (not Happ). Enable **TUN** only if system proxy insufficient.

### 5.2 Test matrix (20–30 min)

| Check | Action |
|-------|--------|
| Cursor Agent | Keep open; note reconnects |
| Google Docs | Edit + scroll continuously |
| Gmail | `mail.google.com` |
| Telegram | Desktop or web |
| Instagram/Meta | If feasible |
| RU sites | `ya.ru`, `vk.com` — **may differ from Happ** (limitation) |
| IP check | `ipinfo.io` / `ifconfig.me` at start + end |

### 5.3 PASS / SOFT PASS / FAIL

| Verdict | Criteria |
|---------|----------|
| **PASS** | 20–30 min usable work; Cursor not looping reconnects; Docs/Gmail/TG load; no connected-but-no-traffic |
| **SOFT PASS** | Minor glitches; core work possible — document caveats |
| **FAIL** | Same class as Happ failure; must abort fallback promotion |

### 5.4 On FAIL

- Note v2rayN version, mode (system proxy / TUN), Windows build.
- v2rayN → **Help / log** (local only — **do not commit** raw logs with tokens).
- No Happ `report.zip` unless also testing Happ in same session.

---

## 6. Exploratory smoke — Karing (second alternate)

Same matrix as §5. Import **same bot sub URL**. Karing auto-detects sing-box JSON.

| Expect | Limitation |
|--------|------------|
| 1 outbound → LV direct | Not relay pool |
| sing-box TUN | No Happ routing profile |
| May feel stable on long sessions | **Cannot validate Auto parity** |

**PASS for Karing smoke** = «owner can work» — **not** «Karing replaces Happ Auto».

Download: [karing.app/ru/download](https://karing.app/ru/download)

---

## 7. Happ-side fallback — relay #2 lab (path E)

Use **before** switching to v2rayN if the goal is isolate relay #1 while keeping Auto routing.

```powershell
# Already generated locally (not in git):
# .local\lab_relay2.json  — relay #2 ×3
# .local\lab_relay2_one.json — single outbound
```

Full steps: [CLIENT-STABILITY-HAPP-RELAY2-LAB.md](CLIENT-STABILITY-HAPP-RELAY2-LAB.md)

---

## 8. Gaps vs Happ Auto (support copy)

| Feature | Happ Auto + BenderVPN RU | v2rayN / Karing (current sub) |
|---------|--------------------------|--------------------------------|
| BenderVPN Auto / no manual pick | ✓ | ✗ single LV node |
| Relay stealth pool (6-way / lab 3-way) | ✓ | ✗ LV direct |
| `Intl_Stealth` TG/IG/Meta | ✓ | ✗ not in emit |
| RU `.ru` direct split | ✓ (routing profile) | ✗ not supported |
| DirectIp leak fix | ✓ (Happ routing) | N/A — different client |
| Portal / bot setup copy | ✓ primary | v2rayN footnote only |
| Long-session WebSocket (Cursor/Docs) | Under investigation | Unknown — smoke required |

**Engineering gap (future):** UA-specific **sing-box emit** with relay outbounds + route rules mirroring stealth split (G5-G) — **not in scope** for this task; **no prod change**.

---

## 9. When support should use this path

| Trigger | Action |
|---------|--------|
| Owner/desktop user: Happ TUN reconnect loop, Docs dead, must work now | Offer **v2rayN smoke** (§5); disclose limitations |
| Happ failure + suspect relay #1 | **relay2 lab** first (§7) |
| v2rayN fails too | Escalate infra; collect local logs — not mass client switch |
| User asks for «another app like Happ» | Happ primary; v2rayN documented fallback; **do not** promise Karing Auto |
| Proxy mode request | **Do not** recommend Bender Happ Proxy — Track B open; SafeVPN is not product path |

---

## 10. Relationship to Happ recovery

| Track | Role |
|-------|------|
| **Happ recovery** | **Active** — DirectIp fixed; TUN fast; long-session soak [§9 recovery doc](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) |
| **relay2 lab** | Happ isolation — same client |
| **Desktop fallback (this doc)** | **Safety net** for launch/support — v2rayN first alternate |
| **Karing** | Exploratory — not launch default |
| **Prod generator parity** | Future — owner approval required |

---

## 11. Tooling

```powershell
python ops/probe_fallback_client_sub.py
python ops/generate_happ_relay2_lab_profile.py --from-json .local/bender_sub.json --write-json .local/lab_relay2.json
python ops/happ_routing_directip_guard.py
python -m pytest tests/test_probe_fallback_client_sub.py -q
```

---

## 12. Result record (owner fills after smoke)

| Path | Date | Duration | Verdict | Notes |
|------|------|----------|---------|-------|
| v2rayN + sub URL | | | **PENDING** | |
| Karing + sub URL | | | **PENDING** | |
| Happ relay2 lab | | | **PENDING** | see recovery §9 |

**CLIENT-SMOKE-003 status:** protocol ready — owner run pending.
