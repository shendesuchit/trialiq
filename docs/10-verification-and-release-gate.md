# TrialIQ Verification and Stable-Demo Release Gate

## Purpose

This page defines what must be true before a TrialIQ checkout is treated as matching the stable-demo baseline.

## Why a single gate exists

Individual unit tests are not enough. TrialIQ spans:

- Python services;
- React/TypeScript frontend;
- Neo4j;
- AACT-derived graph data;
- MCP transport;
- an LLM provider;
- HITL pause/resume;
- PDF generation;
- full-graph scenario qualification.

The stable-demo gate combines those concerns so an environment cannot appear healthy simply because one layer passes.

## Primary command

```powershell
.\scripts\run_batch21_stable_demo_verification.ps1
```

## Gate stages

### 1. Python import-source check

The active virtual environment must import `trialiq` from the current checkout.

This prevents a stale editable/site-packages installation from making tests or runtime behavior come from older code.

### 2. Targeted contracts

The gate runs focused tests covering:

- scenario qualification helpers;
- Batch 21 stable-demo logic;
- preflight behavior;
- HITL contract;
- HITL runtime resume;
- PDF report generation.

### 3. Full regression suite

The complete repository test suite runs.

Verified stable-demo checkpoint on 2026-09-26:

```text
332 passed, 12 skipped, 2 warnings
```

This count is a historical checkpoint, not a forever-fixed invariant. If tests are added later, the expected count should change.

### 4. Frontend production build

The gate runs:

```powershell
npm run build
```

which currently executes TypeScript build plus Vite production build.

A passing dev server is not a substitute for a production build.

### 5. Live API availability

If a healthy local API is already running, the gate uses it. Otherwise the script can start a temporary local Uvicorn process for verification.

### 6. Live readiness and HITL-aware preflight

`demo_preflight.py` verifies:

- API health;
- API readiness;
- Neo4j readiness;
- MCP readiness;
- LLM readiness;
- live agentic retrieval;
- deterministic metrics;
- validation;
- structured synthesis.

The preflight is HITL-aware. If a broad candidate set requires review, it can continue the run instead of incorrectly treating `REVIEW_REQUIRED` as a failure.

### 7. Stable-demo scenario qualification

The qualifier discovers/validates the final demo ladder against the active full graph:

- Basic;
- Intermediate;
- Advanced;
- HITL.

The Batch 21.1 hotfix keeps small-scenario discovery memory bounded by starting from indexed `loaded_trial_count` and limiting the entity scan before trial expansion rather than collecting huge full-graph peer/entity lists.

Output files:

```text
data/profiles/batch21_stable_demo_qualification.json
data/profiles/batch21_stable_demo_scenarios.json
data/profiles/batch21_stable_demo_scenarios.txt
```

### 8. Repository hygiene inspection

The gate checks for known generated paths still tracked in the Git checkout, including build validation output, pytest cache, artifacts and egg-info.

Runtime verification can still pass if cleanup is pending, but the repo should be cleaned before the stable branch/tag is declared final.

## Manual visual smoke

Automated verification deliberately does not pretend to verify visual usability. Before a demo/release freeze, run the four generated questions in the actual UI and confirm:

1. Basic question returns the expected direct evidence-grounded result.
2. Intermediate question produces a small 2–6 related-study set without unnecessary HITL.
3. Advanced question exposes meaningful deterministic comparison data.
4. HITL question pauses above six candidates and resumes successfully after selection.
5. Answer / Studies / Connections / Evidence remain usable.
6. Connections counters/graph/table match the active filter/scope.
7. A PDF report can be downloaded and opened.

## Grounding rejection messages

During live synthesis, logs may show that candidate structured claims were rejected by the grounding contract. That is not automatically a release failure. The important question is whether the final run satisfies the required validated contract.

Do not suppress grounding rejections merely to make logs look clean; unsupported claims should be rejected.

## Release evidence record

For a durable release, archive or commit a small release record containing:

- Git SHA/tag;
- verification timestamp;
- test/build summary;
- readiness summary;
- scenario qualification summary;
- manual smoke result;
- relevant data snapshot identifier.

Large generated databases or caches should not be committed just to preserve the record.

## Definition of Stable Demo

A checkout can be called TrialIQ Stable Demo when:

- automated gate passes;
- manual visual smoke passes;
- dependency manifests can be installed from a clean clone;
- repository hygiene is clean;
- the documentation matches the tagged commit.
