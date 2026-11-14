# Stage 0 - Build the immutable raw manifest (run ONCE, after copying raw files).
# For every file under data/raw: record investigation, relative path, size, SHA-256, file category.
# Then mark every raw file read-only. Re-running refuses to overwrite an existing manifest.
param([string]$Root = (Resolve-Path "$PSScriptRoot\..\..").Path)

$raw      = Join-Path $Root "data\raw"
$manifest = Join-Path $Root "data\raw_manifest.csv"
if (Test-Path $manifest) { Write-Error "Manifest already exists: $manifest. Raw is immutable - use verify_raw.ps1 instead."; exit 1 }

function Get-Category($name) {
    if ($name -like '*Experimental table*')            { return 'experimental_table' }
    if ($name -like '*metadata*.zip')                   { return 'investigation_metadata' }
    if ($name -like '*calibration*')                    { return 'calibration' }
    if ($name -match '^\d{2}CAL\d{2}')                  { return 'raw_test_data' }   # FLEX per-test text files
    if ($name -match '\.(pdf|doc|docx|pptx)$')          { return 'document' }
    if ($name -match '\.xlsx$')                         { return 'supporting_table' }
    return 'other'
}

$rows = Get-ChildItem $raw -Recurse -File | Sort-Object FullName | ForEach-Object {
    $rel = $_.FullName.Substring($raw.Length + 1)
    [pscustomobject]@{
        source_id     = ($rel -split '[\\_]')[0]          # e.g. PSI-69
        relative_path = $rel -replace '\\','/'
        size_bytes    = $_.Length
        sha256        = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
        category      = Get-Category $_.Name
    }
}
$rows | Export-Csv $manifest -NoTypeInformation -Encoding UTF8
Get-ChildItem $raw -Recurse -File | ForEach-Object { $_.IsReadOnly = $true }
Write-Host "Manifest written: $($rows.Count) files. All raw files set read-only."
