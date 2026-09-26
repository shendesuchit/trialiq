# Verification & Trust

## What TrialIQ verifies

The stable-demo gate checks more than unit tests:

1. Python imports from the current checkout.
2. HITL/report/qualification contracts.
3. Full pytest regression.
4. Frontend production build.
5. Live API health.
6. Neo4j, MCP and LLM readiness.
7. Live guided preflight.
8. Basic / Intermediate / Advanced / HITL qualification.
9. Repository hygiene inspection.

## Verified checkpoint

On 2026-09-26:

```text
332 passed, 12 skipped, 2 warnings
Frontend production build: PASS
Live readiness/preflight: PASS
Stable-demo qualification: PASS
```

## Trust principles

- source-backed graph evidence;
- deterministic quantitative comparison;
- deterministic validation;
- unsupported synthesis claims can be rejected;
- HITL controls broad evidence sets;
- execution metadata is inspectable.

## Recommended visuals

Use:

- `08-runtime-readiness.mmd`
- `09-release-verification-flow.mmd`
