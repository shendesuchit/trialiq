# TrialIQ Release Status and Known Limitations

## Current designation

**TrialIQ Stable Demo / Technical Preview**

This designation means the core product workflow has a verified end-to-end release gate and qualified demo ladder. It does not mean the system is production-ready for clinical operations.

## Verified stable-demo capabilities

The current baseline has verified support for:

- direct deterministic study overview;
- guided natural-language investigation;
- MCP-mediated graph retrieval;
- bounded related-study discovery through Condition / Intervention / Sponsor;
- deterministic related-study metrics;
- HITL pause/resume for candidate sets above six;
- deterministic validation;
- structured grounded synthesis;
- progressive Answer / Studies / Connections / Evidence UI;
- graph/table technical inspection;
- report-section review and PDF download;
- Basic / Intermediate / Advanced / HITL scenario qualification.

## Verified checkpoint evidence

On 2026-09-26 the Batch 21/21.1 stable-demo gate completed with:

```text
332 passed, 12 skipped, 2 warnings
Frontend production build: PASS
API / Neo4j / MCP / LLM readiness: PASS
Live guided preflight: PASS
Stable demo qualification: PASS
```

Future test counts may differ as the suite changes. The gate result, not an exact forever-fixed test number, is the real contract.

## Known limitations

### 1. Not a clinical decision system

TrialIQ is an evidence-support/research workspace. Clinically consequential conclusions should be checked against source records.

### 2. HITL pause state is in-process

Paused investigations use a bounded in-process store with expiry. Restarting the API invalidates outstanding checkpoints. Multi-instance production deployment would need a shared durable continuation store.

### 3. Related-study relationship types are intentionally limited

The guided graph currently traverses Condition, Intervention and Sponsor relationships. Facility, Design and Eligibility are not automatically promoted into related-study traversal.

### 4. Source completeness varies

Not every study has complete dates, phase or enrollment. TrialIQ exposes missing data rather than filling it in.

### 5. External LLM dependency

Guided intent/synthesis requires a configured healthy provider for the full live path. The system supports OpenAI, Gemini and OpenRouter through an abstraction, but provider availability/model behavior can change over time.

### 6. No production auth/authorization model

The stable demo does not claim user authentication, role-based authorization, enterprise secret management or production rate limiting.

### 7. No production observability/SLO package

Logging exists, but the project does not yet claim production monitoring, tracing, alerting, SLOs or capacity management.

### 8. No automated data-refresh schedule

The stable demo assumes a deliberately loaded AACT snapshot. Production operation would need a defined refresh, migration and reconciliation policy.

### 9. Frontend dependency-manifest drift must be resolved before final reproducibility tag

The supplied repository state contains a mismatch between `frontend/package.json` and `frontend/package-lock.json`. Existing installed modules can still build, but a clean-clone `npm ci` may not be reproducible until the manifests are reconciled.

This is the most important remaining reproducibility issue before a long-term release tag.

## Suggested next milestone after documentation

A future **Production Hardening** milestone would be separate from the stable-demo scope and could address:

- authentication/authorization;
- secret management;
- durable HITL state;
- observability;
- capacity/concurrency testing;
- controlled data refresh;
- deployment automation;
- security scanning and dependency policy;
- formal clinical/regulatory positioning where applicable.
