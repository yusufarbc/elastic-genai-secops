# Create deploy/compose/.env from .env.example, replacing __GENERATE__ with random secrets.
# Does nothing if .env already exists.
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

if (Test-Path .env) {
    Write-Output '.env already exists; leaving it unchanged'
    exit 0
}

function New-Secret([int]$Length) {
    $chars = [char[]]'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    $bytes = New-Object byte[] $Length
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

$lines = Get-Content .env.example | ForEach-Object {
    if ($_ -eq 'KIBANA_ENCRYPTION_KEY=__GENERATE__') { "KIBANA_ENCRYPTION_KEY=$(New-Secret 48)" }
    elseif ($_ -match '^([A-Z_]+)=__GENERATE__$') { "$($Matches[1])=$(New-Secret 24)" }
    else { $_ }
}
# LF line endings and no BOM, so docker compose reads it the same on every platform
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot '.env'), (($lines -join "`n") + "`n"))
Write-Output 'created deploy/compose/.env (Kibana login: elastic / ELASTIC_PASSWORD in .env)'
