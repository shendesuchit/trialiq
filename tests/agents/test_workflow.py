import asyncio
from unittest.mock import Mock, patch

from fastmcp import FastMCP

import pytest
from pydantic import ValidationError

from trialiq.agents.mcp_client import DirectRetrievalClient, FastMCPRetrievalClient
from trialiq.agents.models import AgentRequest, AgentStatus, RetrievalResult
from trialiq.agents.retrieval import RetrievalAgent
from trialiq.agents.supervisor import SupervisorAgent
from trialiq.agents.synthesis import SynthesisAgent
from trialiq.llm.service import LLMUnavailableError
from trialiq.agents.validation import ValidationAgent
from trialiq.services.models import (
    AnswerStatus,
    ConditionSearchResponse,
    ConditionSearchStatus,
    EntitySearchResponse,
    EntitySearchStatus,
    EvidenceGroundedAnswer,
    GraphQueryResponse,
    GraphQueryStatus,
    SharedEntityComparisonResponse,
    ValidationResult,
)
from trialiq.services.query_intent import QueryIntent


def request():
    return AgentRequest(
        question="Give me an overview of NCT00000102",
        intent=QueryIntent.TRIAL_OVERVIEW,
        nct_id="NCT00000102",
    )


def graph_response(status=GraphQueryStatus.NOT_FOUND, valid=True, evidence=None, warnings=None):
    return GraphQueryResponse(
        status=status,
        nct_id="NCT00000102",
        evidence=evidence,
        validation=ValidationResult(
            valid=valid,
            errors=[],
            warnings=warnings or [],
        ),
    )


def test_agent_request_rejects_out_of_range_limit():
    with pytest.raises(ValidationError):
        AgentRequest(
            question="Find trials",
            intent=QueryIntent.TRIALS_BY_CONDITION,
            condition="diabetes",
            limit=101,
        )


def test_retrieval_agent_marks_unsupported_intent_explicitly():
    result = RetrievalAgent().run(
        AgentRequest(question="unsupported", intent=QueryIntent.UNSUPPORTED)
    )
    assert result.status == AgentStatus.UNSUPPORTED


def test_retrieval_agent_delegates_trial_overview_to_injected_client():
    client = Mock()
    client.get_trial_evidence.return_value = graph_response()

    result = RetrievalAgent(client=client).run(request())

    client.get_trial_evidence.assert_called_once_with("NCT00000102")
    assert result.status == AgentStatus.NOT_FOUND


def test_retrieval_agent_sanitizes_unexpected_client_exception():
    client = Mock()
    client.get_trial_evidence.side_effect = RuntimeError("secret database detail")

    result = RetrievalAgent(client=client).run(request())

    assert result.status == AgentStatus.EXECUTION_ERROR
    assert "secret database detail" not in " ".join(result.errors)


def test_direct_retrieval_client_remains_available_for_deterministic_injection():
    with patch(
        "trialiq.agents.mcp_client.query_trial_by_nct_id",
        return_value=graph_response(),
    ) as query:
        result = DirectRetrievalClient().get_trial_evidence("NCT00000102")

    query.assert_called_once_with("NCT00000102")
    assert result.status == GraphQueryStatus.NOT_FOUND


def test_fastmcp_retrieval_client_calls_structured_trial_evidence_tool():
    server = FastMCP("TrialIQ MCP client test")

    @server.tool(name="get_trial_evidence")
    def get_trial_evidence(nct_id: str) -> GraphQueryResponse:
        return graph_response(
            GraphQueryStatus.SUCCESS,
            True,
            {"found": True, "trial": {"nct_id": nct_id}},
        )

    client = FastMCPRetrievalClient(server=server)
    result = client.get_trial_evidence("NCT00000102")

    assert isinstance(result, GraphQueryResponse)
    assert result.status == GraphQueryStatus.SUCCESS
    assert result.evidence["trial"]["nct_id"] == "NCT00000102"


