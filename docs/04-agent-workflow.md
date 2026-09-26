# TrialIQ Guided Agent Workflow

## Purpose

This page documents the current guided investigation flow from a natural-language question to a grounded answer.

## Normal guided path

```text
Question
  -> structured intent
  -> retrieval through MCP
  -> bounded graph evidence
  -> deterministic metrics
  -> optional human review
  -> deterministic validation
  -> structured synthesis
  -> Investigator Console
```

## Stage 1 — Intent extraction

TrialIQ sends the question to the configured LLM abstraction and requests the typed `ExtractedQueryIntent` structure.

Intent extraction identifies supported fields such as:

- anchor NCT ID;
- desired retrieval intent;
- relationship filters;
- status filters;
- bounded result limit.

A bounded deterministic fallback exists for specifically supported query patterns when LLM intent extraction is unavailable. This fallback is not a general natural-language parser.

## Stage 2 — Supervisor coordination

`SupervisorAgent` owns the guided workflow. It does not ask the model to decide every step dynamically. Instead, it coordinates explicit TrialIQ stages and records trace metadata.

## Stage 3 — MCP retrieval

`RetrievalAgent` uses `FastMCPRetrievalClient` for the normal guided graph path.

For related-study discovery, the controlled MCP tool is `find_related_trials`.

Important properties:

- fixed tool name;
- typed input;
- bounded hop count and limits;
- allowlisted graph relationship types;
- returned evidence is validated into TrialIQ response models.

## Stage 4 — Bounded graph traversal

The graph traversal can use one or two hops over:

- Conditions;
- Interventions;
- Sponsors.

Hub-aware retrieval prioritizes lower-fan-out canonical entities before common high-fan-out entities and applies deterministic per-entity/per-hop bounds.

High-fan-out entities remain valid graph evidence; they are not silently removed from the graph.

## Stage 5 — Deterministic metrics

For each supported related study, backend code derives comparison values from loaded source-backed fields. The agent trace records a `metrics` stage when comparison metrics exist.

Examples:

- completion-date difference in days;
- duration difference in days;
- enrollment difference.

These are not calculated by the synthesis model.

## Stage 6 — Human review when broad

The default threshold is six candidate studies.

```text
candidate_count <= 6
  -> continue

candidate_count > 6
  -> status REVIEW_REQUIRED
  -> investigator chooses SELECTED or ALL
  -> resume using the stored request + retrieval
```

The paused session stores the typed request, retrieved evidence, trace and checkpoint required to resume. It is bounded and expires; it is not production durable state.

### Resume invariant

Resume must not repeat:

- LLM intent extraction;
- MCP graph discovery.

It applies the investigator selection to the already retrieved evidence set and continues downstream.

## Stage 7 — Deterministic validation

`ValidationAgent` decides whether the retrieved evidence is sufficient to synthesize.

Validation may produce:

- status;
- `can_synthesize`;
- warnings;
- errors.

The system can reject unsupported synthesis claims. A grounding rejection is a protection mechanism, not evidence that the graph retrieval failed.

## Stage 8 — Structured synthesis

When validation permits synthesis, TrialIQ requests the typed `StructuredSynthesis` output from the LLM.

The final response carries generation metadata such as:

- generation method;
- provider;
- model;
- grounded flag;
- source count.

## Two-call invariant

For a normal guided related-study question interpreted by the LLM, the expected logical schemas are:

```text
ExtractedQueryIntent
StructuredSynthesis
```

The Batch 21 stable-demo qualifier explicitly checks this behavior.

## Backward-compatible `/query` behavior

The legacy `/api/v1/query` endpoint can run agent mode but cannot expose an interactive HITL checkpoint through its existing response contract. If that path encounters a broad candidate set, it explicitly continues with `ALL`.

The interactive Investigator Console uses `/api/v1/query/agent`, which can return `REVIEW_REQUIRED`, and `/api/v1/query/agent/continue` to resume.

## Execution trace

The result can include trace stages such as:

- intent;
- retrieval;
- metrics;
- human_review;
- validation;
- synthesis.

This makes the guided workflow inspectable without exposing hidden model reasoning.

## Related diagrams

- [`diagrams/03-agent-sequence.mmd`](diagrams/03-agent-sequence.mmd)
- [`diagrams/04-hitl-workflow.mmd`](diagrams/04-hitl-workflow.mmd)
- [`diagrams/02-direct-vs-guided-routing.mmd`](diagrams/02-direct-vs-guided-routing.mmd)
