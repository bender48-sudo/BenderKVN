# CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001 — Desktop Relay Path Fix

**Task:** CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001
**Date:** 2026-06-17
**Mode:** Action-first desktop relay-path fix (registry annotation + owner/staging canary; read-only server check)
**Parent:** [`CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md)
**Branch / HEAD baseline:** `product-referral-cabinet-ui-v1` @ `463cd6e`

> No prod/Remna/Caddy/template/subscription/routing mutation in this task.
> Endpoints redacted to non-identifying tokens (`ep_<hash>:port`). No raw IPs/UUIDs/URLs.

---

## 1. Bad endpoint → real node/path mapping

Mapping derived from the report's `selected_server.json` outbound addresses (hashed
to redacted tokens) cross-checked against `ops/balancer_selectors.py` selectors,
`ssh/config.example` host blocks, and the node registry. No raw IP printed/committed.

| Field | Bad path | Healthy path |
|-------|----------|--------------|
| endpoint (redacted) | `ep_20e413bd:443` | `ep_d1a601f6:443` |
| outbounds | `proxy`, `proxy-2`, `proxy-3` | `proxy-4`, `proxy-5`, `proxy-6` |
| selector const | `RELAY1_SELECTOR` | `RELAY2_SELECTOR` |
| ssh alias | `bvpn-relay` (relay #1) | `bvpn-relay2` (relay #2) |
| registry node | `ru-relay-1` | `ru-relay-2` |
| registry monitor_status | `suspect` | `ok` |
| report(10) reset share | ~80.3% of long-lived resets | comparatively healthy |

- **bad_path_id:** `ru-relay-1` (relay #1, `ep_20e413bd:443`).
- **healthy_path_id:** `ru-relay-2` (relay #2, `ep_d1a601f6:443`).
- **confidence:** HIGH — `selected_server.json` address hashes match the documented
  redacted tokens; positional outbound grouping matches `RELAY1_SELECTOR`/`RELAY2_SELECTOR`;
  independently corroborates the pre-existing `ru-relay-1` suspect status (dial/open storms).
- Both `Intl_Direct` and `Intl_Stealth` balancers span all 6 outbounds, so the bad relay
  also carried stealth (TG/Meta/IG) traffic.

The analyzer now maps the dominant error endpoint to its outbound group natively
(`error_endpoints.top_error_endpoint_outbounds` → `["proxy","proxy-2","proxy-3"]`).

---

## 2. Server-side read-only check — relay #1 (`bvpn-relay`)

Read-only SSH, `2026-06-17`. No restart, no mutation.

| Check | Result | Verdict |
|-------|--------|---------|
| hostname / reachability | reachable | PASS |
| uptime / load | up 48d, load 0.38/0.19/0.12 | PASS |
| memory / disk | 665Mi/1.9Gi used, disk 18% | PASS |
| time sync | synchronized: yes | PASS |
| **xray service** | `systemctl is-active xray` = **inactive**; **no xray process** | **FAIL** |
| **port 443/8443/9443 listener** | held by **`hysteria`**, not VLESS/REALITY/xray | **FAIL** |
| established :443 conns | 843 | INFO (served by hysteria, not the VLESS service the profile targets) |
| firewall | active | PASS |

**Overall verdict: FAIL (service mismatch).** The relay #1 endpoint that the desktop
client targets via VLESS/TCP/REALITY has **xray down**; its ports are occupied by
`hysteria`. VLESS-REALITY handshakes to this endpoint cannot be served correctly,
which is a strong server-side cause for the "connection forcibly/download closed"
resets concentrated on `ep_20e413bd:443`.

---

## 3. Correction decision

- **Server repair (restart/restore xray on relay #1): NOT performed.** Relay #1 is a
  **shared live production relay** (Candidate D injectHosts, 843 active connections).
  Restoring xray requires resolving the `hysteria` port conflict — an **all-users prod
  action**, not a safe single-command rollbackable restart. Per global safety rule 8 this
  requires explicit `APPROVE DESKTOP RELAY SERVER REPAIR DEPLOY`.
- **Registry degradation: YES (annotation).** `ru-relay-1` annotated with the incident
  evidence; excluded from owner/desktop canary; healthy `ru-relay-2` marked as the
  desktop-canary path. No live config/template/subscription changed.
- **Owner/staging desktop canary exclusion: YES.** Artifact generated that excludes the
  bad relay path and keeps the healthy path.

---

## 4. Registry changes (`ops/config/vpn_node_registry.yaml`)

`ru-relay-1`:
- `health.last_smoke_status: desktop_reset_dominant`, `last_smoke_at: 2026-06-17`
- `incident: true`, `exclude_from_desktop_canary: true`
- `last_incident_ref: CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001`
- `exclude_reason` + `notes` record report(10) 80.3% reset share and the server check
  (xray inactive, hysteria on ports). Status stays `active` (no unilateral live drain).

`ru-relay-2`:
- `desktop_canary_path: true`; notes mark it the healthy desktop-canary path.

`PUBLIC_PROD` remains NO-GO (`delivery_path_nodes=1`). No production flags flipped.

---

## 5. Owner/staging desktop relay-path canary

**Generator:** [`ops/generate_desktop_relay_path_canary.py`](../ops/generate_desktop_relay_path_canary.py)
**Artifacts (owner-only, `.local/`, not committed):**
`desktop_relay_path_canary.json`, `desktop_relay_path_canary.md`

- **Excludes:** `ep_20e413bd` (relay #1) outbounds `proxy/proxy-2/proxy-3`.
- **Keeps:** `ep_d1a601f6` (relay #2) outbounds `proxy-4/proxy-5/proxy-6`.
- Pins `Intl_Direct` + `Intl_Stealth` to relay #2 (stealth split preserved).
- Removes relay #1 from in-core direct (anti-loop) rules; keeps relay #2 self-bypass.
- No geoip:ru DirectIp, no relay IP in Happ DirectIp, no FallbackTag=direct, no flat
  Super_Balancer, no user-facing server picker.
- **Build tool (owner builds importable JSON from held sub):**
  `ops/generate_happ_relay2_lab_profile.py`.
- **Rollback:** switch back to normal "BenderVPN Auto" profile; no server change to revert.

---

## 6. Smoke / verify

| Check | Result |
|-------|--------|
| `py_compile` (analyzer, canary gen, registry model, generator, integrity, stealth, matrix, gate) | PASS |
| `validate_vpn_node_registry.py` | PASS (registry OK, no secrets) |
| `vpn_node_smoke_matrix.py --markdown` | relay-1 FAIL/excluded; PUBLIC_PROD NO-GO (expected) |
| `vpn_selector_apply_gate.py --cohort PUBLIC_PROD` | apply disabled / NO-GO (expected) |
| desktop canary generator | tokens correct, prod default unchanged |
| pytest (analyzer + canary + registry + relay1 policy) | 40 passed |
| `git diff --check` | clean |
| secret scan (committed files) | only RFC5737/RFC1918 doc IPs + redaction pattern |

Config-integrity + stealth-routing verifiers require an owner-held template (not committed),
so they run at owner import time; the relay2-lab generator's own `validate_*` enforces the
stealth split and relay-2-only invariants.

---

## 7. Gate status

| Gate | Status |
|------|--------|
| Desktop stability | OPEN — bad path mapped + excluded; PASS only after owner imports canary and confirms |
| Owner relay-path canary | READY — `APPROVE OWNER RELAY-PATH CANARY IMPORT` |
| Relay #1 server repair | BLOCKED on owner — `APPROVE DESKTOP RELAY SERVER REPAIR DEPLOY` (all-users prod) |
| PUBLIC_PROD | NO-GO (`delivery_path_nodes=1`) |
| 300 / 30k | NO-GO (need ≥2 proven delivery paths) |

---

## 8. Owner next action — choose ONE

- **`APPROVE OWNER RELAY-PATH CANARY IMPORT`** — import the relay-2-only desktop canary and
  run a 10–15 min long-session test (recommended immediate workaround).
- **`APPROVE DESKTOP RELAY SERVER REPAIR DEPLOY`** — authorize the all-users prod action to
  restore xray / resolve the hysteria port conflict on relay #1.

> Desktop PASS is NOT claimed. 300/30k GO is NOT claimed. No live prod mutation performed.
