# TrialIQ Stable Demo Scenarios

## Purpose

The stable demo uses a four-level ladder so the product demonstrates increasing complexity without relying on hard-coded NCT behavior.

The active NCT IDs and questions are generated from the currently loaded full graph. This page documents the qualification rules and the story each level is meant to demonstrate.

## Authority for current scenario values

After running the release gate, use:

```text
data/profiles/batch21_stable_demo_scenarios.txt
```

for presenter-friendly questions and:

```text
data/profiles/batch21_stable_demo_scenarios.json
```

for machine-readable scenario metadata.

Do not copy an old NCT ID into runtime code just because it made a good demo on a previous AACT snapshot.

## Level 1 — Basic

### Purpose

Demonstrate that TrialIQ does not force agentic complexity onto a simple retrieval task.

### Expected behavior

- direct deterministic retrieval;
- one study of interest;
- grounded overview/evidence;
- no broad-result HITL;
- no unnecessary related-study traversal.

### Demo message

> TrialIQ uses the simplest governed path that is sufficient for the question.

## Level 2 — Intermediate

### Qualification rule

A valid intermediate related-study probe:

- returns between 2 and 6 studies;
- is valid and has no metric errors;
- uses one related-study relationship type for a clean explanation.

The selection logic prefers a useful small set near four studies and richer comparison metadata.

### Expected behavior

- guided natural-language question;
- LLM structured intent;
- MCP `find_related_trials` retrieval;
- bounded graph discovery;
- deterministic metrics;
- no HITL because the result set is within the automatic threshold;
- grounded synthesis;
- readable Connections explanation.

### Demo message

> TrialIQ can coordinate graph discovery and evidence explanation without making a small investigation feel heavyweight.

## Level 3 — Advanced

### Qualification rule

An advanced scenario must first satisfy the intermediate rule and must also have at least two of these three comparison dimensions at **80% or better coverage** across returned studies:

- completion date;
- duration;
- enrollment.

### Expected behavior

- guided retrieval with a small evidence set;
- deterministic quantitative comparisons;
- comparison matrix/timeline useful enough to demonstrate real contrast;
- missing fields remain explicit where they exist;
- synthesis references supported comparison facts rather than generating arithmetic.

### Demo message

> TrialIQ separates reasoning and explanation from quantitative truth: dates and enrollment differences come from deterministic backend logic.

## Level 4 — HITL

### Qualification rule

The candidate set must contain at least seven studies so it crosses the default threshold of six.

### Expected behavior

1. guided discovery returns a broad candidate set;
2. TrialIQ pauses with `REVIEW_REQUIRED`;
3. the UI shows source-backed candidate metadata;
4. the investigator chooses selected studies or all;
5. TrialIQ resumes without repeating intent extraction or MCP retrieval;
6. the approved evidence set is validated and synthesized;
7. the result records discovered versus analysed study counts.

### Demo message

> Agentic AI does not remove investigator control. TrialIQ pauses when graph discovery becomes broad and lets the investigator define the evidence set used for detailed analysis.

## Why entity fan-out alone is not enough

A shared entity can have a large or small graph fan-out, but that number alone does not determine how many studies the final bounded query will return. The seed study can connect through multiple entities, filters can change the set, and traversal policy applies bounds.

Scenario qualification therefore probes the actual TrialIQ retrieval result rather than selecting examples purely from entity fan-out statistics.

## Required presenter smoke

Before a live demonstration:

- regenerate/verify the stable scenarios against the active graph;
- run all four generated questions once in the UI;
- confirm the HITL pause/resume path;
- confirm Answer / Studies / Connections / Evidence;
- download/open one PDF;
- avoid substituting an unqualified random question as the primary demo.

## Historical scenario examples

Older qualification runs produced useful candidates such as NCT00001239, NCT00000449 and other high/low-fanout studies. They remain engineering history, not the current release contract.

The generated Batch 21 scenario files are authoritative for the active dataset.
