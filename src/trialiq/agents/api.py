"""Public entry points for the experimental agent workflow."""
import re
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from trialiq.chains.intent_extraction import extract_query_intent_with_metadata
from trialiq.chains.intent_fallback import extract_supported_intent_fallback
from trialiq.llm.service import LLMUnavailableError
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer
from trialiq.services.query_intent import QueryIntent, QueryIntentRequest

from .models import (
    AgentRequest, AgentRunResult, AgentStageTrace, AgentStatus, ValidationResult,
)
from .supervisor import SupervisorAgent


def _failed_run(
    question: str,
    *,
    status: AgentStatus,
    answer_status: AnswerStatus,
    message: str,
    limitation: str,
    trace: list[AgentStageTrace] | None = None,
) -> AgentRunResult:
    validation = ValidationResult(
        status=status,
        can_synthesize=False,
        errors=[limitation],
    )
    return AgentRunResult(
        run_id=str(uuid4()),
        status=status,
        answer=EvidenceGroundedAnswer(
            status=answer_status,
            question=question,
            answer=message,
            limitations=[limitation],
        ),
        validation=validation,
        trace=trace or [],
    )


def run_agent_workflow(
    request: AgentRequest,
    *,
    supervisor: SupervisorAgent | None = None,
) -> AgentRunResult:
    """Normalize a typed request and execute the isolated agent workflow."""
    try:
        validated = QueryIntentRequest(
            intent=request.intent,
            nct_id=request.nct_id,
            condition=request.condition,
            intervention=request.intervention,
            sponsor=request.sponsor,
            nct_id_b=request.nct_id_b,
            limit=request.limit,
            max_hops=request.max_hops,
            per_hop_limit=request.per_hop_limit,
            relationship_types=request.relationship_types,
            overall_statuses=request.overall_statuses,
        )
    except ValidationError:
        return _failed_run(
            request.question,
            status=AgentStatus.VALIDATION_FAILED,
            answer_status=AnswerStatus.VALIDATION_FAILED,
            message="The agent request failed validation.",
            limitation="The request did not satisfy the supported query contract.",
        )

    normalized = request.model_copy(
        update={
            "nct_id": validated.nct_id,
            "condition": validated.condition,
            "intervention": validated.intervention,
            "sponsor": validated.sponsor,
            "nct_id_b": validated.nct_id_b,
            "limit": validated.limit,
            "max_hops": validated.max_hops,
            "per_hop_limit": validated.per_hop_limit,
            "relationship_types": validated.relationship_types,
            "overall_statuses": validated.overall_statuses,
        }
    )
    return (supervisor or SupervisorAgent()).run(normalized)