def test_fastmcp_retrieval_client_is_safe_inside_existing_event_loop():
    server = FastMCP("TrialIQ async-context MCP client test")

    @server.tool(name="get_trial_evidence")
    def get_trial_evidence(nct_id: str) -> GraphQueryResponse:
        return graph_response(
            GraphQueryStatus.SUCCESS,
            True,
            {"found": True, "trial": {"nct_id": nct_id}},
        )

    client = FastMCPRetrievalClient(server=server)

    async def invoke_from_async_context():
        return client.get_trial_evidence("NCT00000102")

    result = asyncio.run(invoke_from_async_context())

    assert result.status == GraphQueryStatus.SUCCESS
    assert result.evidence["trial"]["nct_id"] == "NCT00000102"


def test_fastmcp_retrieval_client_calls_bounded_condition_search_tool():
    server = FastMCP("TrialIQ condition MCP client test")

    @server.tool(name="search_trials_by_condition")
    def search_trials_by_condition(
        condition: str,
        limit: int,
    ) -> ConditionSearchResponse:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.NOT_FOUND,
            condition=condition,
            limit=limit,
            validation=ValidationResult(valid=True),
        )

    client = FastMCPRetrievalClient(server=server)
    result = client.search_trials_by_condition("diabetes", 7)

    assert isinstance(result, ConditionSearchResponse)
    assert result.status == ConditionSearchStatus.NOT_FOUND
    assert result.condition == "diabetes"
    assert result.limit == 7


def test_validation_preserves_retrieval_execution_error_without_response():
    retrieval = RetrievalResult(
        status=AgentStatus.EXECUTION_ERROR,
        errors=["Retrieval failed because of an unexpected internal error."],
    )
    result = ValidationAgent().run(retrieval)

    assert result.status == AgentStatus.EXECUTION_ERROR
    assert result.can_synthesize is False


def test_supervisor_stops_when_trial_is_not_found():
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.NOT_FOUND,
        graph_response=graph_response(),
    )
    result = SupervisorAgent(retrieval=retrieval).run(request())
    assert result.status == AgentStatus.NOT_FOUND
    assert result.answer.status == AnswerStatus.NOT_FOUND


def test_supervisor_stops_when_validation_fails():
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.VALIDATION_FAILED,
        graph_response=graph_response(GraphQueryStatus.VALIDATION_FAILED, False),
    )
    result = SupervisorAgent(retrieval=retrieval).run(request())
    assert result.status == AgentStatus.VALIDATION_FAILED
    assert result.answer.status == AnswerStatus.VALIDATION_FAILED


def test_supervisor_preserves_unsupported_status():
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.UNSUPPORTED,
        errors=["Unsupported query intent."],
    )
    result = SupervisorAgent(retrieval=retrieval).run(
        AgentRequest(question="unsupported", intent=QueryIntent.UNSUPPORTED)
    )
    assert result.status == AgentStatus.UNSUPPORTED
    assert result.answer.status == AnswerStatus.UNSUPPORTED


def test_supervisor_synthesizes_valid_graph_evidence_and_propagates_warnings():
    evidence = {"found": True, "trial": {"nct_id": "NCT00000102"}}
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.SUCCESS,
        graph_response=graph_response(
            GraphQueryStatus.SUCCESS,
            True,
            evidence,
            warnings=["Trial record has no source_key."],
        ),
    )
    synthesis = Mock()
    synthesis.run.return_value = EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=request().question,
        answer="grounded",
    )

    result = SupervisorAgent(retrieval=retrieval, synthesis=synthesis).run(request())

    synthesis.run.assert_called_once()
    assert result.status == AgentStatus.SUCCESS
    assert result.answer.answer == "grounded"
    assert "Trial record has no source_key." in result.answer.limitations


