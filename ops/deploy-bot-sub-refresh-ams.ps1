# Auto sub-config refresh notifier (database + scheduler + messages).
# From repo root:  pwsh -File ops/deploy-bot-sub-refresh-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Files = @(
    @{ Local = "bot_src\database.py"; Host = "/opt/remna-shop/src/shop_bot/data_manager/database.py"; Container = "/app/src/shop_bot/data_manager/database.py" },
    @{ Local = "bot_src\scheduler.py"; Host = "/opt/remna-shop/src/shop_bot/data_manager/scheduler.py"; Container = "/app/src/shop_bot/data_manager/scheduler.py" },
    @{ Local = "bot_src\subscription_refresh.py"; Host = "/opt/remna-shop/src/shop_bot/bot/subscription_refresh.py"; Container = "/app/src/shop_bot/bot/subscription_refresh.py" },
    @{ Local = "bot_src\user_messages.py"; Host = "/opt/remna-shop/src/shop_bot/bot/user_messages.py"; Container = "/app/src/shop_bot/bot/user_messages.py" }
)

foreach ($f in $Files) {
    $p = Join-Path $RepoRoot $f.Local
    if (-not (Test-Path $p)) { throw "Missing: $p" }
    python -c "import ast; ast.parse(open(r'$p', encoding='utf-8').read())"
}

$HostAms = "168.100.11.140"
$Port = 3344
$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-o", "StrictHostKeyChecking=accept-new")

foreach ($f in $Files) {
    $base = Split-Path -Leaf $f.Local
    Write-Host "[deploy] scp $base ..."
    & scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot $f.Local), "root@${HostAms}:/tmp/$base"))
}

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/remna-shop/src/shop_bot/bot
for pair in \
  "database.py:/opt/remna-shop/src/shop_bot/data_manager/database.py:/app/src/shop_bot/data_manager/database.py" \
  "scheduler.py:/opt/remna-shop/src/shop_bot/data_manager/scheduler.py:/app/src/shop_bot/data_manager/scheduler.py" \
  "subscription_refresh.py:/opt/remna-shop/src/shop_bot/bot/subscription_refresh.py:/app/src/shop_bot/bot/subscription_refresh.py" \
  "user_messages.py:/opt/remna-shop/src/shop_bot/bot/user_messages.py:/app/src/shop_bot/bot/user_messages.py"
do
  base="${pair%%:*}"
  rest="${pair#*:}"
  host="${rest%%:*}"
  container="${rest#*:}"
  sed -i "s/\r$//" "/tmp/$base"
  test -f "$host" && cp "$host" "${host}.before-sub-refresh-$ts" || true
  install -m 0644 "/tmp/$base" "$host"
  docker cp "/tmp/$base" "remna-shop-bot:$container"
done
docker restart remna-shop-bot
sleep 5
docker exec remna-shop-bot python -c "from shop_bot.data_manager.database import initialize_db, get_sub_config_generation; initialize_db(); print('sub_config_generation', get_sub_config_generation())"
'@

Write-Host "[deploy] install + restart..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh failed" }
Write-Host "Done. After template patch, ops hooks call subscription_config_notify.after_template_patch()."
