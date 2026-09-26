# Graph Discovery Model

## Related-study connection dimensions

TrialIQ currently discovers related studies through exactly three canonical graph relationship families:

- Condition -> Trial via `HAS_CONDITION`
- Intervention -> Trial via `HAS_INTERVENTION`
- Sponsor -> Trial via `SPONSORED_BY`

## Evidence/context dimensions

Trial evidence can also include Facility, Design and Eligibility information. These do not automatically become related-study traversal dimensions.

## Comparison attributes

Study status, phase, type, dates and enrollment are study attributes used for display/filtering/comparison where available.

They should not be confused with graph connection entities.

## Hub-aware retrieval

Common entities can connect thousands of trials. TrialIQ keeps them as valid evidence but bounds graph expansion and prioritizes lower-fan-out entities to avoid uncontrolled traversal.

## Recommended visual

Use `06-graph-domain-model.mmd`.
