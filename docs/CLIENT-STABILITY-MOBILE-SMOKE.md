# CLIENT-STABILITY-MOBILE-SMOKE-001 — Mobile launch stability & speed smoke

**Task:** CLIENT-STABILITY-MOBILE-SMOKE-001  
**Date:** 2026-06-13  
**Mode:** owner-run · **no prod mutation** · **no deploy**  
**Parent:** [CLIENT-STABILITY-001](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) · [AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md)

**Launch gate:** Mobile speed + stability smoke **required** before active acquisition / referral growth push.

**Do not disturb:** If owner is on a **stable desktop Happ session** now, run mobile smoke on **phone only** — no need to touch desktop VPN for this task.

---

## 1. Mobile client support status (inventory)

Source: UA matrix audit (2026-06-10) · post–Candidate D Happ-class shape · verify live: `ops/probe_fallback_client_sub.py`

| Question | Happ iOS / Android | Karing iOS / Android |
|----------|-------------------|----------------------|
| **Subscription format** | Full **Xray JSON** (`Happ/*` UA) | **sing-box JSON** (`Karing/*` UA) |
| **Candidate D / BenderVPN Auto?** | **Yes** — 6 relay outbounds, random balancers | **No** — **1× LV direct** `:443` |
| **Stealth split (`Intl_Stealth`)** | **Yes** — TG/IG/Meta IP + geosite rules | **No** — not in emit |
| **TG/IG/Meta relay-only** | **Yes** (product path) | **Not guaranteed** — global/TUN routing only |
| **RU direct (ya.ru, vk.com, banks)** | **Yes** — import **BenderVPN RU** Happ routing profile (fixed DirectIp, no `geoip:ru`) | **No** — no Happ routing profile; `.ru` may proxy |
| **Manual server pick** | **No** — one profile **BenderVPN Auto** | Single LV node visible |
| **Primary for launch** | **Yes** | **Exploratory only** — see [desktop fallback](CLIENT-STABILITY-DESKTOP-FALLBACK.md) |

**Mobile Happ receives the same Auto JSON as desktop Happ** (same UA class). Differences are OS VPN lifecycle (lock, background, Wi‑Fi/LTE), not subscription emit.

**Verify server emit (read-only):**

```powershell
cd D:\Va\projects\VPN
python ops/probe_fallback_client_sub.py --json
```

Expect `happ.auto_equivalent=true`, `karing.auto_equivalent=false`.

### Known mobile-specific risks

| Risk | Happ mobile | Notes |
|------|-------------|-------|
| Lock / unlock / background | **Test required** | iOS/Android may pause apps; VPN should stay connected |
| Wi‑Fi ↔ mobile data handoff | **Test required** | Listed in commercial launch checklist — often needs one reconnect |
| Airplane mode toggle | **Test required** | Should recover or reconnect cleanly |
| Random relay path quality | **Possible** | Same 6-way pool as desktop; relay #1 bias seen on desktop report(6) |
| Long-session (30+ min) | **Test required** | Desktop WebSocket issues may or may not reproduce on mobile |
| Routing profile not imported | **User error** | Without **BenderVPN RU**, RU direct + DirectIp fix not active |
| Karing wrong path | **Product** | LV direct from RU — different DPI/latency; not launch default |
| Speed variance | **Expected** | Run baseline vs VPN; 2–3 repeats; accept band not single Mbps |

---

## 2. Devices under test (owner fills)

Test **each phone you have**. Mark unavailable OS as **PENDING**.

| Slot | Device model | OS version | Client | App version | Status |
|------|--------------|------------|--------|-------------|--------|
| **A — primary** | | iOS / Android | Happ | | **PENDING** |
| **B — optional** | | iOS / Android | Karing | | **PENDING** / N/A |
| **C — other OS** | | | | | **PENDING** if no device |

Generate empty result template (local only, not committed):

```powershell
python ops/generate_mobile_smoke_template.py --write .local/mobile_smoke_results.md
```

---

## 3. Pre-test setup (once per device + client)

### 3.1 Happ (primary)

