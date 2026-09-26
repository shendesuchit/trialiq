# TrialIQ Product Overview

## Purpose

This page explains what TrialIQ is, what problem it addresses, what capabilities are currently implemented, and where the stable-demo boundary ends.

## Product concept

Clinical-trial investigation is rarely a single-record lookup. An investigator may start with one study and then need to understand which other trials are related, exactly why they are related, how their study timelines or enrollment differ, whether the evidence is complete enough to compare, and which source records support the conclusion.

TrialIQ is designed around that workflow. It combines structured clinical-trial data, a canonical graph, deterministic comparison logic, governed tool access, human review for broad candidate sets, and grounded natural-language synthesis.

The central product idea is:

> **Use the LLM for interpretation and explanation; keep retrieval, graph traversal, quantitative comparison and evidence validation under explicit TrialIQ control.**

## Current capabilities

### Direct evidence-grounded lookup

For a simple trial-overview question, TrialIQ can use deterministic services rather than forcing an agent workflow. This path retrieves the loaded study and supporting graph evidence and returns a grounded answer.

### Related-study discovery

For guided investigation, TrialIQ can discover related studies through the canonical graph using allowlisted relationships:

- Condition / `HAS_CONDITION`
- Intervention / `HAS_INTERVENTION`
- Sponsor / `SPONSORED_BY`

The traversal is bounded and hub-aware so common entities do not create uncontrolled graph expansion.

### Deterministic comparisons

Where source data is available, TrialIQ calculates comparison metrics in backend code rather than asking the LLM to calculate them. Current metrics include supported differences such as:

- start-date difference;
- completion-date difference;
- study-duration difference;
- enrollment difference.

Missing data remains missing; TrialIQ does not fill it in with model guesses.

### Human review for broad investigations

A guided investigation pauses before detailed analysis when the related-study candidate set exceeds six studies. The investigator chooses the evidence set to continue with or explicitly chooses all discovered studies.

### Grounding and evidence review

Retrieved evidence passes through deterministic validation before final synthesis. The Investigator Console exposes source/provenance information, relationship explanations, validation state and execution details.

### Investigator-facing workspaces

The primary result progression is:

```text
Answer -> Studies -> Connections -> Evidence
```

The Studies workspace supports filtering, comparison selection and source-backed timeline/enrollment inspection. The Connections workspace explains the graph relationship in investigator terms and keeps the technical graph explorer optional. The Evidence workspace exposes source records and validation context.

### Report preparation

The investigator can choose which result sections to include in a deterministic PDF report. Report generation records discovered-versus-analysed study counts when HITL was used. Sending email is intentionally not presented as implemented functionality.

## What TrialIQ is not

The current stable demo is not:

- a clinical decision or diagnostic system;
- a replacement for source-record verification;
- a general-purpose unrestricted Cypher agent;
- a production multi-tenant SaaS deployment;
- a durable distributed workflow engine;
- an automated eligibility decision system;
- a guarantee that every AACT field is loaded into the related-study graph.

## Stable-demo maturity

The stable-demo checkpoint verifies the full technical story:

```text
search / lookup
  -> governed intent and tool selection
  -> bounded graph discovery
  -> human review when broad
  -> deterministic comparison
  -> validation
  -> grounded synthesis
  -> investigator evidence review
```

This is the point at which the project should favor defect correction, qualification and documentation over broad redesign.

## Related documents

- [Why TrialIQ uses agentic AI](02-why-agentic-ai.md)
- [System architecture](03-system-architecture.md)
- [Investigator UI](05-investigator-ui.md)
- [Stable demo scenarios](11-stable-demo-scenarios.md)
- [Release status and limitations](15-release-status-and-known-limitations.md)
