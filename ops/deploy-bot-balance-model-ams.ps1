# Deploy balance model (DAILY_RATE + topup) -> AMS remna-shop-bot.
# From repo root:  pwsh -File ops/deploy-bot-balance-model-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Files = @(
    @{ Local = "bot_src\config.py"; RemoteHost = "/opt/remna-shop/src/shop_bot/config.py"; Container = "/app/src/shop_bot/config.py" },
    @{ Local = "bot_src\keyboards.py"; RemoteHost = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"; Container = "/app/src/shop_bot/bot/keyboards.py" },
    @{ Local = "bot_src\handlers.py"; RemoteHost = "/opt/remna-shop/src/shop_bot/bot/handlers.py"; Container = "/app/src/shop_bot/bot/handlers.py" },
    @{ Local = "bot_src\database.py"; RemoteHost = "/opt/remna-shop/src/shop_bot/data_manager/database.py"; Container = "/app/src/shop_bot/data_manager/database.py" },
    @{ Local = "bot_src\scheduler.py"; RemoteHost = "/opt/remna-shop/src/shop_bot/data_manager/scheduler.py"; Container = "/app/src/shop_bot/data_manager/scheduler.py" },
    @{ Local = "bot_src\user_messages.py"; RemoteHost = "/opt/remna-shop/src/shop_bot/bot/user_messages.py"; Container = "/app/src/shop_bot/bot/user_messages.py" }
)

foreach ($f in $Files) {
    $p = Join-Path $RepoRoot $f.Local
    if (-not (Test-Path $p)) { throw "Missing: $p" }
    python -c "import ast; ast.parse(open(r'$p', encoding='utf-8').read())"
}

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

foreach ($f in $Files) {
    $local = Join-Path $RepoRoot $f.Local
    $base = Split-Path -Leaf $f.Local
    Write-Host "[deploy] scp $base ..."
    & scp @($Common + @("-P", "$Port", $local, "root@${HostAms}:/tmp/$base"))
}

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
for pair in \
  "config.py:/opt/remna-shop/src/shop_bot/config.py:/app/src/shop_bot/config.py" \
  "keyboards.py:/opt/remna-shop/src/shop_bot/bot/keyboards.py:/app/src/shop_bot/bot/keyboards.py" \
  "handlers.py:/opt/remna-shop/src/shop_bot/bot/handlers.py:/app/src/shop_bot/bot/handlers.py" \
  "database.py:/opt/remna-shop/src/shop_bot/data_manager/database.py:/app/src/shop_bot/data_manager/database.py" \
  "scheduler.py:/opt/remna-shop/src/shop_bot/data_manager/scheduler.py:/app/src/shop_bot/data_manager/scheduler.py" \
  "user_messages.py:/opt/remna-shop/src/shop_bot/bot/user_messages.py:/app/src/shop_bot/bot/user_messages.py"
do
  base="${pair%%:*}"
  rest="${pair#*:}"
  host="${rest%%:*}"
  container="${rest#*:}"
  sed -i "s/\r$//" "/tmp/$base"
  test -f "$host" && cp "$host" "${host}.before-balance-$ts" || true
  install -m 0644 "/tmp/$base" "$host"
  docker cp "/tmp/$base" "remna-shop-bot:$container"
done
docker restart remna-shop-bot
sleep 4
docker exec remna-shop-bot python -c "from shop_bot.config import DAILY_RATE, TOPUP_PRESETS, balance_to_days; print(DAILY_RATE, list(TOPUP_PRESETS.keys()), balance_to_days(200))"
'@

Write-Host "[deploy] install + restart..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh failed (exit $LASTEXITCODE)" }
Write-Host "Done. Smoke: /start -> Пополнить баланс -> пресеты в днях по 6.67 RUB/day."