def test_supervisor_maps_non_grounded_synthesis_status_without_forcing_execution_error():
    evidence = {"found": True, "trial": {"nct_id": "NCT00000102"}}
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.SUCCESS,
        graph_response=graph_response(GraphQueryStatus.SUCCESS, True, evidence),
    )
    synthesis = Mock()
    synthesis.run.return_value = EvidenceGroundedAnswer(
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        question=request().question,
        answer="insufficient",
    )

    result = SupervisorAgent(retrieval=retrieval, synthesis=synthesis).run(request())

    assert result.status == AgentStatus.INSUFFICIENT_EVIDENCE


def test_synthesis_agent_does_not_leak_generation_exception():
    evidence = {"found": True, "trial": {"nct_id": "NCT00000102"}}
    retrieval = RetrievalResult(
        status=AgentStatus.SUCCESS,
        graph_response=graph_response(GraphQueryStatus.SUCCESS, True, evidence),
    )
    formatted = EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=request().question,
        answer="deterministic",
    )

    service = Mock()
    service.invoke_structured.side_effect = LLMUnavailableError("provider secret detail")
    with (
        patch("trialiq.agents.synthesis.format_trial_overview", return_value=formatted),
        patch("trialiq.agents.synthesis.get_llm_service", return_value=service),
    ):
        llm_request = request().model_copy(update={"intent_source": "llm"})
        result = SynthesisAgent().run(llm_request, retrieval)

    assert result.answer.status == AnswerStatus.GROUNDED
    assert result.generation.degraded is True
    assert "provider secret detail" not in " ".join(result.answer.limitations)


def test_fastmcp_client_rejects_unbounded_timeout():
    with pytest.raises(ValueError):
        FastMCPRetrievalClient(timeout=0)
    with pytest.raises(ValueError):
        FastMCPRetrievalClient(timeout=61)


def test_retrieval_result_records_tool_and_transport():
    client = Mock()
    client.transport = "test-mcp"
    client.get_trial_evidence.return_value = graph_response()

    result = RetrievalAgent(client=client).run(request())

    assert result.tool_name == "get_trial_evidence"
    assert result.transport == "test-mcp"


def test_supervisor_success_trace_records_all_stages():
    evidence = {"found": True, "trial": {"nct_id": "NCT00000102"}}
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.SUCCESS,
        graph_response=graph_response(GraphQueryStatus.SUCCESS, True, evidence),
        tool_name="get_trial_evidence",
        transport="mcp",
    )
    synthesis = Mock()
    synthesis.run.return_value = EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=request().question,
        answer="grounded",
    )

    result = SupervisorAgent(retrieval=retrieval, synthesis=synthesis).run(request())

    assert result.run_id
    assert [stage.stage for stage in result.trace] == [
        "retrieval",
        "validation",
        "synthesis",
    ]
    assert result.trace[0].details["tool_name"] == "get_trial_evidence"
    assert result.trace[0].details["transport"] == "mcp"
    assert all(stage.duration_ms >= 0 for stage in result.trace)


def test_supervisor_failed_validation_trace_stops_before_synthesis():
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.NOT_FOUND,
        graph_response=graph_response(),
        tool_name="get_trial_evidence",
        transport="mcp",
    )
    synthesis = Mock()

    result = SupervisorAgent(retrieval=retrieval, synthesis=synthesis).run(request())

    synthesis.run.assert_not_called()
    assert [stage.stage for stage in result.trace] == ["retrieval", "validation"]
    assert result.status == AgentStatus.NOT_FOUND



def test_fastmcp_retrieval_client_calls_intervention_search_tool():
    server = FastMCP("TrialIQ intervention MCP client test")

    @server.tool(name="search_trials_by_intervention")
    def tool(intervention: str, limit: int) -> EntitySearchResponse:
        return EntitySearchResponse(
            status=EntitySearchStatus.NOT_FOUND,
            entity_type="intervention",
            query=intervention,
            limit=limit,
            validation=ValidationResult(valid=True),
        )

    result = FastMCPRetrievalClient(server=server).search_trials_by_intervention(
        "aspirin", 5
    )
    assert result.entity_type == "intervention"
    assert result.limit == 5


