# Deploy repo bot_src/config.py -> AMS remna-shop-bot (hot-patch).
# From repo root:  pwsh -File ops/deploy-bot-config-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Config = Join-Path $RepoRoot "bot_src\config.py"
if (-not (Test-Path $Config)) { throw "Missing: $Config" }

python -c @"
import ast
from pathlib import Path
ast.parse(Path(r'$Config').read_text(encoding='utf-8'))
"@

$HostAms = "168.100.11.140"
$Port = 3344
$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
if (-not (Test-Path $Key)) {
    $Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
}
$Common = @(
    "-i", $Key,
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=40",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "GSSAPIAuthentication=no",
    "-o", "PreferredAuthentications=publickey"
)

Write-Host "[deploy-bot-config-ams] scp config.py..."
& scp @($Common + @("-P", "$Port", "${Config}", "root@${HostAms}:/tmp/config.py"))

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
CFG=/opt/remna-shop/src/shop_bot/config.py
sed -i 's/\r$//' /tmp/config.py
test -f "$CFG" && cp "$CFG" "$CFG.before-bot-ops-$ts" || true
install -m 0644 /tmp/config.py "$CFG"
docker cp /tmp/config.py remna-shop-bot:/app/src/shop_bot/config.py
docker restart remna-shop-bot
sleep 3
docker exec remna-shop-bot python -c "from shop_bot.config import PLANS; print(PLANS.get('buy_1_month'))"
md5sum "$CFG"
'@

Write-Host "[deploy-bot-config-ams] install + restart..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh remote step failed (exit $LASTEXITCODE)" }

Write-Host "Done. Smoke: TG bot -> buy/extend -> 1 month shows final RUB price (not 1)."
