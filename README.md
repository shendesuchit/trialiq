# TrialIQ

TrialIQ is an evidence-grounded clinical-trial intelligence application built around:

- **PostgreSQL / AACT** as the structured source of truth
- **Neo4j** as the canonical graph used for bounded related-trial retrieval
- **FastAPI** for the application API
- **FastMCP** for controlled agent/tool access
- **React + Vite** for the Investigator Console
- **LLM provider abstraction** supporting OpenAI, Gemini, and OpenRouter
- **Deterministic validation and quantitative comparison logic** for evidence-grounded results

This README is intended to make a new Windows machine recoverable from the Git repository plus a fresh AACT snapshot.

> **Important:** The PostgreSQL and Neo4j physical database files are intentionally **not** stored in Git. They are rebuilt from the official AACT PostgreSQL snapshot and the TrialIQ loader scripts.

---

## 1. Current checkpoint

This repository documents the TrialIQ state through the **Batch 18 result-frame / graph-workspace baseline** plus the TypeScript null-safety hotfix.

The full AACT load used to qualify this checkpoint successfully loaded:

- **602,891 Trial nodes**
- canonical **Condition**
- canonical **Intervention**
- canonical **Sponsor**
- bounded, hub-aware related-trial retrieval

The historical Batch 14 full-load report is stored under:

```text
data/profiles/batch14_full_aact_load.json
```

A newer AACT snapshot can contain a different study count. Treat `602,891` as the historical checkpoint count, **not** as a permanent invariant.

The architecture constraints for the agentic path are:

```text
User question
  -> LLM call 1: structured intent
  -> supervisor
  -> MCP
  -> bounded Neo4j retrieval
  -> deterministic metrics
  -> deterministic grounding validation
  -> LLM call 2: structured grounded synthesis
  -> frontend
```

The normal guided investigation path must not introduce:

- silent MCP -> direct Neo4j fallback
- arbitrary LLM-generated Cypher
- unbounded graph traversal
- live LLM/network calls inside deterministic unit tests
- a third LLM call solely for validation

---

## 2. Repository layout

Important directories and files:

```text
frontend/                         React + Vite Investigator Console
src/trialiq/api/                 FastAPI application and routes
src/trialiq/agents/              Agentic workflow
src/trialiq/chains/              Intent/retrieval logic and fixed Cypher
src/trialiq/config/              Runtime settings
src/trialiq/etl/                 AACT extraction/transform/load services
src/trialiq/graph/               Neo4j connection + schema
src/trialiq/llm/                 Provider abstraction and services
src/trialiq/mcp/                 FastMCP server/tool definitions
src/trialiq/qualification/       Realistic scenario qualification
src/trialiq/services/            Application/business services
tests/                           Backend/frontend contract tests

scripts/load_canonical_graphrag.py
scripts/run_batch13_verification.ps1
scripts/run_batch14_full_load.ps1
scripts/run_batch14_verification.ps1
scripts/run_batch15_qualification.ps1
scripts/run_batch16_verification.ps1
scripts/run_batch17_verification.ps1
scripts/run_batch18_verification.ps1
scripts/run_demo_preflight.bat

docs/batch13-canonical-graphrag.md
docs/batch14-full-graph-retrieval.md

data/profiles/                   Saved load / verification reports
```

Do not use files under `build/` as source code. `src/trialiq/` is authoritative.

---

## 3. Services used locally

A normal local development/demo environment uses the following components:

| Component | Typical local address | Required? | Notes |
|---|---|---:|---|
| PostgreSQL / AACT | `127.0.0.1:5432` | Yes for source verification/load | Database normally named `aact`; AACT tables are under schema `ctgov` |
| Neo4j | `bolt://localhost:7687` | Yes | Canonical graph database; default database is normally `neo4j` |
| TrialIQ FastAPI | `http://127.0.0.1:8000` | Yes | `/health`, `/ready`, `/api/v1/...` |
| FastMCP | in-process in normal agent flow | Yes logically | TrialIQ's `FastMCPRetrievalClient` uses the controlled TrialIQ MCP object directly; standalone MCP startup is optional for diagnostics |
| React/Vite frontend | `http://localhost:5173` by default | Yes for UI | Vite may choose another port if 5173 is busy |

### MCP note

For the normal TrialIQ application, you do **not** need a fourth permanently running MCP terminal if the current in-process MCP client is used.

