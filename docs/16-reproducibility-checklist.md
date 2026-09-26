# TrialIQ One-Year Reproducibility Checklist

## Purpose

This checklist is the final gate for the requirement:

> A maintainer should be able to return to TrialIQ roughly a year later, follow the repository documentation, rebuild the environment, and reproduce the same system behavior rather than depending on hidden local state.

## A. Freeze a reproducible source revision

- [ ] `main` is clean.
- [ ] All intended code/docs are committed.
- [ ] Generated caches/build artifacts are not tracked.
- [ ] A release tag exists (recommended: `trialiq-v0.1-demo` or equivalent).
- [ ] The release record contains the commit SHA.

## B. Freeze dependency metadata

### Python

- [ ] `pyproject.toml` is committed.
- [ ] `uv.lock` is committed and was produced/validated with the release.
- [ ] Python version used for verification is recorded (recommended checkpoint: 3.12).
- [ ] A brand-new virtual environment can install TrialIQ from the release commit.
- [ ] `import trialiq` resolves to the checkout.

### Frontend

- [ ] `frontend/package.json` and `frontend/package-lock.json` describe the same dependency set.
- [ ] Node version is recorded.
- [ ] npm version is recorded.
- [ ] Delete/rename existing `node_modules` in a test clone.
- [ ] `npm ci` succeeds from scratch.
- [ ] `npm run build` succeeds immediately after `npm ci`.

> **Current action required:** documentation review found dependency-manifest drift between `frontend/package.json` and `frontend/package-lock.json`. Reconcile this before checking the frontend boxes above or creating the final long-term reproducibility tag.

## C. Record external service versions

- [ ] PostgreSQL version recorded.
- [ ] AACT snapshot date/version/source recorded.
- [ ] Neo4j version recorded.
- [ ] Neo4j database configuration documented.
- [ ] LLM provider used for release verification recorded.
- [ ] LLM model used for release verification recorded.

Do not hard-code a cloud model as the only future-supported model; the runtime abstraction is intentionally provider/model configurable.

## D. Rebuild source data and graph

- [ ] AACT PostgreSQL can be restored from the documented source.
- [ ] TrialIQ can connect to the configured `ctgov` schema.
- [ ] Bounded canonical verification load passes reconciliation.
- [ ] Full canonical graph load passes reconciliation.
- [ ] Post-load runtime smoke passes.
- [ ] Historical counts are treated as reference evidence, not hard invariants for a newer AACT snapshot.

## E. Runtime startup

- [ ] API starts from the fresh environment.
- [ ] `/health` passes.
- [ ] `/ready` reports the expected dependency health.
- [ ] frontend dev server starts.
- [ ] frontend can call the API through configured CORS origins.
- [ ] MCP readiness passes.
- [ ] configured LLM provider readiness passes.

## F. Stable-demo release gate

- [ ] `scripts/run_batch21_stable_demo_verification.ps1` passes.
- [ ] full regression passes.
- [ ] frontend production build passes.
- [ ] live preflight passes.
- [ ] Basic / Intermediate / Advanced / HITL qualification passes.
- [ ] qualification outputs are archived or summarized for the release.

## G. Manual product smoke

Using `data/profiles/batch21_stable_demo_scenarios.txt`:

- [ ] Basic scenario works.
- [ ] Intermediate scenario works.
- [ ] Advanced comparison works.
- [ ] HITL pauses above six candidates.
- [ ] Analyse selected works.
- [ ] Analyse all works when exercised.
- [ ] Answer tab works.
- [ ] Studies tab works.
- [ ] Connections tab works.
- [ ] Evidence tab works.
- [ ] technical graph explorer still works.
- [ ] visible graph counters match active scope/filter.
- [ ] PDF report downloads and opens.

## H. Documentation validation

- [ ] README matches the tagged architecture.
- [ ] setup guide works from clean clone.
- [ ] rebuild/recovery guide works without undocumented local files.
- [ ] diagrams match real TrialIQ modules and relationship semantics.
- [ ] no page describes Facility/Design/Eligibility as active related-study traversal unless code has changed accordingly.
- [ ] no page claims production clinical readiness.
- [ ] stable-demo scenario page points to generated current scenario files rather than stale hard-coded NCT IDs.

## I. Final release record

Create a small release record with:

```text
Release tag:
Commit SHA:
Verification date:
AACT snapshot:
PostgreSQL version:
Neo4j version:
Python version:
Node version:
npm version:
LLM provider/model used for verification:
Regression summary:
Frontend build summary:
Stable-demo qualification summary:
Manual smoke operator/date:
Known limitations:
```

If every section above is reproducible from a clean machine, TrialIQ has a durable stable-demo release rather than a working local environment that only the original developer can recreate.
