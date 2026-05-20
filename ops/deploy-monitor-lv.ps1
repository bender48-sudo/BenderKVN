# Deploy repo monitor.sh -> LV /opt/scripts/monitor.sh
# From repo root:  pwsh -File ops/deploy-monitor-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
$M = Join-Path $RepoRoot "monitor.sh"
if (-not (Test-Path $M)) { throw "monitor.sh not found: $M" }

$HostLv = "176.126.162.158"
$Port = 3333
$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_lv_ed25519"
if (-not (Test-Path $Key)) {
    $Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
}
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=accept-new", "-o", "GSSAPIAuthentication=no", "-o", "PreferredAuthentications=publickey")

Write-Host "[deploy-monitor-lv] scp..."
& scp @($Common + @("-P", "$Port", "${M}", "root@${HostLv}:/tmp/monitor.sh.new"))

Write-Host "[deploy-monitor-lv] backup + install + md5..."
$cmd = "sed -i 's/\r$//' /tmp/monitor.sh.new && ts=`$(date +%Y%m%d-%H%M%S) && cp /opt/scripts/monitor.sh /opt/scripts/monitor.sh.before-deploy-`$ts && install -m 0755 /tmp/monitor.sh.new /opt/scripts/monitor.sh && md5sum /opt/scripts/monitor.sh"
& ssh @($Common + @("-p", "$Port", "root@${HostLv}", $cmd))

Write-Host "[deploy-monitor-lv] local MD5 (compare with remote):"
(Get-FileHash -Algorithm MD5 $M).Hash.ToLowerInvariant()
