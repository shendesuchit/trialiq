param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [ValidateRange(1, 10000)]
    [int]$BatchSize = 5000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    Write-Host "[1/5] Running read-only full-load preflight..."
    & $Python scripts\batch14_preflight.py `
        --output data\profiles\batch14_preflight.json
    if ($LASTEXITCODE -ne 0) { throw "Batch 14 full-load preflight failed." }

    Write-Host "[2/5] Running Batch 14 focused tests before database mutation..."
    & $Python -m pytest `
        tests\chains\test_cypher_qa.py `
        tests\services\test_trial_catalog_service.py `
        tests\services\test_graph_query_isolation.py `
        tests\etl\test_canonical_graphrag.py `
        -q
    if ($LASTEXITCODE -ne 0) { throw "Batch 14 focused tests failed." }

    Write-Host "[3/5] Loading and reconciling the complete AACT canonical core graph..."
    & $Python scripts\load_canonical_graphrag.py `
        --full-load `
        --batch-size $BatchSize `
        --execution-batch 14 `
        --output data\profiles\batch14_full_aact_load.json
    if ($LASTEXITCODE -ne 0) { throw "Full AACT canonical load/reconciliation failed." }

    Write-Host "[4/5] Running large-graph runtime smoke including a high-fanout placebo probe..."
    & $Python scripts\verify_batch14_runtime.py `
        --full-load `
        --output data\profiles\batch14_full_runtime_smoke.json
    if ($LASTEXITCODE -ne 0) { throw "Batch 14 full-graph runtime smoke failed." }

    Write-Host "[5/5] Running complete TrialIQ pytest suite..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "TrialIQ pytest suite failed." }

    Write-Host "[SUCCESS] Batch 14 full AACT load + reconciliation + runtime verification passed."
    Write-Host "Load report:    $projectRoot\data\profiles\batch14_full_aact_load.json"
    Write-Host "Runtime report: $projectRoot\data\profiles\batch14_full_runtime_smoke.json"
}
finally {
    Pop-Location
}
