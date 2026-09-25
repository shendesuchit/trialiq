param(
    [ValidateRange(1, 1000000)]
    [int]$Limit = 5000,

    [ValidateRange(1, 10000)]
    [int]$BatchSize = 1000,

    [string]$Output = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "TrialIQ virtual-environment Python was not found: $Python"
}

if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $ProjectRoot "data\profiles\batch13_verification_$Limit.json"
}

Push-Location $ProjectRoot
try {
    Write-Host "[1/3] Running Batch 13 focused tests..."
    & $Python -m pytest "tests\etl\test_canonical_graphrag.py" -q
    if ($LASTEXITCODE -ne 0) {
        throw "Batch 13 focused tests failed with exit code $LASTEXITCODE."
    }

    Write-Host "[2/3] Loading and reconciling $Limit canonical AACT trials..."
    & $Python ".\scripts\load_canonical_graphrag.py" `
        --verification-load `
        --limit $Limit `
        --batch-size $BatchSize `
        --output $Output
    if ($LASTEXITCODE -ne 0) {
        throw "Batch 13 canonical verification load failed with exit code $LASTEXITCODE."
    }

    Write-Host "[3/3] Running the full TrialIQ test suite..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "TrialIQ test suite failed with exit code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "[SUCCESS] Batch 13 canonical loader + verification path passed."
    Write-Host "Reconciliation report: $Output"
}
finally {
    Pop-Location
}
