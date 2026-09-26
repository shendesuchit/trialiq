# TrialIQ Notion Import Guide

## Purpose

The Markdown pages under `docs/notion/` are presentation-oriented companions to the repository runbooks. They are intentionally arranged as a funnel so a reader can move from product idea -> architecture -> workflow -> evidence -> operations without opening implementation files first.

## Recommended Notion page tree

```text
TrialIQ
├── 00 — TrialIQ Home
├── 01 — Product Concept
├── 02 — Why Agentic AI
├── 03 — Architecture Overview
├── 04 — End-to-End Workflow
├── 05 — Investigator Experience
├── 06 — Data Foundation
├── 07 — Graph Discovery Model
├── 08 — Stable Demo
├── 09 — Verification & Trust
├── 10 — Rebuild Runbook
├── 11 — Troubleshooting
└── 12 — Maintainer Handoff
```

## Funnel logic

### Layer 1 — Understand the product

Read:

- Home
- Product Concept
- Why Agentic AI

A non-technical reviewer should understand the problem, value and governance before seeing implementation details.

### Layer 2 — Understand how TrialIQ works

Read:

- Architecture Overview
- End-to-End Workflow
- Investigator Experience
- Data Foundation
- Graph Discovery Model

This layer explains the actual TrialIQ components and evidence path.

### Layer 3 — Understand how to prove and operate it

Read:

- Stable Demo
- Verification & Trust
- Rebuild Runbook
- Troubleshooting
- Maintainer Handoff

This layer is for demo owners, engineers and future maintainers.

## Import approach

Notion can import Markdown files. Import the files in numeric order and then nest them under a `TrialIQ` parent page.

The Mermaid files under `docs/diagrams/` are canonical diagram sources. Depending on the Notion workspace, either:

- use a Mermaid-capable embed/integration;
- paste the Mermaid source into a code block;
- export SVG/PNG from the `.mmd` source and attach it to the corresponding page;
- use the provided draw.io XML for the editable system-architecture visual.

## Diagram placement

| Notion page | Recommended TrialIQ diagram |
| --- | --- |
| Home | `01-system-architecture.mmd` |
| Why Agentic AI | `02-direct-vs-guided-routing.mmd` |
| Architecture Overview | `01-system-architecture.mmd`, `11-component-boundaries.mmd` |
| End-to-End Workflow | `03-agent-sequence.mmd`, `04-hitl-workflow.mmd` |
| Investigator Experience | `07-investigator-ui-flow.mmd` |
| Data Foundation | `05-data-lineage.mmd` |
| Graph Discovery Model | `06-graph-domain-model.mmd` |
| Stable Demo | `10-use-case-map.mmd` |
| Verification & Trust | `09-release-verification-flow.mmd`, `08-runtime-readiness.mmd` |

## Source-of-truth rule

The Notion pages are optimized for communication. The repository numbered docs remain the technical source of truth.

When updating TrialIQ:

1. change code/tests;
2. update the numbered repository doc(s);
3. update the matching diagram(s);
4. update the Notion page if the change affects the product story.
