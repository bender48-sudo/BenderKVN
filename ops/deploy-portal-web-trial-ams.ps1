# Hot-patch AMS bot for browser web trial only (keeps prod webhook baseline + trial route).
# pwsh -File ops/deploy-portal-web-trial-ams.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Files = @(
    @{ Local = "bot_src\portal_web_trial.py"; Remote = "/tmp/portal_web_trial.py" },
    @{ Local = "bot_src\web_trial_db.py"; Remote = "/tmp/web_trial_db.py" },
    @{ Local = "bot_src\web_tg_bind.py"; Remote = "/tmp/web_tg_bind.py" },
    @{ Local = "bot_src\webhook_server\app_ams_with_portal_trial.py"; Remote = "/tmp/webhook_app.py" }
)
foreach ($f in $Files) {
    $p = Join-Path $RepoRoot $f.Local
    if (-not (Test-Path $p)) { throw "Missing $p" }
}

python -c @"
import ast
from pathlib import Path
r = Path(r'$RepoRoot')
for n in ('portal_web_trial.py',):
    ast.parse((r / 'bot_src' / n).read_text(encoding='utf-8'))
ast.parse((r / 'bot_src/webhook_server/app_ams_with_portal_trial.py').read_text(encoding='utf-8'))
"@

$HostAms = "168.100.11.140"
$Port = 3344
$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$SshCommon = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-p", "$Port")
$ScpCommon = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-P", "$Port")

foreach ($f in $Files) {
    $local = Join-Path $RepoRoot $f.Local
    & scp @($ScpCommon + @($local, "root@${HostAms}:$($f.Remote)"))
}

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
SB=/opt/remna-shop/src/shop_bot
DM=/opt/remna-shop/src/shop_bot/data_manager
WH=/opt/remna-shop/src/shop_bot/webhook_server
sed -i 's/\r$//' /tmp/portal_web_trial.py /tmp/web_trial_db.py /tmp/web_tg_bind.py /tmp/webhook_app.py
test -f "$WH/app.py" && cp "$WH/app.py" "$WH/app.py.before-web-trial-$ts"
install -m 0644 /tmp/portal_web_trial.py "$SB/portal_web_trial.py"
install -m 0644 /tmp/web_trial_db.py "$SB/web_trial_db.py"
install -m 0644 /tmp/web_tg_bind.py "$SB/web_tg_bind.py"
install -m 0644 /tmp/webhook_app.py "$WH/app.py"
docker cp /tmp/portal_web_trial.py remna-shop-bot:/app/src/shop_bot/portal_web_trial.py
docker cp /tmp/web_trial_db.py remna-shop-bot:/app/src/shop_bot/web_trial_db.py
docker cp /tmp/web_tg_bind.py remna-shop-bot:/app/src/shop_bot/web_tg_bind.py
docker cp /tmp/webhook_app.py remna-shop-bot:/app/src/shop_bot/webhook_server/app.py
docker restart remna-shop-bot
sleep 10
docker exec remna-shop-bot grep -q portal-web-trial /app/src/shop_bot/webhook_server/app.py
docker exec remna-shop-bot test -f /app/src/shop_bot/portal_web_trial.py
curl -fsS -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -H "X-Portal-Web-Trial-Key: $(grep ^PORTAL_WEB_TRIAL_SECRET= /opt/remna-shop/.env | cut -d= -f2)" -d '{"email":"healthcheck@example.invalid"}' http://127.0.0.1:1488/portal-web-trial || true
echo ""
echo DEPLOY_PORTAL_WEB_TRIAL_AMS_OK
'@

& ssh @($SshCommon + @("root@${HostAms}", $sshCmd))
Write-Host "Done. Run: python ops/smoke_web_trial_browser.py"
