# P1-RED-SSH-01: run ssh_audit_from_ams.sh on AMS panel (needs bvpn_ams_ed25519).
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$Script = Join-Path $RepoRoot "ops\ssh_audit_from_ams.sh"
if (-not (Test-Path $Key)) { throw "Missing $Key — run ops/ssh_rollout_operator_keys.ps1" }
& scp -o BatchMode=yes -o IdentitiesOnly=yes -i $Key -P 3344 $Script "root@168.100.11.140:/tmp/ssh_audit_from_ams.sh"
& ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $Key -p 3344 root@168.100.11.140 "sed -i 's/\r$//' /tmp/ssh_audit_from_ams.sh; bash /tmp/ssh_audit_from_ams.sh"
if ($LASTEXITCODE -ne 0) { throw "remote audit failed" }
