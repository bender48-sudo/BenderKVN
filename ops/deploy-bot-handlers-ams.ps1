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
$PortalWebTrial = Join-Path $RepoRoot "bot_src\portal_web_trial.py"
$WebTrialDb = Join-Path $RepoRoot "bot_src\web_trial_db.py"
$WebTgBind = Join-Path $RepoRoot "bot_src\web_tg_bind.py"
$VpnWizard = Join-Path $RepoRoot "bot_src\vpn_setup_wizard.py"
$SubQr = Join-Path $RepoRoot "bot_src\subscription_qr.py"
$SubRefresh = Join-Path $RepoRoot "bot_src\subscription_refresh.py"
$AutoRenew = Join-Path $RepoRoot "bot_src\auto_renew_billing.py"
$SupportAuth = Join-Path $RepoRoot "bot_src\support_auth.py"
$SupportHandler = Join-Path $RepoRoot "bot_src\support_handler.py"
$RemnaApi = Join-Path $RepoRoot "bot_src\remnawave_api.py"
$Database = Join-Path $RepoRoot "bot_src\database.py"
$WebhookApp = Join-Path $RepoRoot "bot_src\webhook_server\app_ams_with_portal_trial.py"
$WebhookAppMain = Join-Path $RepoRoot "bot_src\webhook_server\app.py"
$WebhookAuth = Join-Path $RepoRoot "bot_src\webhook_server\auth.py"
$WebhookPayQ = Join-Path $RepoRoot "bot_src\webhook_server\payment_queue.py"
$WebhookPayAmt = Join-Path $RepoRoot "bot_src\webhook_server\payment_amount_verify.py"
$WebhookPayloadRedact = Join-Path $RepoRoot "bot_src\webhook_server\payload_redact.py"
$PortalCabinet = Join-Path $RepoRoot "bot_src\portal_cabinet.py"
$PortalBrowserResolve = Join-Path $RepoRoot "bot_src\portal_browser_resolve.py"
$PortalTelegramSetup = Join-Path $RepoRoot "bot_src\portal_telegram_setup.py"
$SubscriptionResolve = Join-Path $RepoRoot "bot_src\subscription_resolve.py"
$PublicUrls = Join-Path $RepoRoot "bot_src\public_urls.py"
$AdminHandlers = Join-Path $RepoRoot "bot_src\admin_handlers.py"
$AdminFlowTest = Join-Path $RepoRoot "bot_src\admin_flow_test.py"
$AdminFlowGuide = Join-Path $RepoRoot "bot_src\admin_flow_guide.py"
$AdminAuth = Join-Path $RepoRoot "bot_src\admin_auth.py"
$SchemaMigrations = Join-Path $RepoRoot "bot_src\schema_migrations.py"
$SetupUrlService = Join-Path $RepoRoot "bot_src\setup_url_service.py"
$SubscriptionCache = Join-Path $RepoRoot "bot_src\subscription_cache.py"
foreach ($f in @($Handlers, $UserMsgs, $Scheduler, $Keyboards, $MainPy, $ConfigPy, $PortalLinks, $PortalWebTrial, $WebTrialDb, $WebTgBind, $VpnWizard, $SubQr, $SubRefresh, $AutoRenew, $SupportAuth, $SupportHandler, $RemnaApi, $PortalCabinet, $PortalBrowserResolve, $PortalTelegramSetup, $SubscriptionResolve, $PublicUrls, $AdminHandlers, $AdminFlowTest, $AdminFlowGuide, $AdminAuth, $SchemaMigrations, $SetupUrlService, $SubscriptionCache, $Database, $WebhookApp, $WebhookAppMain, $WebhookAuth, $WebhookPayQ, $WebhookPayAmt, $WebhookPayloadRedact)) {
    if (-not (Test-Path $f)) { throw "Missing: $f" }
}

python -c @"
import ast
from pathlib import Path
root = Path(r'$RepoRoot')
for name in ('handlers.py', 'user_messages.py', 'scheduler.py', 'keyboards.py', 'main.py', 'config.py', 'portal_links.py', 'portal_web_trial.py', 'subscription_refresh.py', 'subscription_qr.py', 'auto_renew_billing.py', 'database.py', 'remnawave_api.py'):
    ast.parse((root / 'bot_src' / name).read_text(encoding='utf-8'))
ast.parse((root / 'bot_src/webhook_server/app_ams_with_portal_trial.py').read_text(encoding='utf-8'))
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

