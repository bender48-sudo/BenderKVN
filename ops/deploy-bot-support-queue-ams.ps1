# P6-SCALE-07: support queue timestamps + snapshot tooling deploy.
# pwsh -File ops/deploy-bot-support-queue-ams.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Files = @(
    @{ Local = "bot_src\database.py"; Host = "/opt/remna-shop/src/shop_bot/data_manager/database.py"; Container = "/app/src/shop_bot/data_manager/database.py" },
    @{ Local = "bot_src\support_handler.py"; Host = "/opt/remna-shop/src/shop_bot/bot/support_handler.py"; Container = "/app/src/shop_bot/bot/support_handler.py" }
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
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-o", "StrictHostKeyChecking=accept-new")

foreach ($f in $Files) {
    $base = Split-Path -Leaf $f.Local
    Write-Host "[deploy] scp $base ..."
    & scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot $f.Local), "root@${HostAms}:/tmp/$base"))
}

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
for pair in \
  "database.py:/opt/remna-shop/src/shop_bot/data_manager/database.py:/app/src/shop_bot/data_manager/database.py" \
  "support_handler.py:/opt/remna-shop/src/shop_bot/bot/support_handler.py:/app/src/shop_bot/bot/support_handler.py"
do
  base=${pair%%:*}
  rest=${pair#*:}
  host=${rest%%:*}
  container=${rest#*:}
  cp "$host" "${host}.before-support-queue-$ts"
  sed -i 's/\r$//' "/tmp/$base"
  install -m 0644 "/tmp/$base" "$host"
  docker cp "$host" "remna-shop-bot:$container"
done
cd /opt/remna-shop && docker compose restart remna-shop-bot
sleep 3
docker exec remna-shop-bot python3 -c "from shop_bot.data_manager.database import initialize_db; initialize_db(); print('DB migrate OK')"
'@

& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
Write-Host "[deploy-bot-support-queue-ams] done"
