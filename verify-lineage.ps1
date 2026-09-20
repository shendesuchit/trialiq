$ErrorActionPreference = 'Stop'

Write-Host '=== TrialIQ lineage verification ===' -ForegroundColor Cyan

Write-Host "`n[1/4] Backend unit tests" -ForegroundColor Yellow
Set-Location 'F:\trialiq'
$env:PYTHONPATH = 'F:\trialiq\src'
& '.venv\Scripts\python.exe' -m pytest tests/services/test_lineage_service.py -q

Write-Host "`n[2/4] API route smoke test" -ForegroundColor Yellow
$baseUrl = 'http://127.0.0.1:8000'
$lineageUrl = "$baseUrl/api/v1/lineage/trials/NCT00000102"
$response = Invoke-RestMethod -Uri $lineageUrl -Method Get

if ($response.nct_id -ne 'NCT00000102') {
    throw "Unexpected NCT ID: $($response.nct_id)"
}

if ($response.status -notin @('SUCCESS', 'NOT_FOUND', 'VALIDATION_FAILED', 'EXECUTION_ERROR')) {
    throw "Unexpected lineage status: $($response.status)"
}

if ($null -eq $response.records) {
    throw 'Lineage response does not contain records.'
}

Write-Host "Lineage status: $($response.status)"
Write-Host "Source count: $($response.source_count)"

Write-Host "`n[3/4] OpenAPI route check" -ForegroundColor Yellow
$openApi = Invoke-RestMethod -Uri "$baseUrl/openapi.json" -Method Get
$routeExists = $openApi.paths.PSObject.Properties.Name -contains '/api/v1/lineage/trials/{nct_id}'

if (-not $routeExists) {
    throw 'Lineage route is missing from OpenAPI.'
}

Write-Host 'Lineage route is registered in OpenAPI.'

Write-Host "`n[4/4] Frontend production build" -ForegroundColor Yellow
Set-Location 'F:\trialiq\frontend'
& npm run build

Write-Host "`nAll lineage verification steps completed." -ForegroundColor Green
