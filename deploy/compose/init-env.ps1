# Create deploy/compose/.env from .env.example, replacing __GENERATE__ with random secrets.
# If .env already exists, only settings missing from it are appended; existing values are kept.
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

function New-Secret([int]$Length) {
    $chars = [char[]]'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    $bytes = New-Object byte[] $Length
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

$envPath = Join-Path $PSScriptRoot '.env'
$created = -not (Test-Path $envPath)
$existing = @()
if (-not $created) { $existing = Get-Content $envPath | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { $_.Split('=')[0] } }

$out = New-Object System.Collections.Generic.List[string]
$added = 0
foreach ($line in Get-Content .env.example) {
    if ($line -eq '' -or $line.StartsWith('#')) { if ($created) { $out.Add($line) }; continue }
    $key = $line.Split('=')[0]
    if ($existing -contains $key) { continue }
    if ($line -eq 'KIBANA_ENCRYPTION_KEY=__GENERATE__') { $out.Add("KIBANA_ENCRYPTION_KEY=$(New-Secret 48)") }
    elseif ($line -match '^([A-Z_]+)=__GENERATE__$') { $out.Add("$($Matches[1])=$(New-Secret 24)") }
    else { $out.Add($line) }
    $added++
}
# LF line endings and no BOM, so docker compose reads it the same on every platform
$text = ($out -join "`n") + "`n"
if ($created) { [System.IO.File]::WriteAllText($envPath, $text) }
elseif ($added -gt 0) { [System.IO.File]::AppendAllText($envPath, $text) }

if ($created) { Write-Output 'created deploy/compose/.env (Kibana login: elastic / ELASTIC_PASSWORD in .env)' }
else { Write-Output "deploy/compose/.env: added $added missing setting(s)" }
