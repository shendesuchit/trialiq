param(
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    Write-Host "[1/3] Building the Batch 16 investigator frontend..."
    Push-Location "frontend"
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
    }
    finally {
        Pop-Location
    }

    Write-Host "[2/3] Running Batch 16 UX-contract and graph regression tests..."
    & $Python -m pytest `
        tests\frontend\test_batch16_ui_contract.py `
        tests\services\test_graph_view_service.py `
        tests\services\test_related_trial_metrics.py `
        tests\services\test_trial_catalog_service.py `
        tests\services\test_graph_query_isolation.py `
        -q
    if ($LASTEXITCODE -ne 0) { throw "Batch 16 focused tests failed." }

    Write-Host "[3/3] Running complete TrialIQ pytest suite..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "TrialIQ pytest suite failed." }

    Write-Host "[SUCCESS] Batch 16 final investigator UX consistency passed."
    Write-Host "Next check: inspect NCT00001239 and NCT00000620 in the Investigator UI."
}
finally {
    Pop-Location
}
