# Change Start: Add answer composition service

from trialiq.services.answer_formatter import format_trial_overview, format_condition_search
from trialiq.services.query_orchestrator import answer_question
from trialiq.services.graph_query_service import query_trial_by_nct_id, query_trials_by_condition
from trialiq.services.models import (
    AnswerStatus,
    EvidenceGroundedAnswer,
    GraphQueryStatus,
    OrchestrationStatus,
)
from trialiq.services.query_intent import (
    QueryIntent,
    QueryIntentRequest,
)


def _map_orchestration_status(
    status: OrchestrationStatus,
) -> AnswerStatus:
    status_mapping = {
        OrchestrationStatus.NOT_FOUND: AnswerStatus.NOT_FOUND,
        OrchestrationStatus.UNSUPPORTED: AnswerStatus.UNSUPPORTED,
        OrchestrationStatus.MISSING_NCT_ID: AnswerStatus.MISSING_NCT_ID,
        OrchestrationStatus.VALIDATION_FAILED: AnswerStatus.VALIDATION_FAILED,
        OrchestrationStatus.EXECUTION_ERROR: AnswerStatus.EXECUTION_ERROR,
    }

    return status_mapping.get(
        status,
        AnswerStatus.VALIDATION_FAILED,
    )


def answer_trial_overview(question: str) -> EvidenceGroundedAnswer:
    orchestration_response = answer_question(question)

    if orchestration_response.status != OrchestrationStatus.SUCCESS:
        answer_kwargs = {
            "status": _map_orchestration_status(orchestration_response.status),
            "question": question,
            "answer": orchestration_response.message,
            "limitations": [
                f"Orchestration status: {orchestration_response.status.value}"
            ],
        }

        # Preserve structured evidence payloads even for NOT_FOUND,
        # VALIDATION_FAILED, and execution-error responses. This allows
        # clients to distinguish an empty result from missing response data.
        if orchestration_response.condition_search_response is not None:
            answer_kwargs["condition_search_response"] = (
                orchestration_response.condition_search_response
            )
        if orchestration_response.graph_response is not None:
            answer_kwargs["graph_response"] = orchestration_response.graph_response

        return EvidenceGroundedAnswer(**answer_kwargs)

    if orchestration_response.condition_search_response is not None:
        return format_condition_search(
            search_response=orchestration_response.condition_search_response,
            question=question,
        )

    if orchestration_response.graph_response is None:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer="No graph evidence was available for this request.",
            limitations=[
                "The orchestration response did not contain graph evidence."
            ],
        )

    return format_trial_overview(
        graph_response=orchestration_response.graph_response,
        question=question,
    )

# Change Start: Add deterministic NCT-based answer service



# Change Start: Add deterministic NCT-based answer service

# Change Start: Validate deterministic MCP NCT input

def answer_trial_overview_by_nct_id(
    nct_id: str,
) -> EvidenceGroundedAnswer:
    """Return a validated trial overview using a specific NCT ID."""

    question = f"Give me an overview of {nct_id}"

    try:
        validated_request = QueryIntentRequest(
            intent=QueryIntent.TRIAL_OVERVIEW,
            nct_id=nct_id,
        )
    except ValueError as exc:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.VALIDATION_FAILED,
            question=question,
            answer="The supplied NCT ID is invalid.",
            limitations=["The supplied NCT ID failed validation."],
        )

    normalized_nct_id = validated_request.nct_id

    try:
        graph_response = query_trial_by_nct_id(normalized_nct_id)
    except Exception:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=f"Give me an overview of {normalized_nct_id}",
            answer="The trial evidence could not be retrieved.",
            limitations=[
                "An unexpected error occurred while retrieving graph evidence."
            ],
        )

    if graph_response.status == GraphQueryStatus.NOT_FOUND:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.NOT_FOUND,
            question=question,
            answer="The requested clinical trial was not found.",
            graph_response=graph_response.model_dump(),
            limitations=[
                "No graph evidence was found for the requested NCT ID."
            ],
        )

    if graph_response.status == GraphQueryStatus.VALIDATION_FAILED:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.VALIDATION_FAILED,
            question=question,
            answer="The trial evidence failed validation.",
            graph_response=graph_response.model_dump(),
            limitations=graph_response.validation.errors,
        )

    if graph_response.status == GraphQueryStatus.EXECUTION_ERROR:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=question,
            answer="The trial evidence could not be retrieved.",
            graph_response=graph_response.model_dump(),
            limitations=graph_response.validation.errors,
        )

    if graph_response.status == GraphQueryStatus.SUCCESS:
        return format_trial_overview(
            graph_response=graph_response,
            question=f"Give me an overview of {normalized_nct_id}",
        )

    return EvidenceGroundedAnswer(
        status=AnswerStatus.VALIDATION_FAILED,
        question=question,
        answer="The graph query returned an unrecognized status.",
        graph_response=graph_response.model_dump(),
        limitations=[
            f"Unexpected graph query status: {graph_response.status}"
        ],
    )

# Change End


def answer_trials_by_condition(
    condition: str,
    question: str | None = None,
    limit: int = 20,
) -> EvidenceGroundedAnswer:
    resolved_question = question or f"Find clinical trials for {condition}"
    try:
        search_response = query_trials_by_condition(condition, limit)
    except Exception:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=resolved_question,
            answer="The condition-based trial search could not be completed.",
            limitations=["An unexpected error occurred during condition search."],
        )

    if search_response.status.value == "VALIDATION_FAILED":
        answer_status = AnswerStatus.VALIDATION_FAILED
    elif search_response.status.value == "EXECUTION_ERROR":
        answer_status = AnswerStatus.EXECUTION_ERROR
    elif search_response.status.value == "NOT_FOUND":
        answer_status = AnswerStatus.NOT_FOUND
    else:
        return format_condition_search(search_response, resolved_question)

    return EvidenceGroundedAnswer(
        status=answer_status,
        question=resolved_question,
        answer="No matching trials were found for the requested condition.",
        condition_search_response=search_response,
        limitations=search_response.validation.errors or [
            f"Condition search status: {search_response.status.value}"
        ],
    )