The MCP server can still be run independently for diagnostics:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m trialiq.mcp.server
```

The MCP server exposes controlled tools including trial evidence retrieval, condition/intervention/sponsor search, shared-entity comparison, related-trial discovery, source verification, and trial overview.

---

## 4. Prerequisites

Recommended Windows setup:

- Windows 10/11
- Git
- Python **3.12**
- `uv` (recommended because `uv.lock` is committed) or `pip`
- Node.js LTS + npm
- PostgreSQL with `psql`, `createdb`, and `pg_restore`
- Neo4j Desktop or Neo4j Community/Enterprise server
- PowerShell 7 or Windows PowerShell 5.1
- An API key for at least one configured LLM provider for the agentic path

Useful official download pages:

- AACT: https://aact.ctti-clinicaltrials.org/landing
- AACT PostgreSQL snapshots: https://aact.ctti-clinicaltrials.org/downloads/snapshots
- AACT Windows/PostgreSQL setup: https://aact.ctti-clinicaltrials.org/install_postgres
- PostgreSQL: https://www.postgresql.org/download/windows/
- Neo4j Deployment Center: https://neo4j.com/deployment-center/
- Neo4j Windows installation: https://neo4j.com/docs/operations-manual/current/installation/windows/
- Node.js: https://nodejs.org/
- Python: https://www.python.org/downloads/windows/

---

## 5. Clone the repository

```powershell
git clone https://github.com/shendesuchit/trialiq.git
cd trialiq
```

If you are restoring the protected Batch 18 checkpoint after it has been tagged:

```powershell
git fetch --tags
git checkout trialiq-batch18-demo-baseline
```

For ongoing development, switch back to the intended branch after recovery.

---

## 6. Python environment

### Option A — `uv` (recommended)

From the repository root:

```powershell
uv sync
```

If the environment is not automatically activated:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Option B — standard `venv` + pip

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
```

If test tooling is not included by the package metadata in your checkout, install the repository's development dependencies according to `pyproject.toml`.

Confirm that TrialIQ resolves from this checkout rather than a stale `site-packages` install:

```powershell
.\.venv\Scripts\python.exe -c "import trialiq; print(trialiq.__file__)"
```

The path should resolve under this repository's `src\trialiq` tree.

If it does not, reinstall editable mode:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

---

## 7. Environment configuration

Create the real local environment file from the committed template:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`.

**Never commit `.env` or real API/database passwords.**

Use the variable names already defined by the checked-in `.env.example` and `src/trialiq/config/settings.py`. Do not invent alternate names.

The current application supports configuration for:

### Neo4j

Typical values:

```text
URI:       bolt://localhost:7687
database:  neo4j
username:  neo4j
password:  <your local password>
```

### PostgreSQL / AACT

Typical local values:

```text
host:      127.0.0.1
port:      5432
database:  aact
schema:    ctgov
username:  <your local PostgreSQL user>
password:  <your local password>
```

### LLM

TrialIQ supports:

```text
LLM_PROVIDER=auto
LLM_PROVIDER_PRIORITY=openai,gemini,openrouter
```

or an explicit provider:

```text
LLM_PROVIDER=gemini
```

Known provider settings include:

```text
OPENAI_API_KEY
OPENAI_MODEL

GEMINI_API_KEY
GEMINI_MODEL

OPENROUTER_API_KEY
OPENROUTER_MODEL

LLM_REQUEST_TIMEOUT_SECONDS
LLM_MAX_RETRIES
```

The working demo configuration at the Batch 18 checkpoint used Gemini successfully, but model availability changes over time. Use a model currently available to your provider account and verify it through the TrialIQ readiness/preflight path.

---

# Part A — Rebuild PostgreSQL / AACT

## 8. Download an AACT snapshot

AACT is maintained by the Clinical Trials Transformation Initiative (CTTI) and refreshes the ClinicalTrials.gov registry into a relational PostgreSQL model.

1. Open the AACT site:
   - https://aact.ctti-clinicaltrials.org/landing
2. Sign in/create an AACT account if required.
3. Open PostgreSQL snapshots:
   - https://aact.ctti-clinicaltrials.org/downloads/snapshots
4. Download the desired recent full PostgreSQL snapshot.
5. Extract the downloaded ZIP.

The extracted archive contains a PostgreSQL dump named:

```text
postgres_data.dmp
```

It may also include the schema diagram, data dictionary, and supporting documentation.

Do **not** commit the multi-gigabyte AACT ZIP or dump to Git.

---

## 9. Install PostgreSQL

Install PostgreSQL with at least:

- PostgreSQL server
- `psql`
- `createdb`
- `pg_restore`
- pgAdmin (optional but convenient)

AACT's Windows documentation describes restoring the dump into a local `aact` database and notes that its dump has historically referenced `ctti` and `read_only` roles.

### GUI method

AACT documents a pgAdmin workflow at:

https://aact.ctti-clinicaltrials.org/install_postgres

### Command-line method

Ensure the PostgreSQL `bin` directory is on PATH, or use the executable's full path.

Create the database:

```powershell
createdb -U postgres aact
```

A robust restore that avoids restoring original owner/ACL metadata is:

```powershell
pg_restore `
  -h 127.0.0.1 `
  -p 5432 `
  -U postgres `
  -e `
  -v `
  -O `
  -x `
  --no-owner `
  -d aact `
  "C:\path\to\postgres_data.dmp"
