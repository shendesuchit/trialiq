# TrialIQ Home

## One-line definition

TrialIQ is an evidence-grounded clinical-trial intelligence workspace that combines AACT data, a canonical Neo4j graph, governed MCP tools, deterministic comparisons, human review and grounded LLM synthesis.

## Current status

**Stable Demo / Technical Preview**

The current release gate verifies the backend, frontend build, Neo4j, MCP, configured LLM provider, live guided workflow and four-level demo scenario qualification.

## What a reviewer should understand in 60 seconds

1. TrialIQ starts from a study of interest and a natural-language investigation question.
2. Simple lookup can remain deterministic.
3. Guided questions use an LLM only for structured intent and final grounded synthesis.
4. Graph retrieval is performed by controlled TrialIQ tools over bounded Condition / Intervention / Sponsor relationships.
5. Quantitative comparisons come from deterministic backend calculations.
6. Broad result sets pause for investigator selection before synthesis.
7. The final UI keeps the answer, compared studies, graph connections and evidence inspectable.

## Product flow

```text
Study of interest
  -> Question
  -> Direct or Guided TrialIQ path
  -> related-study discovery when requested
  -> HITL when broad
  -> deterministic comparison + validation
  -> Answer / Studies / Connections / Evidence
  -> PDF report
```

## Pages in this workspace

- Product Concept
- Why Agentic AI
- Architecture Overview
- End-to-End Workflow
- Investigator Experience
- Data Foundation
- Graph Discovery Model
- Stable Demo
- Verification & Trust
- Rebuild Runbook
- Troubleshooting
- Maintainer Handoff

## Recommended visual

Use `docs/diagrams/01-system-architecture.mmd` or the editable `trialiq-system-architecture.drawio`.
