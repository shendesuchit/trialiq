param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [switch]$SkipLiveLlm
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    Write-Host "[1/4] Running Batch 15 focused qualification and two-call contract tests..."
    & $Python -m pytest `
        tests\qualification\test_scenario_qualification.py `
        tests\agents\test_agent_question_runtime.py `
        tests\chains\test_cypher_qa.py `
        tests\services\test_related_trial_metrics.py `
        tests\services\test_trial_catalog_service.py `
        -q
    if ($LASTEXITCODE -ne 0) { throw "Batch 15 focused tests failed." }

    Write-Host "[2/4] Re-running the Batch 14 full-graph bounded runtime smoke as a regression gate..."
    & $Python scripts\verify_batch14_runtime.py `
        --full-load `
        --output data\profiles\batch15_batch14_regression_smoke.json
    if ($LASTEXITCODE -ne 0) { throw "Batch 14 full-graph regression smoke failed." }

    Write-Host "[3/4] Qualifying realistic full-graph scenarios through MCP and the guided agent path..."
    $qualifyArgs = @(
        "scripts\qualify_batch15_scenarios.py",
        "--output", "data\profiles\batch15_realistic_qualification.json",
        "--candidates-output", "data\profiles\batch15_demo_candidates.json"
    )
    if ($SkipLiveLlm) {
        $qualifyArgs += "--skip-live-llm"
        Write-Warning "Live two-call LLM checks are being skipped; this is not the final qualification mode."
    }
    & $Python @qualifyArgs
    if ($LASTEXITCODE -ne 0) { throw "Batch 15 realistic scenario qualification failed." }

    Write-Host "[4/4] Running the complete TrialIQ pytest suite..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "TrialIQ pytest suite failed." }

    Write-Host "[SUCCESS] Batch 15 realistic scenario qualification passed."
    Write-Host "Qualification report: $projectRoot\data\profiles\batch15_realistic_qualification.json"
    Write-Host "Demo candidate pool:   $projectRoot\data\profiles\batch15_demo_candidates.json"
    Write-Host "Regression report:     $projectRoot\data\profiles\batch15_batch14_regression_smoke.json"
}
finally {
    Pop-Location
}
