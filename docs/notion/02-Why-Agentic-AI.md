# Why Agentic AI

## The key reviewer question

> Why does TrialIQ need an agent instead of normal search?

## The answer

TrialIQ does **not** use an agent for every question. Direct lookup remains deterministic.

The guided path is valuable when a question requires TrialIQ to coordinate several governed steps:

```text
understand intent
  -> select supported retrieval
  -> discover bounded graph connections
  -> compare source-backed fields
  -> pause for human review when broad
  -> validate evidence
  -> explain the validated result
```

## What the LLM controls

- structured intent;
- grounded natural-language synthesis.

## What the LLM does not control

- arbitrary Cypher;
- graph relationship allowlists;
- traversal bounds;
- date/duration/enrollment arithmetic;
- whether broad results need human review;
- evidence validation policy.

## Why MCP is important

MCP exposes named TrialIQ retrieval tools rather than giving the model unrestricted database access.

## Why HITL is important

When more than six candidates are discovered, TrialIQ pauses and lets the investigator approve the detailed evidence set. Agentic coordination therefore increases capability without removing investigator control.

## Recommended visual

Use `docs/diagrams/02-direct-vs-guided-routing.mmd`.
