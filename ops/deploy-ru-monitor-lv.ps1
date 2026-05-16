# Deploy ru-monitor.py -> LV /opt/scripts/ru-monitor.py
# From repo root:  pwsh -File ops/deploy-ru-monitor-lv.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
$F = Join-Path $RepoRoot "ru-monitor.py"
if (-not (Test-Path $F)) { throw "ru-monitor.py not found: $F" }

$HostLv = "176.126.162.158"
$Port = 3333
$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=accept-new", "-o", "GSSAPIAuthentication=no", "-o", "PreferredAuthentications=publickey")

Write-Host "[deploy-ru-monitor-lv] scp..."
& scp @($Common + @("-P", "$Port", "${F}", "root@${HostLv}:/tmp/ru-monitor.py.new"))

Write-Host "[deploy-ru-monitor-lv] install..."
$cmd = "sed -i 's/\r$//' /tmp/ru-monitor.py.new && ts=`$(date +%Y%m%d-%H%M%S) && cp /opt/scripts/ru-monitor.py /opt/scripts/ru-monitor.py.before-deploy-`$ts && install -m 0755 /tmp/ru-monitor.py.new /opt/scripts/ru-monitor.py && md5sum /opt/scripts/ru-monitor.py"
& ssh @($Common + @("-p", "$Port", "root@${HostLv}", $cmd))

Write-Host "[deploy-ru-monitor-lv] local MD5:"
(Get-FileHash -Algorithm MD5 $F).Hash.ToLowerInvariant()