def test_fastmcp_retrieval_client_calls_shared_entity_comparison_tool():
    server = FastMCP("TrialIQ comparison MCP client test")

    @server.tool(name="compare_trial_shared_entities")
    def tool(
        nct_id_a: str, nct_id_b: str, limit_per_type: int
    ) -> SharedEntityComparisonResponse:
        return SharedEntityComparisonResponse(
            status=GraphQueryStatus.SUCCESS,
            nct_id_a=nct_id_a,
            nct_id_b=nct_id_b,
            limit_per_type=limit_per_type,
            validation=ValidationResult(valid=True),
        )

    result = FastMCPRetrievalClient(server=server).compare_trial_shared_entities(
        "NCT00000001", "NCT00000002", 5
    )
    assert result.status == GraphQueryStatus.SUCCESS
    assert result.limit_per_type == 5


def _entity_response(entity_type: str, query: str) -> EntitySearchResponse:
    return EntitySearchResponse(
        status=EntitySearchStatus.SUCCESS,
        entity_type=entity_type,
        query=query,
        limit=5,
        matches=[{"nct_id": "NCT00000102", "trial": {"nct_id": "NCT00000102", "brief_title": "Example"}, "matched_entities": [{"name": query}]}],
        validation=ValidationResult(valid=True),
    )


def test_retrieval_agent_routes_intervention_search_to_controlled_client():
    client = Mock()
    client.search_trials_by_intervention.return_value = _entity_response("intervention", "aspirin")
    result = RetrievalAgent(client=client).run(AgentRequest(question="Find aspirin trials", intent=QueryIntent.TRIALS_BY_INTERVENTION, intervention="aspirin", limit=5))
    client.search_trials_by_intervention.assert_called_once_with("aspirin", 5)
    assert result.status == AgentStatus.SUCCESS
    assert result.tool_name == "search_trials_by_intervention"
    assert result.transport == "custom"


def test_retrieval_agent_routes_sponsor_search_to_controlled_client():
    client = Mock()
    client.search_trials_by_sponsor.return_value = _entity_response("sponsor", "Sponsor A")
    result = RetrievalAgent(client=client).run(AgentRequest(question="Find Sponsor A trials", intent=QueryIntent.TRIALS_BY_SPONSOR, sponsor="Sponsor A", limit=5))
    client.search_trials_by_sponsor.assert_called_once_with("Sponsor A", 5)
    assert result.tool_name == "search_trials_by_sponsor"


def test_retrieval_agent_routes_shared_entity_comparison():
    client = Mock()
    client.compare_trial_shared_entities.return_value = SharedEntityComparisonResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id_a="NCT00000102",
        nct_id_b="NCT00000103",
        limit_per_type=5,
        shared_entities=[],
        validation=ValidationResult(valid=True),
    )
    result = RetrievalAgent(client=client).run(AgentRequest(question="Compare shared metadata", intent=QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS, nct_id="NCT00000102", nct_id_b="NCT00000103", limit=5))
    client.compare_trial_shared_entities.assert_called_once_with("NCT00000102", "NCT00000103", 5)
    assert result.status == AgentStatus.SUCCESS
    assert result.tool_name == "compare_trial_shared_entities"


def test_validation_and_synthesis_accept_entity_search_evidence():
    retrieval = RetrievalResult(status=AgentStatus.SUCCESS, entity_search_response=_entity_response("intervention", "aspirin"))
    validation = ValidationAgent().run(retrieval)
    synthesis = SynthesisAgent().run(AgentRequest(question="Find aspirin trials", intent=QueryIntent.TRIALS_BY_INTERVENTION, intervention="aspirin"), retrieval)
    assert validation.can_synthesize is True
    assert synthesis.answer.status == AnswerStatus.GROUNDED
    assert "aspirin" in synthesis.answer.answer


