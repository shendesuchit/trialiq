param(
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    Write-Host "[1/3] Running Batch 14 focused tests..."
    & $Python -m pytest `
        tests\chains\test_cypher_qa.py `
        tests\services\test_trial_catalog_service.py `
        tests\services\test_graph_query_isolation.py `
        tests\etl\test_canonical_graphrag.py `
        -q
    if ($LASTEXITCODE -ne 0) { throw "Batch 14 focused tests failed." }

    Write-Host "[2/3] Running Batch 14 runtime smoke against the current canonical graph..."
    & $Python scripts\verify_batch14_runtime.py `
        --output data\profiles\batch14_runtime_smoke.json
    if ($LASTEXITCODE -ne 0) { throw "Batch 14 runtime smoke failed." }

    Write-Host "[3/3] Running complete TrialIQ pytest suite..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "TrialIQ pytest suite failed." }

    Write-Host "[SUCCESS] Batch 14 retrieval hardening + full-load readiness passed."
    Write-Host "Runtime smoke: $projectRoot\data\profiles\batch14_runtime_smoke.json"
}
finally {
    Pop-Location
}
