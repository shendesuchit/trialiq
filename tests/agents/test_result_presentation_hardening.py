from unittest.mock import patch

from trialiq.agents.models import (
    AgentRequest,
    AgentStatus,
    RetrievalResult,
    StructuredFinding,
    StructuredSynthesis,
)
from trialiq.agents.synthesis import SynthesisAgent
from trialiq.agents.synthesis_contract import (
    build_deterministic_related_synthesis,
    filter_grounded_synthesis,
)
from trialiq.llm.models import LLMInvocationMetadata
from trialiq.services.models import (
    GraphQueryStatus,
    RelatedTrialAggregateMetrics,
    RelatedTrialMetrics,
    RelatedTrialSearchResponse,
    ValidationResult,
)
from trialiq.services.query_intent import QueryIntent


def _retrieval() -> RetrievalResult:
    return RetrievalResult(
        status=AgentStatus.SUCCESS,
        related_trial_response=RelatedTrialSearchResponse(
            status=GraphQueryStatus.SUCCESS,
            seed_nct_id="NCT03416088",
            anchor_trial={
                "nct_id": "NCT03416088",
                "brief_title": "Anchor trial",
                "overall_status": "COMPLETED",
            },
            max_hops=1,
            per_hop_limit=10,
            limit=20,
            relationship_types=["HAS_CONDITION", "HAS_INTERVENTION"],
            overall_statuses=["COMPLETED"],
            matches=[
                {
                    "nct_id": "NCT04214743",
                    "trial": {
                        "nct_id": "NCT04214743",
                        "brief_title": "Related condition trial",
                        "overall_status": "COMPLETED",
                    },
                    "discovery_hop": 1,
                    "connected_via": [
                        {
                            "source_nct_id": "NCT03416088",
                            "relationship_type": "HAS_CONDITION",
                            "entity": {"name": "Retinal Microcirculation Disorder"},
                            "entity_id": "condition:retinal microcirculation disorder",
                        }
                    ],
                },
                {
                    "nct_id": "NCT04731987",
                    "trial": {
                        "nct_id": "NCT04731987",
                        "brief_title": "Related intervention trial",
                        "overall_status": "COMPLETED",
                    },
                    "discovery_hop": 1,
                    "connected_via": [
                        {
                            "source_nct_id": "NCT03416088",
                            "relationship_type": "HAS_INTERVENTION",
                            "entity": {"name": "Beverage consumption"},
                            "entity_id": "intervention:beverage consumption|behavioral",
                        }
                    ],
                },
            ],
            metrics=RelatedTrialAggregateMetrics(
                related_trial_count=2,
                unique_shared_entity_count=2,
                evidence_path_count=2,
            ),
            validation=ValidationResult(valid=True),
        ),
    )


def _request() -> AgentRequest:
    return AgentRequest(
        question="Find completed trials connected to NCT03416088 through its conditions or interventions.",
        intent=QueryIntent.RELATED_TRIALS,
        nct_id="NCT03416088",
        relationship_types=["HAS_CONDITION", "HAS_INTERVENTION"],
        overall_statuses=["COMPLETED"],
        intent_source="llm",
    )


class _FakeLLM:
    def __init__(self, synthesis: StructuredSynthesis):
        self.synthesis = synthesis

    def invoke_structured(self, _messages, _schema):
        return self.synthesis, LLMInvocationMetadata(
            provider="gemini",
            model="gemini-3.5-flash-lite",
            attempted_providers=["gemini"],
            latency_ms=12.5,
        )


def test_deterministic_related_synthesis_is_concise_and_explains_missing_comparisons():
    synthesis = build_deterministic_related_synthesis(_retrieval())
    assert synthesis is not None
    assert synthesis.headline == "2 completed related trials connected to NCT03416088"
    assert len(synthesis.key_findings) == 2
    assert "Retinal Microcirculation Disorder" in synthesis.key_findings[0].statement
    assert synthesis.key_findings[0].evidence_ids == ["path:NCT04214743:0"]
    assert "cannot be calculated" in synthesis.summary


def test_deterministic_related_synthesis_surfaces_available_quantitative_metric():
    retrieval = _retrieval()
    response = retrieval.related_trial_response
    assert response is not None
    response.matches[0].metrics = RelatedTrialMetrics(
        shared_condition_count=1,
        total_shared_entity_count=1,
        evidence_path_count=1,
        completion_date_difference_days=-487,
        completion_date_comparison="Completed 487 days before the study of interest (NCT03416088).",
        enrollment_difference=22,
        enrollment_comparison="Enrollment was 22 more participants than the study of interest (NCT03416088).",
    )

    synthesis = build_deterministic_related_synthesis(retrieval)

    assert synthesis is not None
    assert "Completed 487 days before the study of interest (NCT03416088)." in synthesis.key_findings[0].statement
    assert "metric:NCT04214743:completion_date_difference_days" in synthesis.key_findings[0].evidence_ids


def test_filter_grounded_synthesis_keeps_valid_findings_and_rejects_only_invalid_ones():
    synthesis = StructuredSynthesis(
        headline="Two connections",
        summary="One valid finding and one invalid finding.",
        key_findings=[
            StructuredFinding(
                statement="NCT04214743 shares the retrieved condition.",
                evidence_ids=["path:NCT04214743:0"],
            ),
            StructuredFinding(
                statement="Unsupported connection.",
                evidence_ids=["path:invented:999"],
            ),
        ],
    )
    filtered, errors = filter_grounded_synthesis(synthesis, _retrieval())
    assert filtered is not None
    assert len(filtered.key_findings) == 1
    assert filtered.key_findings[0].evidence_ids == ["path:NCT04214743:0"]
    assert len(errors) == 1
    assert "unknown evidence IDs" in errors[0]


def test_synthesis_retains_valid_subset_and_reports_grounding_diagnostics():
    synthesis = StructuredSynthesis(
        headline="Two connections",
        summary="Grounded response.",
        key_findings=[
            StructuredFinding(
                statement="NCT04214743 shares the retrieved condition.",
                evidence_ids=["path:NCT04214743:0"],
            ),
            StructuredFinding(
                statement="Unsupported connection.",
                evidence_ids=["path:invented:999"],
            ),
        ],
    )
    with patch("trialiq.agents.synthesis.get_llm_service", return_value=_FakeLLM(synthesis)):
        result = SynthesisAgent().run(_request(), _retrieval())

    assert result.structured is not None
    assert len(result.structured.key_findings) == 1
    assert result.generation.method.value == "LLM"
    assert result.generation.degraded is True
    assert result.generation.error_category == "grounding_validation"
    assert result.generation.rejected_claim_count == 1
    assert result.generation.grounding_errors


def test_synthesis_uses_deterministic_structured_fallback_when_all_llm_findings_fail():
    synthesis = StructuredSynthesis(
        headline="Unsupported",
        summary="Unsupported response.",
        key_findings=[
            StructuredFinding(
                statement="Unsupported connection.",
                evidence_ids=["path:invented:999"],
            )
        ],
    )
    with patch("trialiq.agents.synthesis.get_llm_service", return_value=_FakeLLM(synthesis)):
        result = SynthesisAgent().run(_request(), _retrieval())

    assert result.structured is not None
    assert len(result.structured.key_findings) == 2
    assert result.generation.method.value == "DETERMINISTIC"
    assert result.generation.degraded is True
    assert result.generation.error_category == "grounding_validation"
    assert result.generation.rejected_claim_count == 1
    assert any("deterministic structured evidence summary" in item for item in result.answer.limitations)
