# New Independent Exit Path — 2026-06-17

**Task:** NEW-INDEPENDENT-EXIT-PATH-001
**Outcome:** **PATH A** — `nl-node-1` validated as the **second independent exit candidate**.
Repo support (criteria, model, validator, canary artifact, tests) landed. Promotion to
counted capacity is **owner-gated** behind a controlled A2/A4 traffic smoke.
**Companion:** [`RU-RELAY-ARCH-UNIFICATION-2026-06-17.md`](RU-RELAY-ARCH-UNIFICATION-2026-06-17.md) ·
[`NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md`](NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md) ·
[`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md)

> Read-only SSH + local dry-run only. No remote mutation, no Remna/Caddy/template/
> subscription change, no PUBLIC_PROD apply. IPs/secrets redacted as `ep_<hash>:port`.

---

## 1. Why this task

Single-path debt: `lv-exit-1` is the only proven delivery/exit path. The RU relays
(`ru-relay-1`, `ru-relay-2`) are compliant hysteria frontends that **forward to the same
upstream group** (`ru-fwd-upstream-1`) and ultimately exit via LV — they are **not**
independent delivery capacity. Goal: a real second independent exit with its own egress,
lifecycle, generator support, canary, rollback, and smoke.

---

## 2. INDEPENDENT_EXIT_PATH_V1 criteria

A node counts as an **independent exit** only if all hold:

1. independent upstream/provider or clearly independent egress;
2. **not** the same `shared_upstream_group` as existing relays;
3. `path_role=exit` (not relay frontend);
4. service architecture documented + `architecture_compliance=compliant`;
5. health checks (node-level smoke);
6. canary/drain + rollback support;
7. generator support (CANARY preview);
8. config integrity + stealth/routing guard compatible;
9. lifecycle `staging → canary → production`;
10. acceptance traffic smoke PASS before `delivery_path_eligible=true`.

**Counting rule (honest capacity):** exits sharing a `shared_upstream_group` collapse to
**one** independent path; relays/backup/lab/staging/non-eligible never count;
`PUBLIC_PROD` requires **≥2** independent exit paths.

Implemented as `count_independent_exit_paths()` (validator) and `is_independent_exit()` /
`is_independent_exit_candidate()` (model).

---

## 3. Capacity truth (current)

| Path | Type | Egress (redacted) | Independent exit? |
|------|------|-------------------|-------------------|
| `lv-exit-1` | Real exit (xray/REALITY) | `ep_82c23da5` | **YES** (counts as 1) |
| `ru-relay-1` | hysteria frontend | → `ru-fwd-upstream-1` → LV | No (shared upstream) |
| `ru-relay-2` | hysteria frontend | → `ru-fwd-upstream-1` → LV | No (shared upstream) |
| `nl-node-1` | Real exit (remnanode VLESS/REALITY) | `ep_2a1adf7b` | **Candidate** (not yet counted) |

`delivery_path_nodes = 1` · `independent_exit_paths = 1` · PUBLIC_PROD **NO-GO**.

---

## 4. NL decision: SUITABLE (PATH A)

Read-only check on `bvpn-nl` (2026-06-17):

| Check | Result |
|-------|--------|
| Exit service | `remnanode` container (VLESS/REALITY) Up ~4w |
| Hysteria forwarder | **inactive / not present** (not a relay frontend) |
| Egress IP token | `ep_2a1adf7b` — **distinct** from LV `ep_82c23da5` and RU upstream `ep_4b84b15b` |
| Ports | 443 (REALITY), 8443 (XHTTP), 4433 (backup edge) listening; 9443 selfsteal DENY external |
| Firewall | ufw active, scoped per port |
| Node health | up ~57d, load ~0.1 |

**Verdict:** NL is a genuinely independent exit (own provider/geo/egress, real exit stack).
The blockers are **acceptance**, not architecture:

- `acceptance_status=pending_traffic_smoke`;
- owner A2/A4 traffic smoke (TG via stealth relay, Google/general via NL direct);
- then `staging → canary` (`canary_percent>0`) → `active` + `delivery_path_eligible=true`.

No NL provisioning/reconfiguration was required (PATH C / PATH B not needed).

---

## 5. Changes

### Repo (committed)

| File | Change |
|------|--------|
| `ops/validate_vpn_node_registry.py` | `count_independent_exit_paths()` + summary line `independent_exit_paths` |
| `ops/vpn_registry_model.py` | `is_independent_exit()`, `is_independent_exit_candidate()`; model fields |
| `ops/generate_independent_exit_canary.py` | New: INDEPENDENT_EXIT_PATH_V1 scorecard + canary artifact (.local only) |
| `ops/config/vpn_node_registry.yaml` | `nl-node-1`: `architecture_compliance=compliant`, `independent_exit_candidate=true`, `acceptance_status=pending_traffic_smoke`, evidence notes |
| `tests/test_independent_exit_path.py` | New: counting + helper tests |
| docs/backlog | This doc + capacity plan / runbook / acceptance / backlog updates |

### Server-side

**None.** Read-only SSH only. No deploy/reload/restart, no Remna/Caddy/template/subscription change.

### Honesty guard

`nl-node-1` stays `status=staging`, `delivery_path_eligible=false`, `canary_percent=0` →
`independent_exit_paths=1`. The candidate cannot inflate capacity or be selected for
production. `generate_independent_exit_canary.py` **refuses** to build if the candidate is
already counted.

---

## 6. Canary artifact (.local only — not committed)

| Path | Purpose |
|------|---------|
| `.local/independent_exit_nl_canary.json` | Scorecard + synthetic CANARY preview + smoke/rollback |
| `.local/independent_exit_nl_canary.md` | Owner import + controlled traffic-smoke runbook |

Import a NEW Happ profile (owner-held NL config from vault), disable auto-refresh, run
the A2/A4 checklist. Rollback = switch back to normal profile; no server change.

---

## 7. Tests / smoke

| Command | Result |
|---------|--------|
| `validate_vpn_node_registry.py` | OK · `independent_exit_paths=1` |
| `vpn_selector_apply_gate.py --cohort PUBLIC_PROD` | APPLY_ALLOWED=False (NO-GO) |
| `generate_vpn_config_from_registry.py --cohort CANARY --dry-run` | GO (lv only; NL excluded) |
| `generate_vpn_config_from_registry.py --cohort PUBLIC_PROD --dry-run` | NO-GO (paths=1 < 2) |
| `generate_independent_exit_canary.py` | artifacts written; blockers=[acceptance smoke] |
| pytest (registry/model/arch/generator/independent-exit/stealth) | **65 passed** |
| `git diff --check` | clean |
| secret scan (committed files) | clean (no IPs/URLs/tokens) |

---

## 8. Gate update

| Gate | Status |
|------|--------|
| LAB_OWNER | GO |
| NL independent-exit architecture | **VALIDATED** |
| NL acceptance traffic smoke | **PENDING (owner)** |
| CANARY (public/user) | NO-GO (`canary_percent=0`) |
| PUBLIC_PROD | NO-GO (`independent_exit_paths=1`) |
| Paid beta / commercial | NO-GO |
| 300 / 30k | NO-GO |

---

## 9. Next owner action

**APPROVE NL INDEPENDENT EXIT TRAFFIC SMOKE** — import `.local/independent_exit_nl_canary.md`
and run the A2/A4 controlled traffic checklist on owner/staging devices. On PASS, a separate
owner-approved task promotes `nl-node-1` to canary then active (`delivery_path_eligible=true`),
making `independent_exit_paths=2`.

---

## 10. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Deploy/reload | **NO** |
| Remna/Caddy/template/subscription changes | **NO** |
| VPN routing changes (live) | **NO** |
| LV path preserved | **YES** |
| RU relays claimed as independent | **NO** |
| `delivery_path_nodes` inflated | **NO** (stays 1) |
| Raw logs/secrets committed | **NO** |
| Desktop PASS claimed | **NO** |
| 300/30k GO claimed | **NO** |