1. Install Happ from **App Store** (iOS) or **Google Play** (Android).
2. Bot or portal → copy subscription link / QR → import **BenderVPN Auto**.
3. Import **BenderVPN RU** routing profile (portal setup / `generate_happ_routing_link.py` deeplink if used before).
4. Confirm routing profile **active** in Happ.
5. **Refresh subscription** (🔄) once before smoke — note time.
6. Connect VPN; record **connect time** (seconds from tap to connected).

**Do not** refresh subscription mid-smoke.

### 3.2 Karing (exploratory only)

1. Install from [karing.app](https://karing.app/ru/download).
2. Import **same bot sub URL** as Happ.
3. Expect **one LV node** — not Auto-equivalent.
4. Connect; record connect time.

**Limitation copy for notes:** «Karing smoke = connectivity only, not Auto parity.»

---

## 4. Speed test protocol

Run on **same network** for baseline and VPN. Prefer **Wi‑Fi first**, repeat key checks on **mobile data**.

| Step | Action |
|------|--------|
| 1 | Note network: Wi‑Fi name or «LTE/5G» |
| 2 | **Disconnect VPN** → run speed test **2–3 times** |
| 3 | Record best/median: **download**, **upload**, **ping** (Mbps / ms) |
| 4 | **Connect BenderVPN** (Happ primary) → wait until stable |
| 5 | Run same speed test **2–3 times** |
| 6 | Compute rough **% loss** vs baseline median (download focus) |

**Tools (pick one):** [fast.com](https://fast.com) · [speedtest.net app](https://www.speedtest.net/apps) · operator speed test.

**Acceptance guidance (not hard SLA):**

| Verdict band | Download vs baseline |
|--------------|----------------------|
| Good | ≤ ~30% loss or still comfortable for browsing/HD video |
| SOFT | ~30–50% loss but usable |
| FAIL | > ~50% loss **and** subjectively unusable for normal browsing |

Ping: note if **+100 ms** vs baseline on same network.

### Speed table (copy per device)

| Network | Mode | Run 1 ↓/↑/ping | Run 2 | Run 3 | Median ↓ | Baseline ↓ | ~% loss |
|---------|------|----------------|-------|-------|----------|------------|---------|
| Wi‑Fi | No VPN | | | | | — | — |
| Wi‑Fi | Happ VPN | | | | | | |
| Mobile data | No VPN | | | | | — | — |
| Mobile data | Happ VPN | | | | | | |

---

## 5. Site & app matrix (per network pass)

Score: **Y** = works · **N** = fail · **P** = partial/slow · **—** = not tested

| Check | Wi‑Fi Happ | Mobile data Happ | Notes |
|-------|------------|------------------|-------|
| Setup / import | | | |
| Connect time (sec) | | | target ≤ ~10 s after first setup |
| google.com | | | |
| mail.google.com / Gmail app | | | |
| Google Docs (app or browser) | | | scroll 2 min |
| Telegram | | | |
| Instagram / Meta | | | if feasible |
| YouTube (30–60 s clip) | | | optional |
| ya.ru | | | **expect RU direct** on Happ + routing |
| vk.com | | | **expect RU direct** |
| Domestic bank / `.ru` site | | | no credentials in screenshots |
| ipinfo.io / ifconfig.me | | | intl check — not check.ru |
| fast.com / speedtest | | | see §4 |

---

## 6. Stability protocol

Run **Happ primary** unless slot B explicitly tests Karing.

| Phase | Duration | Actions | Record |
|-------|----------|---------|--------|
| **Active use** | **15 min** | Telegram + browser tab + optional YouTube | reconnects, freezes |
| **Idle lock** | **30 min** | Lock screen; phone in pocket | VPN icon still on? |
| **After unlock** | **5 min** | Open Telegram + google.com | silent death Y/N |
| **Wi‑Fi → mobile data** | — | Switch with VPN connected | auto-recover / manual reconnect / fail |
| **Mobile data → Wi‑Fi** | — | Switch back | same |
| **Airplane mode** (optional) | — | ON 10 s → OFF | reconnect time (sec) |

**Reconnect behavior:** note **automatic** vs **one manual tap** vs **repeated failures**.

---

## 7. PASS / SOFT PASS / FAIL

### PASS

- Import + routing profile setup succeeds
- Connect ≤ **~10 s** after initial setup (first connect may be slower — note separately)
- Intl blocked services work (Google, Gmail, Telegram)
- RU sites behave as expected (**direct** on Happ + **BenderVPN RU**)
- Speed acceptable for browsing / short video (see §4 bands)
- Lock/unlock does **not** kill VPN silently
- Wi‑Fi ↔ mobile data recovers **automatically or with one reconnect**
- No repeated manual reconnect loop

### SOFT PASS

- Minor slowdown or **one** reconnect on network switch; user can continue
- Docs/Gmail slightly slow but usable
- Document caveats in result table

### FAIL

- Cannot import or connect
- Intl services blocked or unusable
- Gmail/Docs/Telegram unstable
- Speed too low for normal browsing (subjective + §4 FAIL band)
- VPN **silently dies** after lock or network switch
- Repeated manual reconnect required
- Karing promoted as Auto equivalent (process fail — wrong client)

---

## 8. What to capture on FAIL

| Do | Do not |
|----|--------|
| Screenshot Happ **connected/disconnected** state — **crop sub URL / QR** | Share subscription URL or tokens |
| Note **time**, **network type**, **app version** | Commit screenshots to git |
| Happ → export diagnostic / logs if available — **local only** | Paste vless links in tickets |
| For Happ: note routing profile name (**BenderVPN RU** Y/N) | |
| Run `probe_fallback_client_sub.py` on PC — confirms server emit | |

---

## 9. Master result table (owner fills)

| Device | Client | Network phase | Duration | Speed verdict | Stability verdict | **Overall** | Date |
|--------|--------|---------------|----------|---------------|-------------------|-------------|------|
| | Happ | Wi‑Fi full | | | | **PENDING** | |
| | Happ | Mobile data full | | | | **PENDING** | |
| | Happ | Lock/unlock + switch | | — | | **PENDING** | |
| | Karing | Wi‑Fi exploratory | | | | **PENDING** / N/A | |
| Other OS | | | | | | **PENDING** | |

**Gate status:** **OPEN** until ≥1 **Happ** row = PASS or SOFT PASS on **both** Wi‑Fi and mobile data.

---

## 10. Setup friction checklist (user-facing)

| Step | Friction? | Notes |
|------|-----------|-------|
| Find Happ in store | | |
| Import sub (link/QR) | | |
| Import routing profile | | |
| «0 servers» confusion | | expected — Auto picks server |
| First connect time | | |
| Refresh subscription clarity | | |
| Support path obvious | | bot / FAQ |

---

## 11. Relationship to other tracks

| Track | Role |
|-------|------|
| **Happ mobile** | **Launch primary** — this smoke validates it |
| **Happ desktop long-session** | Separate — [recovery §9](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) |
| **Desktop fallback (v2rayN/Karing)** | Windows only — [CLIENT-STABILITY-DESKTOP-FALLBACK.md](CLIENT-STABILITY-DESKTOP-FALLBACK.md) |
| **Karing mobile** | Exploratory — not launch default |
| **Referral / acquisition growth** | **Blocked** until mobile smoke PASS/SOFT PASS recorded |

---

## 12. Tooling

```powershell
python ops/probe_fallback_client_sub.py
python ops/generate_mobile_smoke_template.py --write .local/mobile_smoke_results.md
python ops/happ_routing_directip_guard.py
```

---

## 13. Quick owner runbook (summary)

1. **Phone only** — leave desktop VPN as-is if stable.
2. Happ → import sub + **BenderVPN RU** routing → connect on **Wi‑Fi**.
3. Baseline speed ×2–3 → VPN speed ×2–3 → site matrix → 15 min active use.
4. Lock **30 min** → unlock test → switch to **mobile data** → repeat speed + key sites.
5. Optional: airplane toggle; optional Karing exploratory pass.
6. Fill §9 table → PASS / SOFT PASS / FAIL.
7. Update this doc or `.local/mobile_smoke_results.md` — **do not commit** raw screenshots or sub URLs.
