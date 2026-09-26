# TrialIQ Data Lineage and Graph Model

## Purpose

This page explains where TrialIQ evidence comes from, how the canonical graph is built, what relationships drive related-study discovery, and which study fields are comparison attributes rather than graph edges.

## Source foundation

TrialIQ uses an AACT PostgreSQL database as its structured source for clinical-trial records. The expected schema is `ctgov`.

The physical PostgreSQL database is not stored in Git. A clean environment restores or creates the AACT database separately and uses the TrialIQ ETL/load scripts to build Neo4j.

## Canonical load pipeline

```text
AACT PostgreSQL / ctgov
  -> deterministic extraction
  -> normalization
  -> conservative canonical identity
  -> Neo4j batched load
  -> relationship provenance
  -> reconciliation
  -> runtime graph
```

The canonical core graph loader is `scripts/load_canonical_graphrag.py`, backed by `src/trialiq/etl/canonical_graphrag.py`.

## Canonical entity identity

The core canonicalization rules introduced for the graph are intentionally conservative:

- Condition: normalized lower/trimmed name;
- Sponsor: normalized lower/trimmed name;
- Intervention: normalized name plus intervention type.

Repeated source rows that map to the same Trial/canonical entity are represented by a single graph relationship while preserving source-row provenance on that relationship.

## Relationship direction

The graph model uses the entity-to-trial convention:

```text
Condition    -[:HAS_CONDITION]-> Trial
Intervention -[:HAS_INTERVENTION]-> Trial
Sponsor      -[:SPONSORED_BY]-> Trial
```

Reconciliation and runtime queries must not silently assume the inverse direction unless the graph model is deliberately migrated everywhere.

## Related-study discovery dimensions

The current bounded related-study traversal is allowlisted to exactly three relationship families:

1. `HAS_CONDITION`
2. `HAS_INTERVENTION`
3. `SPONSORED_BY`

These are the graph dimensions that explain why one trial is related to another in the current guided workflow.

## Evidence/context dimensions

Trial evidence can also include nodes or collections such as:

- Facility;
- Design;
- Eligibility.

These can support single-study evidence and lineage, but the current guided related-study traversal does **not** automatically use them as discovery relationships.

This distinction prevents the UI or documentation from implying capabilities the retrieval contract does not implement.

## Trial attributes used for filtering/comparison

Study properties can be used as study metadata, filters or deterministic comparison inputs where loaded and supported. Examples include:

- `overall_status`;
- `phase`;
- `study_type`;
- `start_date`;
- `completion_date`;
- `primary_completion_date` where available;
- `enrollment`;
- titles.

These are not necessarily graph relationship nodes.

## Hub-aware bounded retrieval

Full AACT data contains very common entities. A naïve traversal through a high-fan-out condition, intervention or sponsor could produce enormous candidate sets.

TrialIQ therefore uses bounded, deterministic retrieval rules that prefer lower-fan-out shared entities and cap expansion.

Important behavior:

- high-fan-out entities remain valid evidence;
- exact search can still return them;
- they are not deleted simply because they are common;
- traversal bounds prevent one common entity from multiplying into an uncontrolled search.

## Historical full-load checkpoint

A historical full-load qualification successfully loaded **602,891 Trial nodes** plus canonical Condition, Intervention and Sponsor entities/relationships.

That number is a checkpoint-specific result, not a permanent assertion about ClinicalTrials.gov or AACT. A future AACT snapshot may legitimately produce a different count.

## Provenance and reconciliation

The loader and verification paths preserve evidence needed to reason about where graph facts came from.

Important provenance concepts include:

- source table;
- source IDs;
- source row count;
- canonical key;
- relationship identity;
- trial/NCT identity.

Reconciliation verifies the loaded scope rather than assuming a successful write means the graph is correct.

## Source verification

TrialIQ also exposes source-verification logic that compares graph evidence with the canonical AACT PostgreSQL source and reports discrepancies explicitly.

This is separate from ordinary related-study discovery and is useful for trust/debugging.

## Data completeness

TrialIQ must not invent missing attributes. If a related study lacks a start date, completion date or enrollment value, the corresponding comparison may be unavailable.

The stable-demo qualifier measures comparison coverage rather than assuming every study has complete fields.

## Graph model diagram

See [`diagrams/06-graph-domain-model.mmd`](diagrams/06-graph-domain-model.mmd) and [`diagrams/05-data-lineage.mmd`](diagrams/05-data-lineage.mmd).
