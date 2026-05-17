# Deploy repo bot_src/handlers.py + user_messages.py -> AMS remna-shop-bot (hot-patch).
# Image is not bind-mounted — needs host tree + docker cp + restart (see docs/DEPLOY.md §4.3).
# From repo root:  pwsh -File ops/deploy-bot-handlers-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Handlers = Join-Path $RepoRoot "bot_src\handlers.py"
$UserMsgs = Join-Path $RepoRoot "bot_src\user_messages.py"
$Scheduler = Join-Path $RepoRoot "bot_src\scheduler.py"
foreach ($f in @($Handlers, $UserMsgs, $Scheduler)) {
    if (-not (Test-Path $f)) { throw "Missing: $f" }
}

python -c @"
import ast
from pathlib import Path
root = Path(r'$RepoRoot')
ast.parse((root / 'bot_src/handlers.py').read_text(encoding='utf-8'))
ast.parse((root / 'bot_src/user_messages.py').read_text(encoding='utf-8'))
ast.parse((root / 'bot_src/scheduler.py').read_text(encoding='utf-8'))
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

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
BT=/opt/remna-shop/src/shop_bot/bot
DM=/opt/remna-shop/src/shop_bot/data_manager
sed -i 's/\r$//' /tmp/handlers.py /tmp/user_messages.py /tmp/scheduler.py
mkdir -p "$BT" "$DM"
test -f "$BT/handlers.py" && cp "$BT/handlers.py" "$BT/handlers.py.before-bot-ops-$ts" || true
test -f "$BT/user_messages.py" && cp "$BT/user_messages.py" "$BT/user_messages.py.before-bot-ops-$ts" || true
test -f "$DM/scheduler.py" && cp "$DM/scheduler.py" "$DM/scheduler.py.before-bot-ops-$ts" || true
install -m 0644 /tmp/handlers.py "$BT/handlers.py"
install -m 0644 /tmp/user_messages.py "$BT/user_messages.py"
install -m 0644 /tmp/scheduler.py "$DM/scheduler.py"
docker cp /tmp/handlers.py remna-shop-bot:/app/src/shop_bot/bot/handlers.py
docker cp /tmp/user_messages.py remna-shop-bot:/app/src/shop_bot/bot/user_messages.py
docker cp /tmp/scheduler.py remna-shop-bot:/app/src/shop_bot/data_manager/scheduler.py
docker restart remna-shop-bot
echo "Remote md5:"
md5sum "$BT/handlers.py" "$BT/user_messages.py" "$DM/scheduler.py"
'@

Write-Host "[deploy-bot-handlers-ams] ssh backup + install + docker cp + restart..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh remote step failed (exit $LASTEXITCODE)" }

Write-Host "[deploy-bot-handlers-ams] local MD5 (compare with remote lines):"
(Get-FileHash -Algorithm MD5 $Handlers).Hash.ToLowerInvariant()
(Get-FileHash -Algorithm MD5 $UserMsgs).Hash.ToLowerInvariant()
(Get-FileHash -Algorithm MD5 $Scheduler).Hash.ToLowerInvariant()
Write-Host "Done. Smoke: open bot in Telegram (/start); admin /status if available."
