"""Supervisor for the isolated experimental TrialIQ agent workflow."""
from time import perf_counter
from uuid import uuid4

from trialiq.llm.service import get_llm_service
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer

from .models import (
    AgentRequest,
    AgentRunResult,
    AgentStageTrace,
    AgentStatus,
    GenerationMetadata,
    GenerationMethod,
    SynthesisResult,
)
from .retrieval import RetrievalAgent
from .synthesis import SynthesisAgent
from .validation import ValidationAgent


_ANSWER_TO_AGENT_STATUS = {
    AnswerStatus.GROUNDED: AgentStatus.SUCCESS,
    AnswerStatus.NOT_FOUND: AgentStatus.NOT_FOUND,
    AnswerStatus.INSUFFICIENT_EVIDENCE: AgentStatus.INSUFFICIENT_EVIDENCE,
    AnswerStatus.UNSUPPORTED: AgentStatus.UNSUPPORTED,
    AnswerStatus.MISSING_NCT_ID: AgentStatus.VALIDATION_FAILED,
    AnswerStatus.VALIDATION_FAILED: AgentStatus.VALIDATION_FAILED,
    AnswerStatus.EXECUTION_ERROR: AgentStatus.EXECUTION_ERROR,
}

_AGENT_TO_ANSWER_STATUS = {
    AgentStatus.NOT_FOUND: AnswerStatus.NOT_FOUND,
    AgentStatus.VALIDATION_FAILED: AnswerStatus.VALIDATION_FAILED,
    AgentStatus.EXECUTION_ERROR: AnswerStatus.EXECUTION_ERROR,
    AgentStatus.INSUFFICIENT_EVIDENCE: AnswerStatus.INSUFFICIENT_EVIDENCE,
    AgentStatus.UNSUPPORTED: AnswerStatus.UNSUPPORTED,
}



def _configured_llm_identity() -> tuple[str | None, str | None]:
    """Return the active non-secret LLM identity without affecting workflow success."""
    try:
        status = get_llm_service().status()
        return status.selected_provider, status.selected_model
    except Exception:
        return None, None


def _generation_metadata(
    retrieval,
    answer: EvidenceGroundedAnswer,
) -> GenerationMetadata:
    """Describe the synthesis path that actually produced the answer text."""
    source_count = len(answer.sources)
    grounded = answer.status == AnswerStatus.GROUNDED

    if retrieval.graph_response is not None:
        provider, model = _configured_llm_identity()
        return GenerationMetadata(
            method=GenerationMethod.LLM,
            grounded=grounded,
            provider=provider,
            model=model,
            source_count=source_count,
        )

    return GenerationMetadata(
        method=GenerationMethod.DETERMINISTIC,
        grounded=grounded,
        source_count=source_count,
    )

def _duration_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


