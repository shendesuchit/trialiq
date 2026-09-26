# TrialIQ Diagram Catalogue

All diagrams in this directory describe the actual TrialIQ product, modules, data model or verification workflow. They are not generic AI/RAG reference diagrams.

## Canonical sources

| File | Diagram type | TrialIQ question answered |
| --- | --- | --- |
| `01-system-architecture.mmd` | Architecture flow | What are the major TrialIQ runtime/data components? |
| `02-direct-vs-guided-routing.mmd` | Decision/process flow | When does TrialIQ use deterministic vs guided execution? |
| `03-agent-sequence.mmd` | UML-style sequence | How does a guided question move through UI, API, LLM, MCP, Neo4j, HITL and validation? |
| `04-hitl-workflow.mmd` | State diagram | How does a broad TrialIQ result pause and resume? |
| `05-data-lineage.mmd` | Data-flow diagram | How does AACT evidence become a validated TrialIQ answer? |
| `06-graph-domain-model.mmd` | UML-style class/domain model | Which graph entities/relationships exist and which drive discovery? |
| `07-investigator-ui-flow.mmd` | UI state/flow | How does an investigator move through TrialIQ? |
| `08-runtime-readiness.mmd` | Runtime dependency flow | What does TrialIQ readiness/preflight check? |
| `09-release-verification-flow.mmd` | Release process flow | What must pass before the stable demo is declared healthy? |
| `10-use-case-map.mmd` | Use-case map | What can the investigator and maintainer do in TrialIQ? |
| `11-component-boundaries.mmd` | Component map | Which repository modules own which responsibilities? |
| `trialiq-system-architecture.drawio` | Editable draw.io XML | Presentation/editing version of the high-level TrialIQ architecture |

## Rendering

GitHub can render Mermaid blocks when they are embedded in Markdown. `.mmd` files are kept as small canonical sources that can also be pasted into Mermaid Live/editor tooling or imported into documentation systems that support Mermaid.

For Notion, either:

1. paste the Mermaid source into a Mermaid-capable embed/integration; or
2. export SVG/PNG from the `.mmd` source and attach the image to the corresponding Notion page.

## Maintenance rule

If a diagram changes a relationship, component, endpoint or workflow rule, verify the source code first. The diagram must follow TrialIQ; TrialIQ must not be changed merely to match an old diagram.
