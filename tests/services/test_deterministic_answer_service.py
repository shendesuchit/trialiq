
from unittest.mock import patch

from trialiq.services.answer_service import answer_trial_overview_by_nct_id
from trialiq.services.models import (
    EvidenceGroundedAnswer,
    GraphQueryResponse,
    GraphQueryStatus,
    ValidationResult,
)


VALID_NCT_ID = "NCT00000102"


def _valid_evidence(nct_id: str = VALID_NCT_ID) -> dict:
    return {
        "found": True,
        "nct_id": nct_id,
        "trial": {
            "nct_id": nct_id,
            "brief_title": "Test clinical trial",
        },
        "conditions": [
            {"nct_id": nct_id, "name": "Test condition"},
        ],
        "interventions": [
            {"nct_id": nct_id, "name": "Test intervention"},
        ],
        "sponsors": [
            {"nct_id": nct_id, "name": "Test sponsor"},
        ],
        "facilities": [
            {"nct_id": nct_id, "name": "Test facility"},
        ],
        "designs": [
            {"nct_id": nct_id, "design": "Parallel assignment"},
        ],
        "eligibilities": [
            {"nct_id": nct_id, "criteria": "Test eligibility"},
        ],
        "source": {
            "system": "test",
            "database": "test_db",
        },
    }


def _successful_graph_response(
    nct_id: str = VALID_NCT_ID,
) -> GraphQueryResponse:
    return GraphQueryResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id=nct_id,
        evidence=_valid_evidence(nct_id),
        validation=ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
        ),
    )


def test_valid_nct_id_returns_grounded_answer() -> None:
    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id",
        return_value=_successful_graph_response(),
    ) as mock_query:
        result = answer_trial_overview_by_nct_id(VALID_NCT_ID)

    mock_query.assert_called_once_with(VALID_NCT_ID)
    assert isinstance(result, EvidenceGroundedAnswer)
    assert result.status.value == "GROUNDED"
    assert result.answer
    assert result.graph_response is not None


def test_lowercase_nct_id_is_normalized() -> None:
    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id",
        return_value=_successful_graph_response(),
    ) as mock_query:
        result = answer_trial_overview_by_nct_id(VALID_NCT_ID.lower())

    mock_query.assert_called_once_with(VALID_NCT_ID)
    assert result.status.value == "GROUNDED"


def test_invalid_nct_id_returns_validation_failure() -> None:
    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id"
    ) as mock_query:
        result = answer_trial_overview_by_nct_id("INVALID-NCT")

    mock_query.assert_not_called()
    assert result.status.value == "VALIDATION_FAILED"


def test_empty_nct_id_returns_validation_failure() -> None:
    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id"
    ) as mock_query:
        result = answer_trial_overview_by_nct_id("")

    mock_query.assert_not_called()
    assert result.status.value == "VALIDATION_FAILED"


def test_unknown_valid_nct_id_returns_not_found() -> None:
    unknown_nct_id = "NCT99999999"

    response = GraphQueryResponse(
        status=GraphQueryStatus.NOT_FOUND,
        nct_id=unknown_nct_id,
        evidence={
            "found": False,
            "nct_id": unknown_nct_id,
        },
        validation=ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
        ),
    )

    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id",
        return_value=response,
    ):
        result = answer_trial_overview_by_nct_id(unknown_nct_id)

    assert result.status.value == "NOT_FOUND"


def test_graph_validation_failure_is_propagated() -> None:
    response = GraphQueryResponse(
        status=GraphQueryStatus.VALIDATION_FAILED,
        nct_id=VALID_NCT_ID,
        evidence=None,
        validation=ValidationResult(
            valid=False,
            errors=["Evidence validation failed"],
            warnings=[],
        ),
    )

    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id",
        return_value=response,
    ):
        result = answer_trial_overview_by_nct_id(VALID_NCT_ID)

    assert result.status.value == "VALIDATION_FAILED"
    assert "Evidence validation failed" in str(result.limitations)


def test_graph_execution_failure_is_propagated() -> None:
    response = GraphQueryResponse(
        status=GraphQueryStatus.EXECUTION_ERROR,
        nct_id=VALID_NCT_ID,
        evidence=None,
        validation=ValidationResult(
            valid=False,
            errors=["Neo4j execution failed"],
            warnings=[],
        ),
    )

    with patch(
        "trialiq.services.answer_service.query_trial_by_nct_id",
        return_value=response,
    ):
        result = answer_trial_overview_by_nct_id(VALID_NCT_ID)

    assert result.status.value == "EXECUTION_ERROR"
    assert "Neo4j execution failed" in str(result.limitations)