```

If you follow the AACT Windows guide literally, create the `ctti` and `read_only` PostgreSQL roles and restore using the role settings described there.

For an existing `aact` database that is being replaced with a new snapshot, use the AACT refresh guidance carefully. AACT warns that schema and PostgreSQL-version changes can affect dump compatibility.

---

## 10. Verify AACT

Open `psql`:

```powershell
psql -U postgres -d aact
```

Then:

```sql
SELECT COUNT(*) FROM ctgov.studies;
SELECT COUNT(*) FROM ctgov.conditions;
SELECT COUNT(*) FROM ctgov.interventions;
SELECT COUNT(*) FROM ctgov.sponsors;
```

Exit:

```text
\q
```

The exact counts depend on the snapshot date.

If you prefer AACT's search-path convention:

```sql
ALTER ROLE <your-user> IN DATABASE aact
SET search_path = ctgov, public;
```

Reconnect after changing the role search path.

---

# Part B — Rebuild Neo4j

## 11. Install Neo4j

Use either:

- **Neo4j Desktop** for the easiest local developer experience, or
- a local Neo4j server installation.

Official download:

https://neo4j.com/deployment-center/

On Windows, Neo4j also documents ZIP/service installation at:

https://neo4j.com/docs/operations-manual/current/installation/windows/

Create/start a local instance and record:

```text
Bolt URI:  bolt://localhost:7687
Database:  neo4j
Username:  neo4j
Password:  <your password>
```

Put the matching settings into `.env`.

Confirm connectivity in Neo4j Query/Browser:

```cypher
RETURN 1 AS ok;
```

---

## 12. Apply TrialIQ graph schema

TrialIQ contains the Neo4j schema definition:

```text
src/trialiq/graph/schema.cypher
```

You can execute it in Neo4j Query/Browser or with `cypher-shell`.

Example:

```powershell
Get-Content ".\src\trialiq\graph\schema.cypher" |
    cypher-shell `
        -a "bolt://localhost:7687" `
        -u "neo4j" `
        -p "<your-password>" `
        -d "neo4j"
```

Do not paste real passwords into scripts committed to Git.

---

## 13. Canonical GraphRAG loader

The canonical full-graph path introduced in Batch 13/14 is represented by:

```text
scripts/load_canonical_graphrag.py
scripts/run_batch13_verification.ps1
scripts/run_batch14_full_load.ps1
scripts/run_batch14_verification.ps1

src/trialiq/etl/canonical_graphrag.py

docs/batch13-canonical-graphrag.md
docs/batch14-full-graph-retrieval.md
```

### First: 5,000-trial verification

Before attempting a full load on a newly rebuilt machine:

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\run_batch13_verification.ps1
```

The historical successful report is:

```text
data/profiles/batch13_verification_5000.json
```

A successful run must reconcile source rows with canonical graph relationships and report no reconciliation errors.

### Full AACT load

After the smaller verification succeeds:

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\run_batch14_full_load.ps1
```

The historical Batch 18-era full-load checkpoint produced:

```text
602,891 Trial nodes
1,083,806 HAS_CONDITION relationships
1,001,094 canonical HAS_INTERVENTION relationships
961,152 canonical SPONSORED_BY relationships
```

The same report also reconciled represented source rows and provenance.

With a newer AACT snapshot, exact totals can legitimately differ.

### Post-load verification

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\run_batch14_verification.ps1
```

Relevant historical reports:

```text
data/profiles/batch14_full_aact_load.json
data/profiles/batch14_full_runtime_smoke.json
data/profiles/batch14_preflight.json
data/profiles/batch14_runtime_smoke.json
```

Do not declare a fresh graph ready until the load, reconciliation, and runtime smoke checks succeed.

---

## 14. Realistic scenario qualification

