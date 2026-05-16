# Deploy daily-report.sh -> LV /opt/scripts/daily-report.sh
# From repo root:  pwsh -File ops/deploy-daily-report-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
$F = Join-Path $RepoRoot "daily-report.sh"
if (-not (Test-Path $F)) { throw "daily-report.sh not found: $F" }

$HostLv = "176.126.162.158"
$Port = 3333
$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=accept-new", "-o", "GSSAPIAuthentication=no", "-o", "PreferredAuthentications=publickey")

Write-Host "[deploy-daily-report-lv] scp..."
& scp @($Common + @("-P", "$Port", "${F}", "root@${HostLv}:/tmp/daily-report.sh.new"))

Write-Host "[deploy-daily-report-lv] install..."
$cmd = "sed -i 's/\r$//' /tmp/daily-report.sh.new && ts=`$(date +%Y%m%d-%H%M%S) && cp /opt/scripts/daily-report.sh /opt/scripts/daily-report.sh.before-deploy-`$ts && install -m 0755 /tmp/daily-report.sh.new /opt/scripts/daily-report.sh && md5sum /opt/scripts/daily-report.sh"
& ssh @($Common + @("-p", "$Port", "root@${HostLv}", $cmd))

Write-Host "[deploy-daily-report-lv] local MD5:"
(Get-FileHash -Algorithm MD5 $F).Hash.ToLowerInvariant()
