# P3-RED-MIN-01: deploy payload redact + audit to AMS bot.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
$Port = 3344
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-o", "IdentitiesOnly=yes")

$Files = @(
    @{ Local = "bot_src\webhook_server\payload_redact.py"; Container = "/app/src/shop_bot/webhook_server/payload_redact.py" },
    @{ Local = "bot_src\webhook_server\payment_queue.py"; Container = "/app/src/shop_bot/webhook_server/payment_queue.py" },
    @{ Local = "ops\data_minimization_audit.py"; Container = "/tmp/data_minimization_audit.py" },
    @{ Local = "ops\data_field_inventory.json"; Container = "/tmp/data_field_inventory.json" }
)

foreach ($f in $Files) {
    python -m py_compile (Join-Path $RepoRoot $f.Local) 2>$null
    $base = Split-Path -Leaf $f.Local
    & scp @($Common + @("-P", "$Port", (Join-Path $RepoRoot $f.Local), "root@168.100.11.140:/tmp/$base"))
}

$ssh = @'
set -e
docker cp /tmp/payload_redact.py remna-shop-bot:/app/src/shop_bot/webhook_server/payload_redact.py
docker cp /tmp/payment_queue.py remna-shop-bot:/app/src/shop_bot/webhook_server/payment_queue.py
docker cp /tmp/data_minimization_audit.py remna-shop-bot:/tmp/data_minimization_audit.py
docker cp /tmp/data_field_inventory.json remna-shop-bot:/tmp/data_field_inventory.json
docker restart remna-shop-bot
sleep 6
docker exec -e DATA_INVENTORY=/tmp/data_field_inventory.json remna-shop-bot python /tmp/data_minimization_audit.py
'@

Write-Host "[deploy] bot webhook redact + audit..."
& ssh @($Common + @("-p", "$Port", "root@168.100.11.140", $ssh))
if ($LASTEXITCODE -ne 0) { throw "deploy failed" }
Write-Host "Done."