After the full graph is ready:

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\run_batch15_qualification.ps1
```

Relevant saved reports:

```text
data/profiles/batch15_batch14_regression_smoke.json
data/profiles/batch15_demo_candidates.json
data/profiles/batch15_realistic_qualification.json
```

Historically useful demo candidates include:

```text
NCT00001239
NCT00000620
NCT00620139
NCT00065754
```

These are qualification examples, not hard-coded product behavior.

---

# Part C — Frontend and runtime

## 15. Install frontend dependencies

```powershell
cd frontend
npm ci
```

Build once before running the app:

```powershell
npm run build
```

The current frontend package scripts are:

```text
npm run dev
npm run build
npm run preview
```

Return to repository root:

```powershell
cd ..
```

---

## 16. Start Neo4j and PostgreSQL first

Before starting TrialIQ:

1. PostgreSQL is running and the `aact` database is accessible.
2. Neo4j is running and Bolt connectivity works.
3. `.env` contains the correct local settings.
4. At least one LLM provider is configured if you want the agentic path.

---

## 17. Start the FastAPI application

Open a PowerShell terminal in the repository root:

```powershell
$env:PYTHONPATH = "$PWD\src"

.\.venv\Scripts\python.exe `
    -m uvicorn trialiq.api.app:app `
    --host 127.0.0.1 `
    --port 8000 `
    --reload
```

Keep this terminal open.

### Health check

In another PowerShell terminal:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

### Readiness check

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/ready"
```

The readiness path should confirm the required runtime dependencies used by the current application.

---

## 18. Start the frontend

Open another PowerShell terminal:

```powershell
cd <repo-root>\frontend
npm run dev
```

Vite normally prints the exact local URL, commonly:

```text
http://localhost:5173
```

Open the displayed URL in a browser.

---

## 19. Optional standalone MCP server

The normal TrialIQ agent client can use the FastMCP server in-process.

For direct MCP diagnostics only:

```powershell
cd <repo-root>
$env:PYTHONPATH = "$PWD\src"

.\.venv\Scripts\python.exe -m trialiq.mcp.server
```

Do not replace the governed MCP workflow with a silent direct-Neo4j fallback.

---

# Part D — Verification

## 20. Demo preflight

With dependencies configured:

```powershell
.\scripts\run_demo_preflight.bat
```

A healthy demo preflight should check the API/runtime path, Neo4j, MCP and configured LLM, then exercise an agentic evidence flow.

---

## 21. Full backend regression

From repository root:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest -q
```

Do not compare only against an old historical test count; the suite grows as TrialIQ evolves. The important result is that the current checked-in suite completes without unexpected failures.

---

## 22. Frontend production build

```powershell
cd frontend
npm ci
npm run build
cd ..
```

This catches TypeScript and Vite compilation failures that may not be visible in development mode.

---

## 23. Batch-specific regression chain

For the current UI/graph baseline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_batch16_verification.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_batch17_verification.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_batch18_verification.ps1
```

### Batch 18 checkpoint caveat

The Batch 18 UI was visually confirmed running after the TypeScript hotfix:

```text
buildGraphLayout(analysisGraph.nodes ?? [], reportedDepth)
```

Before creating or relying on the final `trialiq-batch18-demo-baseline` Git tag, capture a **successful post-hotfix output** from:

```powershell
.\scripts\run_batch18_verification.ps1
```

Do not describe Batch 18 as fully verified until that final run succeeds.

---

## 24. Canonical demo question

A useful end-to-end guided investigation is:

```text
Find completed trials connected to NCT03416088 through its conditions
or interventions. Explain exactly why they are connected, compare their
completion timelines and enrollment, and show the evidence supporting
each conclusion.
```

The guided agentic path should use MCP for controlled retrieval and preserve evidence/provenance.

---

# Part E — Repository hygiene and disaster recovery

## 25. Files that should NOT be committed

The root `.gitignore` should exclude at least:

```text
.env
.venv/
venv/
node_modules/
frontend/node_modules/
__pycache__/
.pytest_cache/
*.pyc
*.log
*.tsbuildinfo
build/
dist/
frontend/dist/
*.patch

neo4j-data/
neo4j-logs/
postgres-data/

large AACT .zip / .dmp / .backup files
```

Also remove local one-off backup files such as:

```text
*.before_*
```

unless they have intentionally been turned into documented source artifacts.

Do not commit:

- real API keys
- PostgreSQL passwords
- Neo4j passwords
- physical PostgreSQL database storage
- physical Neo4j database storage
- downloaded full AACT snapshot ZIPs/dumps
- Python bytecode
- TypeScript build caches
- generated `build/` copies of Python packages

---

## 26. Files worth keeping

Small source-backed samples and verification evidence are useful to preserve when intentional:

```text
artifacts/aact_sample_5.json

data/extracted/
data/transformed/
data/profiles/

docs/
scripts/
tests/
```

`data/profiles/` is especially useful as evidence of historical successful loads and qualifications, but it is not a substitute for rerunning verification after rebuilding a database.

