# TrialIQ Documentation Index

## Purpose

This index is the entry point for the maintained TrialIQ documentation set. It separates product explanation, architecture, operating procedures, release verification and presentation-ready Notion pages so that the repository can remain understandable and recoverable long after the original implementation work.

**Current baseline:** TrialIQ Stable Demo / Technical Preview, Batch 21 / 21.1 release-gate checkpoint.

## Recommended reading funnel

### For a product or business reviewer

1. [Product overview](01-product-overview.md)
2. [Why TrialIQ uses agentic AI](02-why-agentic-ai.md)
3. [Investigator UI](05-investigator-ui.md)
4. [Stable demo scenarios](11-stable-demo-scenarios.md)
5. [Release status and known limitations](15-release-status-and-known-limitations.md)

### For an architect or engineer

1. [System architecture](03-system-architecture.md)
2. [Agent workflow](04-agent-workflow.md)
3. [Data lineage and graph model](06-data-lineage-and-graph-model.md)
4. [API and MCP contract](07-api-and-mcp-contract.md)
5. [Architecture decisions and guardrails](14-architecture-decisions-and-guardrails.md)

### For a maintainer rebuilding TrialIQ

1. [Setup and local development](08-setup-and-local-development.md)
2. [Rebuild and recovery](09-rebuild-and-recovery.md)
3. [Verification and release gate](10-verification-and-release-gate.md)
4. [Troubleshooting](12-troubleshooting.md)
5. [Repository hygiene and maintenance](13-repository-hygiene-and-maintenance.md)
6. [Reproducibility checklist](16-reproducibility-checklist.md)

### For Notion / presentation use

Start with [NOTION_IMPORT_GUIDE.md](NOTION_IMPORT_GUIDE.md) and the Markdown pages under [`notion/`](notion/).

## Current source-of-truth hierarchy

When documents disagree, use this order:

1. current executable source and tests in `src/`, `frontend/`, `tests/`;
2. current stable-demo release gate and generated qualification outputs;
3. the numbered documents in this directory;
4. architecture diagrams under `docs/diagrams/`;
5. batch-specific historical documents;
6. old handoff/chat notes.

The docs are intended to describe the code, not override it.

## Architecture diagrams

The canonical diagram sources are in [`diagrams/`](diagrams/README.md):

- system architecture;
- direct vs guided routing;
- guided-agent sequence;
- HITL workflow;
- data lineage;
- graph domain model;
- investigator UI state flow;
- runtime readiness;
- release verification;
- TrialIQ use-case map;
- editable draw.io system architecture XML.

Every diagram is TrialIQ-specific. No generic reference architecture is used as a substitute for actual TrialIQ components.

## Historical engineering documents

The following documents remain useful history:

- `batch13-canonical-graphrag.md` — canonical Condition/Intervention/Sponsor graph loading and reconciliation;
- `batch14-full-graph-retrieval.md` — full-graph, fan-out-aware bounded retrieval;
- `TRIALIQ_HITL_CONTRACT.md` — detailed human-review behavior;
- `investigator-console-checkpoints.md` — UI behavior contract and milestone summary;
- `demo_questions.md` — legacy demo questions; the live Batch 21 scenario outputs are authoritative now.

Do not delete historical reports simply because a newer stable checkpoint exists; they can be valuable when diagnosing data-load or behavior regressions.
