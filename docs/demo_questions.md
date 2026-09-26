# TrialIQ Demo Questions

## Current source of truth

The stable demo no longer depends on a permanently hard-coded seed NCT ID. The Batch 21 qualifier selects and verifies a four-level scenario ladder against the currently loaded full graph.

After running:

```powershell
.\scripts\run_batch21_stable_demo_verification.ps1
```

use the generated presenter summary:

```text
data/profiles/batch21_stable_demo_scenarios.txt
```

and machine-readable metadata:

```text
data/profiles/batch21_stable_demo_scenarios.json
```

## Demo ladder

### Basic

Purpose: direct evidence-grounded lookup without unnecessary agentic complexity.

### Intermediate

Purpose: a small 2–6 study related-trial result through a clear supported relationship dimension, with no HITL needed.

### Advanced

Purpose: a small result set with strong deterministic comparison coverage across completion/duration/enrollment dimensions.

### HITL

Purpose: more than six discovered candidates, causing the investigator-review checkpoint before detailed analysis.

## Presenter checks

Before presenting:

1. run all four generated questions in the UI;
2. confirm Answer / Studies / Connections / Evidence;
3. confirm the HITL scenario pauses and resumes;
4. confirm deterministic comparison values appear where source data is available;
5. download and open one PDF report.

## Historical examples

Older TrialIQ development used specific seeds such as NCT03416088 for GraphRAG demonstrations. Those examples are useful history, but the generated Batch 21 stable scenarios are authoritative for the active dataset.
