# Finish phase 11 on prod: AMS cron + NL backup edge (retries, hot-prod safe).
# No template --apply unless LV node is down (auto script enforces).
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Ops = Join-Path $Repo "ops"
$Scp = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3")

function Invoke-ScpWithRetry {
    param([string]$Local, [string]$Remote, [int]$Max = 6)
    for ($i = 1; $i -le $Max; $i++) {
        try {
            & scp @Scp $Local $Remote
            if ($LASTEXITCODE -eq 0) { return $true }
        } catch { }
        Write-Host "scp retry $i/$Max $Local"
        Start-Sleep -Seconds ([Math]::Min(30, 3 * $i))
    }
    return $false
}

function Invoke-SshWithRetry {
    param([string]$HostAlias, [string]$Cmd, [int]$Max = 6)
    for ($i = 1; $i -le $Max; $i++) {
        $out = ssh -o BatchMode=yes -o ConnectTimeout=30 -o ServerAliveInterval=15 @($HostAlias, $Cmd) 2>&1
        if ($LASTEXITCODE -eq 0) { return $out }
        Write-Host "ssh retry $i/$Max $HostAlias"
        Start-Sleep -Seconds ([Math]::Min(30, 3 * $i))
    }
    throw "ssh failed on $HostAlias after $Max attempts"
}

$amsFiles = @(
    "lv_nl_failover_common.py", "lv_node_down_nl_failover.py", "verify_nl_failover_sub.py",
    "lv_node_failover_auto.py", "run_lv_node_failover_auto_ams.sh",
    "install_ams_node_failover_cron.sh", "install_ams_sync_injecthosts_cron.sh",
    "run_sync_injecthosts_connected_ams.sh", "sync_injecthosts_connected.py",
    "ams_node_resilience_smoke.sh", "panel_client.py", "site_urls.py",
    "load_env_file.py", "subscription_fetch.py", "balancer_selectors.py",
    "trim_injecthosts_no_xhttp.py", "subscription_config_notify.py",
    "verify_vpn_balancer_profile.py", "probe_subscription.py"
)

Write-Host "=== AMS deploy ==="
foreach ($f in $amsFiles) {
    $src = Join-Path $Ops $f
    if (-not (Test-Path $src)) { throw "missing $src" }
    if (-not (Invoke-ScpWithRetry $src "bvpn-ams:/opt/scripts/")) { throw "scp failed: $f" }
    Write-Host "OK $f"
}

Invoke-SshWithRetry "bvpn-ams" @"
sed -i 's/\r$//' /opt/scripts/*.sh
bash /opt/scripts/install_ams_node_failover_cron.sh
bash /opt/scripts/install_ams_sync_injecthosts_cron.sh
bash /opt/scripts/ams_node_resilience_smoke.sh
crontab -l 2>/dev/null | grep -E 'lv-node-failover|sync-injecthosts' || true
"@

Write-Host "=== NL backup edge ==="
if (-not (Invoke-ScpWithRetry (Join-Path $Ops "patch-caddy-sub-backup-nl.sh") "bvpn-nl:/tmp/patch-nl.sh")) {
    Write-Warning "NL scp failed - skip NL edge (add DNS n4l8q manually later)"
} else {
    try {
        Invoke-SshWithRetry "bvpn-nl" "sed -i 's/\r$//' /tmp/patch-nl.sh; bash /tmp/patch-nl.sh"
    } catch {
        Write-Warning "NL patch failed: $_ (need DNS A n4l8q -> 91.90.192.17 in Dynadot)"
    }
}

Write-Host "=== Workstation verify (no apply) ==="
Set-Location $Repo
python ops/lv_node_down_nl_failover.py --status
python ops/lv_node_failover_auto.py
python ops/sync_injecthosts_connected.py

Write-Host "PHASE11_PROD_FINISH_OK"
