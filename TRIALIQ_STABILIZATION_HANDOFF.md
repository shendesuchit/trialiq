# TrialIQ Stable-Demo Handoff

**Status:** Stable Demo / Technical Preview baseline reached.

**Release-gate checkpoint:** Batch 21 + Batch 21.1 memory-safe qualification hotfix.

**Verified:** 2026-09-26.

## What is stable

TrialIQ now has a verified end-to-end local/demo workflow covering:

- deterministic trial lookup;
- governed guided investigations;
- MCP-mediated graph retrieval;
- bounded Condition / Intervention / Sponsor related-study traversal;
- deterministic comparison metrics;
- human review when a related-study set exceeds six candidates;
- reuse of the existing retrieval on HITL resume;
- deterministic evidence/grounding validation;
- structured grounded synthesis;
- progressive Investigator UI: Answer / Studies / Connections / Evidence;
- deterministic PDF report generation;
- full-graph scenario qualification for Basic / Intermediate / Advanced / HITL demo levels.

## Protected architecture

The following rules are architectural guardrails, not optional implementation details:

1. MCP is the required transport boundary for the guided graph workflow.
2. There is no silent MCP -> direct Neo4j fallback.
3. TrialIQ does not execute arbitrary LLM-generated Cypher.
4. Related-study traversal is bounded and allowlisted.
5. Related-study graph dimensions are Condition, Intervention and Sponsor unless a deliberate future migration changes the model everywhere.
6. Quantitative date/duration/enrollment comparisons are deterministic backend calculations.
7. Validation is deterministic; the normal guided workflow does not spend a third LLM call on validation.
8. A normal guided investigation uses two logical LLM stages: structured intent and structured grounded synthesis.
9. When a broad result set requires human review, resume reuses the interpreted request and retrieved evidence instead of repeating retrieval.
10. The browser does not query Neo4j or emit Cypher.

## Current verified release gate

The Batch 21/21.1 release gate completed with:

```text
332 passed, 12 skipped, 2 warnings
Frontend production build: PASS
API health: PASS
API readiness: PASS
Neo4j readiness: PASS
MCP readiness: PASS
LLM readiness: PASS
Live agentic preflight: PASS
Stable demo qualification: PASS
```

The qualification outputs are generated under:

```text
data/profiles/batch21_stable_demo_qualification.json
data/profiles/batch21_stable_demo_scenarios.json
data/profiles/batch21_stable_demo_scenarios.txt
```

Those files should be regenerated against the active full graph before a demo or after a material data refresh.

## Data architecture

The authoritative data flow is:

```text
AACT PostgreSQL / ctgov
  -> TrialIQ extraction + normalization
  -> canonical graph load + reconciliation
  -> Neo4j
  -> fixed/parameterized read paths
  -> deterministic evidence and metrics
  -> validation
  -> investigator-facing response
```

Historical full-load qualification used 602,891 Trial nodes. That count is a checkpoint result, not a permanent invariant; a later AACT snapshot can legitimately contain a different study count.

## Human review contract

The default automatic-analysis threshold is six candidates.

- `candidate_count <= 6`: guided workflow continues automatically.
- `candidate_count > 6`: `/api/v1/query/agent` returns `REVIEW_REQUIRED`.
- the investigator can analyse selected studies or all discovered studies;
- resume occurs through `/api/v1/query/agent/continue`;
- the selected evidence set drives downstream validation and synthesis;
- the final result records the human-review decision.

Paused investigations are currently stored in a bounded in-process store. This is appropriate for the current local/demo runtime but is not durable multi-instance workflow persistence.

## UI contract

The result workspace should preserve this progression:

```text
Answer -> Studies -> Connections -> Evidence -> Prepare report -> PDF
```

The Connections view keeps the investigator-facing relationship explanation primary and the technical graph explorer progressive/optional. Styling may evolve, but functionality should not be replaced by a visually inspired redesign without a deliberate product decision.

## Immediate maintenance priorities

1. Keep the Stable Demo release gate green.
2. Regenerate the four stable demo scenarios after meaningful graph/data changes.
3. Keep generated/cache/build outputs out of Git.
4. Keep README and numbered docs aligned with the stable checkpoint.
5. Resolve frontend `package.json` / `package-lock.json` dependency-manifest drift before declaring a long-term reproducible release tag.
6. Treat `docs/16-reproducibility-checklist.md` as the gate for a clean-machine rebuild.

## Documentation source of truth

Start with `docs/00-index.md`. The numbered documents are the maintained documentation set. Batch-specific documents remain historical implementation evidence.
