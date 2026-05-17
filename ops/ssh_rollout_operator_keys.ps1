# P1-RED-SSH-01: generate and install per-host operator keys (Windows).
param(
    [switch]$GenerateOnly,
    [switch]$InstallLv,
    [switch]$InstallAms
)

$ErrorActionPreference = "Stop"
$SshDir = Join-Path $env:USERPROFILE ".ssh"
$Keys = @(
    @{ Name = "bvpn_lv_ed25519"; Host = "bvpn-lv" },
    @{ Name = "bvpn_ams_ed25519"; Host = "bvpn-ams" }
)

function Ensure-Key([string]$Name) {
    $priv = Join-Path $SshDir $Name
    $pub = "$priv.pub"
    if (-not (Test-Path $priv)) {
        Write-Host "[gen] $Name"
        & ssh-keygen -t ed25519 -f $priv -N '""' -C "bender-$Name"
    } else {
        Write-Host "[skip] exists $Name"
    }
    return $pub
}

function Install-Pubkey([string]$HostAlias, [string]$PubPath) {
    if (-not (Test-Path $PubPath)) { throw "Missing $PubPath" }
    $tag = (Split-Path -Leaf $PubPath) -replace '\.pub$', ''
    Write-Host "[install] $HostAlias <- $(Split-Path -Leaf $PubPath)"
    $tmp = "/tmp/$tag.pub"
    & scp -o BatchMode=yes -o ConnectTimeout=20 $PubPath "${HostAlias}:$tmp"
    if ($LASTEXITCODE -ne 0) { throw "scp failed for $HostAlias" }
    $remote = "grep -q '$tag' /root/.ssh/authorized_keys 2>/dev/null || cat $tmp >> /root/.ssh/authorized_keys; rm -f $tmp"
    & ssh -o BatchMode=yes -o ConnectTimeout=20 $HostAlias $remote
    if ($LASTEXITCODE -ne 0) { throw "ssh install failed for $HostAlias" }
}

New-Item -ItemType Directory -Force -Path $SshDir | Out-Null
foreach ($k in $Keys) {
    Ensure-Key $k.Name | Out-Null
}

if ($GenerateOnly -and -not $InstallLv -and -not $InstallAms) {
    Write-Host "Done (generate only). Update ~/.ssh/config from ssh/config.example"
    exit 0
}

if ($InstallLv) {
    Install-Pubkey "bvpn-lv" (Join-Path $SshDir "bvpn_lv_ed25519.pub")
}
if ($InstallAms) {
    Install-Pubkey "bvpn-ams" (Join-Path $SshDir "bvpn_ams_ed25519.pub")
}

if (-not $InstallLv -and -not $InstallAms) {
    Write-Host "Use -InstallLv / -InstallAms to append pubkeys (keeps legacy keys)."
}