class SupervisorAgent:
    def __init__(self, retrieval=None, validation=None, synthesis=None):
        self.retrieval = retrieval or RetrievalAgent()
        self.validation = validation or ValidationAgent()
        self.synthesis = synthesis or SynthesisAgent()

    def run(self, request: AgentRequest) -> AgentRunResult:
        run_id = str(uuid4())
        trace: list[AgentStageTrace] = []

        started = perf_counter()
        retrieval = self.retrieval.run(request)
        related = retrieval.related_trial_response
        retrieval_details: dict[str, str | int | float | bool | None] = {
            "intent": request.intent.value,
            "tool_name": retrieval.tool_name,
            "transport": retrieval.transport,
        }
        if related is not None:
            retrieval_details.update(
                {
                    "anchor_nct_id": related.seed_nct_id,
                    "relationship_types": ",".join(related.relationship_types),
                    "overall_statuses": ",".join(related.overall_statuses),
                    "match_count": len(related.matches),
                }
            )
        trace.append(
            AgentStageTrace(
                stage="retrieval",
                status=retrieval.status,
                duration_ms=_duration_ms(started),
                details=retrieval_details,
            )
        )

        if related is not None and any(match.metrics is not None for match in related.matches):
            metrics_started = perf_counter()
            comparison_metric_count = sum(
                sum(
                    value is not None
                    for value in (
                        match.metrics.start_date_difference_days,
                        match.metrics.completion_date_difference_days,
                        match.metrics.duration_difference_days,
                        match.metrics.enrollment_difference,
                    )
                )
                for match in related.matches
                if match.metrics is not None
            )
            trace.append(
                AgentStageTrace(
                    stage="metrics",
                    status=retrieval.status,
                    duration_ms=_duration_ms(metrics_started),
                    details={
                        "source": "deterministic_backend",
                        "related_trial_count": related.metrics.related_trial_count,
                        "shared_entity_count": related.metrics.unique_shared_entity_count,
                        "evidence_path_count": related.metrics.evidence_path_count,
                        "comparison_metric_count": comparison_metric_count,
                    },
                )
            )

        started = perf_counter()
        validation = self.validation.run(retrieval)
        trace.append(
            AgentStageTrace(
                stage="validation",
                status=validation.status,
                duration_ms=_duration_ms(started),
                details={
                    "can_synthesize": validation.can_synthesize,
                    "warning_count": len(validation.warnings),
                    "error_count": len(validation.errors),
                },
            )
        )

        if not validation.can_synthesize:
            answer = EvidenceGroundedAnswer(
                status=_AGENT_TO_ANSWER_STATUS.get(
                    validation.status,
                    AnswerStatus.VALIDATION_FAILED,
                ),
                question=request.question,
                answer="The requested evidence could not be used to produce a grounded answer.",
                graph_response=retrieval.graph_response,
                condition_search_response=retrieval.condition_search_response,
                entity_search_response=retrieval.entity_search_response,
                shared_entity_response=retrieval.shared_entity_response,
                related_trial_response=retrieval.related_trial_response,
                limitations=validation.errors or [f"Validation status: {validation.status.value}"],
            )
            return AgentRunResult(
                run_id=run_id,
                status=validation.status,
                answer=answer,
                retrieval=retrieval,
                validation=validation,
                trace=trace,
            )

        started = perf_counter()
        synthesis_output = self.synthesis.run(request, retrieval)
        if isinstance(synthesis_output, SynthesisResult):
            answer = synthesis_output.answer
            generation = synthesis_output.generation
            structured_synthesis = synthesis_output.structured
        else:
            # Preserve compatibility with deterministic test doubles and older
            # injected synthesis implementations.
            answer = synthesis_output
            generation = _generation_metadata(retrieval, answer)
            structured_synthesis = None

        if validation.warnings:
            answer = answer.model_copy(
                update={
                    "limitations": list(
                        dict.fromkeys([*answer.limitations, *validation.warnings])
                    )
                }
            )

        final_status = _ANSWER_TO_AGENT_STATUS.get(
            answer.status,
            AgentStatus.EXECUTION_ERROR,
        )
        trace.append(
            AgentStageTrace(
                stage="synthesis",
                status=final_status,
                duration_ms=_duration_ms(started),
                details={
                    "source_count": len(answer.sources),
                    "limitation_count": len(answer.limitations),
                    "generation_method": generation.method.value,
                    "generation_provider": generation.provider,
                    "generation_model": generation.model,
                    "generation_degraded": generation.degraded,
                    "attempted_providers": ",".join(generation.attempted_providers),
                    "failover_reason": generation.failover_reason,
                    "error_category": generation.error_category,
                    "llm_latency_ms": generation.latency_ms,
                    "validated_claim_count": (
                        len(structured_synthesis.key_findings)
                        if structured_synthesis is not None
                        else 0
                    ),
                    "rejected_claim_count": generation.rejected_claim_count,
                    "grounding_error_count": len(generation.grounding_errors),
                    "grounding_errors": " | ".join(generation.grounding_errors) or None,
                },
            )
        )

        return AgentRunResult(
            run_id=run_id,
            status=final_status,
            answer=answer,
            retrieval=retrieval,
            validation=validation,
            generation=generation,
            structured_synthesis=structured_synthesis,
            trace=trace,
        )