Write-Host "[deploy-bot-handlers-ams] scp..."
& scp @($Common + @("-P", "$Port", "${Handlers}", "root@${HostAms}:/tmp/handlers.py"))
& scp @($Common + @("-P", "$Port", "${UserMsgs}", "root@${HostAms}:/tmp/user_messages.py"))
& scp @($Common + @("-P", "$Port", "${Scheduler}", "root@${HostAms}:/tmp/scheduler.py"))
& scp @($Common + @("-P", "$Port", "${Keyboards}", "root@${HostAms}:/tmp/keyboards.py"))
& scp @($Common + @("-P", "$Port", "${MainPy}", "root@${HostAms}:/tmp/main.py"))
& scp @($Common + @("-P", "$Port", "${ConfigPy}", "root@${HostAms}:/tmp/config.py"))
& scp @($Common + @("-P", "$Port", "${PortalLinks}", "root@${HostAms}:/tmp/portal_links.py"))
& scp @($Common + @("-P", "$Port", "${PortalWebTrial}", "root@${HostAms}:/tmp/portal_web_trial.py"))
& scp @($Common + @("-P", "$Port", "${WebTrialDb}", "root@${HostAms}:/tmp/web_trial_db.py"))
& scp @($Common + @("-P", "$Port", "${WebTgBind}", "root@${HostAms}:/tmp/web_tg_bind.py"))
& scp @($Common + @("-P", "$Port", "${VpnWizard}", "root@${HostAms}:/tmp/vpn_setup_wizard.py"))
& scp @($Common + @("-P", "$Port", "${SubQr}", "root@${HostAms}:/tmp/subscription_qr.py"))
& scp @($Common + @("-P", "$Port", "${SubRefresh}", "root@${HostAms}:/tmp/subscription_refresh.py"))
& scp @($Common + @("-P", "$Port", "${AutoRenew}", "root@${HostAms}:/tmp/auto_renew_billing.py"))
& scp @($Common + @("-P", "$Port", "${Database}", "root@${HostAms}:/tmp/database.py"))
& scp @($Common + @("-P", "$Port", "${SupportAuth}", "root@${HostAms}:/tmp/support_auth.py"))
& scp @($Common + @("-P", "$Port", "${SupportHandler}", "root@${HostAms}:/tmp/support_handler.py"))
& scp @($Common + @("-P", "$Port", "${RemnaApi}", "root@${HostAms}:/tmp/remnawave_api.py"))
& scp @($Common + @("-P", "$Port", "${WebhookApp}", "root@${HostAms}:/tmp/webhook_app_ams.py"))
& scp @($Common + @("-P", "$Port", "${WebhookAppMain}", "root@${HostAms}:/tmp/webhook_app_main.py"))
& scp @($Common + @("-P", "$Port", "${WebhookAuth}", "root@${HostAms}:/tmp/webhook_auth.py"))
& scp @($Common + @("-P", "$Port", "${WebhookPayQ}", "root@${HostAms}:/tmp/webhook_payment_queue.py"))
& scp @($Common + @("-P", "$Port", "${WebhookPayAmt}", "root@${HostAms}:/tmp/webhook_payment_amount_verify.py"))
& scp @($Common + @("-P", "$Port", "${WebhookPayloadRedact}", "root@${HostAms}:/tmp/webhook_payload_redact.py"))
& scp @($Common + @("-P", "$Port", "${PortalCabinet}", "root@${HostAms}:/tmp/portal_cabinet.py"))
& scp @($Common + @("-P", "$Port", "${PortalBrowserResolve}", "root@${HostAms}:/tmp/portal_browser_resolve.py"))
& scp @($Common + @("-P", "$Port", "${PortalTelegramSetup}", "root@${HostAms}:/tmp/portal_telegram_setup.py"))
& scp @($Common + @("-P", "$Port", "${SubscriptionResolve}", "root@${HostAms}:/tmp/subscription_resolve.py"))
& scp @($Common + @("-P", "$Port", "${PublicUrls}", "root@${HostAms}:/tmp/public_urls.py"))
& scp @($Common + @("-P", "$Port", "${AdminHandlers}", "root@${HostAms}:/tmp/admin_handlers.py"))
& scp @($Common + @("-P", "$Port", "${AdminFlowTest}", "root@${HostAms}:/tmp/admin_flow_test.py"))
& scp @($Common + @("-P", "$Port", "${AdminFlowGuide}", "root@${HostAms}:/tmp/admin_flow_guide.py"))
& scp @($Common + @("-P", "$Port", "${AdminAuth}", "root@${HostAms}:/tmp/admin_auth.py"))
& scp @($Common + @("-P", "$Port", "${SchemaMigrations}", "root@${HostAms}:/tmp/schema_migrations.py"))
& scp @($Common + @("-P", "$Port", "${SetupUrlService}", "root@${HostAms}:/tmp/setup_url_service.py"))
& scp @($Common + @("-P", "$Port", "${SubscriptionCache}", "root@${HostAms}:/tmp/subscription_cache.py"))

