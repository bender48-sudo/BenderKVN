# NL Canary Import Artifact Fix — 2026-06-18

**Task:** NL-CANARY-IMPORT-ARTIFACT-FIX-001
**Status:** **DONE** (generator + validator + docs). NL traffic smoke remains **NOT PASSED**.
**Companion:** [`NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md`](NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md)

---

## 1. Incident

Owner imported `.local/independent_exit_nl_canary.json` into Happ expecting a VPN profile.
That file was **metadata/runbook JSON** (scorecard, checklist, synthetic preview) — **not**
importable VLESS/REALITY config. Happ failed/crashed/disconnected immediately.

**Expected:** metadata JSON is never valid Happ import input.
**NL smoke:** **NOT performed** · registry **not** promoted.

---

## 2. Root cause

- Ambiguous filenames (`*.json` looked importable).
- Runbook said “import .md/json” without separating metadata vs profile.
- No fail-fast validator before client import.
- No separate validated `*_IMPORTABLE_PROFILE.json` output.

---

## 3. Fix

### New artifact names (`.local` only — not committed)

| File | Import into Happ? |
|------|-------------------|
| `independent_exit_nl_canary_RUNBOOK.md` | **NO** — instructions |
| `independent_exit_nl_canary_METADATA.json` | **NO** — metadata/runbook |
| `independent_exit_nl_canary_IMPORTABLE_PROFILE.json` | **YES** — only if `status=GENERATED` |

Metadata JSON includes:
- `artifact_type: metadata_runbook_not_importable`
- `importable_profile: false`
- `do_not_import_this_file: true`
- `warning: DO NOT IMPORT THIS JSON INTO HAPP...`

### Validator

`ops/validate_happ_importable_profile.py` rejects metadata/runbook JSON and accepts
known Happ/Xray profile shapes (outbounds + vless proxies + routing).

### Importable profile generation

`ops/generate_independent_exit_canary.py` reads owner config from (ignored, never committed):

1. `.secrets/nl_owner_direct_config.json` (preferred)
2. `.secrets/owner_sub.json`

Requires NL direct + relay-2 outbounds. Output validated before write.
If missing: `IMPORTABLE_PROFILE_NOT_GENERATED_MISSING_OWNER_CONFIG`.

---

## 4. Registry / gates (unchanged)

- `nl-node-1`: staging · `acceptance_status=pending_traffic_smoke`
- `delivery_path_eligible=false` · `independent_exit_paths=1`
- PUBLIC_PROD **NO-GO**

---

## 5. Next owner action

**GENERATE IMPORTABLE NL PROFILE FROM OWNER CONFIG** — place NL-capable subscription JSON at
`.secrets/nl_owner_direct_config.json`, run:

```bash
python ops/generate_independent_exit_canary.py
python ops/validate_happ_importable_profile.py .local/independent_exit_nl_canary_IMPORTABLE_PROFILE.json
```

Then **RUN OWNER NL TRAFFIC SMOKE** using only the validated `*_IMPORTABLE_PROFILE.json`.

---

## 6. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Registry promotion | **NO** |
| NL smoke PASS claimed | **NO** |
| Secrets committed | **NO** |
| 300/30k GO claimed | **NO** |