def run_agent_question(
    question: str,
    *,
    limit: int = 20,
    supervisor: SupervisorAgent | None = None,
) -> AgentRunResult:
    """Extract intent, validate it, and execute the agent workflow."""
    normalized_question = question.strip() if question else ""
    if not normalized_question:
        return _failed_run(
            question,
            status=AgentStatus.VALIDATION_FAILED,
            answer_status=AnswerStatus.VALIDATION_FAILED,
            message="The question cannot be empty.",
            limitation="Question validation failed.",
        )

    malformed_nct = re.search(r"\bNCT\d+\b", normalized_question, flags=re.IGNORECASE)
    if malformed_nct and not re.search(
        r"\bNCT\d{8}\b",
        normalized_question,
        flags=re.IGNORECASE,
    ):
        return _failed_run(
            normalized_question,
            status=AgentStatus.VALIDATION_FAILED,
            answer_status=AnswerStatus.VALIDATION_FAILED,
            message="The supplied NCT ID is invalid.",
            limitation="Use the format NCT followed by exactly 8 digits.",
        )

    intent_started = perf_counter()
    intent_source = "llm"
    intent_metadata = None
    intent_error_category = None
    intent_attempted_providers: list[str] = []
    intent_failover_reason = None
    intent_latency_ms = None
    try:
        extracted, intent_metadata = extract_query_intent_with_metadata(
            normalized_question
        )
    except LLMUnavailableError as exc:
        intent_error_category = exc.error_category
        intent_attempted_providers = exc.attempted_providers
        intent_failover_reason = exc.failover_reason
        intent_latency_ms = exc.latency_ms
        extracted = extract_supported_intent_fallback(normalized_question)
        if extracted is None:
            intent_trace = AgentStageTrace(
                stage="intent",
                status=AgentStatus.EXECUTION_ERROR,
                duration_ms=round((perf_counter() - intent_started) * 1000, 3),
                details={
                    "source": "llm_unavailable",
                    "attempted_providers": ",".join(intent_attempted_providers),
                    "failover_reason": intent_failover_reason,
                    "error_category": intent_error_category,
                    "llm_latency_ms": intent_latency_ms,
                },
            )
            return _failed_run(
                normalized_question,
                status=AgentStatus.EXECUTION_ERROR,
                answer_status=AnswerStatus.EXECUTION_ERROR,
                message="The query could not be interpreted because no LLM provider is available.",
                limitation="Intent extraction is unavailable and the question is outside the bounded deterministic fallback patterns.",
                trace=[intent_trace],
            )
        intent_source = "deterministic_fallback"
    except ValueError:
        return _failed_run(
            normalized_question,
            status=AgentStatus.VALIDATION_FAILED,
            answer_status=AnswerStatus.VALIDATION_FAILED,
            message="The supplied query failed validation.",
            limitation="Intent extraction could not validate the supplied query.",
        )
    except Exception:
        return _failed_run(
            normalized_question,
            status=AgentStatus.EXECUTION_ERROR,
            answer_status=AnswerStatus.EXECUTION_ERROR,
            message="The query could not be processed by the agent workflow.",
            limitation="Intent extraction failed because of an unexpected internal error.",
        )

    request = AgentRequest(
        question=normalized_question,
        intent=extracted.intent,
        nct_id=extracted.nct_id,
        condition=extracted.condition,
        intervention=extracted.intervention,
        sponsor=extracted.sponsor,
        nct_id_b=extracted.nct_id_b,
        limit=limit,
        max_hops=extracted.max_hops,
        per_hop_limit=extracted.per_hop_limit,
        relationship_types=extracted.relationship_types,
        overall_statuses=extracted.overall_statuses,
        intent_source=intent_source,
    )

    if extracted.intent == QueryIntent.UNSUPPORTED:
        result = (supervisor or SupervisorAgent()).run(request)
    else:
        result = run_agent_workflow(request, supervisor=supervisor)

    intent_details = {
        "intent": extracted.intent.value,
        "source": intent_source,
        "provider": intent_metadata.provider if intent_metadata else None,
        "model": intent_metadata.model if intent_metadata else None,
        "relationship_types": ",".join(extracted.relationship_types),
        "overall_statuses": ",".join(extracted.overall_statuses),
        "attempted_providers": (
            ",".join(intent_metadata.attempted_providers)
            if intent_metadata
            else ",".join(intent_attempted_providers)
        ),
        "failover_reason": (
            intent_metadata.failover_reason if intent_metadata else intent_failover_reason
        ),
        "error_category": (
            intent_metadata.error_category if intent_metadata else intent_error_category
        ),
        "llm_latency_ms": (
            intent_metadata.latency_ms if intent_metadata else intent_latency_ms
        ),
    }
    intent_trace = AgentStageTrace(
        stage="intent",
        status=AgentStatus.SUCCESS,
        duration_ms=round((perf_counter() - intent_started) * 1000, 3),
        details=intent_details,
    )
    updates: dict[str, object] = {"trace": [intent_trace, *result.trace]}
    if intent_source == "deterministic_fallback":
        fallback_warning = (
            "LLM intent extraction was unavailable; TrialIQ used its bounded "
            "deterministic fallback for this supported query pattern."
        )
        updates["answer"] = result.answer.model_copy(
            update={
                "limitations": list(
                    dict.fromkeys([*result.answer.limitations, fallback_warning])
                )
            }
        )
    return result.model_copy(update=updates)
