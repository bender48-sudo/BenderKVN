# Sync VPN ops scripts to bvpn-lv and install autotrim cron.
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Ops = Join-Path $Repo "ops"
$HostAlias = if ($env:BVPN_LV_HOST) { $env:BVPN_LV_HOST } else { "bvpn-lv" }
$Remote = "/opt/scripts"

$files = @(
    "install_latency_autotrim_cron.sh",
    "run_latency_selector_autotrim.sh",
    "relay_latency_probe.py",
    "nl_reachability_probe_ru.py",
    "latency_selector_autotrim.py",
    "patch_add_nl_intl_gated.py",
    "patch_intl_stealth_split.py",
    "patch_dns_split_config.py",
    "probe_dns_leak.py",
    "patch_trim_injecthosts_relay_only.py",
    "relay_failover_template.py",
    "balancer_selectors.py",
    "panel_client.py",
    "site_urls.py",
    "load_env_file.py",
    "verify_vpn_balancer_profile.py",
    "subscription_fetch.py",
    "dns_split_config.py",
    "subscription_config_notify.py",
    "vpn_verify_gate.py",
    "diagnose_throughput.py",
    "audit_bbr_congestion.py",
    "audit_policy_latency.py",
    "probe_subscription.py",
    "diagnose_happ_import.py",
    "probe_ru_bypass.py",
    "verify_ru_bypass_status.py",
    "patch_routing_regexp_to_geosite_ru.py",
    "happ_geosite_guard.py",
    "transport_mux_audit.py"
)

foreach ($f in $files) {
    $src = Join-Path $Ops $f
    if (-not (Test-Path $src)) { throw "missing $src" }
    scp -o BatchMode=yes $src "${HostAlias}:${Remote}/"
}
ssh -o BatchMode=yes $HostAlias "chmod 755 ${Remote}/install_latency_autotrim_cron.sh ${Remote}/run_latency_selector_autotrim.sh; bash ${Remote}/install_latency_autotrim_cron.sh"
Write-Host "DEPLOY_LV_VPN_OPS_OK"
