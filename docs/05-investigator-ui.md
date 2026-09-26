# TrialIQ Investigator UI

## Purpose

This page documents the current user-facing workflow and the behavioral contracts that should survive future visual refinements.

## Primary navigation

The Investigator Console separates study selection, querying, evidence review and architecture/runtime explanation while keeping the main result flow progressive.

The result workspace uses four primary tabs:

```text
Answer -> Studies -> Connections -> Evidence
```

These tabs are not cosmetic aliases. Each has a distinct investigator purpose.

## Study selection and question entry

The investigator chooses a study of interest and enters a question. TrialIQ supports:

- **Direct** mode for deterministic retrieval;
- **Guided** mode for the governed agent workflow.

The selected NCT ID remains visible as the study of interest so the user can distinguish the reference study from discovered related studies.

## HITL candidate review

When a guided related-study query discovers more than six candidates, the UI displays an investigator checkpoint before detailed analysis.

The checkpoint includes source-backed candidate information such as:

- NCT ID;
- title;
- status;
- phase where available;
- enrollment where available;
- connection types;
- shared entities;
- evidence-path count;
- direct/two-step depth;
- whether TrialIQ suggested the candidate.

Available actions include:

- restore/use the deterministic suggested shortlist;
- individually select studies;
- select all shown studies;
- **Analyse selected**;
- **Analyse all**.

An empty individual selection is not silently interpreted as approval.

## Answer tab

The Answer tab is the primary investigator-facing conclusion.

It should prioritize:

- the grounded answer;
- key findings;
- generation method/grounding context;
- limitations only as needed;
- paths to Studies, Connections and Evidence.

Technical details should not dominate the answer before the investigator sees the conclusion.

## Studies tab

The Studies workspace supports understanding and comparing the studies actually analysed.

Current behavior includes:

- filtering by available study fields;
- semantic study-status presentation;
- selection of related studies for comparison;
- inclusion of the reference study automatically in the comparison matrix;
- a comparison limit for readable side-by-side review;
- compact signed deterministic deltas;
- timeline/enrollment evidence when source data is available;
- explicit missing-data states instead of fabricated values.

The study comparison matrix is intentionally horizontal so the same measure can be scanned across the reference and selected related studies.

## Connections tab

The Connections workspace explains **why** the analysed studies are related to the study of interest.

The investigator-facing relationship types are:

- Conditions;
- Interventions;
- Sponsors.

The UI distinguishes:

- analysed studies connected through an entity;
- the broader loaded-graph reach of that entity.

This distinction prevents a loaded-graph fan-out count from being mistaken for the number of studies actually analysed in the current investigation.

### Connection branch view

Selecting a shared entity shows the related analysed studies supported by that entity. The existing branch interaction, incremental “show more” behavior and evidence explanation are functional behavior and should be preserved across styling work.

### Technical graph explorer

The node-link graph is progressive disclosure for technical inspection. It is not required to understand the clinical relationship explanation.

The explorer includes capabilities such as:

- relationship filtering;
- analysed/expanded scope;
- direct/two-step depth;
- Network/Table views;
- zoom/fit controls;
- node selection and details;
- CSV export for visible studies/connections.

Visible graph counters should describe the currently visible filtered graph, not an unfiltered internal collection.

## Evidence tab

The Evidence workspace exposes source-backed support for the result.

It can show:

- loaded graph evidence;
- lineage/source identifiers;
- validation state;
- warnings/limitations;
- the evidence supporting the study of interest and related conclusions.

Clinically consequential conclusions should be verified against source records.

## Architecture & Runtime view

TrialIQ also includes an explanatory architecture/runtime experience. This is separate from the clinical result tabs and exists to make the system behavior inspectable.

It can explain:

- system architecture;
- current-run stages;
- MCP/tool/transport metadata;
- validation and synthesis steps;
- generation method/provider metadata.

It must not fabricate stages that did not run.

## Report preparation

The **Prepare report** interaction lets the investigator choose which sections leave the UI:

- Answer summary;
- Analysed studies;
- Connection explanation;
- Evidence references;
- Technical execution details (off by default).

The PDF is generated deterministically by the backend. An investigator-authored note is kept distinct from machine-derived evidence.

## UI guardrails

Future UI work should preserve these rules:

1. Do not replace functionality merely to match a reference image.
2. Keep the four result tabs and their behavioral responsibilities intact unless a product decision explicitly changes them.
3. Do not present unsupported graph dimensions as live related-study traversal types.
4. Keep missing clinical data explicit.
5. Keep technical graph tooling optional/progressive.
6. Keep discovered-versus-analysed counts distinct after HITL.
7. Keep source/provenance access available from the result.
8. Ensure graph/table counters reflect the active filter/scope.

## Related diagram

See [`diagrams/07-investigator-ui-flow.mmd`](diagrams/07-investigator-ui-flow.mmd).
