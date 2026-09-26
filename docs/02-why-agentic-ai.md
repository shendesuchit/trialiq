# Why TrialIQ Uses Agentic AI

## The question this architecture must answer

A reviewer should reasonably ask:

> **Why does TrialIQ need agentic AI instead of normal clinical-trial search?**

The answer is not that every query needs an agent. TrialIQ deliberately keeps a direct deterministic path for simple retrieval. Agentic coordination is useful when a question combines interpretation, relationship discovery, comparison, evidence selection and explanation.

## Direct search is sufficient when

A request is essentially:

- retrieve one known NCT study;
- show its loaded evidence;
- produce a deterministic overview;
- perform a supported exact entity search.

In these cases, adding an agent would create cost and uncertainty without adding product value.

## The guided path becomes useful when

An investigator asks a question such as:

> Find trials related to this study, explain why they are connected, compare their available study timing and enrollment, and show the evidence.

That request contains multiple decisions:

1. identify the study and requested comparison intent;
2. select the supported TrialIQ retrieval operation;
3. discover connected trials through allowed graph relationships;
4. control graph breadth and hub fan-out;
5. decide whether the candidate set is too broad for automatic detailed analysis;
6. preserve investigator control when it is broad;
7. compute quantitative differences from source-backed fields;
8. validate what can actually be claimed;
9. explain the result in natural language without inventing unsupported facts.

No single keyword search result page performs that workflow.

## Division of responsibility

TrialIQ intentionally separates probabilistic and deterministic responsibilities.

| Stage | Owner | Why |
| --- | --- | --- |
| Understand natural-language intent | LLM | Language interpretation is the model's strength |
| Select supported workflow | TrialIQ supervisor | Product policy remains explicit |
| Access retrieval capabilities | FastMCP | Tool boundary is governed and inspectable |
| Execute graph retrieval | TrialIQ graph services | Fixed, parameterized, read-only Cypher |
| Bound graph expansion | TrialIQ retrieval policy | Prevent uncontrolled graph traversal |
| Calculate differences | Deterministic backend | Numbers should not depend on model arithmetic |
| Decide broad-result review | Deterministic threshold | Same input produces same review policy |
| Select evidence when broad | Investigator | Human controls the analysis scope |
| Validate evidence | Deterministic validator | Grounding is a system rule, not model opinion |
| Explain validated result | LLM | Natural-language synthesis adds usability |

## Why MCP matters

MCP is not a decorative layer in TrialIQ. It is the controlled interface used by the guided workflow to invoke supported retrieval capabilities.

The MCP server exposes named TrialIQ tools such as:

- `get_trial_evidence`
- `search_trials_by_condition`
- `search_trials_by_intervention`
- `search_trials_by_sponsor`
- `compare_trial_shared_entities`
- `find_related_trials`
- `verify_trial_evidence`
- `get_trial_overview`

The LLM does not receive a blank database prompt and produce arbitrary Cypher. TrialIQ controls what the tools do and how broad their operations may be.

## The two-logical-LLM-call contract

For a normal guided related-study investigation, the intended LLM stages are:

1. `ExtractedQueryIntent`
2. `StructuredSynthesis`

Retrieval, metrics, human-review policy and validation stay outside the LLM call count.

The architecture specifically avoids adding a third model call just to decide whether the answer is grounded.

## Human review is part of the agent design

When graph discovery finds more than six candidates, TrialIQ pauses before synthesis. This is important because “agentic” should not mean “the system autonomously expands scope until it decides it is done.”

Instead:

```text
broad discovery
  -> pause
  -> show candidates
  -> investigator approves selected studies or all
  -> reuse existing retrieval
  -> validate selected evidence
  -> synthesize
```

This keeps the investigator in control of the evidence set.

## What makes TrialIQ different from an LLM wrapper

TrialIQ's value is the controlled chain around the model:

- source-backed AACT data;
- canonical graph identities;
- fixed graph semantics;
- bounded traversal;
- deterministic comparisons;
- explicit review thresholds;
- validation before synthesis;
- evidence and execution trace in the UI.

The LLM is one component of the system, not the source of truth.

## Related diagram

See [`diagrams/03-agent-sequence.mmd`](diagrams/03-agent-sequence.mmd) and [`diagrams/02-direct-vs-guided-routing.mmd`](diagrams/02-direct-vs-guided-routing.mmd).
