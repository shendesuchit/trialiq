# TrialIQ canonical demo questions

## Primary end-to-end agentic demonstration

> Find completed trials connected to NCT03416088 through its conditions or interventions. Explain exactly why they are connected, compare their completion timelines and enrollment, and show the evidence supporting each conclusion.

Expected path: LLM intent extraction → supervisor → MCP retrieval → bounded Neo4j traversal → deterministic related-trial metrics → deterministic grounding validation → structured LLM synthesis → evidence/graph/execution UI.

## Focused verification questions

1. **Connection evidence** — Find trials connected to NCT03416088 through its conditions or interventions and explain exactly which canonical entities connect each trial.
2. **Timeline comparison** — Find completed trials connected to NCT03416088 through its conditions or interventions and compare their completion dates with the anchor trial.
3. **Enrollment comparison** — Find completed trials connected to NCT03416088 through its conditions or interventions and compare their enrollment with the anchor trial.
4. **Bounded deterministic fallback** — Find completed trials connected to NCT03416088 through its conditions or interventions. This wording is intentionally supported by the bounded fallback used when all LLM providers are unavailable during intent extraction.

## Presenter checks before a demo

Run `scripts\run_demo_preflight.bat F:\trialiq` after the API, MCP server, Neo4j, and configured LLM provider are running. The preflight requires API/Neo4j/MCP/LLM readiness, MCP transport, related-trial evidence, stable entity IDs, deterministic metrics, both logical LLM stages for the primary query, structured synthesis, and the expected execution trace stages.
