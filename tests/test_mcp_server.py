from trialiq.mcp import server
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


def make_answer(status=AnswerStatus.GROUNDED):
    return EvidenceGroundedAnswer(
        status=status,
        question="Give me an overview of NCT00000102",
        answer="Mock grounded answer",
        sources=[],
    )


def test_get_trial_evidence_delegates_to_graph_query_service(monkeypatch):
    expected = GraphQueryResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id="NCT00000102",
        evidence={"found": True, "trial": {"nct_id": "NCT00000102"}},
        validation=ValidationResult(valid=True),
    )
    captured = {}

    def fake_query(nct_id):
        captured["nct_id"] = nct_id
        return expected

    monkeypatch.setattr(server, "query_trial_by_nct_id", fake_query)

    result = server.get_trial_evidence("NCT00000102")

    assert captured["nct_id"] == "NCT00000102"
    assert result is expected


def test_search_trials_by_condition_delegates_with_bound(monkeypatch):
    expected = ConditionSearchResponse(
        status=ConditionSearchStatus.NOT_FOUND,
        condition="diabetes",
        limit=7,
        matches=[],
        validation=ValidationResult(valid=True),
    )
    captured = {}

    def fake_search(condition, limit):
        captured.update(condition=condition, limit=limit)
        return expected

    monkeypatch.setattr(server, "query_trials_by_condition", fake_search)

    result = server.search_trials_by_condition("diabetes", 7)

    assert captured == {"condition": "diabetes", "limit": 7}
    assert result is expected


def test_get_trial_overview_delegates_to_nct_answer_service(monkeypatch):
    captured = {}

    def fake_answer(nct_id):
        captured["nct_id"] = nct_id
        return make_answer()

    monkeypatch.setattr(server, "answer_trial_overview_by_nct_id", fake_answer)

    result = server.get_trial_overview("NCT00000102")

    assert captured["nct_id"] == "NCT00000102"
    assert isinstance(result, EvidenceGroundedAnswer)
    assert result.status == AnswerStatus.GROUNDED
    assert result.answer == "Mock grounded answer"


def test_get_trial_overview_preserves_non_grounded_status(monkeypatch):
    monkeypatch.setattr(
        server,
        "answer_trial_overview_by_nct_id",
        lambda _: make_answer(AnswerStatus.INSUFFICIENT_EVIDENCE),
    )

    result = server.get_trial_overview("NCT99999999")

    assert result.status == AnswerStatus.INSUFFICIENT_EVIDENCE



def test_search_trials_by_intervention_delegates_with_bound(monkeypatch):
    expected = EntitySearchResponse(
        status=EntitySearchStatus.NOT_FOUND,
        entity_type="intervention",
        query="aspirin",
        limit=6,
        validation=ValidationResult(valid=True),
    )
    captured = {}
    monkeypatch.setattr(
        server,
        "query_trials_by_intervention",
        lambda intervention, limit: captured.update(intervention=intervention, limit=limit) or expected,
    )

    result = server.search_trials_by_intervention("aspirin", 6)
    assert captured == {"intervention": "aspirin", "limit": 6}
    assert result is expected


def test_search_trials_by_sponsor_delegates_with_bound(monkeypatch):
    expected = EntitySearchResponse(
        status=EntitySearchStatus.NOT_FOUND,
        entity_type="sponsor",
        query="sponsor a",
        limit=6,
        validation=ValidationResult(valid=True),
    )
    monkeypatch.setattr(server, "query_trials_by_sponsor", lambda *_: expected)
    assert server.search_trials_by_sponsor("Sponsor A", 6) is expected


def test_compare_trial_shared_entities_delegates(monkeypatch):
    expected = SharedEntityComparisonResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id_a="NCT00000001",
        nct_id_b="NCT00000002",
        limit_per_type=8,
        validation=ValidationResult(valid=True),
    )
    captured = {}
    monkeypatch.setattr(
        server,
        "query_shared_entities_between_trials",
        lambda a, b, limit: captured.update(a=a, b=b, limit=limit) or expected,
    )

    result = server.compare_trial_shared_entities("NCT00000001", "NCT00000002", 8)
    assert captured == {"a": "NCT00000001", "b": "NCT00000002", "limit": 8}
    assert result is expected


def test_find_related_trials_delegates_with_all_bounds(monkeypatch):
    from trialiq.services.models import RelatedTrialSearchResponse

    expected = RelatedTrialSearchResponse(
        status=GraphQueryStatus.NOT_FOUND,
        seed_nct_id="NCT00000001",
        max_hops=2,
        per_hop_limit=7,
        limit=15,
        validation=ValidationResult(valid=True),
    )
    captured = {}
    monkeypatch.setattr(
        server,
        "query_related_trials",
        lambda seed, hops, per_hop, limit, **filters: captured.update(
            seed=seed, hops=hops, per_hop=per_hop, limit=limit, **filters
        ) or expected,
    )

    result = server.find_related_trials("NCT00000001", 2, 7, 15)
    assert captured == {
        "seed": "NCT00000001",
        "hops": 2,
        "per_hop": 7,
        "limit": 15,
        "relationship_types": None,
        "overall_statuses": None,
    }
    assert result is expected


def test_verify_trial_evidence_tool_delegates(monkeypatch):
    from trialiq.services.source_verification import TrialVerificationResponse, VerificationStatus

    expected = TrialVerificationResponse(
        nct_id="NCT00000102",
        status=VerificationStatus.VERIFIED,
        validation=ValidationResult(valid=True),
    )
    captured = {}
    monkeypatch.setattr(
        server,
        "verify_trial_evidence",
        lambda nct_id: captured.update(nct_id=nct_id) or expected,
    )

    result = server.verify_trial_evidence_tool("NCT00000102")
    assert captured == {"nct_id": "NCT00000102"}
    assert result is expected
