"""Read-only graph query service for TrialIQ."""

from trialiq.chains.cypher_qa import get_trial_graph, search_trials_by_condition
from trialiq.services.models import (
    ConditionSearchResponse,
    ConditionSearchStatus,
    ConditionTrialMatch,
    GraphQueryResponse,
    GraphQueryStatus,
    ValidationResult,
)
from trialiq.validation.evidence import validate_trial_evidence


def query_trial_by_nct_id(nct_id: str) -> GraphQueryResponse:
    """Retrieve and validate graph evidence for a clinical trial."""
    try:
        evidence = get_trial_graph(nct_id)
        validation = validate_trial_evidence(
            evidence=evidence,
            requested_nct_id=nct_id,
        )
        validation_result = ValidationResult(**validation)
        if evidence.get("found") is not True:
            status = GraphQueryStatus.NOT_FOUND
        elif not validation_result.valid:
            status = GraphQueryStatus.VALIDATION_FAILED
        else:
            status = GraphQueryStatus.SUCCESS
        return GraphQueryResponse(
            status=status,
            nct_id=nct_id,
            evidence=evidence,
            validation=validation_result,
        )
    except Exception as exc:
        return GraphQueryResponse(
            status=GraphQueryStatus.EXECUTION_ERROR,
            nct_id=nct_id,
            evidence=None,
            validation=ValidationResult(
                valid=False,
                errors=[f"Graph query execution failed: {exc}"],
                warnings=[],
            ),
        )


def query_trials_by_condition(
    condition: str,
    limit: int = 20,
) -> ConditionSearchResponse:
    """Retrieve trials using deterministic exact condition matching."""
    normalized = condition.strip().casefold()
    if not normalized:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.VALIDATION_FAILED,
            condition=normalized,
            limit=limit,
            matches=[],
            validation=ValidationResult(
                valid=False,
                errors=["Condition cannot be empty."],
                warnings=[],
            ),
        )
    if not 1 <= limit <= 100:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.VALIDATION_FAILED,
            condition=normalized,
            limit=limit,
            matches=[],
            validation=ValidationResult(
                valid=False,
                errors=["Limit must be between 1 and 100."],
                warnings=[],
            ),
        )
    try:
        result = search_trials_by_condition(normalized, limit)
        matches = [
            ConditionTrialMatch(**match)
            for match in result["matches"]
        ]
        found = bool(matches)
        return ConditionSearchResponse(
            status=(
                ConditionSearchStatus.SUCCESS
                if found
                else ConditionSearchStatus.NOT_FOUND
            ),
            condition=normalized,
            limit=limit,
            matches=matches,
            validation=ValidationResult(valid=True, errors=[], warnings=[]),
        )
    except Exception as exc:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.EXECUTION_ERROR,
            condition=normalized,
            limit=limit,
            matches=[],
            validation=ValidationResult(
                valid=False,
                errors=[f"Condition search execution failed: {exc}"],
                warnings=[],
            ),
        )
