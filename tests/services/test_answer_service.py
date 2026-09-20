# Change Start: Add deterministic answer service tests

from unittest.mock import patch

from trialiq.services.answer_service import answer_trial_overview
from trialiq.services.models import (
    AnswerStatus,
    OrchestrationResponse,
    OrchestrationStatus,
)


def test_unsupported_request_maps_to_unsupported_answer():
    orchestration_response = OrchestrationResponse(
        status=OrchestrationStatus.UNSUPPORTED,
        message="The requested question is unsupported.",
    )

    with patch(
        "trialiq.services.answer_service.answer_question",
        return_value=orchestration_response,
    ):
        result = answer_trial_overview("Compare two clinical trials.")

    assert result.status == AnswerStatus.UNSUPPORTED
    assert result.answer == "The requested question is unsupported."
    assert "Orchestration status: UNSUPPORTED" in result.limitations


def test_missing_nct_id_maps_to_missing_nct_answer():
    orchestration_response = OrchestrationResponse(
        status=OrchestrationStatus.MISSING_NCT_ID,
        message="Please provide a specific clinical trial NCT ID.",
    )

    with patch(
        "trialiq.services.answer_service.answer_question",
        return_value=orchestration_response,
    ):
        result = answer_trial_overview("Give me a trial overview.")

    assert result.status == AnswerStatus.MISSING_NCT_ID
    assert "specific clinical trial NCT ID" in result.answer


def test_not_found_preserves_not_found_status():
    orchestration_response = OrchestrationResponse(
        status=OrchestrationStatus.NOT_FOUND,
        message="The requested clinical trial was not found.",
    )

    with patch(
        "trialiq.services.answer_service.answer_question",
        return_value=orchestration_response,
    ):
        result = answer_trial_overview(
            "Give me an overview of NCT99999999."
        )

    assert result.status == AnswerStatus.NOT_FOUND
    assert "not found" in result.answer


def test_success_without_graph_response_returns_insufficient_evidence():
    orchestration_response = OrchestrationResponse(
        status=OrchestrationStatus.SUCCESS,
        message="The query was processed successfully.",
        graph_response=None,
    )

    with patch(
        "trialiq.services.answer_service.answer_question",
        return_value=orchestration_response,
    ):
        result = answer_trial_overview(
            "Give me an overview of NCT00000102."
        )

    assert result.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert "No graph evidence was available" in result.answer


# Change End