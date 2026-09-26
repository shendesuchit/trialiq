# Data Foundation

## Source

TrialIQ uses AACT PostgreSQL as the structured clinical-trial source foundation.

## Canonical graph pipeline

```text
AACT / ctgov
  -> extraction
  -> normalization
  -> conservative canonical identity
  -> batched Neo4j load
  -> provenance
  -> reconciliation
  -> runtime graph
```

## Why both PostgreSQL and Neo4j?

**PostgreSQL / AACT** provides the structured source foundation and source verification.

**Neo4j** provides the canonical relationship graph used for bounded related-study discovery.

## Evidence principle

The graph is a runtime representation, not permission to detach answers from source lineage.

## Historical checkpoint

A historical full load qualified 602,891 Trial nodes. A future AACT snapshot can legitimately produce a different count.

## Recommended visual

Use `05-data-lineage.mmd`.
