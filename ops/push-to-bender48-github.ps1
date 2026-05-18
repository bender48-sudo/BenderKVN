# Push main to https://github.com/bender48-sudo/BenderKVN.git
# Run after signing in as bender48-sudo (not VaDi-ai):
#   Windows: Параметры → Учётные записи → Диспетчер учётных данных → Удалить github.com для VaDi-ai
#   Then: git push -u origin main  (browser login as bender48-sudo)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
git remote set-url origin https://github.com/bender48-sudo/BenderKVN.git
Write-Host "Remote:" (git remote get-url origin)
Write-Host "Pushing main..."
git push -u origin main
Write-Host "OK: https://github.com/bender48-sudo/BenderKVN"