def test_validation_and_synthesis_accept_empty_shared_entity_comparison():
    response = SharedEntityComparisonResponse(status=GraphQueryStatus.SUCCESS, nct_id_a="NCT00000102", nct_id_b="NCT00000103", limit_per_type=5, shared_entities=[], validation=ValidationResult(valid=True))
    retrieval = RetrievalResult(status=AgentStatus.SUCCESS, shared_entity_response=response)
    validation = ValidationAgent().run(retrieval)
    synthesis = SynthesisAgent().run(AgentRequest(question="What do these trials share?", intent=QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS, nct_id="NCT00000102", nct_id_b="NCT00000103"), retrieval)
    assert validation.can_synthesize is True
    assert synthesis.answer.status == AnswerStatus.GROUNDED
    assert "No shared conditions" in synthesis.answer.answer


def test_fastmcp_client_calls_bounded_related_trial_tool():
    from trialiq.services.models import RelatedTrialSearchResponse

    server = FastMCP("related-trial-test")

    @server.tool(name="find_related_trials")
    def find_related_trials(
        seed_nct_id: str,
        max_hops: int,
        per_hop_limit: int,
        limit: int,
        relationship_types: list[str] | None = None,
        overall_statuses: list[str] | None = None,
    ):
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.NOT_FOUND,
            seed_nct_id=seed_nct_id,
            max_hops=max_hops,
            per_hop_limit=per_hop_limit,
            limit=limit,
            relationship_types=relationship_types or [],
            overall_statuses=overall_statuses or [],
            validation=ValidationResult(valid=True),
        )

    result = FastMCPRetrievalClient(server=server).find_related_trials(
        "NCT00000001", 2, 6, 12
    )
    assert result.seed_nct_id == "NCT00000001"
    assert result.max_hops == 2
    assert result.per_hop_limit == 6
    assert result.limit == 12


def test_direct_client_delegates_bounded_related_trial_search():
    from trialiq.services.models import RelatedTrialSearchResponse

    expected = RelatedTrialSearchResponse(
        status=GraphQueryStatus.NOT_FOUND,
        seed_nct_id="NCT00000001",
        max_hops=1,
        per_hop_limit=5,
        limit=10,
        validation=ValidationResult(valid=True),
    )
    with patch("trialiq.agents.mcp_client.query_related_trials", return_value=expected) as query:
        result = DirectRetrievalClient().find_related_trials("NCT00000001", 1, 5, 10)
    query.assert_called_once_with(
        "NCT00000001",
        1,
        5,
        10,
        relationship_types=None,
        overall_statuses=None,
    )
    assert result is expected


def _related_response():
    from trialiq.services.models import RelatedTrialSearchResponse
    return RelatedTrialSearchResponse(
        status=GraphQueryStatus.SUCCESS,
        seed_nct_id="NCT00000102",
        max_hops=2,
        per_hop_limit=5,
        limit=10,
        matches=[{
            "nct_id": "NCT00000103",
            "trial": {"nct_id": "NCT00000103", "brief_title": "Related trial"},
            "discovery_hop": 1,
            "connected_via": [{
                "source_nct_id": "NCT00000102",
                "relationship_type": "HAS_CONDITION",
                "entity": {"name": "Diabetes"},
            }],
        }],
        validation=ValidationResult(valid=True),
    )


def test_retrieval_agent_routes_related_trial_traversal_with_bounds():
    client = Mock()
    client.find_related_trials.return_value = _related_response()
    request = AgentRequest(
        question="Find trials related to NCT00000102 within two hops",
        intent=QueryIntent.RELATED_TRIALS,
        nct_id="NCT00000102",
        max_hops=2,
        per_hop_limit=5,
        limit=10,
    )
    result = RetrievalAgent(client=client).run(request)
    client.find_related_trials.assert_called_once_with(
        "NCT00000102",
        2,
        5,
        10,
        ["HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"],
        [],
    )
    assert result.status == AgentStatus.SUCCESS
    assert result.tool_name == "find_related_trials"
    assert result.transport == "custom"


