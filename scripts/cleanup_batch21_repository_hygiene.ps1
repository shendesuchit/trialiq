param(
    [string]$GitRoot = "F:\github\trialiq\trialiq"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $GitRoot ".git"))) {
    Write-Host "[STOP] Git repository not found at $GitRoot" -ForegroundColor Red
    exit 1
}

Write-Host "TrialIQ Batch 21 repository hygiene" -ForegroundColor Cyan
Write-Host "Repository: $GitRoot"
Write-Host ""

$Dirty = @(& git -C $GitRoot status --porcelain)
if ($LASTEXITCODE -ne 0) {
    Write-Host "[STOP] Could not read Git status." -ForegroundColor Red
    exit 1
}

if ($Dirty.Count -gt 0) {
    Write-Host "[INFO] Existing working-tree changes are present. They will not be discarded." -ForegroundColor Yellow
}

$GeneratedPaths = @(
    ".build_validation",
    ".pytest-cache",
    "artifacts",
    "src/trialiq.egg-info"
)

Write-Host "Untracking known generated/cache paths while preserving local files..." -ForegroundColor Cyan
& git -C $GitRoot rm -r --cached --ignore-unmatch -- $GeneratedPaths
if ($LASTEXITCODE -ne 0) {
    Write-Host "[STOP] git rm --cached failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Staged repository-hygiene changes:" -ForegroundColor Cyan
& git -C $GitRoot diff --cached --name-status

Write-Host ""
Write-Host "[PASS] Generated/cache paths are staged for removal from Git only." -ForegroundColor Green
Write-Host "Local copies were not deleted. Review the staged diff before committing." -ForegroundColor Yellow
