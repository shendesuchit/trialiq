# TrialIQ Investigator Console checkpoints

This file keeps the demo/UI milestones explicit so they survive chat/context changes.

## Completed

- [x] Baseline and Agentic execution modes are real backend paths, not a cosmetic switch.
- [x] Agentic mode exposes real MCP transport/tool metadata and backend execution trace.
- [x] Evidence workspace shows source coverage, validation, graph evidence, and technical audit payload.
- [x] Baseline remains deterministic and does not fabricate agent/MCP stages.
- [x] Related-trial `NOT_FOUND` is treated as a valid bounded zero-match result when the backend reports it.
- [x] Investigator answer is no longer blocked by a large pre-answer architecture strip; runtime provenance is compact and inspectable after the answer.

## Required before demo/release polish is considered complete

- [x] Backend exposes explicit generation metadata: `generation.method`, `provider`, `model`, `grounded`, and source count. The UI labels LLM vs deterministic synthesis from this metadata rather than guessing from Agentic mode.
- [x] Interactive **Architecture & Runtime** view has System Architecture and Current Run modes. Nodes are clickable and current-run status/tool/transport/duration/generation details come from returned backend metadata.
- [x] Build the real **GraphRAG / Neo4j relationship view** for bounded related-trial paths (Trial → Condition/Intervention/Sponsor → Related Trial), with hop and relationship labels, relationship filtering, 1/2-hop controls, and a selection inspector.
- [x] Preserve `/api/v1/lineage/trials/{nct_id}` as source/provenance lineage and add sibling `/api/v1/lineage/trials/{nct_id}/graph` returning a bounded typed DTO (`nodes[]`, `edges[]`, `seed_node`, `hop`, `relationship`, `truncated`).
- [ ] Find and document a demo seed NCT with actual one-hop/two-hop graph neighbors so the GraphRAG visualization has meaningful data.
- [ ] Exercise all agent response branches in the UI: condition, intervention, sponsor, shared entity, related trial/multi-hop, success, zero-match, and error states.
- [ ] Surface reconciliation states only from real backend metadata: `VERIFIED`, `CONFLICT`, `MISSING_SOURCE`, `NOT_CHECKED`.
- [ ] Integrate cross-source reconciliation into agent validation/synthesis/trace/limitations after the initial UI milestone.
- [ ] Final accessibility/responsive/polish pass: keyboard/focus, reduced motion, loading states, error states, long-answer collapsing, compact timings, and mobile layouts.

## Guardrails

- Browser never queries Neo4j or emits Cypher.
- No arbitrary LLM-generated Cypher.
- No silent MCP → direct-service fallback.
- No fabricated MCP/tool/trace/reconciliation metadata.
- Keep deterministic tests isolated from live LLM/network dependencies.
