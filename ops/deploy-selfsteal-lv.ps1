# Deploy selfsteal-monitor.py -> LV /opt/scripts/selfsteal-monitor.py
# From repo root:  pwsh -File ops/deploy-selfsteal-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
$F = Join-Path $RepoRoot "selfsteal-monitor.py"
if (-not (Test-Path $F)) { throw "selfsteal-monitor.py not found: $F" }

$HostLv = "176.126.162.158"
$Port = 3333
$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=accept-new", "-o", "GSSAPIAuthentication=no", "-o", "PreferredAuthentications=publickey")

Write-Host "[deploy-selfsteal-lv] scp..."
& scp @($Common + @("-P", "$Port", "${F}", "root@${HostLv}:/tmp/selfsteal-monitor.py.new"))

Write-Host "[deploy-selfsteal-lv] install..."
$cmd = "sed -i 's/\r$//' /tmp/selfsteal-monitor.py.new && ts=`$(date +%Y%m%d-%H%M%S) && cp /opt/scripts/selfsteal-monitor.py /opt/scripts/selfsteal-monitor.py.before-deploy-`$ts && install -m 0755 /tmp/selfsteal-monitor.py.new /opt/scripts/selfsteal-monitor.py && md5sum /opt/scripts/selfsteal-monitor.py"
& ssh @($Common + @("-p", "$Port", "root@${HostLv}", $cmd))

Write-Host "[deploy-selfsteal-lv] local MD5:"
(Get-FileHash -Algorithm MD5 $F).Hash.ToLowerInvariant()
