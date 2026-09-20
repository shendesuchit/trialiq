from fastapi.testclient import TestClient

from trialiq.api.app import app
from trialiq.mcp.server import mcp


results = []

# Application initialization
assert app is not None
results.append("PASS: FastAPI application initialized")

client = TestClient(app)

# Health endpoint
response = client.get("/health")
assert response.status_code == 200
results.append("PASS: GET /health")

# Readiness endpoint
response = client.get("/ready")
assert response.status_code in (200, 503)
results.append(
    f"PASS: GET /ready responded with {response.status_code}"
)

# OpenAPI route registration
schema = app.openapi()
paths = schema.get("paths", {})

assert "/api/v1/trials/overview" in paths
results.append("PASS: Trial overview route registered in OpenAPI")

assert "/api/v1/query" in paths
results.append("PASS: Query route registered in OpenAPI")

# Request validation
response = client.post(
    "/api/v1/trials/overview",
    json={"nct_id": ""},
)

assert response.status_code in (400, 422)
results.append("PASS: Invalid trial request rejected")

# MCP initialization
assert mcp is not None
results.append("PASS: MCP server initialized")

for result in results:
    print(result)

print("API/MCP validation complete")