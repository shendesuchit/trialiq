param(
    [string]$Source = "F:\trialiq",
    [string]$Target = "F:\github\trialiq\trialiq"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Source)) {
    throw "Source does not exist: $Source"
}

if (-not (Test-Path "$Target\.git")) {
    throw "Target is not the expected Git repository: $Target"
}

$Branch = git -C $Target branch --show-current

if (-not $Branch -or $Branch -eq "main") {
    throw "Refusing to sync directly into main. Create/switch to a Batch feature branch first."
}

Write-Host "Source : $Source"
Write-Host "Target : $Target"
Write-Host "Branch : $Branch"

$RoboArgs = @(
    $Source
    $Target
    "/E"
    "/COPY:DAT"
    "/DCOPY:DAT"
    "/R:1"
    "/W:1"
    "/XJ"
    "/NP"

    "/XD"
    ".git"
    ".venv"
    "venv"
    "node_modules"
    "__pycache__"
    ".pytest_cache"
    ".pytest-tmp"
    ".mypy_cache"
    ".ruff_cache"
    ".vite"
    "build"
    "dist"
    "htmlcov"
    "coverage"

    "/XF"
    ".env"
    ".env.local"
    ".env.development.local"
    ".env.production.local"
    ".env.test.local"
    "*.pyc"
    "*.pyo"
    "*.log"
    "*.patch"
    "*.rej"
    "*.orig"
    "*.tsbuildinfo"
    "combined_files*.txt"
    "*inspection_bundle*.txt"
)

& robocopy.exe @RoboArgs
$RoboExit = $LASTEXITCODE

if ($RoboExit -ge 8) {
    throw "Robocopy failed with exit code $RoboExit."
}

Write-Host "`nSync completed." -ForegroundColor Green
Write-Host "Nothing was committed or pushed." -ForegroundColor Yellow

Write-Host "`n=== Git status ===" -ForegroundColor Cyan
git -C $Target status --short
