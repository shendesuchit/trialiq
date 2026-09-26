# TrialIQ API and MCP Contract

## Purpose

This page summarizes the stable public/local interfaces used by the Investigator Console, verification scripts and governed agent workflow.

## FastAPI application

Entry point:

```text
trialiq.api.app:app
```

Typical local URL:

```text
http://127.0.0.1:8000
```

## Health and readiness

### `GET /health`

Purpose: confirms the API process is running.

This is a liveness check, not proof that Neo4j, MCP or an LLM provider are available.

### `GET /ready`

Purpose: returns dependency-level runtime readiness without hiding degraded subsystems.

The release preflight evaluates API, Neo4j, MCP and LLM readiness separately.

## Trial endpoints

### `GET /api/v1/trials/catalog`

Purpose: supports bounded/searchable study selection in the Investigator Console.

### `POST /api/v1/trials/overview`

Purpose: returns an evidence-grounded trial overview through the deterministic service path.

## Query endpoints

### `POST /api/v1/query`

Purpose: backward-compatible query contract supporting selected workflow mode.

Important HITL behavior: this contract cannot return an interactive pause. If agent mode produces a broad candidate set, the compatibility path explicitly chooses `ALL` and completes.

### `POST /api/v1/query/agent`

Purpose: runs the guided agent workflow and can return either a completed `AgentRunResult` or an `AgentHumanReviewRun` with status `REVIEW_REQUIRED`.

### `POST /api/v1/query/agent/continue`

Purpose: resumes a paused guided investigation with the investigator-approved selection.

The resume contract references the stored run/checkpoint and does not repeat graph retrieval.

### `POST /api/v1/query/agent/report`

Purpose: generates a PDF from the already shown/approved result sections.

The response is `application/pdf` with a TrialIQ filename based on the investigation seed where possible.

## Lineage endpoints

### `GET /api/v1/lineage/trials/{nct_id}`

Purpose: exposes source/provenance lineage for a study.

### `GET /api/v1/lineage/trials/{nct_id}/graph`

Purpose: returns a bounded typed graph view for the technical relationship visualization.

## MCP server

Entry point:

```text
python -m trialiq.mcp.server
```

Normal application behavior can use the MCP object/client in-process; a fourth permanently running MCP terminal is not required for the stable local demo.

## Governed MCP tools

### `health_check`

Verifies the TrialIQ MCP transport.

### `get_trial_evidence`

Retrieves validated, read-only graph evidence for an NCT ID.

### `search_trials_by_condition`

Bounded exact case-insensitive condition search.

### `search_trials_by_intervention`

Bounded exact case-insensitive intervention search.

### `search_trials_by_sponsor`

Bounded exact case-insensitive sponsor search.

### `compare_trial_shared_entities`

Compares two studies over bounded shared Condition, Intervention and Sponsor entities.

### `find_related_trials`

Discovers related studies with bounded one/two-hop traversal over allowlisted graph relationships and optional relationship/status filters.

### `verify_trial_evidence`

Compares graph evidence with the AACT source and reports discrepancies.

### `get_trial_overview`

Returns the deterministic evidence-grounded overview for an NCT ID.

## Contract guardrails

- MCP tools return typed TrialIQ models.
- Retrieval is read-only for investigator paths.
- Cypher is TrialIQ-owned and validated; model-generated arbitrary Cypher is not accepted.
- Graph traversal has explicit bounds.
- Sensitive credentials are configuration, not response metadata.
- The UI should display only runtime stages/metadata actually returned by the backend.

## Error semantics

TrialIQ response models distinguish states such as:

- success/grounded;
- not found;
- insufficient evidence;
- unsupported;
- validation failed;
- execution error;
- review required for the interactive guided path.

A zero-match bounded graph search is not the same as an execution failure.
