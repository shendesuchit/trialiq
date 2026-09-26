param(
    [string]$ProjectRoot = "",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$GitRoot = "F:\github\trialiq\trialiq"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Frontend = Join-Path $ProjectRoot "frontend"
$StartedApi = $null

function Stop-WithError([string]$Message) {
    Write-Host "[STOP] $Message" -ForegroundColor Red
    exit 1
}

function Test-ApiHealth([string]$Url) {
    try {
        $Response = Invoke-WebRequest -Uri ($Url.TrimEnd('/') + "/health") -UseBasicParsing -TimeoutSec 3
        return $Response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

try {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " TrialIQ Batch 21 - stable demo completion verification" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Project: $ProjectRoot"
    Write-Host "API:     $BaseUrl"
    Write-Host ""

    if (-not (Test-Path $Python)) {
        Stop-WithError "Python virtual environment not found at $Python"
    }
    if (-not (Test-Path (Join-Path $Frontend "package.json"))) {
        Stop-WithError "Frontend package.json not found."
    }
    if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
        Stop-WithError "frontend\node_modules is missing. Run npm ci in frontend first."
    }

    Write-Host "[1/8] Verifying Python import source..." -ForegroundColor Cyan
    $ImportPath = (& $Python -c "import trialiq; print(trialiq.__file__)" | Select-Object -Last 1).Trim()
    if ($LASTEXITCODE -ne 0) {
        Stop-WithError "Could not import TrialIQ from the active virtual environment."
    }
    $ExpectedSource = (Join-Path $ProjectRoot "src\trialiq").ToLowerInvariant()
    if (-not $ImportPath.ToLowerInvariant().StartsWith($ExpectedSource)) {
        Write-Host "Resolved import: $ImportPath" -ForegroundColor Yellow
        Stop-WithError "The virtual environment is importing a stale TrialIQ installation. Run: .venv\Scripts\python.exe -m pip install -e ."
    }
    Write-Host "[PASS] TrialIQ import resolves to this checkout." -ForegroundColor Green

    Write-Host ""
    Write-Host "[2/8] Running Batch 21 targeted contracts..." -ForegroundColor Cyan
    & $Python -m pytest `
        tests\qualification\test_scenario_qualification.py `
        tests\qualification\test_batch21_stable_demo.py `
        tests\qualification\test_batch21_preflight_contract.py `
        tests\agents\test_batch20_hitl_contract.py `
        tests\agents\test_batch20_1_hitl_runtime.py `
        tests\services\test_batch20_1_report_pdf.py `
        -q
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Targeted Batch 21 contracts failed." }
    Write-Host "[PASS] Targeted contracts." -ForegroundColor Green

    Write-Host ""
    Write-Host "[3/8] Running full regression suite..." -ForegroundColor Cyan
    & $Python -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Full regression suite failed." }
    Write-Host "[PASS] Full regression suite." -ForegroundColor Green

    Write-Host ""
    Write-Host "[4/8] Running frontend production build..." -ForegroundColor Cyan
    Push-Location $Frontend
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { Stop-WithError "Frontend production build failed." }
    }
    finally {
        Pop-Location
    }
    Write-Host "[PASS] Frontend production build." -ForegroundColor Green

    Write-Host ""
    Write-Host "[5/8] Ensuring live API is available..." -ForegroundColor Cyan
    if (-not (Test-ApiHealth $BaseUrl)) {
        $Uri = [System.Uri]$BaseUrl
        if ($Uri.Scheme -ne "http" -or $Uri.Host -notin @("127.0.0.1", "localhost")) {
            Stop-WithError "API is not reachable and automatic startup is only supported for a local http://127.0.0.1 or localhost URL."
        }
        $Stdout = Join-Path $env:TEMP "trialiq_batch21_api_stdout.log"
        $Stderr = Join-Path $env:TEMP "trialiq_batch21_api_stderr.log"
        Remove-Item $Stdout, $Stderr -Force -ErrorAction SilentlyContinue
        $StartedApi = Start-Process `
            -FilePath $Python `
            -ArgumentList @("-m", "uvicorn", "trialiq.api.app:app", "--host", $Uri.Host, "--port", [string]$Uri.Port) `
            -WorkingDirectory $ProjectRoot `
            -RedirectStandardOutput $Stdout `
            -RedirectStandardError $Stderr `
            -PassThru

        $Ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            if ($StartedApi.HasExited) { break }
            if (Test-ApiHealth $BaseUrl) {
                $Ready = $true
                break
            }
        }
        if (-not $Ready) {
            Write-Host "API stdout: $Stdout" -ForegroundColor Yellow
            Write-Host "API stderr: $Stderr" -ForegroundColor Yellow
            Stop-WithError "TrialIQ API did not become healthy within 30 seconds."
        }
        Write-Host "[PASS] Temporary TrialIQ API started for release verification." -ForegroundColor Green
    }
    else {
        Write-Host "[PASS] Existing TrialIQ API is healthy." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "[6/8] Running live readiness + HITL-aware demo preflight..." -ForegroundColor Cyan
    & $Python scripts\demo_preflight.py --base-url $BaseUrl --timeout 30
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Live demo preflight failed." }
    Write-Host "[PASS] Live demo preflight." -ForegroundColor Green

    Write-Host ""
    Write-Host "[7/8] Qualifying final Basic / Intermediate / Advanced / HITL scenarios..." -ForegroundColor Cyan
    & $Python scripts\qualify_batch21_stable_demo.py `
        --output data\profiles\batch21_stable_demo_qualification.json `
        --scenarios-output data\profiles\batch21_stable_demo_scenarios.json `
        --summary-output data\profiles\batch21_stable_demo_scenarios.txt
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Stable-demo scenario qualification failed." }
    Write-Host "[PASS] Stable-demo scenario qualification." -ForegroundColor Green

    Write-Host ""
    Write-Host "[8/8] Repository hygiene inspection..." -ForegroundColor Cyan
    if (Test-Path (Join-Path $GitRoot ".git")) {
        $GeneratedPatterns = @(
            ".build_validation/*",
            ".pytest-cache/*",
            "artifacts/*",
            "src/trialiq.egg-info/*"
        )
        $TrackedGenerated = @(& git -C $GitRoot ls-files -- $GeneratedPatterns)
        if ($TrackedGenerated.Count -gt 0) {
            Write-Host "[INFO] Generated files are still tracked in the Git checkout." -ForegroundColor Yellow
            Write-Host "       Run scripts\cleanup_batch21_repository_hygiene.ps1 after syncing Batch 21." -ForegroundColor Yellow
            $TrackedGenerated | ForEach-Object { Write-Host "       $_" -ForegroundColor Yellow }
        }
        else {
            Write-Host "[PASS] No known generated/cache paths are tracked." -ForegroundColor Green
        }
    }
    else {
        Write-Host "[SKIP] Git checkout not found at $GitRoot. Runtime verification is unaffected." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " [SUCCESS] TrialIQ Batch 21 stable demo release gate passed" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Generated release evidence:"
    Write-Host "  $ProjectRoot\data\profiles\batch21_stable_demo_qualification.json"
    Write-Host "  $ProjectRoot\data\profiles\batch21_stable_demo_scenarios.json"
    Write-Host "  $ProjectRoot\data\profiles\batch21_stable_demo_scenarios.txt"
    Write-Host ""
    Write-Host "Only manual visual smoke remains before documentation:" -ForegroundColor Yellow
    Write-Host "  1. Run the four questions listed in batch21_stable_demo_scenarios.txt."
    Write-Host "  2. Confirm Answer / Studies / Connections / Evidence remain functional."
    Write-Host "  3. Confirm the HITL scenario pauses above six candidates and resumes correctly."
    Write-Host "  4. Download one PDF report and open it successfully."
}
finally {
    if ($null -ne $StartedApi -and -not $StartedApi.HasExited) {
        Stop-Process -Id $StartedApi.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[INFO] Temporary TrialIQ API stopped." -ForegroundColor DarkGray
    }
}
