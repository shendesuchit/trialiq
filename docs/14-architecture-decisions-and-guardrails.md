# TrialIQ Architecture Decisions and Guardrails

## Purpose

This page records the design constraints that protect TrialIQ's evidence-grounded behavior. These are decisions that future refactors should not accidentally erase.

## ADR-01 — AACT/PostgreSQL remains the structured source foundation

### Decision

AACT PostgreSQL is the structured source used to build and verify the TrialIQ graph.

### Rationale

The graph is a runtime representation optimized for relationship discovery, not a replacement for source provenance.

### Consequence

Neo4j physical files are rebuildable; they should not become the only copy of source truth.

---

## ADR-02 — Neo4j is the canonical related-study graph

### Decision

Related-study discovery uses a canonical Neo4j graph built from normalized AACT entities.

### Rationale

The graph makes shared conditions, interventions and sponsors explicit and supports bounded relationship discovery.

### Consequence

Graph identity and loader reconciliation are product correctness concerns, not just ingestion details.

---

## ADR-03 — Related-study traversal is allowlisted

### Decision

The current related-study traversal uses:

- `HAS_CONDITION`;
- `HAS_INTERVENTION`;
- `SPONSORED_BY`.

### Rationale

These are explicit, explainable connection dimensions supported by the current graph contract.

### Consequence

Facility, Design and Eligibility may be evidence/context without automatically becoming traversal relationships.

---

## ADR-04 — No arbitrary LLM-generated Cypher

### Decision

The LLM does not generate arbitrary runtime Cypher for Neo4j execution.

### Rationale

Database access must remain bounded, parameterized, testable and explainable.

### Consequence

New graph capabilities should be implemented as explicit TrialIQ query/service/tool contracts.

---

## ADR-05 — MCP is the guided graph transport boundary

### Decision

The normal guided workflow reaches graph capabilities through the TrialIQ MCP client/server tool surface.

### Rationale

This makes available operations explicit and auditable.

### Consequence

Do not add a silent MCP -> direct graph-service fallback merely to hide MCP failures.

---

## ADR-06 — Quantitative comparisons are deterministic

### Decision

Study timing/duration/enrollment differences are computed by backend code.

### Rationale

Quantitative truth should not vary with model output.

### Consequence

The synthesis model can explain a metric but should not be the system that computes it.

---

## ADR-07 — Validation is deterministic

### Decision

Evidence and grounding validation are system stages, not an extra model opinion.

### Rationale

A model should not be asked to certify its own unsupported claims.

### Consequence

The normal guided path preserves two logical LLM calls rather than adding a third validation call.

---

## ADR-08 — Human review is triggered by result breadth

### Decision

The default automatic-analysis threshold is six candidates.

### Rationale

Broad graph results should not automatically become a large evidence set without investigator control.

### Consequence

`candidate_count > 6` produces an interactive review checkpoint on `/query/agent`.

---

## ADR-09 — HITL resume reuses retrieval

### Decision

After investigator selection, TrialIQ resumes from the paused request/retrieval rather than repeating intent extraction and graph discovery.

### Rationale

The review decision should scope the already discovered evidence, not restart the investigation with potentially different results.

### Consequence

A future durable workflow store must preserve the information needed for the same invariant.

---

## ADR-10 — The browser does not query Neo4j

### Decision

The frontend consumes typed API responses.

### Rationale

Database policy, credentials and query safety remain server-side.

### Consequence

Graph visualizations are derived from backend DTOs rather than browser-generated Cypher.

---

## ADR-11 — Missing source data stays missing

### Decision

TrialIQ does not impute missing clinical-trial dates/enrollment merely to make comparisons complete.

### Rationale

An evidence support system must distinguish absent source data from known values.

### Consequence

UI and synthesis must support explicit unavailable states.

---

## ADR-12 — UI styling must not silently replace product behavior

### Decision

Reference designs may inform visual styling, but existing interaction/function contracts must not be replaced without an explicit product decision.

### Rationale

A visually attractive redesign can accidentally remove graph controls, branch interactions or evidence pathways that are functional requirements.

### Consequence

UI patches should be reviewed against behavior contracts, not screenshots alone.

---

## ADR-13 — Stable demo scenarios are data-qualified, not hard-coded

### Decision

The Basic / Intermediate / Advanced / HITL demo ladder is selected/verified against the active graph.

### Rationale

AACT data changes over time and entity fan-out alone does not guarantee the final bounded candidate count.

### Consequence

Generated Batch 21 scenario outputs are the authority for the current dataset.

---

## ADR-14 — Stable demo is not production deployment

### Decision

The current release designation is Stable Demo / Technical Preview.

### Rationale

The architecture proves the core evidence-grounded workflow but intentionally lacks several production operational/security controls.

### Consequence

Do not imply production clinical suitability without a separate production-hardening program.
