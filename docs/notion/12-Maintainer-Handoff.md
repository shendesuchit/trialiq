# Maintainer Handoff

## Current baseline

TrialIQ is a Stable Demo / Technical Preview with a passing automated Batch 21/21.1 release gate.

## Never casually break these invariants

- MCP is the guided graph transport boundary.
- No silent MCP -> direct Neo4j fallback.
- No arbitrary LLM-generated Cypher.
- Related-study traversal stays bounded and allowlisted.
- Condition / Intervention / Sponsor are the current relationship dimensions.
- Quantitative comparisons stay deterministic.
- Normal guided flow stays at two logical LLM calls.
- HITL resume reuses existing retrieval.
- Browser never queries Neo4j directly.
- Missing source data stays missing.

## Before changing behavior

Ask which layer owns the problem:

```text
AACT -> ETL -> Neo4j -> deterministic services -> MCP -> supervisor -> validation -> synthesis -> API -> UI
```

Do not redesign the backend because of a presentation bug, and do not redesign the UI because a qualification script is inefficient.

## Before a release

- clean working tree;
- clean-clone dependency install;
- release gate pass;
- manual four-scenario smoke;
- PDF smoke;
- docs match code;
- release tag.

## Documentation source of truth

Repository `docs/00-index.md` and the numbered documents are authoritative. This Notion space is the communication layer.
