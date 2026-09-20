# TrialIQ

Graph-powered, evidence-grounded clinical-trial intelligence system.

## Local backend checks

Unit tests require no live services:

```powershell
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pytest -m "not integration" -q
```

Neo4j-backed integration tests are deliberately opt-in. Start the local graph
service, set the matching Neo4j variables from `.env.example`, then run:

```powershell
docker compose up -d neo4j
$env:TRIALIQ_RUN_INTEGRATION = "1"
.venv\Scripts\python.exe -m pytest -q
```

`GET /health` confirms that the API process is running. `GET /ready` additionally
confirms that the configured Neo4j database is reachable.
