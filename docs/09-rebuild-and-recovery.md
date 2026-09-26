# TrialIQ Rebuild and Recovery Runbook

## Purpose

This runbook is written for a future maintainer rebuilding TrialIQ from a clean machine after the original local databases and virtual environments are gone.

The goal is not merely to start the API. The goal is to reproduce the same architectural behavior and pass the stable-demo release gate.

## Recovery inputs you must preserve

A complete recovery requires:

1. the Git repository at a known commit/tag;
2. `.env.example` from that same commit;
3. `uv.lock` and Python project metadata from that same commit;
4. `frontend/package.json` and `frontend/package-lock.json` from that same commit;
5. access to an AACT PostgreSQL snapshot or the ability to obtain/restore one;
6. Neo4j 5.x or the compatible version documented by the release;
7. at least one supported LLM provider credential/model configuration for guided workflow verification.

The PostgreSQL and Neo4j physical data files are intentionally not the source of truth for Git recovery. Neo4j should be rebuilt from AACT using TrialIQ loaders.

## Step 1 — Recover the exact repository revision

Prefer a release tag. If no tag exists, record the commit SHA before rebuilding.

```powershell
git clone https://github.com/shendesuchit/trialiq.git
cd trialiq
git status
git rev-parse HEAD
```

Do not begin recovery from a working tree with uncommitted local patches unless you deliberately intend to reproduce those patches.

## Step 2 — Verify toolchain compatibility

Recommended baseline for this checkpoint:

- Windows 10/11;
- Python 3.12;
- Neo4j 5 Community-compatible runtime;
- PostgreSQL compatible with the AACT snapshot;
- Node.js version accepted by the committed Vite version;
- npm capable of lockfileVersion 3.

Before the final long-term release tag, record actual versions:

```powershell
python --version
node --version
npm --version
git --version
```

Also record Neo4j and PostgreSQL versions in the release notes.

## Step 3 — Restore AACT PostgreSQL

Restore the official/approved AACT PostgreSQL snapshot according to the AACT distribution format used at the time of recovery.

TrialIQ expects the structured AACT tables under the configured schema, normally:

```text
POSTGRES_DATABASE=aact_full
POSTGRES_SCHEMA=ctgov
```

Validate connectivity before loading Neo4j. The exact study count can differ from the historical checkpoint if the AACT snapshot is newer.

## Step 4 — Configure TrialIQ

```powershell
Copy-Item .env.example .env
```

Set:

- PostgreSQL credentials/database/schema;
- Neo4j URI/credentials/database;
- allowed CORS origins;
- LLM provider/model/API key configuration.

Keep secrets outside Git.

## Step 5 — Recreate the Python environment

Recommended path:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

If the release includes a validated `uv.lock`, a lock-based `uv` restore is preferable because it avoids silently resolving newer transitive dependencies.

Then confirm the stale-editable-install problem is not present:

```powershell
.\.venv\Scripts\python.exe -c "import trialiq; print(trialiq.__file__)"
```

The path must resolve inside this checkout under `src\trialiq`.

## Step 6 — Start/initialize Neo4j

For the repository-provided local container:

```powershell
docker compose up -d neo4j
```

Confirm that `.env` credentials match the runtime you actually started.

An empty Neo4j service is not enough for the stable demo. The canonical graph must be loaded.

## Step 7 — Run a bounded verification load first

Before attempting a full graph load, use the canonical loader on a deterministic bounded scope:

```powershell
.\.venv\Scripts\python.exe .\scripts\load_canonical_graphrag.py `
  --verification-load `
  --limit 5000 `
  --batch-size 1000 `
  --output .\data\profiles\recovery_verification_load.json
```

A successful run must reconcile the loaded scope.

Then run the relevant loader/retrieval tests before proceeding to the full graph.

## Step 8 — Load the full canonical graph

The stable path uses the full-load runner:

```powershell
.\scripts\run_batch14_full_load.ps1
```

or the underlying loader:

```powershell
.\.venv\Scripts\python.exe .\scripts\load_canonical_graphrag.py `
  --full-load `
  --batch-size 5000 `
  --output .\data\profiles\recovery_full_aact_load.json
```

The operation is designed to be rerunnable and reconciled.

Historical full-load verification reached 602,891 Trial nodes. Treat that as historical evidence only; do not fail a new snapshot solely because its trial count is different.

## Step 9 — Recreate frontend dependencies

From a clean checkout:

```powershell
Push-Location frontend
npm ci
npm run build
Pop-Location
```

If `npm ci` reports that `package.json` and `package-lock.json` are out of sync, stop and reconcile the committed manifests. Do not work around a manifest conflict by keeping an old `node_modules` directory; that defeats reproducibility.

## Step 10 — Start TrialIQ runtime

API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn trialiq.api.app:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

MCP normally runs through the in-process TrialIQ MCP integration. A standalone MCP process is optional for diagnostics.

## Step 11 — Run readiness checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Then run:

```powershell
.\.venv\Scripts\python.exe .\scripts\demo_preflight.py --base-url http://127.0.0.1:8000 --timeout 30
```

A healthy stable-demo environment must confirm API, Neo4j, MCP and LLM readiness and complete the guided preflight.

## Step 12 — Run the stable-demo release gate

```powershell
.\scripts\run_batch21_stable_demo_verification.ps1
```

Do not call the environment “recovered” until this gate passes.

## Step 13 — Manual visual smoke

Use the generated:

```text
data/profiles/batch21_stable_demo_scenarios.txt
```

Run all four qualified questions and confirm:

- Basic direct behavior;
- Intermediate related-study behavior;
- Advanced deterministic comparisons;
- HITL pause/resume above six candidates;
- Answer / Studies / Connections / Evidence;
- one successful PDF download/open.

## Step 14 — Record the recovered environment

Store a release/recovery note containing:

- Git SHA/tag;
- AACT snapshot date/version;
- PostgreSQL version;
- Neo4j version;
- Python version;
- Node/npm version;
- selected LLM provider/model for verification;
- full regression result;
- frontend build result;
- Batch 21 qualification result;
- manual smoke date/operator.

This final record is what makes future reproduction auditable rather than anecdotal.
