# TrialIQ Troubleshooting

## Purpose

This page collects failure modes that have actually mattered during TrialIQ development and stabilization.

## 1. Python imports stale TrialIQ code

### Symptom

Routes, tests or runtime behavior do not match the checked-out source.

### Check

```powershell
.\.venv\Scripts\python.exe -c "import trialiq; print(trialiq.__file__)"
```

Expected path: this checkout under `src\trialiq`.

### Fix

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

The stable-demo verification runner performs this check before continuing.

## 2. `/health` passes but `/ready` fails

`/health` only proves the API process is alive. `/ready` checks runtime dependencies and may fail/degrade when Neo4j, MCP or LLM configuration is not healthy.

Check:

- `.env` values;
- Neo4j process/credentials/database;
- MCP health;
- configured LLM keys/models/network availability.

## 3. Neo4j connection failure

Verify:

```text
NEO4J_URI
NEO4J_USERNAME
NEO4J_PASSWORD
NEO4J_DATABASE
```

If using `compose.yaml`, ensure `.env` credentials match the container authentication you actually started.

An empty Neo4j instance can be “reachable” while still lacking the canonical graph required for meaningful TrialIQ results.

## 4. Full-graph query or qualification hits Neo4j transaction memory

A Batch 21 qualifier version previously used large `collect(DISTINCT ...)` operations across the full graph and hit the Neo4j transaction-memory cap.

Batch 21.1 fixed that by using indexed `loaded_trial_count`, a bounded entity scan and later trial expansion.

Do not “fix” a memory-unsafe qualification query merely by raising Neo4j memory. First verify that the query is bounded by design.

## 5. Guided query returns `REVIEW_REQUIRED`

This is expected when the discovered candidate count exceeds six.

For the interactive flow:

- show the HITL checkpoint;
- select studies or choose all;
- call `/api/v1/query/agent/continue`.

Do not treat `REVIEW_REQUIRED` as an API error.

## 6. Old preflight expects immediate `SUCCESS`

The pre-HITL assumption that every `/query/agent` request immediately returns success is obsolete. Use the current HITL-aware `scripts/demo_preflight.py`.

## 7. Structured synthesis grounding rejects claims

A log such as “grounding validation rejected_claims=...” indicates the contract removed unsupported proposed claims.

Investigate only if the final validated run fails or the answer becomes unusable. Do not disable the grounding contract just to eliminate the log message.

## 8. Connections graph shows misleading counts or an empty tiny node

The UI must derive visible counts from the active relationship/scope/depth filter. A zero-result relationship filter should show an explicit empty state rather than retaining totals from an unfiltered graph.

If this regresses, inspect frontend visible-node/visible-edge derivation before changing backend retrieval.

## 9. Graph labels overlap or become unreadably small

Graph fitting should preserve minimum readable node/font sizes and wrap/truncate long labels predictably. Do not solve crowding by globally shrinking UI typography.

## 10. PowerShell says `else` is not recognized

In an interactive PowerShell session, pasting an `if { ... }` block and then executing `else { ... }` separately causes `else` to be interpreted as a command.

Paste the whole conditional in one execution, or use scripts that avoid a detached `else` block.

## 11. PowerShell says string terminator is missing

Windows PowerShell 5.1 can misread UTF-8 scripts containing unsupported punctuation such as an em dash when the file has no BOM.

For portable maintenance scripts:

- prefer ASCII-only status text;
- or save with a Windows PowerShell-compatible encoding.

## 12. Git commands say “not a git repository”

The development/runtime source directory and Git checkout have historically been separate:

```text
F:\trialiq
F:\github\trialiq\trialiq
```

Do not assume the runtime directory contains `.git`.

Use:

```powershell
git -C F:\github\trialiq\trialiq status
```

or run Git from the actual checkout.

## 13. `git diff --cached` behaves like `--no-index`

This happens when the command is not being run inside a Git repository. Confirm the repo path before interpreting the diff error as an unsupported Git option.

## 14. Frontend build works locally but clean install may not

The supplied stable source state contains a `package.json` / `package-lock.json` dependency-manifest mismatch. Existing `node_modules` can hide that drift.

Before long-term release:

1. reconcile the two manifests deliberately;
2. delete/rename `node_modules` in a test copy;
3. run `npm ci`;
4. run `npm run build`;
5. commit both manifests together.

## 15. Timeline looks compressed because of extreme date outliers

The Studies timeline has to balance a full-range view with practical readability. Use the UI's focused/full-range behavior rather than silently dropping valid source dates.

## 16. Missing date/enrollment comparisons

This can be legitimate source incompleteness. TrialIQ should show the data as unavailable; it should not synthesize a replacement value.

## 17. PDF report fails

Verify:

- result payload is complete;
- at least one report section is selected;
- `/api/v1/query/agent/report` is reachable;
- backend report contract tests pass.

The PDF generator is deterministic and does not require an extra LLM call.

## Escalation rule

When troubleshooting a demo failure, isolate the layer before redesigning the architecture:

```text
source data -> graph -> deterministic service -> MCP -> supervisor -> validation -> synthesis -> API -> UI
```

A UI symptom does not automatically imply a graph/data defect, and a qualification-script failure does not automatically imply an application defect.
