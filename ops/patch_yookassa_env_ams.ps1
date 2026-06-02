# Merge YOOKASSA_* from local secret_key 2.txt / .secrets/yookassa.env into /opt/remna-shop/.env on AMS.
# From repo root:  pwsh -File ops/patch_yookassa_env_ams.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$patch = Join-Path $env:TEMP "yookassa_ams_patch.env"
python -c @"
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(r'$RepoRoot') / 'bot_src'))
import importlib.util
spec = importlib.util.spec_from_file_location('le', Path(r'$RepoRoot') / 'bot_src' / 'local_env.py')
le = importlib.util.module_from_spec(spec)
spec.loader.exec_module(le)
os.environ.pop('YOOKASSA_SHOP_ID', None)
os.environ.pop('YOOKASSA_SECRET_KEY', None)
le.load_local_env()
sid = (os.getenv('YOOKASSA_SHOP_ID') or '').strip()
sec = (os.getenv('YOOKASSA_SECRET_KEY') or '').strip()
if not sid or not sec:
    raise SystemExit('FAIL: YOOKASSA keys missing locally')
Path(r'$patch').write_text(
    f'YOOKASSA_SHOP_ID={sid}\nYOOKASSA_SECRET_KEY={sec}\n',
    encoding='utf-8',
)
print('OK: patch file written (not printing values)')
"@

$HostAms = "168.100.11.140"
$Port = 3344
$Key = Join-Path $env:USERPROFILE ".ssh\bvpn_ams_ed25519"
if (-not (Test-Path $Key)) { $Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519" }
$Common = @("-i", $Key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=40", "-o", "StrictHostKeyChecking=accept-new")

& scp @($Common + @("-P", "$Port", $patch, "root@${HostAms}:/tmp/yookassa_patch.env"))

$sshCmd = @'
set -e
ENV=/opt/remna-shop/.env
ts=$(date +%Y%m%d-%H%M%S)
cp "$ENV" "$ENV.before-yookassa-$ts"
grep -v '^YOOKASSA_SHOP_ID=' "$ENV" | grep -v '^YOOKASSA_SECRET_KEY=' > "$ENV.tmp" || true
cat /tmp/yookassa_patch.env >> "$ENV.tmp"
mv "$ENV.tmp" "$ENV"
chmod 600 "$ENV"
rm -f /tmp/yookassa_patch.env
grep -q '^YOOKASSA_SHOP_ID=' "$ENV" && grep -q '^YOOKASSA_SECRET_KEY=' "$ENV"
docker exec remna-shop-bot sh -c 'test -n "$YOOKASSA_SHOP_ID" && test -n "$YOOKASSA_SECRET_KEY"' && echo YOOKASSA_ENV_OK || echo YOOKASSA_ENV_WARN_restart_bot
'@

& ssh @($Common + @("-p", "$Port", "root@${HostAms}", $sshCmd))
Remove-Item -Force $patch -ErrorAction SilentlyContinue
Write-Host "Done patch_yookassa_env_ams"
