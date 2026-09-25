"""Unit tests for the bounded GraphRAG visualization DTO."""

from types import SimpleNamespace
from unittest.mock import patch

from trialiq.services.lineage_service import get_trial_graph_view
from trialiq.services.models import GraphQueryStatus, ValidationResult


def _seed_response(status: GraphQueryStatus = GraphQueryStatus.SUCCESS):
    evidence = {
        "trial": {
            "nct_id": "NCT00000102",
            "brief_title": "Seed trial",
            "overall_status": "COMPLETED",
            "source_key": "trial:NCT00000102",
        }
    } if status == GraphQueryStatus.SUCCESS else None
    return SimpleNamespace(
        status=status,
        evidence=evidence,
        validation=ValidationResult(valid=status == GraphQueryStatus.SUCCESS),
    )


def _related_response():
    condition = {
        "name": "Congenital Adrenal Hyperplasia",
        "downcase_name": "congenital adrenal hyperplasia",
        "source_key": "conditions:shared:cah",
    }
    intervention = {
        "name": "Nifedipine",
        "source_key": "interventions:shared:nifedipine",
    }
    return SimpleNamespace(
        status=GraphQueryStatus.SUCCESS,
        validation=ValidationResult(valid=True),
        matches=[
            SimpleNamespace(
                nct_id="NCT00000103",
                trial={"nct_id": "NCT00000103", "brief_title": "Hop one", "source_key": "trial:NCT00000103"},
                discovery_hop=1,
                connected_via=[SimpleNamespace(
                    source_nct_id="NCT00000102",
                    relationship_type="HAS_CONDITION",
                    entity=condition,
                )],
            ),
            SimpleNamespace(
                nct_id="NCT00000104",
                trial={"nct_id": "NCT00000104", "brief_title": "Hop two", "source_key": "trial:NCT00000104"},
                discovery_hop=2,
                connected_via=[SimpleNamespace(
                    source_nct_id="NCT00000103",
                    relationship_type="HAS_INTERVENTION",
                    entity=intervention,
                )],
            ),
        ],
    )


def test_graph_view_builds_evidence_backed_nodes_and_edges():
    with patch("trialiq.services.lineage_service.query_trial_by_nct_id", return_value=_seed_response()), patch(
        "trialiq.services.lineage_service.query_related_trials", return_value=_related_response()
    ):
        graph = get_trial_graph_view("nct00000102", max_hops=2, per_hop_limit=10, limit=20)

    assert graph.status == GraphQueryStatus.SUCCESS
    assert graph.seed_node == "trial:NCT00000102"
    assert graph.match_count == 2
    assert {node.id for node in graph.nodes} >= {
        "trial:NCT00000102",
        "trial:NCT00000103",
        "trial:NCT00000104",
        "condition:congenital-adrenal-hyperplasia",
        "intervention:nifedipine",
    }
    assert {edge.relationship.value for edge in graph.edges} == {"HAS_CONDITION", "HAS_INTERVENTION"}
    assert all(edge.source.startswith("trial:") for edge in graph.edges)
    assert all(edge.target.startswith(("condition:", "intervention:")) for edge in graph.edges)


def test_graph_view_preserves_seed_for_valid_zero_match_search():
    related = SimpleNamespace(
        status=GraphQueryStatus.NOT_FOUND,
        validation=ValidationResult(valid=True),
        matches=[],
    )
    with patch("trialiq.services.lineage_service.query_trial_by_nct_id", return_value=_seed_response()), patch(
        "trialiq.services.lineage_service.query_related_trials", return_value=related
    ):
        graph = get_trial_graph_view("NCT00000102", max_hops=1, per_hop_limit=20, limit=40)

    assert graph.status == GraphQueryStatus.SUCCESS
    assert graph.related_status == GraphQueryStatus.NOT_FOUND
    assert graph.seed_node == "trial:NCT00000102"
    assert graph.match_count == 0
    assert len(graph.nodes) == 1
    assert graph.edges == []
    assert graph.limitations == ["No related trials were found within the configured graph search bounds."]


def test_graph_view_stops_when_seed_trial_is_missing():
    with patch(
        "trialiq.services.lineage_service.query_trial_by_nct_id",
        return_value=_seed_response(GraphQueryStatus.NOT_FOUND),
    ):
        graph = get_trial_graph_view("NCT00000102")

    assert graph.status == GraphQueryStatus.NOT_FOUND
    assert graph.seed_node is None
    assert graph.nodes == []
    assert graph.edges == []
