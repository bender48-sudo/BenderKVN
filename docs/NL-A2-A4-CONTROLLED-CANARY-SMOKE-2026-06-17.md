# NL A2/A4 Controlled Canary Smoke — 2026-06-17

**Task:** NL-A2-A4-CONTROLLED-CANARY-SMOKE-001
**Status:** PARTIAL — node-level SSH PASS; synthetic canary preview + owner artifact ready;
A2/A4 **traffic** smoke still owner-gated.
**Companion:** [`NODE-RU-NL-BALANCER-CANARY-2026-06-17.md`](NODE-RU-NL-BALANCER-CANARY-2026-06-17.md) ·
[`VPN_PRODUCTION_GUARDRAILS.md`](VPN_PRODUCTION_GUARDRAILS.md) ·
[`ops/patch_add_nl_intl_gated.py`](../ops/patch_add_nl_intl_gated.py)

> Read-only SSH + local dry-run only. No remote mutation, no Remna/Caddy/template/
> subscription change, no PUBLIC_PROD apply. IPs/secrets redacted (node IDs only).

---

## 1. A2/A4 interpretation (repo context)

| Term | Meaning in BenderVPN repo |
|------|---------------------------|
| **A2** | Amsterdam/NL **exit** as second geographic delivery path (not relay diversity) |
| **A4** | NL direct **×4** hosts in **`Intl_Direct`** selector only (`VPN-AUD-220` / `patch_add_nl_intl_gated.py`) |
| **Controlled** | Owner/staging cohort only; `canary_percent=0` in live registry; synthetic preview for planning |
| **Not in scope** | PUBLIC_PROD apply, mass subscription refresh, disabling LV, relay2 production default |

Stealth invariant: **`Intl_Stealth`** stays relay-only (TG/Meta/IG never via NL direct).

---

## 2. SSH read-only revalidation (nl-node-1 / `bvpn-nl`)

| Check | Result | Verdict |
|-------|--------|---------|
| SSH reachability | OK | PASS |
| Hostname / uptime | up ~58d, load ~0.1 | PASS |
| OS/kernel | Ubuntu 5.15 x86_64 | PASS |
| CPU/RAM/disk | 2 vCPU, ~1.9GB RAM, disk 17% | PASS |
| Time sync | UTC, synchronized | PASS |
| remnanode | Up ~4 weeks | PASS |
| caddy-selfsteal | Up ~4 weeks | PASS |
| VPN ports | 443, 8443, 9443, 4433 listening | PASS |
| Firewall | ufw active | PASS |
| Outbound | HTTPS 200 (~0.17s) | PASS |
| Service logs | clean (redacted) | PASS |
| Cert maintenance | ACME renewal info present | PASS |

**Node verdict:** **PASS (node-level)** — healthy stack, not yet A2/A4 traffic-proven.

---

## 3. Canary design

### What was tested

- Read-only SSH inventory on `bvpn-nl`
- Registry validation + smoke matrix + apply gate
- CANARY dry-run with current registry (NL excluded — honest)
- Synthetic canary preview (`--synthetic-canary-node nl-node-1`) — in-memory only
- Owner artifact: `.local/nl_canary_owner_profile.{json,md}` + `nl_canary_selector_preview.json`

### What did NOT change

- `delivery_path_eligible=false`, `canary_percent=0`, `allow_new_assignments=false`
- `delivery_path_nodes=1` (lv-exit-1 only)
- PUBLIC_PROD NO-GO, APPLY_ALLOWED=false
- LV production path intact
- No Remna/Caddy/template/subscription/deploy/reload

### Rollback

- Registry: `git checkout ops/config/vpn_node_registry.yaml` or revert commit
- Pre-edit backup: `.local/vpn_node_registry.backup_20260617_nl_canary.yaml`
- No remote rollback needed (no remote mutation)

---

## 4. Registry changes

| Field | Before | After | Why safe |
|-------|--------|-------|----------|
| `health.last_smoke_status` | `staging_node_reachable` | `ssh_revalidation_pass` | SSH evidence refresh |
| `notes` | NODE-RU-NL-BALANCER-CANARY-001 | NL-A2-A4-CONTROLLED-CANARY-SMOKE-001 | Sprint traceability |
| `updated_at` | 2026-06-17T00:00:00Z | 2026-06-17T20:00:00Z | Timestamp bump |
| `canary_percent` | 0 | **0** (unchanged) | No fake canary |
| `delivery_path_eligible` | false | **false** (unchanged) | Not production capacity |
| `status` | staging | **staging** (unchanged) | Traffic smoke pending |

