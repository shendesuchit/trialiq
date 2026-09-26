# End-to-End Workflow

## Guided question

1. Investigator submits a guided question.
2. TrialIQ requests typed `ExtractedQueryIntent` from the configured LLM service.
3. `SupervisorAgent` starts the governed workflow.
4. `RetrievalAgent` calls the MCP client.
5. MCP executes the supported TrialIQ retrieval tool.
6. Neo4j returns bounded related-study evidence.
7. TrialIQ calculates deterministic comparison metrics.
8. If more than six candidates exist, TrialIQ pauses for investigator review.
9. After selection, TrialIQ reuses the existing retrieval and validates the approved evidence set.
10. TrialIQ requests typed `StructuredSynthesis` from the LLM.
11. The UI receives the answer, analysed studies, connections, evidence and trace.

## Two-call contract

Normal guided flow:

```text
LLM call 1 -> structured intent
LLM call 2 -> structured grounded synthesis
```

Validation is deterministic and does not add a third LLM call.

## Broad-result flow

```text
Retrieval
  -> >6 candidates
  -> REVIEW_REQUIRED
  -> Analyse selected / Analyse all
  -> resume without repeated retrieval
  -> validation
  -> synthesis
```

## Recommended visuals

Use:

- `03-agent-sequence.mmd`
- `04-hitl-workflow.mmd`
