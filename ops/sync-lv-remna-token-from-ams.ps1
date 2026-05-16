# Sync working REMNA_API_TOKEN from AMS shop -> LV balancer + ru-monitor.
# From repo root: pwsh -File ops/sync-lv-remna-token-from-ams.ps1
$ErrorActionPreference = "Stop"
$Ops = $PSScriptRoot
$Tmp = Join-Path (Split-Path $Ops -Parent) ".secrets\_lv_sync_token.tmp"

Write-Host "[sync-lv-remna] read AMS token..."
ssh -o BatchMode=yes -o ConnectTimeout=20 bvpn-ams 'grep -m1 ^REMNA_API_TOKEN= /opt/remna-shop/.env | cut -d= -f2-' |
    Out-File -Encoding ascii -NoNewline $Tmp
$token = (Get-Content -Raw $Tmp).Trim().Trim('"').Trim("'")
if (-not $token.StartsWith("eyJ")) { Remove-Item -Force $Tmp -ErrorAction SilentlyContinue; throw "AMS REMNA_API_TOKEN missing or invalid" }

Write-Host "[sync-lv-remna] probe AMS token..."
$code = python -c "import urllib.request,sys; t=sys.argv[1]; r=urllib.request.Request('https://k9x2m1.conntest.xyz:2053/api/hosts',headers={'Authorization':'Bearer '+t,'X-Forwarded-Proto':'https'}); exec('try:\n urllib.request.urlopen(r,timeout=15); print(200)\nexcept urllib.error.HTTPError as e: print(e.code)')" $token
if ($code -ne "200") { Remove-Item -Force $Tmp -ErrorAction SilentlyContinue; throw "AMS token probe failed: HTTP $code" }

Write-Host "[sync-lv-remna] apply on LV..."
scp -o BatchMode=yes (Join-Path $Ops "apply_lv_panel_token.py") root@bvpn-lv:/tmp/apply_lv_panel_token.py | Out-Null
Get-Content -Raw $Tmp | ssh -o BatchMode=yes root@bvpn-lv "python3 /tmp/apply_lv_panel_token.py"
Remove-Item -Force $Tmp -ErrorAction SilentlyContinue

Write-Host "[sync-lv-remna] verify LV..."
ssh -o BatchMode=yes root@bvpn-lv "bash /tmp/probe_remna_token.sh /etc/bvpn/balancer.env; bash /tmp/probe_remna_token.sh /etc/bvpn/ru-monitor.env"

Write-Host "SYNC_LV_REMNA_TOKEN_FROM_AMS_OK (run /opt/scripts/ru-monitor.py on LV to confirm log)"
