# Pre-deploy VPN product gate (Windows workstation with panel token).
# Full RU probes + autotrim dry-run: run on bvpn-lv after sync (install_latency_autotrim_cron.sh).
# Speed (relay CPU/bw): python ops/diagnose_throughput.py --ssh --ssh-alias bvpn-relay bvpn-relay2
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = "python"
$fail = 0
function Step($label, $cmd) {
    Write-Host "`n=== $label ===" -ForegroundColor Cyan
    & $py @cmd
    if ($LASTEXITCODE -ne 0) { $script:fail = 1; Write-Host "FAIL: $label" -ForegroundColor Red }
}

Step "balancer profile" @("ops/verify_vpn_balancer_profile.py")
Step "policy latency" @("ops/audit_policy_latency.py")
Step "subscription" @("ops/probe_subscription.py")
Step "happ import" @("ops/diagnose_happ_import.py")
Step "transport mux" @("ops/transport_mux_audit.py")
Step "throughput phase1" @("ops/diagnose_throughput.py")
Step "autotrim dry-run" @("ops/latency_selector_autotrim.py")

if ($fail -eq 0) {
    Write-Host "`nPRE_DEPLOY_VPN_PRODUCT_OK (workstation). On LV: bash ops/install_latency_autotrim_cron.sh && python3 /opt/scripts/vpn_verify_gate.py" -ForegroundColor Green
} else {
    Write-Host "`nPRE_DEPLOY_VPN_PRODUCT_FAIL" -ForegroundColor Red
    exit 1
}