---

## 27. Clean-check before committing

From repository root:

```powershell
git status --short
```

Look specifically for accidental secrets or generated files.

Useful additional check:

```powershell
git status --ignored --short
```

Search staged/untracked text for obvious secret-bearing filenames before the first push.

Never stage `.env`.

---

## 28. Create the protected Batch 18 checkpoint

After:

- full backend tests pass
- frontend build passes
- Batch 18 post-hotfix verification passes
- `.env` is not tracked
- generated files have been excluded

commit the checkpoint:

```powershell
git add -A
git status

git commit -m "TrialIQ full AACT graph and investigator UX through Batch 18"
```

Push the import branch:

```powershell
git push -u origin import/batch18-tested-baseline
```

After reviewing it, merge it to the intended main branch using your normal GitHub/GitHub Desktop workflow.

Then create the protected tag on the verified commit:

```powershell
git tag -a trialiq-batch18-demo-baseline `
    -m "Verified TrialIQ Batch 18 demo baseline"

git push origin trialiq-batch18-demo-baseline
```

The older GitHub state is separately protected by:

```text
backup/pre-batch18-old
pre-batch18-old-github
```

---

# Part F — Full disaster-recovery sequence

If the machine and all local databases are lost:

```text
1. Install Git, Python, Node.js, PostgreSQL and Neo4j.
2. Clone the TrialIQ repository.
3. Checkout the protected baseline tag/branch if required.
4. Create Python environment and install TrialIQ.
5. Run npm ci in frontend.
6. Copy .env.example -> .env and configure secrets locally.
7. Download a fresh official AACT PostgreSQL snapshot.
8. Restore postgres_data.dmp into local database aact.
9. Verify ctgov.studies and source tables.
10. Start/configure Neo4j.
11. Apply src/trialiq/graph/schema.cypher.
12. Run Batch 13 5k canonical verification.
13. Run Batch 14 full canonical graph load.
14. Run Batch 14 reconciliation/runtime verification.
15. Run Batch 15 realistic qualification.
16. Start FastAPI.
17. Run /health and /ready.
18. Install/build/start frontend.
19. Run demo preflight.
20. Run full pytest suite.
21. Run frontend production build.
22. Run Batch 16/17/18 verification.
23. Open the Investigator Console and perform a live demo query.
```

At that point the application is rebuilt from source and official source data rather than restored from opaque local database files.

---

## 29. Troubleshooting

### Python imports a stale TrialIQ installation

Check:

```powershell
.\.venv\Scripts\python.exe -c "import trialiq; print(trialiq.__file__)"
```

If it is not this checkout:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

### `/ready` fails

Verify:

- Neo4j instance is running
- Bolt URI is correct
- username/password are correct
- configured database exists
- `.env` is loaded by the process

### Source verification fails

Verify:

- PostgreSQL is running
- `aact` exists
- AACT tables exist under `ctgov`
- application PostgreSQL credentials are correct
- the downloaded snapshot restored successfully

### Agent path fails but deterministic graph retrieval works

Check:

- selected LLM provider
- API key
- configured model
- provider quota/availability
- startup/readiness output
- MCP transport metadata

Do not work around an MCP failure by silently switching the agentic workflow to direct Neo4j access.

### Frontend compiles in dev but production build fails

Always run:

```powershell
cd frontend
npm run build
```

The production build includes TypeScript compilation and is required before declaring a UI batch verified.

---

## 30. Reference documents

Read these before changing the canonical load path:

```text
docs/batch13-canonical-graphrag.md
docs/batch14-full-graph-retrieval.md
```

Primary verification/load scripts:

```text
scripts/run_batch13_verification.ps1
scripts/run_batch14_full_load.ps1
scripts/run_batch14_verification.ps1
scripts/run_batch15_qualification.ps1
scripts/run_batch16_verification.ps1
scripts/run_batch17_verification.ps1
scripts/run_batch18_verification.ps1
```

---

## 31. Security

This repository is intended to contain source code and rebuild instructions, **not credentials**.

Before every public push:

```powershell
git status
git diff --cached
```

Confirm that no real values from `.env` or local database credentials are staged.

If a real API key is ever committed, treat it as compromised and rotate it at the provider immediately, even if the commit is later deleted.

---

## 32. Development rule for future batches

Treat the current backend/data foundation as stable unless a concrete defect requires a change.

Future UX work should preserve:

```text
Answer
Studies
Connections
Evidence
```

and keep the technical graph as progressive disclosure rather than the primary clinical workflow.

Before starting a new enhancement batch, create a clean commit/tag or branch from the last verified state.
