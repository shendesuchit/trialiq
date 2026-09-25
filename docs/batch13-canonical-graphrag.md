# Batch 13 — Canonical core GraphRAG + verification load

Batch 13 introduces the scalable AACT-to-Neo4j path for the investigator graph
without changing the Batch 12 frontend or the runtime LLM/MCP orchestration.

## Scope

The loader covers the graph types already used by the investigator workflow:

- `Trial`
- `Condition` / `HAS_CONDITION`
- `Intervention` / `HAS_INTERVENTION`
- `Sponsor` / `SPONSORED_BY`

Canonical identity is conservative and source-backed:

- Condition: `lower(trim(name))`
- Sponsor: `lower(trim(name))`
- Intervention: `lower(trim(name)) + "|" + lower(trim(intervention_type))`

Repeated AACT rows for the same Trial/canonical entity become one Neo4j
relationship. All contributing AACT IDs remain on that relationship in
`source_ids`, with `source_row_count` preserving the represented row count.

## Safety and migration behavior

The loader:

1. Applies canonical-key uniqueness constraints and normalized-name indexes.
2. Reads AACT in deterministic NCT-ID order and writes in bounded batches.
3. Replaces canonical core relationships only for the current trial scope.
4. Removes legacy trial-scoped Condition/Intervention/Sponsor nodes only for
   that scope.
5. Preserves unrelated graph data such as Facility/Design/Eligibility.
6. Uses fixed loader-owned Cypher; no LLM-generated Cypher is involved.
7. Reconciles Trial counts, unique Trial/entity edge counts, represented source
   rows, and relationship provenance.
8. Runs the existing graph-vs-AACT verifier against a deterministic sample.

The operation is rerunnable. If a run is interrupted, rerunning the same scope
replaces that scope from AACT again.

## Verification load — recommended first run

From the TrialIQ repository root:

```powershell
& ".\.venv\Scripts\python.exe" `
  ".\scripts\load_canonical_graphrag.py" `
  --verification-load `
  --limit 5000 `
  --batch-size 1000 `
  --output ".\data\profiles\batch13_verification_5000.json"
```

A successful command exits with code `0` and prints:

```text
Batch 13 reconciliation passed.
```

The JSON report contains the exact NCT scope, counts loaded, legacy cleanup,
source-row representation, reconciliation status, and source-verification
samples.

After the loader succeeds, run the repository tests:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
```

Do not start the full load until both the Batch 13 reconciliation report and the
repository tests pass.

## Full load — later gate

Once the verification load is accepted, the same path is used for the complete
AACT core graph:

```powershell
& ".\.venv\Scripts\python.exe" `
  ".\scripts\load_canonical_graphrag.py" `
  --full-load `
  --batch-size 1000 `
  --output ".\data\profiles\batch13_full_load.json"
```

Batch 14 should harden hub-aware retrieval before this full graph becomes the
normal investigator runtime dataset.

## One-command verification runner

Batch 13 also includes a PowerShell runner that executes the focused loader tests,
the canonical verification load/reconciliation, and then the complete TrialIQ test
suite:

```powershell
& ".\scripts\run_batch13_verification.ps1"
```

Optional overrides:

```powershell
& ".\scripts\run_batch13_verification.ps1" -Limit 10000 -BatchSize 1000
```
