$ErrorActionPreference = "Stop"
Write-Host "=== TrialIQ provenance verification ==="

Write-Host "[1/4] Provenance unit tests"
Set-Location F:\trialiq
$env:PYTHONPATH = "F:\trialiq\src"
& ".venv\Scripts\python.exe" -m pytest tests/services/test_lineage_service.py tests/test_provenance.py -q

Write-Host "[2/4] Provenance module import check"
& ".venv\Scripts\python.exe" -c "from trialiq.provenance import enrich_transformed_artifact; print('Provenance module import: OK')"

Write-Host "[3/4] OpenAPI route check"
& ".venv\Scripts\python.exe" -c "from trialiq.api.app import app; routes = {r.path for r in app.routes}; assert '/api/v1/lineage/trials/{nct_id}' in routes; print('Lineage route is registered in OpenAPI application routes.')"

Write-Host "[4/4] Frontend production build"
Set-Location F:\trialiq\frontend
npm run build

Write-Host "All provenance verification steps completed."
