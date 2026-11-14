# Stage 0 - Verify raw archive against the manifest. Run before every ETL run.
# Fails (exit 1) if any file is missing, changed, not read-only, or unexpected.
param([string]$Root = (Resolve-Path "$PSScriptRoot\..\..").Path)

$raw      = Join-Path $Root "data\raw"
$manifest = Import-Csv (Join-Path $Root "data\raw_manifest.csv")
$problems = @()
$known    = @{}

foreach ($m in $manifest) {
    $p = Join-Path $raw ($m.relative_path -replace '/','\')
    $known[$p.ToLower()] = $true
    if (-not (Test-Path $p))                                                   { $problems += "MISSING  $($m.relative_path)"; continue }
    if ((Get-FileHash $p -Algorithm SHA256).Hash.ToLower() -ne $m.sha256)      { $problems += "CHANGED  $($m.relative_path)" }
    if (-not (Get-Item $p).IsReadOnly)                                         { $problems += "WRITABLE $($m.relative_path)" }
}
Get-ChildItem $raw -Recurse -File | Where-Object { -not $known[$_.FullName.ToLower()] } |
    ForEach-Object { $problems += "UNLISTED $($_.FullName.Substring($raw.Length + 1))" }

if ($problems.Count) { $problems | ForEach-Object { Write-Host $_ }; Write-Host "RAW VERIFY FAILED ($($problems.Count) problems)"; exit 1 }
Write-Host "RAW VERIFY OK - $($manifest.Count) files match manifest."
