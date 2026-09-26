# Architecture Overview

## Core TrialIQ stack

| Layer | TrialIQ technology / module |
| --- | --- |
| Investigator UI | React + Vite |
| API | FastAPI |
| Guided orchestration | SupervisorAgent |
| Governed tools | FastMCP |
| Graph | Neo4j |
| Structured source | AACT PostgreSQL / `ctgov` |
| Deterministic logic | TrialIQ services/metrics/validation |
| LLM abstraction | OpenAI / Gemini / OpenRouter |
| Qualification | Batch 21 stable-demo qualifier |

## Architectural flow

```text
AACT PostgreSQL
  -> TrialIQ canonical ETL
  -> Neo4j

Investigator Console
  -> FastAPI
  -> Direct deterministic path OR Guided path
  -> MCP
  -> bounded Neo4j retrieval
  -> deterministic metrics
  -> optional HITL
  -> validation
  -> structured synthesis
  -> UI evidence workspaces
```

## Protected boundaries

- Browser never queries Neo4j directly.
- LLM never emits arbitrary runtime Cypher.
- MCP remains the guided graph transport boundary.
- Quantitative comparisons are deterministic.
- Related-study traversal is allowlisted and bounded.

## Recommended visuals

Use:

- `01-system-architecture.mmd`
- `11-component-boundaries.mmd`
