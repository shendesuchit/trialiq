from unittest.mock import Mock, patch

from trialiq.agents.api import run_agent_question
from trialiq.agents.models import StructuredFinding, StructuredSynthesis
from trialiq.agents.retrieval import RetrievalAgent
from trialiq.agents.supervisor import SupervisorAgent
from trialiq.chains.intent_extraction import ExtractedQueryIntent
from trialiq.llm.models import LLMInvocationMetadata
from trialiq.services.models import GraphQueryResponse, GraphQueryStatus, ValidationResult
from trialiq.services.query_intent import QueryIntent


class FakeTwoCallLLMService:
    def __init__(self):
        self.schemas: list[str] = []

    def invoke_structured(self, _messages, schema):
        self.schemas.append(schema.__name__)
        metadata = LLMInvocationMetadata(
            provider="fake",
            model="fake-model",
            attempted_providers=["fake"],
            latency_ms=1.0,
        )
        if schema is ExtractedQueryIntent:
            return (
                ExtractedQueryIntent(
                    intent=QueryIntent.TRIAL_OVERVIEW,
                    nct_id="NCT00000102",
                ),
                metadata,
            )
        if schema is StructuredSynthesis:
            return (
                StructuredSynthesis(
                    headline="Trial overview",
                    summary="The retrieved trial metadata supports this overview.",
                    key_findings=[
                        StructuredFinding(
                            statement="The trial was retrieved from validated graph evidence.",
                            evidence_ids=["trial:NCT00000102"],
                        )
                    ],
                ),
                metadata,
            )
        raise AssertionError(f"Unexpected schema: {schema}")


def test_normal_agent_question_uses_two_logical_llm_calls():
    service = FakeTwoCallLLMService()
    client = Mock()
    client.transport = "mcp"
    client.get_trial_evidence.return_value = GraphQueryResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id="NCT00000102",
        evidence={
            "found": True,
            "trial": {
                "nct_id": "NCT00000102",
                "brief_title": "Test trial",
            },
        },
        validation=ValidationResult(valid=True),
    )
    supervisor = SupervisorAgent(retrieval=RetrievalAgent(client=client))

    with (
        patch("trialiq.chains.intent_extraction.get_llm_service", return_value=service),
        patch("trialiq.agents.synthesis.get_llm_service", return_value=service),
    ):
        result = run_agent_question(
            "Give me an overview of NCT00000102",
            supervisor=supervisor,
        )

    assert service.schemas == ["ExtractedQueryIntent", "StructuredSynthesis"]
    assert result.status.value == "SUCCESS"
    assert [stage.stage for stage in result.trace] == [
        "intent",
        "retrieval",
        "validation",
        "synthesis",
    ]
    assert result.trace[0].details["source"] == "llm"
    assert result.generation is not None
    assert result.generation.provider == "fake"
    assert result.structured_synthesis is not None


def test_unavailable_llm_uses_bounded_fallback_and_marks_result_degraded():
    from trialiq.llm.service import LLMUnavailableError
    from trialiq.services.models import RelatedTrialSearchResponse

    client = Mock()
    client.transport = "mcp"
    client.find_related_trials.return_value = RelatedTrialSearchResponse(
        status=GraphQueryStatus.SUCCESS,
        seed_nct_id="NCT03416088",
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
                    "brief_title": "Related completed trial",
                    "overall_status": "COMPLETED",
                },
                "discovery_hop": 1,
                "connected_via": [
                    {
                        "source_nct_id": "NCT03416088",
                        "relationship_type": "HAS_CONDITION",
                        "entity": {"name": "Retinal Microcirculation Disorder"},
                    }
                ],
            }
        ],
        validation=ValidationResult(valid=True),
    )
    supervisor = SupervisorAgent(retrieval=RetrievalAgent(client=client))
    error = LLMUnavailableError(
        "provider unavailable",
        attempted_providers=["openai", "gemini"],
        failover_reason="timeout",
        error_category="timeout",
        latency_ms=25.0,
    )

    with patch(
        "trialiq.agents.api.extract_query_intent_with_metadata",
        side_effect=error,
    ):
        result = run_agent_question(
            "Find completed trials connected to NCT03416088 through its conditions or interventions.",
            supervisor=supervisor,
        )

    assert result.status.value == "SUCCESS"
    assert result.trace[0].details["source"] == "deterministic_fallback"
    assert result.trace[0].details["attempted_providers"] == "openai,gemini"
    assert result.generation is not None
    assert result.generation.degraded is True
    assert any("bounded deterministic fallback" in item for item in result.answer.limitations)
    client.find_related_trials.assert_called_once_with(
        "NCT03416088",
        1,
        10,
        20,
        ["HAS_CONDITION", "HAS_INTERVENTION"],
        ["COMPLETED"],
    )


def test_unavailable_llm_outside_fallback_returns_non_secret_intent_trace():
    from trialiq.llm.service import LLMUnavailableError

    error = LLMUnavailableError(
        "provider unavailable",
        attempted_providers=["openai", "gemini"],
        failover_reason="authentication",
        error_category="authentication",
        latency_ms=12.0,
    )

    with patch(
        "trialiq.agents.api.extract_query_intent_with_metadata",
        side_effect=error,
    ):
        result = run_agent_question("Which trial should I choose?")

    assert result.status.value == "EXECUTION_ERROR"
    assert len(result.trace) == 1
    assert result.trace[0].stage == "intent"
    assert result.trace[0].details["source"] == "llm_unavailable"
    assert result.trace[0].details["attempted_providers"] == "openai,gemini"
    assert result.trace[0].details["error_category"] == "authentication"
    assert "provider unavailable" not in result.answer.answer
    assert "provider unavailable" not in " ".join(result.answer.limitations)
