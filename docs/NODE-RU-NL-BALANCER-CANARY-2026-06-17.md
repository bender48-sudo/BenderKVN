# RU/NL Node Connection + Canary Balancer Path — 2026-06-17

**Task:** NODE-RU-NL-BALANCER-CANARY-001
**Status:** PARTIAL — NL validated and moved to `staging`; owner canary path generated;
live multi-node delivery apply remains owner-gated.
**Companion:** [`VPN_PRODUCTION_GUARDRAILS.md`](VPN_PRODUCTION_GUARDRAILS.md) ·
[`VPN-NODE-ONBOARDING-EXECUTION.md`](VPN-NODE-ONBOARDING-EXECUTION.md) ·
[`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md)

> Read-only SSH inventory only. No remote mutation, no Remna/Caddy/template/
> subscription change, no live selector apply. IPs/secrets redacted (node IDs only).

---

## 1. SSH node inventory (read-only)

All four nodes reachable via existing SSH aliases. System checks were read-only;
public IPs redacted at source.

| Node (alias) | SSH | Services observed | Network | Resources | Logs | Verdict |
|--------------|-----|-------------------|---------|-----------|------|---------|
| lv-exit-1 (`bvpn-lv`) | OK | `remnanode` + `adguardhome` up 13d; caddy active; ports 443/8443/9443/2053/18443 | ports listening | 2 CPU / 2GB (disk 69%) | clean | **PASS** (production exit, unchanged) |
| nl-node-1 (`bvpn-nl`) | OK | `remnanode` + `caddy-selfsteal` up 4w; ports 443/8443/9443/4433 | ports listening | 2 CPU / 2GB (disk 17%, load 0) | clean | **PASS (node-level)** |
| ru-relay (`bvpn-relay`) | OK | raw xray (no docker); ports 443/8443/9443; zabbix-agent | ports listening | 1 CPU / 2GB (disk 18%, load 0) | clean | **WARN** (reachable; identity vs registry relay-1/2 ambiguous from one alias) |
| ams-backup-edge (`bvpn-ams`) | OK | `remnawave` panel (healthy) + db/redis + `subscription-page` ×2 + `remna-shop-bot` + `caddy-selfsteal` | ports listening | 2 CPU / 2GB (disk 34%) | clean | **WARN** (control plane + sub edge; not VPN delivery exit) |

Notes:
- **AMS** is the Remnawave **control plane + subscription edge + shop bot host** —
  confirms registry `ams-backup-edge` (not delivery capacity).
- **`bvpn-relay`** maps to a single RU relay host; the redacted registry holds two
  RU relay entries (`ru-relay-1` suspect, `ru-relay-2` ok). Node reachability does
  **not** clear `ru-relay-1`'s client-stability suspicion → relay-1 stays suspect.
- **NL** is genuinely up and serving the node stack (remnanode + selfsteal, 4-week
  uptime) — strong node-level evidence, but **not** A2/A4 traffic-proven.

## 2. Registry alignment

| Node | Before | After | Why |
|------|--------|-------|-----|
| nl-node-1 | `status: disabled`, smoke `not_in_live_subs` (2026-06-11) | `status: staging`, smoke `staging_node_reachable` (2026-06-17) | SSH PASS: node + remnanode + selfsteal healthy. Honest onboarding state. |
| (all others) | — | unchanged | relay identity ambiguous; relay-1 stays suspect; LV/AMS already correct |

**Honesty guarantees (unchanged after edit):**
- `nl-node-1`: `delivery_path_eligible=false`, `canary_percent=0`,
  `allow_new_assignments=false` → does NOT count toward `delivery_path_nodes`.
- `delivery_path_nodes = 1` (lv-exit-1 only). PUBLIC_PROD still NO-GO,
  `APPLY_ALLOWED=false`, all GO gates still false.
- Selector still hard-excludes NL with reason
  "NL staging — A2/A4 controlled smoke + owner approval gate pending".

## 3. Balancer architecture (what "balancer" means here)

This repo's delivery balancing is **registry-driven selector composition**, not a
one-off patch:

```
node registry (SoT) -> node smoke matrix -> selector cohort -> production guardrails
  -> selector apply gate -> owner-approved live apply (subscription Intl selectors)
```

- The registry does **not** drive live subscription generation yet
  (SUB-GEN-SELECTOR-STRATEGY-001 OPEN), so registry edits are **repo-side planning
  with zero live effect** — inherently safe and git-revertible.
- The **only real canary available today** is the **owner-only canary profile**
  (`ops/generate_owner_canary_profile.py`, `.local` output) — an isolated client
  profile the owner imports manually. It changes **no** production default and is
  not mass-issued.
- A **public/user canary** (NL or relay-2 at `canary_percent>0`) requires live
  subscription/selector apply → that is the gated **APPROVE PROD APPLY** step,
  deliberately out of this sprint's surface. We did **not** fake canary state.

## 4. Changes made

**Local repo only (no remote mutation):**
- `ops/config/vpn_node_registry.yaml`: nl-node-1 `disabled→staging` + SSH-evidence
  health/notes; `updated_at` bump.
- `ops/vpn_node_selector.py`: NL hard-gate generalized to cover `staging` (keeps
  A2/A4 + owner-approval reason); removed redundant lower NL special-case.
- Tests updated for the new honest NL state (still excluded everywhere).
- This doc + backlog updates.

**Remote nodes:** read-only inventory only. **No** services restarted/reloaded.
**No** Remna/Caddy/template/subscription change. LV path untouched.

## 5. Smoke results

| Check | Before | After |
|-------|--------|-------|
| `validate_vpn_node_registry.py` | OK | OK |
| smoke matrix `nl-node-1` | BLOCKED (disabled) | **WARN (staging; promotion gate pending)** |
| `delivery_path_nodes` | 1 | 1 (honest, unchanged) |
| `public_prod_go` | False | False |
| apply gate PUBLIC_PROD `APPLY_ALLOWED` | False | False |
| CANARY cohort | NO-GO | NO-GO (no canary-ready node; not faked) |
| owner canary profile | relay2-lab candidate | relay2-lab candidate; NL excluded even with flags |
| `pytest tests/` | 250 passed | 250 passed |

Owner canary profile written to `.local/owner_canary_profile.{json,md}` (NOT
committed). Import/rollback instructions are inside that profile.

## 6. Speed / stability / scalability impact

- **Speed:** no change (no routing/selector change applied).
- **Stability:** no change to live path; LV production intact; relay-1 still excluded.
- **Scalability:** materially advanced on the **pipeline** — NL is now a validated
  `staging` candidate (out of BLOCKED), with a clear, gated promotion path to become
  the 2nd delivery path. Actual capacity (`delivery_path_nodes`) unchanged until the
  gated apply.

## 7. Rollback

- Registry/selector/test changes are git-tracked:
  `git checkout ops/config/vpn_node_registry.yaml ops/vpn_node_selector.py tests/`
  or `git revert <commit>`.
- Pre-edit registry snapshot: `.local/vpn_node_registry.backup_<ts>.yaml` (local).
- No remote rollback needed — **no remote mutation was performed.**

## 8. Gate update

| Gate | Status |
|------|--------|
| LAB_OWNER | GO (unchanged) |
| Owner canary (manual profile) | AVAILABLE (owner-only `.local`) |
| Public/user CANARY | NO-GO (needs canary-ready node + APPROVE PROD APPLY) |
| PUBLIC_PROD | NO-GO (`delivery_path_nodes=1`) |
| Small paid beta | NO-GO |
| Commercial launch | NO-GO |
| 300 / 30k | NO-GO |

## 9. Remaining blockers to 2-path delivery

1. NL A2/A4 controlled traffic smoke (Telegram/Google/Meta via NL exit) +
   MONITOR-FLAP closeout.
2. NL acceptance checklist P0 (subscription inclusion, Happ import, routing sanity).
3. Owner `APPROVE PROD APPLY` for live selector/subscription inclusion of NL.
4. Only then: NL `staging→canary` (`canary_percent>0`) → `active` +
   `delivery_path_eligible=true` → `delivery_path_nodes=2`.

## 10. Exact next owner action

- **APPROVE NL A2/A4 CONTROLLED CANARY SMOKE** — authorize a controlled NL traffic
  smoke (owner/staging cohort only) so NL can progress `staging→canary`; OR
- **APPROVE OWNER CANARY IMPORT** — import `.local/owner_canary_profile.md`
  (relay2-lab isolation) to validate the canary path client-side now.

No broad production rollout is requested or performed.
