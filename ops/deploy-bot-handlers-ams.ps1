# Deploy repo bot_src/handlers.py + user_messages.py -> AMS remna-shop-bot (hot-patch).
# Image is not bind-mounted — needs host tree + docker cp + restart (see docs/DEPLOY.md §4.3).
# From repo root:  pwsh -File ops/deploy-bot-handlers-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Handlers = Join-Path $RepoRoot "bot_src\handlers.py"
$UserMsgs = Join-Path $RepoRoot "bot_src\user_messages.py"
$Scheduler = Join-Path $RepoRoot "bot_src\scheduler.py"
$Keyboards = Join-Path $RepoRoot "bot_src\keyboards.py"
$MainPy = Join-Path $RepoRoot "bot_src\main.py"
$ConfigPy = Join-Path $RepoRoot "bot_src\config.py"
$PortalLinks = Join-Path $RepoRoot "bot_src\portal_links.py"
foreach ($f in @($Handlers, $UserMsgs, $Scheduler, $Keyboards, $MainPy, $ConfigPy, $PortalLinks)) {
    if (-not (Test-Path $f)) { throw "Missing: $f" }
}

python -c @"
import ast
from pathlib import Path
root = Path(r'$RepoRoot')
for name in ('handlers.py', 'user_messages.py', 'scheduler.py', 'keyboards.py', 'main.py', 'config.py', 'portal_links.py'):
    ast.parse((root / 'bot_src' / name).read_text(encoding='utf-8'))
"@

$HostAms = "168.100.11.140"
$Port = 3344
$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @(
    "-i", $Key,
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=40",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "GSSAPIAuthentication=no",
    "-o", "PreferredAuthentications=publickey"
)

Write-Host "[deploy-bot-handlers-ams] scp..."
& scp @($Common + @("-P", "$Port", "${Handlers}", "root@${HostAms}:/tmp/handlers.py"))
& scp @($Common + @("-P", "$Port", "${UserMsgs}", "root@${HostAms}:/tmp/user_messages.py"))
& scp @($Common + @("-P", "$Port", "${Scheduler}", "root@${HostAms}:/tmp/scheduler.py"))
& scp @($Common + @("-P", "$Port", "${Keyboards}", "root@${HostAms}:/tmp/keyboards.py"))
& scp @($Common + @("-P", "$Port", "${MainPy}", "root@${HostAms}:/tmp/main.py"))
& scp @($Common + @("-P", "$Port", "${ConfigPy}", "root@${HostAms}:/tmp/config.py"))
& scp @($Common + @("-P", "$Port", "${PortalLinks}", "root@${HostAms}:/tmp/portal_links.py"))

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
BT=/opt/remna-shop/src/shop_bot/bot
DM=/opt/remna-shop/src/shop_bot/data_manager
sed -i 's/\r$//' /tmp/handlers.py /tmp/user_messages.py /tmp/scheduler.py /tmp/keyboards.py /tmp/main.py /tmp/config.py /tmp/portal_links.py
mkdir -p "$BT" "$DM"
CFG=/opt/remna-shop/src/shop_bot/config.py
for f in handlers.py user_messages.py keyboards.py; do
  test -f "$BT/$f" && cp "$BT/$f" "$BT/$f.before-bot-ops-$ts" || true
done
test -f "$DM/scheduler.py" && cp "$DM/scheduler.py" "$DM/scheduler.py.before-bot-ops-$ts" || true
test -f "$CFG" && cp "$CFG" "$CFG.before-bot-ops-$ts" || true
test -f /opt/remna-shop/src/shop_bot/main.py && cp /opt/remna-shop/src/shop_bot/main.py "/opt/remna-shop/src/shop_bot/main.py.before-bot-ops-$ts" || true
install -m 0644 /tmp/handlers.py "$BT/handlers.py"
install -m 0644 /tmp/user_messages.py "$BT/user_messages.py"
install -m 0644 /tmp/keyboards.py "$BT/keyboards.py"
install -m 0644 /tmp/scheduler.py "$DM/scheduler.py"
install -m 0644 /tmp/config.py "$CFG"
install -m 0644 /tmp/portal_links.py "$BT/portal_links.py"
install -m 0644 /tmp/main.py /opt/remna-shop/src/shop_bot/main.py
docker cp /tmp/handlers.py remna-shop-bot:/app/src/shop_bot/bot/handlers.py
docker cp /tmp/user_messages.py remna-shop-bot:/app/src/shop_bot/bot/user_messages.py
docker cp /tmp/keyboards.py remna-shop-bot:/app/src/shop_bot/bot/keyboards.py
docker cp /tmp/scheduler.py remna-shop-bot:/app/src/shop_bot/data_manager/scheduler.py
docker cp /tmp/config.py remna-shop-bot:/app/src/shop_bot/config.py
docker cp /tmp/portal_links.py remna-shop-bot:/app/src/shop_bot/bot/portal_links.py
docker cp /tmp/main.py remna-shop-bot:/app/src/shop_bot/main.py
docker restart remna-shop-bot
echo "Remote md5:"
md5sum "$BT/handlers.py" "$BT/user_messages.py" "$BT/keyboards.py" "$CFG" /opt/remna-shop/src/shop_bot/main.py "$DM/scheduler.py"
'@

Write-Host "[deploy-bot-handlers-ams] ssh backup + install + docker cp + restart..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh remote step failed (exit $LASTEXITCODE)" }

Write-Host "[deploy-bot-handlers-ams] local MD5 (compare with remote lines):"
(Get-FileHash -Algorithm MD5 $Handlers).Hash.ToLowerInvariant()
(Get-FileHash -Algorithm MD5 $UserMsgs).Hash.ToLowerInvariant()
(Get-FileHash -Algorithm MD5 $Scheduler).Hash.ToLowerInvariant()
Write-Host "Done. Smoke: open bot in Telegram (/start); admin /status if available."
