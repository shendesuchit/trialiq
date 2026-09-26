# TrialIQ Setup and Local Development

## Purpose

This is the normal local setup guide for an engineer who already has the repository and access to the required AACT/Neo4j data environment.

For a clean-machine rebuild from raw prerequisites, use [09-rebuild-and-recovery.md](09-rebuild-and-recovery.md).

## Recommended environment

The repository CI and historical verified development path use **Python 3.12**. `pyproject.toml` currently permits Python `>=3.11`, but Python 3.12 is the safest reproduction target for this checkpoint.

Other required tools:

- Git;
- PostgreSQL with an AACT snapshot for load/source verification;
- Neo4j 5.x Community or compatible Neo4j 5 runtime;
- Node.js/npm compatible with the committed frontend dependency set;
- at least one configured LLM provider for the live guided path.

## Clone and create backend environment

```powershell
git clone https://github.com/shendesuchit/trialiq.git
cd trialiq

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

If using `uv`, keep `uv.lock` with the same commit and prefer a lock-based sync rather than resolving fresh dependency versions.

## Environment configuration

Copy the committed template:

```powershell
Copy-Item .env.example .env
```

Configure at minimum:

### Neo4j

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<local password>
NEO4J_DATABASE=neo4j
```

### AACT/PostgreSQL

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=aact_full
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=<local password>
POSTGRES_SCHEMA=ctgov
```

### CORS

```text
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### LLM

Choose one or more configured providers:

```text
LLM_PROVIDER=auto
LLM_PROVIDER_PRIORITY=openai,gemini,openrouter
LLM_STARTUP_PROBE=true
LLM_REQUEST_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=0
```

Then set the relevant API key/model pairs for OpenAI, Gemini and/or OpenRouter.

Do not commit `.env` or provider credentials.

## Neo4j local service

For a lightweight empty/local Neo4j service, the repository includes:

```powershell
docker compose up -d neo4j
```

`compose.yaml` currently uses Neo4j 5 Community and exposes ports 7474 and 7687.

For the full stable-demo experience, Neo4j must contain the canonical AACT-derived graph, not merely an empty container.

## Frontend install

```powershell
Push-Location frontend
npm ci
Pop-Location
```

### Frontend dependency-manifest warning

At documentation time, the supplied repository state shows a mismatch between `frontend/package.json` and the root dependency set recorded in `frontend/package-lock.json`. The verified local build used the existing installed frontend environment and reported Vite 8.3.0.

For a clean clone, **do not assume reproducibility until this drift is reconciled and `npm ci` succeeds from scratch**. See [16-reproducibility-checklist.md](16-reproducibility-checklist.md).

## Start the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn trialiq.api.app:app --host 127.0.0.1 --port 8000
```

Confirm:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

## Start the frontend

In another terminal:

```powershell
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173` when available.

## Optional standalone MCP diagnostic

The normal guided path can use the MCP object in-process. To run the server independently for diagnostics:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m trialiq.mcp.server
```

## Unit tests

Unit tests do not require live Neo4j when integration tests are excluded:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration" -q
```

## Full repository tests with integration opt-in

With Neo4j configured:

```powershell
$env:TRIALIQ_RUN_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

## Stable-demo verification

With the full local runtime available:

```powershell
.\scripts\run_batch21_stable_demo_verification.ps1
```

Use this gate before claiming that a local environment matches the stable-demo baseline.
