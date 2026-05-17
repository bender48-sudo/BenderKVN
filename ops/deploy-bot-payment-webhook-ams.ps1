# P6-RED-PAY-01/02: database + webhook queue + auth -> AMS remna-shop-bot.
# From repo root:  pwsh -File ops/deploy-bot-payment-webhook-ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Files = @(
    @{ Local = "bot_src\database.py"; Host = "/opt/remna-shop/src/shop_bot/data_manager/database.py"; Container = "/app/src/shop_bot/data_manager/database.py" },
    @{ Local = "bot_src\webhook_server\payment_queue.py"; Host = "/opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py"; Container = "/app/src/shop_bot/webhook_server/payment_queue.py" },
    @{ Local = "bot_src\webhook_server\app.py"; Host = "/opt/remna-shop/src/shop_bot/webhook_server/app.py"; Container = "/app/src/shop_bot/webhook_server/app.py" },
    @{ Local = "bot_src\webhook_server\payload_redact.py"; Host = "/opt/remna-shop/src/shop_bot/webhook_server/payload_redact.py"; Container = "/app/src/shop_bot/webhook_server/payload_redact.py" },
    @{ Local = "bot_src\webhook_server\auth.py"; Host = "/opt/remna-shop/src/shop_bot/webhook_server/auth.py"; Container = "/app/src/shop_bot/webhook_server/auth.py" },
    @{ Local = "bot_src\main.py"; Host = "/opt/remna-shop/src/shop_bot/main.py"; Container = "/app/src/shop_bot/main.py" },
    @{ Local = "bot_src\handlers.py"; Host = "/opt/remna-shop/src/shop_bot/bot/handlers.py"; Container = "/app/src/shop_bot/bot/handlers.py" }
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
mkdir -p /opt/remna-shop/src/shop_bot/webhook_server
for pair in \
  "database.py:/opt/remna-shop/src/shop_bot/data_manager/database.py:/app/src/shop_bot/data_manager/database.py" \
  "payment_queue.py:/opt/remna-shop/src/shop_bot/webhook_server/payment_queue.py:/app/src/shop_bot/webhook_server/payment_queue.py" \
  "app.py:/opt/remna-shop/src/shop_bot/webhook_server/app.py:/app/src/shop_bot/webhook_server/app.py" \
  "auth.py:/opt/remna-shop/src/shop_bot/webhook_server/auth.py:/app/src/shop_bot/webhook_server/auth.py" \
  "main.py:/opt/remna-shop/src/shop_bot/main.py:/app/src/shop_bot/main.py" \
  "handlers.py:/opt/remna-shop/src/shop_bot/bot/handlers.py:/app/src/shop_bot/bot/handlers.py"
do
  base="${pair%%:*}"
  rest="${pair#*:}"
  host="${rest%%:*}"
  container="${rest#*:}"
  sed -i "s/\r$//" "/tmp/$base"
  test -f "$host" && cp "$host" "${host}.before-pay-wh-$ts" || true
  install -m 0644 "/tmp/$base" "$host"
  docker cp "/tmp/$base" "remna-shop-bot:$container"
done
docker restart remna-shop-bot
sleep 5
docker exec remna-shop-bot python -c "from shop_bot.data_manager.database import initialize_db, count_webhook_dlq; initialize_db(); print('dlq', count_webhook_dlq())"
'@

Write-Host "[deploy] install + restart..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh failed" }
& scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot "ops\smoke_webhook_auth_ams.py"), "root@${HostAms}:/tmp/smoke_webhook_auth_ams.py"))
& scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot "ops\smoke_webhook_payment_idempotency_ams.py"), "root@${HostAms}:/tmp/smoke_webhook_payment_idempotency_ams.py"))
Write-Host "[deploy] smoke auth..."
& ssh @($Common + @("-p", "$Port", "root@${HostAms}", "docker cp /tmp/smoke_webhook_auth_ams.py remna-shop-bot:/tmp/smoke_webhook_auth_ams.py && docker exec remna-shop-bot python /tmp/smoke_webhook_auth_ams.py"))
if ($LASTEXITCODE -ne 0) { throw "smoke_webhook_auth failed" }
Write-Host "Done. WEBHOOK_AUTH_OK. Idempotency: docker exec remna-shop-bot python /tmp/smoke_webhook_payment_idempotency_ams.py"
