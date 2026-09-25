# Batch 14 — Full-graph retrieval hardening + AACT full-load readiness

Batch 14 prepares the canonical TrialIQ graph for the complete AACT core load
without changing the Batch-12 investigator layout or the two-logical-LLM-call
agent contract.

## Runtime changes

The read path now uses canonical identity consistently:

- Condition exact search uses `Condition.normalized_name`.
- Intervention and Sponsor exact search use `normalized_name`.
- Trial-to-trial shared entity comparison uses `canonical_key`; Intervention
  identity therefore continues to include intervention type.
- Related-trial traversal remains allowlisted to `HAS_CONDITION`,
  `HAS_INTERVENTION`, and `SPONSORED_BY`.

### Hub-aware traversal

For every frontier Trial, the traversal selects at most five canonical entities
per relationship type, ordered by the materialized `loaded_trial_count`. Lower
fan-out entities are expanded first. Every selected entity contributes at most
50 Trial candidates before the deterministic per-hop limit is applied.

Candidate Trials are ordered by:

1. lowest shared-entity fan-out,
2. greatest number of distinct shared selected entities,
3. lowest summed fan-out, then
4. NCT ID.

High-fanout entities remain in Neo4j and remain valid evidence. They are not
silently deleted or filtered from exact searches; they simply cannot multiply
an unbounded traversal.

### Study catalog protection

The study selector probes at most 201 distinct connected Trials. Counts up to
200 are exact. If more than 200 are observed, the API returns
`related_trial_count=200` with `related_trial_count_capped=true`; the existing UI
renders `200+ connected studies`. No layout or styling changes are introduced.

## Full-load support

The canonical loader introduced in Batch 13 remains the ingestion mechanism.
Batch 14 adds:

- progress output for each source/write batch,
- fan-out and Trial text indexes applied by the loader,
- a read-only full-load preflight,
- a post-load canonical runtime smoke suite,
- a high-fanout `placebo` bounded-traversal probe, and
- one PowerShell path for preflight -> focused tests -> full load/reconciliation
  -> runtime smoke -> complete pytest.

The full graph continues to contain only the core investigator topology for this
phase: Trial, Condition, Intervention, and Sponsor. Facility, Design, and
Eligibility are preserved if already present but are not broadened by the full
canonical load.

## Verification before full load

From the project root:

```powershell
& ".\scripts\run_batch14_verification.ps1"
```

This runs the focused Batch-14 tests, runtime smoke against the current canonical
graph, and the complete TrialIQ pytest suite.

## Complete AACT load

After the verification path passes:

```powershell
& ".\scripts\run_batch14_full_load.ps1"
```

The default source/write batch size is 5,000 and can be changed without changing
loader semantics:

```powershell
& ".\scripts\run_batch14_full_load.ps1" -BatchSize 10000
```

Reports are written under `data/profiles/`:

- `batch14_preflight.json`
- `batch14_full_aact_load.json`
- `batch14_full_runtime_smoke.json`

The existing canonical loader is idempotent and scoped by Trial ID; if a load is
interrupted, rerunning the full-load command safely replaces the core canonical
relationships for each encountered Trial and reconciles the completed run.

## Architectural constraints preserved

Batch 14 does not add LLM-generated Cypher, direct runtime fallback, arbitrary
relationship traversal, or extra logical LLM calls. MCP remains the intended
agent graph transport, Cypher remains fixed/parameterized/allowlisted,
quantitative result calculations remain deterministic, and frontend presentation
remains frontend-owned.