def test_validation_requires_related_trial_path_evidence():
    response = _related_response()
    response.matches[0].connected_via = []
    result = ValidationAgent().run(RetrievalResult(status=AgentStatus.SUCCESS, related_trial_response=response))
    assert result.status == AgentStatus.INSUFFICIENT_EVIDENCE
    assert result.can_synthesize is False


def test_synthesis_explains_related_trial_path_evidence():
    retrieval = RetrievalResult(status=AgentStatus.SUCCESS, related_trial_response=_related_response())
    synthesis = SynthesisAgent().run(
        AgentRequest(question="Find related trials", intent=QueryIntent.RELATED_TRIALS, nct_id="NCT00000102", max_hops=2),
        retrieval,
    )
    assert synthesis.answer.status == AnswerStatus.GROUNDED
    assert "NCT00000103" in synthesis.answer.answer
    assert "HAS_CONDITION" in synthesis.answer.answer
    assert "Diabetes" in synthesis.answer.answer
    assert synthesis.answer.related_trial_response is not None


def test_supervisor_related_trial_trace_records_mcp_tool():
    retrieval_agent = Mock()
    retrieval_agent.run.return_value = RetrievalResult(
        status=AgentStatus.SUCCESS,
        related_trial_response=_related_response(),
        tool_name="find_related_trials",
        transport="mcp",
    )
    result = SupervisorAgent(retrieval=retrieval_agent).run(
        AgentRequest(question="Find related trials", intent=QueryIntent.RELATED_TRIALS, nct_id="NCT00000102", max_hops=2)
    )
    assert result.status == AgentStatus.SUCCESS
    assert [stage.stage for stage in result.trace] == ["retrieval", "validation", "synthesis"]
    assert result.trace[0].details["tool_name"] == "find_related_trials"
    assert result.trace[0].details["transport"] == "mcp"


def test_supervisor_reports_llm_generation_metadata_for_graph_answer():
    evidence = {"found": True, "trial": {"nct_id": "NCT00000102"}}
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.SUCCESS,
        graph_response=graph_response(GraphQueryStatus.SUCCESS, True, evidence),
        tool_name="get_trial_evidence",
        transport="mcp",
    )
    synthesis = Mock()
    synthesis.run.return_value = EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=request().question,
        answer="grounded",
        sources=[],
    )

    with patch(
        "trialiq.agents.supervisor._configured_llm_identity",
        return_value=("openrouter", "demo-model"),
    ):
        result = SupervisorAgent(retrieval=retrieval, synthesis=synthesis).run(request())

    assert result.generation is not None
    assert result.generation.method.value == "LLM"
    assert result.generation.provider == "openrouter"
    assert result.generation.model == "demo-model"
    assert result.generation.grounded is True
    assert result.trace[-1].details["generation_method"] == "LLM"


def test_supervisor_reports_deterministic_generation_metadata_for_related_trials():
    retrieval_agent = Mock()
    retrieval_agent.run.return_value = RetrievalResult(
        status=AgentStatus.SUCCESS,
        related_trial_response=_related_response(),
        tool_name="find_related_trials",
        transport="mcp",
    )

    result = SupervisorAgent(retrieval=retrieval_agent).run(
        AgentRequest(
            question="Find related trials",
            intent=QueryIntent.RELATED_TRIALS,
            nct_id="NCT00000102",
            max_hops=2,
        )
    )

    assert result.generation is not None
    assert result.generation.method.value == "DETERMINISTIC"
    assert result.generation.provider is None
    assert result.generation.model is None
    assert result.generation.grounded is True
    assert result.trace[-1].details["generation_method"] == "DETERMINISTIC"


def test_supervisor_omits_generation_metadata_when_validation_stops_workflow():
    retrieval = Mock()
    retrieval.run.return_value = RetrievalResult(
        status=AgentStatus.NOT_FOUND,
        graph_response=graph_response(),
    )

    result = SupervisorAgent(retrieval=retrieval).run(request())

    assert result.generation is None
    assert [stage.stage for stage in result.trace] == ["retrieval", "validation"]
