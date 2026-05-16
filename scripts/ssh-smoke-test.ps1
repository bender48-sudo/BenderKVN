# Проверка: SSH из этого ПК работает без пароля (BatchMode).
# Запуск из PowerShell: .\scripts\ssh-smoke-test.ps1

$ErrorActionPreference = 'Stop'
$hosts = @('bvpn-lv', 'bvpn-ams', 'bvpn-nl', 'bvpn-relay')

foreach ($h in $hosts) {
    Write-Host "Testing $h ..." -ForegroundColor Cyan
    ssh -o BatchMode=yes -o ConnectTimeout=15 $h "echo OK && hostname"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: $h" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "OK: $h" -ForegroundColor Green
}
Write-Host "All hosts OK." -ForegroundColor Green