$sshCmd = @'
set -e
ts=$(date +%Y%m%d-%H%M%S)
BT=/opt/remna-shop/src/shop_bot/bot
SB=/opt/remna-shop/src/shop_bot
DM=/opt/remna-shop/src/shop_bot/data_manager
WH=/opt/remna-shop/src/shop_bot/webhook_server
sed -i 's/\r$//' /tmp/handlers.py /tmp/user_messages.py /tmp/scheduler.py /tmp/keyboards.py /tmp/main.py /tmp/config.py /tmp/portal_links.py /tmp/portal_web_trial.py /tmp/portal_telegram_setup.py /tmp/subscription_resolve.py /tmp/web_trial_db.py /tmp/web_tg_bind.py /tmp/vpn_setup_wizard.py /tmp/subscription_qr.py /tmp/subscription_refresh.py /tmp/auto_renew_billing.py /tmp/support_auth.py /tmp/support_handler.py /tmp/remnawave_api.py /tmp/portal_cabinet.py /tmp/portal_browser_resolve.py /tmp/public_urls.py /tmp/admin_handlers.py /tmp/admin_flow_test.py /tmp/admin_flow_guide.py /tmp/schema_migrations.py /tmp/setup_url_service.py /tmp/subscription_cache.py /tmp/database.py /tmp/webhook_app_ams.py /tmp/webhook_app_main.py /tmp/webhook_auth.py /tmp/webhook_payment_queue.py /tmp/webhook_payment_amount_verify.py /tmp/webhook_payload_redact.py
ENV=/opt/remna-shop/.env
grep -q '^WEB_TRIAL_DAYS=' "$ENV" 2>/dev/null && sed -i '/^WEB_TRIAL_DAYS=/d' "$ENV" || true
echo 'WEB_TRIAL_DAYS=1' >> "$ENV"
sed -i 's|REMNA_BASE_URL=https://k9x2m1.conntest.xyz:2053|REMNA_BASE_URL=https://k9x2m1.conntest.xyz:8443|' "$ENV" || true
sed -i 's|SUB_DOMAIN=p4n7q.conntest.xyz:2053|SUB_DOMAIN=p4n7q.conntest.xyz:8443|' "$ENV" || true
grep -q '^ADMIN_TELEGRAM_IDS=' "$ENV" 2>/dev/null || echo 'ADMIN_TELEGRAM_IDS=' >> "$ENV"
mkdir -p "$BT" "$DM" "$WH"
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
install -m 0644 /tmp/portal_web_trial.py "$SB/portal_web_trial.py"
install -m 0644 /tmp/web_trial_db.py "$SB/web_trial_db.py"
install -m 0644 /tmp/web_tg_bind.py "$SB/web_tg_bind.py"
install -m 0644 /tmp/vpn_setup_wizard.py "$SB/vpn_setup_wizard.py"
install -m 0644 /tmp/subscription_qr.py "$SB/subscription_qr.py"
install -m 0644 /tmp/subscription_refresh.py "$BT/subscription_refresh.py"
install -m 0644 /tmp/auto_renew_billing.py "$SB/auto_renew_billing.py"
install -m 0644 /tmp/database.py "$DM/database.py"
install -m 0644 /tmp/support_auth.py "$SB/support_auth.py"
install -m 0644 /tmp/support_handler.py "$BT/support_handler.py"
install -m 0644 /tmp/remnawave_api.py "$SB/remnawave_api.py"
install -m 0644 /tmp/remnawave_api.py "$SB/modules/remnawave_api.py"
install -m 0644 /tmp/portal_cabinet.py "$SB/portal_cabinet.py"
install -m 0644 /tmp/portal_browser_resolve.py "$SB/portal_browser_resolve.py"
install -m 0644 /tmp/portal_telegram_setup.py "$SB/portal_telegram_setup.py"
install -m 0644 /tmp/subscription_resolve.py "$SB/subscription_resolve.py"
install -m 0644 /tmp/public_urls.py "$SB/public_urls.py"
install -m 0644 /tmp/admin_handlers.py "$BT/admin_handlers.py"
install -m 0644 /tmp/admin_flow_test.py "$SB/admin_flow_test.py"
install -m 0644 /tmp/admin_flow_guide.py "$SB/admin_flow_guide.py"
install -m 0644 /tmp/admin_auth.py "$SB/admin_auth.py"
install -m 0644 /tmp/schema_migrations.py "$SB/schema_migrations.py"
install -m 0644 /tmp/setup_url_service.py "$SB/setup_url_service.py"
install -m 0644 /tmp/subscription_cache.py "$SB/subscription_cache.py"
install -m 0644 /tmp/webhook_app_ams.py "$WH/app_ams_with_portal_trial.py"
install -m 0644 /tmp/webhook_app_main.py "$WH/app.py"
install -m 0644 /tmp/webhook_auth.py "$WH/auth.py"
install -m 0644 /tmp/webhook_payment_queue.py "$WH/payment_queue.py"
install -m 0644 /tmp/webhook_payment_amount_verify.py "$WH/payment_amount_verify.py"
install -m 0644 /tmp/webhook_payload_redact.py "$WH/payload_redact.py"
install -m 0644 /tmp/main.py /opt/remna-shop/src/shop_bot/main.py
docker cp /tmp/handlers.py remna-shop-bot:/app/src/shop_bot/bot/handlers.py
docker cp /tmp/user_messages.py remna-shop-bot:/app/src/shop_bot/bot/user_messages.py
docker cp /tmp/keyboards.py remna-shop-bot:/app/src/shop_bot/bot/keyboards.py
docker cp /tmp/scheduler.py remna-shop-bot:/app/src/shop_bot/data_manager/scheduler.py
docker cp /tmp/config.py remna-shop-bot:/app/src/shop_bot/config.py
docker cp /tmp/portal_links.py remna-shop-bot:/app/src/shop_bot/bot/portal_links.py
docker cp /tmp/portal_web_trial.py remna-shop-bot:/app/src/shop_bot/portal_web_trial.py
docker cp /tmp/web_trial_db.py remna-shop-bot:/app/src/shop_bot/web_trial_db.py
docker cp /tmp/web_tg_bind.py remna-shop-bot:/app/src/shop_bot/web_tg_bind.py
docker cp /tmp/vpn_setup_wizard.py remna-shop-bot:/app/src/shop_bot/vpn_setup_wizard.py
docker cp /tmp/subscription_qr.py remna-shop-bot:/app/src/shop_bot/subscription_qr.py
docker cp /tmp/subscription_refresh.py remna-shop-bot:/app/src/shop_bot/bot/subscription_refresh.py
docker cp /tmp/auto_renew_billing.py remna-shop-bot:/app/src/shop_bot/auto_renew_billing.py
docker cp /tmp/database.py remna-shop-bot:/app/src/shop_bot/data_manager/database.py
docker cp /tmp/support_auth.py remna-shop-bot:/app/src/shop_bot/support_auth.py
docker cp /tmp/support_handler.py remna-shop-bot:/app/src/shop_bot/bot/support_handler.py
docker cp /tmp/remnawave_api.py remna-shop-bot:/app/src/shop_bot/remnawave_api.py
docker cp /tmp/remnawave_api.py remna-shop-bot:/app/src/shop_bot/modules/remnawave_api.py
docker cp /tmp/portal_cabinet.py remna-shop-bot:/app/src/shop_bot/portal_cabinet.py
docker cp /tmp/portal_browser_resolve.py remna-shop-bot:/app/src/shop_bot/portal_browser_resolve.py
docker cp /tmp/portal_telegram_setup.py remna-shop-bot:/app/src/shop_bot/portal_telegram_setup.py
docker cp /tmp/subscription_resolve.py remna-shop-bot:/app/src/shop_bot/subscription_resolve.py
docker cp /tmp/public_urls.py remna-shop-bot:/app/src/shop_bot/public_urls.py
docker cp /tmp/admin_handlers.py remna-shop-bot:/app/src/shop_bot/bot/admin_handlers.py
docker cp /tmp/admin_flow_test.py remna-shop-bot:/app/src/shop_bot/admin_flow_test.py
docker cp /tmp/admin_flow_guide.py remna-shop-bot:/app/src/shop_bot/admin_flow_guide.py
docker cp /tmp/admin_auth.py remna-shop-bot:/app/src/shop_bot/admin_auth.py
docker cp /tmp/schema_migrations.py remna-shop-bot:/app/src/shop_bot/schema_migrations.py
docker cp /tmp/setup_url_service.py remna-shop-bot:/app/src/shop_bot/setup_url_service.py
docker cp /tmp/subscription_cache.py remna-shop-bot:/app/src/shop_bot/subscription_cache.py
docker cp /tmp/webhook_app_ams.py remna-shop-bot:/app/src/shop_bot/webhook_server/app_ams_with_portal_trial.py
docker cp /tmp/webhook_app_main.py remna-shop-bot:/app/src/shop_bot/webhook_server/app.py
docker cp /tmp/webhook_auth.py remna-shop-bot:/app/src/shop_bot/webhook_server/auth.py
docker cp /tmp/webhook_payment_queue.py remna-shop-bot:/app/src/shop_bot/webhook_server/payment_queue.py
docker cp /tmp/webhook_payment_amount_verify.py remna-shop-bot:/app/src/shop_bot/webhook_server/payment_amount_verify.py
docker cp /tmp/webhook_payload_redact.py remna-shop-bot:/app/src/shop_bot/webhook_server/payload_redact.py
docker cp /tmp/main.py remna-shop-bot:/app/src/shop_bot/main.py
docker exec remna-shop-bot pip install -q 'tenacity>=8.2,<10'
cd /opt/remna-shop && docker compose restart remna-shop-bot
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