**Production capacity count:** unchanged (`delivery_path_nodes=1`).

---

## 5. Generated canary artifact

| Path | Purpose | Committed |
|------|---------|-----------|
| `.local/nl_canary_owner_profile.json` | Structured smoke plan + synthetic preview | **NO** |
| `.local/nl_canary_owner_profile.md` | Owner import runbook + checklist | **NO** |
| `.local/nl_canary_selector_preview.json` | Synthetic CANARY outbound mapping | **NO** |
| `.local/generated_vpn_config_preview.*` | Generator output (synthetic NL) | **NO** |

**Import:** add NEW Happ profile named *"BenderVPN NL Canary — owner/staging only — do NOT refresh subscription"*; paste owner-held NL config from vault; disable auto-refresh.

**Rollback:** switch back to normal BenderVPN profile; delete NL canary profile; no server change unless separate `patch_add_nl_intl_gated.py --apply`.

**Generator:** [`ops/generate_nl_canary_smoke_artifact.py`](../ops/generate_nl_canary_smoke_artifact.py) · synthetic overlay in [`ops/generate_vpn_config_from_registry.py`](../ops/generate_vpn_config_from_registry.py) (`--synthetic-canary-node`).

---

## 6. Smoke results

| Command | Result |
|---------|--------|
| `validate_vpn_node_registry.py` | OK |
| `vpn_node_smoke_matrix.py --markdown` | nl-node-1 WARN (staging); `canary_ready_nodes=0` |
| `vpn_selector_apply_gate.py --cohort PUBLIC_PROD` | APPLY_ALLOWED=false |
| `generate_vpn_config_from_registry.py --cohort CANARY --dry-run` | lv-exit-1 only (NL excluded) |
| `generate_vpn_config_from_registry.py --cohort CANARY --synthetic-canary-node nl-node-1` | lv-exit-1 + nl-node-1 preview |
| `generate_nl_canary_smoke_artifact.py` | artifacts written to `.local/` |
| `vpn_stealth_routing_guard` (pytest fixtures) | PASS (7 tests) |
| `pytest` (VPN suites) | 68+ passed |
| `git diff --check` | clean on staged files |

Synthetic preview outbounds: `out-lv-exit-1`, `out-nl-node-1` (position-independent tags).

---

## 7. Gate update

| Gate | Status |
|------|--------|
| LAB_OWNER | GO |
| NL node-level SSH | **PASS** |
| NL A2/A4 traffic smoke | **NOT STARTED** (owner import + traffic test) |
| Owner NL canary artifact | **AVAILABLE** (`.local/`) |
| Public/user CANARY | NO-GO (`canary_percent=0`) |
| PUBLIC_PROD | NO-GO (`delivery_path_nodes=1`) |
| F&F / paid beta / commercial | NO-GO |
| 300 / 30k | NO-GO |

---

## 8. Remaining blockers to 2-path delivery

1. Owner **APPROVE NL CANARY TRAFFIC SMOKE** — import `.local/nl_canary_owner_profile.md` and run A2/A4 checklist (TG/Google/Meta).
2. MONITOR-FLAP-TUNE closeout reviewed or PARTIAL soak risk accepted.
3. NL acceptance checklist P0 (Happ import, routing sanity through NL exit).
4. Owner **APPROVE PROD APPLY** for live `patch_add_nl_intl_gated.py` / selector inclusion.
5. Only then: `staging→canary` (`canary_percent>0`) → `active` + `delivery_path_eligible=true`.

---

## 9. Exact next owner action

**APPROVE NL CANARY TRAFFIC SMOKE** — import the owner NL canary profile from `.local/` and run the A2/A4 traffic checklist on owner/staging devices only.

---

## 10. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Deploy/reload | **NO** |
| Remna/Caddy/template/subscription changes | **NO** |
| VPN routing changes (live) | **NO** |
| LV path preserved | **YES** |
| Raw secrets printed | **NO** |
| Raw logs committed | **NO** |
| 300/30k GO claimed | **NO** |
| "Undetectable VPN" claimed | **NO** |
