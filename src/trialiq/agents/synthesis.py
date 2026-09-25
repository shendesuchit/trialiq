"""Synthesis agent using validated evidence and structured LLM output."""
import logging

from trialiq.llm.service import LLMUnavailableError, get_llm_service
from trialiq.services.answer_formatter import (
    format_condition_search,
    format_entity_search,
    format_related_trial_search,
    format_shared_entity_comparison,
    format_trial_overview,
)
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer

from .models import (
    AgentRequest,
    GenerationMetadata,
    GenerationMethod,
    RetrievalResult,
    StructuredSynthesis,
    SynthesisResult,
)
from .synthesis_contract import (
    build_deterministic_related_synthesis,
    build_synthesis_messages,
    filter_grounded_synthesis,
    render_structured_synthesis,
)

logger = logging.getLogger(__name__)


class SynthesisAgent:
    def _deterministic_answer(
        self,
        request: AgentRequest,
        retrieval: RetrievalResult,
    ) -> EvidenceGroundedAnswer:
        if retrieval.graph_response is not None:
            return format_trial_overview(retrieval.graph_response, request.question)
        if retrieval.condition_search_response is not None:
            return format_condition_search(
                retrieval.condition_search_response,
                request.question,
            )
        if retrieval.entity_search_response is not None:
            return format_entity_search(retrieval.entity_search_response, request.question)
        if retrieval.related_trial_response is not None:
            return format_related_trial_search(
                retrieval.related_trial_response,
                request.question,
            )
        if retrieval.shared_entity_response is not None:
            return format_shared_entity_comparison(
                retrieval.shared_entity_response,
                request.question,
            )
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=request.question,
            answer="No evidence was available to synthesize an answer.",
            limitations=retrieval.errors or ["Retrieval produced no response."],
        )

    def run(self, request: AgentRequest, retrieval: RetrievalResult) -> SynthesisResult:
        deterministic = self._deterministic_answer(request, retrieval)
        source_count = len(deterministic.sources)
        grounded = deterministic.status == AnswerStatus.GROUNDED
        fallback_structured = build_deterministic_related_synthesis(retrieval)

        if not grounded:
            return SynthesisResult(
                answer=deterministic,
                generation=GenerationMetadata(
                    method=GenerationMethod.DETERMINISTIC,
                    grounded=False,
                    source_count=source_count,
                ),
            )

        # Only natural-language requests that successfully used the LLM intent
        # stage consume the second logical LLM call. Typed/internal workflows and
        # deterministic intent fallback remain fully deterministic, which keeps
        # unit tests and degraded operation free of live network dependencies.
        if request.intent_source != "llm":
            return SynthesisResult(
                answer=deterministic,
                structured=fallback_structured,
                generation=GenerationMetadata(
                    method=GenerationMethod.DETERMINISTIC,
                    grounded=True,
                    source_count=source_count,
                    degraded=request.intent_source == "deterministic_fallback",
                ),
            )

        try:
            structured, metadata = get_llm_service().invoke_structured(
                build_synthesis_messages(request.question, retrieval),
                StructuredSynthesis,
            )
            filtered, grounding_errors = filter_grounded_synthesis(structured, retrieval)
            rejected_claim_count = len(structured.key_findings) - (
                len(filtered.key_findings) if filtered is not None else 0
            )
            if grounding_errors:
                logger.warning(
                    "Structured synthesis grounding validation rejected_claims=%s error_count=%s",
                    rejected_claim_count,
                    len(grounding_errors),
                )
                if filtered is None:
                    return self._degraded_result(
                        deterministic,
                        source_count,
                        "Narrative synthesis was rejected by deterministic grounding validation; a deterministic structured evidence summary is shown.",
                        structured=fallback_structured,
                        provider=metadata.provider,
                        model=metadata.model,
                        attempted_providers=metadata.attempted_providers,
                        failover_reason=metadata.failover_reason,
                        error_category="grounding_validation",
                        latency_ms=metadata.latency_ms,
                        grounding_errors=grounding_errors,
                        rejected_claim_count=rejected_claim_count,
                    )

                answer = deterministic.model_copy(
                    update={
                        "answer": render_structured_synthesis(filtered),
                        "limitations": list(
                            dict.fromkeys(
                                [
                                    *deterministic.limitations,
                                    "Some LLM findings were removed because deterministic grounding validation rejected their evidence references or metric wording.",
                                ]
                            )
                        ),
                    }
                )
                return SynthesisResult(
                    answer=answer,
                    structured=filtered,
                    generation=GenerationMetadata(
                        method=GenerationMethod.LLM,
                        grounded=True,
                        provider=metadata.provider,
                        model=metadata.model,
                        source_count=source_count,
                        attempted_providers=metadata.attempted_providers,
                        failover_reason=metadata.failover_reason,
                        error_category="grounding_validation",
                        latency_ms=metadata.latency_ms,
                        degraded=True,
                        grounding_errors=grounding_errors,
                        rejected_claim_count=rejected_claim_count,
                    ),
                )

            assert filtered is not None
            answer = deterministic.model_copy(
                update={"answer": render_structured_synthesis(filtered)}
            )
            return SynthesisResult(
                answer=answer,
                structured=filtered,
                generation=GenerationMetadata(
                    method=GenerationMethod.LLM,
                    grounded=True,
                    provider=metadata.provider,
                    model=metadata.model,
                    source_count=source_count,
                    attempted_providers=metadata.attempted_providers,
                    failover_reason=metadata.failover_reason,
                    error_category=metadata.error_category,
                    latency_ms=metadata.latency_ms,
                ),
            )
        except LLMUnavailableError as exc:
            logger.warning("Structured synthesis unavailable after bounded provider attempts")
            return self._degraded_result(
                deterministic,
                source_count,
                "Narrative synthesis is unavailable; a deterministic structured evidence summary is shown.",
                structured=fallback_structured,
                attempted_providers=exc.attempted_providers,
                failover_reason=exc.failover_reason,
                error_category=exc.error_category,
                latency_ms=exc.latency_ms,
            )
        except Exception:
            logger.exception("Structured synthesis failed unexpectedly")
            return self._degraded_result(
                deterministic,
                source_count,
                "Narrative synthesis could not be completed; a deterministic structured evidence summary is shown.",
                structured=fallback_structured,
            )

    @staticmethod
    def _degraded_result(
        deterministic: EvidenceGroundedAnswer,
        source_count: int,
        warning: str,
        *,
        structured: StructuredSynthesis | None = None,
        provider: str | None = None,
        model: str | None = None,
        attempted_providers: list[str] | None = None,
        failover_reason: str | None = None,
        error_category: str | None = None,
        latency_ms: float | None = None,
        grounding_errors: list[str] | None = None,
        rejected_claim_count: int = 0,
    ) -> SynthesisResult:
        limitations = list(dict.fromkeys([*deterministic.limitations, warning]))
        return SynthesisResult(
            answer=deterministic.model_copy(update={"limitations": limitations}),
            structured=structured,
            generation=GenerationMetadata(
                method=GenerationMethod.DETERMINISTIC,
                grounded=True,
                provider=provider,
                model=model,
                source_count=source_count,
                attempted_providers=attempted_providers or [],
                failover_reason=failover_reason,
                error_category=error_category,
                latency_ms=latency_ms,
                degraded=True,
                grounding_errors=grounding_errors or [],
                rejected_claim_count=rejected_claim_count,
            ),
        )
