"""Application services for evidence-grounded TrialIQ answers."""

from trialiq.services.answer_formatter import (
    format_condition_search,
    format_trial_overview,
)
from trialiq.llm.integration import get_configured_llm  # legacy test patch target
from trialiq.services.answer_generation import generate_trial_overview_answer
from trialiq.services.graph_query_service import (
    query_trial_by_nct_id,
    query_trials_by_condition,
)
from trialiq.services.models import (
    AnswerStatus,
    EvidenceGroundedAnswer,
    GraphQueryStatus,
    OrchestrationStatus,
)
from trialiq.services.query_intent import QueryIntent, QueryIntentRequest
from trialiq.services.query_orchestrator import answer_question


def _map_orchestration_status(status: OrchestrationStatus) -> AnswerStatus:
    status_mapping = {
        OrchestrationStatus.NOT_FOUND: AnswerStatus.NOT_FOUND,
        OrchestrationStatus.UNSUPPORTED: AnswerStatus.UNSUPPORTED,
        OrchestrationStatus.MISSING_NCT_ID: AnswerStatus.MISSING_NCT_ID,
        OrchestrationStatus.VALIDATION_FAILED: AnswerStatus.VALIDATION_FAILED,
        OrchestrationStatus.EXECUTION_ERROR: AnswerStatus.EXECUTION_ERROR,
    }
    return status_mapping.get(status, AnswerStatus.VALIDATION_FAILED)


def _generate_from_validated_graph(
    question: str,
    graph_response,
) -> EvidenceGroundedAnswer:
    """Generate the final answer only after deterministic evidence validation."""
    validation_result = format_trial_overview(
        graph_response=graph_response,
        question=question,
    )

    if validation_result.status != AnswerStatus.GROUNDED:
        return validation_result

    try:
        generated_answer = generate_trial_overview_answer(
            question=question,
            graph_response=graph_response,
        )
    except Exception:
        limitations = list(
            dict.fromkeys(
                [
                    *validation_result.limitations,
                    "Narrative synthesis is unavailable; deterministic validated evidence output is shown.",
                ]
            )
        )
        return validation_result.model_copy(update={"limitations": limitations})

    return validation_result.model_copy(update={"answer": generated_answer})


def answer_trial_overview(question: str) -> EvidenceGroundedAnswer:
    """Answer a natural-language trial overview request."""
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

    return _generate_from_validated_graph(
        question=question,
        graph_response=orchestration_response.graph_response,
    )


def answer_trial_overview_by_nct_id(nct_id: str) -> EvidenceGroundedAnswer:
    """Return a validated, LLM-generated trial overview for an NCT ID."""
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
            limitations=[str(exc)],
        )

    normalized_nct_id = validated_request.nct_id
    question = f"Give me an overview of {normalized_nct_id}"

    try:
        graph_response = query_trial_by_nct_id(normalized_nct_id)
    except Exception as exc:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=question,
            answer="The trial evidence could not be retrieved.",
            limitations=[f"Graph retrieval failed: {exc}"],
        )

    if graph_response.status == GraphQueryStatus.NOT_FOUND:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.NOT_FOUND,
            question=question,
            answer="The requested clinical trial was not found.",
            graph_response=graph_response,
            limitations=[
                "No graph evidence was found for the requested NCT ID."
            ],
        )

    if graph_response.status == GraphQueryStatus.VALIDATION_FAILED:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.VALIDATION_FAILED,
            question=question,
            answer="The trial evidence failed validation.",
            graph_response=graph_response,
            limitations=graph_response.validation.errors,
        )

    if graph_response.status == GraphQueryStatus.EXECUTION_ERROR:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=question,
            answer="The trial evidence could not be retrieved.",
            graph_response=graph_response,
            limitations=graph_response.validation.errors,
        )

    if graph_response.status == GraphQueryStatus.SUCCESS:
        return _generate_from_validated_graph(
            question=question,
            graph_response=graph_response,
        )

    return EvidenceGroundedAnswer(
        status=AnswerStatus.VALIDATION_FAILED,
        question=question,
        answer="The graph query returned an unrecognized status.",
        graph_response=graph_response,
        limitations=[
            f"Unexpected graph query status: {graph_response.status}"
        ],
    )


def answer_trials_by_condition(
    condition: str,
    question: str | None = None,
    limit: int = 20,
) -> EvidenceGroundedAnswer:
    """Return formatted condition-based trial search results."""
    resolved_question = question or f"Find clinical trials for {condition}"

    try:
        search_response = query_trials_by_condition(condition, limit)
    except Exception as exc:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=resolved_question,
            answer="The condition-based trial search could not be completed.",
            limitations=[f"Condition search failed: {exc}"],
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
