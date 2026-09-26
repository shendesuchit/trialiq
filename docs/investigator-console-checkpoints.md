# TrialIQ Investigator Console Stable-Demo Contract

This document summarizes the UI behavior that is considered part of the current TrialIQ stable-demo baseline.

## Completed stable behaviors

- [x] Direct and Guided modes are real backend paths, not cosmetic labels.
- [x] Guided mode exposes actual MCP transport/tool metadata and execution trace.
- [x] Evidence workspace shows source/provenance support and validation context.
- [x] Direct mode remains deterministic and does not fabricate agent/MCP stages.
- [x] Bounded zero-match related-trial results are represented as valid zero-match outcomes rather than generic failures.
- [x] The answer is the primary result; architecture/runtime details are progressive and inspectable.
- [x] Generation metadata exposes method/provider/model/grounding/source-count information from backend state.
- [x] Architecture & Runtime view can explain the system and overlay current-run metadata.
- [x] GraphRAG relationship view supports Trial -> shared entity -> related Trial reasoning over Condition/Intervention/Sponsor evidence.
- [x] `/api/v1/lineage/trials/{nct_id}` remains the source/provenance lineage path.
- [x] `/api/v1/lineage/trials/{nct_id}/graph` exposes a bounded graph DTO for technical visualization.
- [x] Result workspace is progressive: Answer / Studies / Connections / Evidence.
- [x] Related-study comparison uses deterministic date/duration/enrollment metrics where loaded.
- [x] Broad candidate sets trigger an investigator HITL checkpoint above six candidates.
- [x] HITL supports suggested selection, individual selection, Analyse selected and Analyse all.
- [x] Resume reuses the existing retrieval rather than repeating graph discovery.
- [x] Report preparation lets the investigator choose output sections before PDF download.
- [x] Connections view preserves investigator-facing branch/entity interactions and keeps the technical graph explorer optional.
- [x] Technical graph visible counts are scoped to the active relationship/scope/depth filter.
- [x] Study comparison uses a horizontal comparison matrix and compact deterministic deltas.
- [x] Timeline handling supports readable focused/full-range behavior rather than compressing the entire chart around extreme dates.

## Current stable-demo manual smoke

Use the four generated questions from:

```text
data/profiles/batch21_stable_demo_scenarios.txt
```

Confirm:

- [ ] Basic direct scenario works.
- [ ] Intermediate guided scenario works.
- [ ] Advanced comparison scenario works.
- [ ] HITL pauses above six candidates.
- [ ] Analyse selected completes.
- [ ] Answer tab remains functional.
- [ ] Studies tab remains functional.
- [ ] Connections tab remains functional.
- [ ] Evidence tab remains functional.
- [ ] One PDF downloads and opens.

## UI guardrails

- Browser never queries Neo4j or emits Cypher.
- No arbitrary LLM-generated Cypher is introduced through UI features.
- No silent MCP -> direct-service fallback is invented by frontend behavior.
- Do not fabricate tool/trace/reconciliation metadata.
- Styling references may improve visual treatment but must not silently replace existing TrialIQ functionality.
- Missing clinical-trial values remain explicit; UI must not fill gaps with invented data.
