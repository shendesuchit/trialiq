$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "[$Name]"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit code $LASTEXITCODE)"
    }
}

Write-Host "=== TrialIQ consolidated verification ==="
Set-Location F:\trialiq
$env:PYTHONPATH = "F:\trialiq\src"
$python = ".venv\Scripts\python.exe"

Invoke-Step "1/5 Unit and service tests" {
    & $python -m pytest tests/services/test_lineage_service.py tests/test_provenance.py -q
}

Invoke-Step "2/5 Import checks" {
    & $python -c "from trialiq.provenance import enrich_transformed_artifact; from trialiq.services.lineage_service import get_trial_lineage; print('Core imports: OK')"
}

Invoke-Step "3/5 OpenAPI contract checks" {
    & $python -c "from trialiq.api.app import app; paths = app.openapi()['paths']; expected = '/api/v1/lineage/trials/{nct_id}'; assert expected in paths, f'Missing route: {expected}'; methods = paths[expected]; assert 'get' in methods, 'Lineage route is not exposed as GET'; print(f'OpenAPI route: {expected}'); print('OpenAPI contract: OK')"
}

Invoke-Step "4/5 Backend readiness checks" {
    & $python -c "from trialiq.api.app import app; paths = app.openapi()['paths']; required = ['/health', '/ready', '/api/v1/query', '/api/v1/trials/overview', '/api/v1/lineage/trials/{nct_id}']; missing = [p for p in required if p not in paths]; assert not missing, 'Missing OpenAPI paths: ' + ', '.join(missing); print('Required API paths: OK')"
}

Set-Location F:\trialiq\frontend
Invoke-Step "5/5 Frontend production build" {
    npm run build
}

Write-Host "=== Consolidated verification passed ===" -ForegroundColor Green
