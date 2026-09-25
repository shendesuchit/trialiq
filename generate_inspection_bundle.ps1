
# Change Start
$ErrorActionPreference = "Stop"

$ProjectRoot = "F:\trialiq"
$OutputFile = Join-Path $ProjectRoot "trialiq_full_inspection_bundle.txt"

# Files and directories to include
$IncludeDirectories = @(
    "src",
    "tests"
)

$IncludeFiles = @(
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "README.md",
    ".env.example"
)

# Directories and files to exclude
$ExcludePatterns = @(
    '\.venv\\'
    '__pycache__'
    '\\.git\\'
    '\.pytest_cache'
    'node_modules'
    '\.env$'
    '\.env\.'
    '\.pem$'
    '\.key$'
    '\.p12$'
    '\.pfx$'
)

# Extensions to include from source directories
$AllowedExtensions = @(
    ".py",
    ".toml",
    ".txt",
    ".md",
    ".yaml",
    ".yml",
    ".json"
)

function Should-Exclude {
    param (
        [string]$FilePath
    )

    foreach ($Pattern in $ExcludePatterns) {
        if ($FilePath -match $Pattern) {
            return $true
        }
    }

    return $false
}

function Add-FileToBundle {
    param (
        [string]$FilePath,
        [System.IO.StreamWriter]$Writer
    )

    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) {
        return
    }

    if (Should-Exclude -FilePath $FilePath) {
        return
    }

    $RelativePath = $FilePath.Substring(
       $ProjectRoot.TrimEnd('\').Length + 1
    )

    $Writer.WriteLine("")
    $Writer.WriteLine("============================================================")
    $Writer.WriteLine("FILE: $RelativePath")
    $Writer.WriteLine("============================================================")
    $Writer.WriteLine("")

    # Basic secret redaction for common environment-style values.
    $Content = Get-Content -LiteralPath $FilePath -Raw

    $Content = $Content -replace `
        '(?im)^(\s*(?:[A-Z0-9_]*(?:KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL)[A-Z0-9_]*)\s*=\s*).+$', `
        '$1[REDACTED]'

    $Content = $Content -replace `
        '(?im)(["'']?(?:api[_-]?key|access[_-]?token|password|secret)["'']?\s*[:=]\s*["'']?)[^"'',\s}]+', `
        '$1[REDACTED]'

    $Writer.WriteLine($Content)
    $Writer.WriteLine("")
    $Writer.WriteLine("END FILE: $RelativePath")
}

# Avoid including the output bundle itself if the script is rerun.
if (Test-Path -LiteralPath $OutputFile) {
    Remove-Item -LiteralPath $OutputFile -Force
}

$Writer = New-Object System.IO.StreamWriter(
    $OutputFile,
    $false,
    [System.Text.Encoding]::UTF8
)

try {
    $Writer.WriteLine("TRIALIQ FULL INSPECTION BUNDLE")
    $Writer.WriteLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    $Writer.WriteLine("Project root: $ProjectRoot")
    $Writer.WriteLine("")
    $Writer.WriteLine("Sensitive values should be treated as redacted where detected.")
    $Writer.WriteLine("")

    # Include source and test directories.
    foreach ($Directory in $IncludeDirectories) {
        $DirectoryPath = Join-Path $ProjectRoot $Directory

        if (-not (Test-Path -LiteralPath $DirectoryPath -PathType Container)) {
            continue
        }

        $Files = Get-ChildItem `
            -LiteralPath $DirectoryPath `
            -File `
            -Recurse |
            Where-Object {
                ($AllowedExtensions -contains $_.Extension.ToLowerInvariant()) `
                -and (-not (Should-Exclude -FilePath $_.FullName))
            } |
            Sort-Object FullName

        foreach ($File in $Files) {
            Add-FileToBundle `
                -FilePath $File.FullName `
                -Writer $Writer
        }
    }

    # Include selected root-level files.
    foreach ($FileName in $IncludeFiles) {
        $FilePath = Join-Path $ProjectRoot $FileName

        if (Test-Path -LiteralPath $FilePath -PathType Leaf) {
            Add-FileToBundle `
                -FilePath $FilePath `
                -Writer $Writer
        }
    }
}
finally {
    $Writer.Flush()
    $Writer.Close()
}

Write-Host ""
Write-Host "Inspection bundle generated successfully:"
Write-Host $OutputFile
Write-Host ""
Write-Host "Review the bundle manually for any secrets before uploading."
# Change End