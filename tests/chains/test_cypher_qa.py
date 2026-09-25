
from unittest.mock import MagicMock, patch

import pytest

from trialiq.chains.cypher_qa import (
    _serialize_node,
    _serialize_nodes,
    get_trial_graph,
)


NCT_ID = "NCT00000102"

COLLECTIONS = (
    "conditions",
    "interventions",
    "sponsors",
    "facilities",
    "designs",
    "eligibilities",
)


def build_graph_record(
    *,
    nct_id: str = NCT_ID,
) -> dict:
    """Build a complete mocked Neo4j graph record."""

    trial = {
        "nct_id": nct_id,
        "source_key": f"Trial:{nct_id}",
        "brief_title": "Test clinical trial",
    }

    return {
        "trial": trial,
        "conditions": [
            {
                "nct_id": nct_id,
                "source_key": f"Condition:{nct_id}:1",
                "name": "Condition A",
            }
        ],
        "interventions": [
            {
                "nct_id": nct_id,
                "source_key": f"Intervention:{nct_id}:1",
                "name": "Intervention A",
            }
        ],
        "sponsors": [
            {
                "nct_id": nct_id,
                "source_key": f"Sponsor:{nct_id}:1",
                "name": "Sponsor A",
            }
        ],
        "facilities": [
            {
                "nct_id": nct_id,
                "source_key": f"Facility:{nct_id}:1",
                "name": "Facility A",
            }
        ],
        "designs": [
            {
                "nct_id": nct_id,
                "source_key": f"Design:{nct_id}:1",
                "design": "Parallel",
            }
        ],
        "eligibilities": [
            {
                "nct_id": nct_id,
                "source_key": f"Eligibility:{nct_id}:1",
                "criteria": "Adults",
            }
        ],
    }


def build_connection(
    records: list[dict],
) -> MagicMock:
    """Build a mocked Neo4j connection."""

    connection = MagicMock()
    connection.execute_read.return_value = records

    return connection


def test_serialize_node_returns_none_for_none() -> None:
    assert _serialize_node(None) is None


def test_serialize_node_converts_mapping_to_dict() -> None:
    node = {
        "nct_id": NCT_ID,
        "source_key": f"Trial:{NCT_ID}",
    }

    result = _serialize_node(node)

    assert result == node
    assert isinstance(result, dict)


def test_serialize_nodes_excludes_none_values() -> None:
    nodes = [
        {
            "nct_id": NCT_ID,
        },
        None,
        {
            "source_key": "Condition:1",
        },
    ]

    result = _serialize_nodes(nodes)

    assert result == [
        {"nct_id": NCT_ID},
        {"source_key": "Condition:1"},
    ]


def test_get_trial_graph_passes_exact_nct_id_to_query() -> None:
    connection = build_connection(
        [build_graph_record()],
    )

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        result = get_trial_graph(NCT_ID)

    connection.execute_read.assert_called_once()

    query, parameters = connection.execute_read.call_args.args

    assert "$nct_id" in query
    assert parameters == {"nct_id": NCT_ID}
    assert result["nct_id"] == NCT_ID


def test_get_trial_graph_query_contains_trial_scope() -> None:
    connection = build_connection(
        [build_graph_record()],
    )

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        get_trial_graph(NCT_ID)

    query = connection.execute_read.call_args.args[0]

    assert "MATCH (trial:Trial {nct_id: $nct_id})" in query
    assert "OPTIONAL MATCH (condition:Condition)-[rel:HAS_CONDITION]->(trial)" in query
    assert "OPTIONAL MATCH (intervention:Intervention)-[rel:HAS_INTERVENTION]->(trial)" in query
    assert "OPTIONAL MATCH (sponsor:Sponsor)-[rel:SPONSORED_BY]->(trial)" in query
    assert "OPTIONAL MATCH (facility:Facility)-[:HAS_FACILITY]->(trial)" in query
    assert "OPTIONAL MATCH (design:Design)-[:HAS_DESIGN]->(trial)" in query
    assert "OPTIONAL MATCH (eligibility:Eligibility)-[:HAS_ELIGIBILITY]->(trial)" in query


def test_get_trial_graph_closes_connection_after_success() -> None:
    connection = build_connection(
        [build_graph_record()],
    )

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        result = get_trial_graph(NCT_ID)

    connection.close.assert_called_once()
    assert result["found"] is True


def test_get_trial_graph_closes_connection_after_query_failure() -> None:
    connection = build_connection([])

    connection.execute_read.side_effect = RuntimeError(
        "Neo4j unavailable",
    )

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        with pytest.raises(RuntimeError, match="Neo4j unavailable"):
            get_trial_graph(NCT_ID)

    connection.close.assert_called_once()


def test_get_trial_graph_returns_not_found_structure() -> None:
    connection = build_connection([])

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        result = get_trial_graph(NCT_ID)

    assert result == {
        "found": False,
        "nct_id": NCT_ID,
        "trial": None,
        "conditions": [],
        "interventions": [],
        "sponsors": [],
        "facilities": [],
        "designs": [],
        "eligibilities": [],
    }


def test_get_trial_graph_serializes_all_entity_collections() -> None:
    connection = build_connection(
        [build_graph_record()],
    )

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        result = get_trial_graph(NCT_ID)

    assert result["found"] is True
    assert result["trial"]["nct_id"] == NCT_ID

    for collection in COLLECTIONS:
        assert isinstance(result[collection], list)
        assert result[collection]
        assert result[collection][0]["nct_id"] == NCT_ID


def test_get_trial_graph_does_not_change_requested_nct_id() -> None:
    requested_nct_id = "NCT12345678"

    connection = build_connection(
        [build_graph_record(nct_id=requested_nct_id)],
    )

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        result = get_trial_graph(requested_nct_id)

    assert result["nct_id"] == requested_nct_id
    assert result["trial"]["nct_id"] == requested_nct_id

    _query, parameters = connection.execute_read.call_args.args

    assert parameters["nct_id"] == requested_nct_id


def test_get_trial_graph_preserves_returned_entity_data() -> None:
    record = build_graph_record()

    record["conditions"].append(
        {
            "nct_id": NCT_ID,
            "source_key": f"Condition:{NCT_ID}:2",
            "name": "Condition B",
        }
    )

    connection = build_connection([record])

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        result = get_trial_graph(NCT_ID)

    assert len(result["conditions"]) == 2
    assert result["conditions"][1]["name"] == "Condition B"


def test_get_trial_graph_raises_for_missing_trial_key() -> None:
    record = build_graph_record()
    del record["trial"]

    connection = build_connection([record])

    with patch(
        "trialiq.chains.cypher_qa.Neo4jConnection",
        return_value=connection,
    ):
        with pytest.raises(KeyError, match="trial"):
            get_trial_graph(NCT_ID)

    connection.close.assert_called_once()

def test_find_related_trials_bounded_stops_at_requested_hops() -> None:
    from trialiq.chains.cypher_qa import find_related_trials_bounded

    connection = MagicMock()
    connection.execute_read.side_effect = [
        [{"trial": {"nct_id": NCT_ID}}],
        [{
            "source_nct_id": NCT_ID,
            "relationship_type": "HAS_CONDITION",
            "canonical_key": "condition a",
            "entity": {
                "name": "Condition A",
                "canonical_key": "condition a",
                "loaded_trial_count": 2,
            },
            "fanout": 2,
        }],
        [{
            "canonical_key": "condition a",
            "related": {"nct_id": "NCT00000002", "brief_title": "Hop one"},
        }],
        [{
            "source_nct_id": "NCT00000002",
            "relationship_type": "HAS_INTERVENTION",
            "canonical_key": "intervention a|drug",
            "entity": {
                "name": "Intervention A",
                "canonical_key": "intervention a|drug",
                "loaded_trial_count": 2,
            },
            "fanout": 2,
        }],
        [{
            "canonical_key": "intervention a|drug",
            "related": {"nct_id": "NCT00000003", "brief_title": "Hop two"},
        }],
    ]
    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        result = find_related_trials_bounded(
            NCT_ID, max_hops=2, per_hop_limit=5, limit=10
        )

    assert [item["discovery_hop"] for item in result["matches"]] == [1, 2]
    assert [item["nct_id"] for item in result["matches"]] == [
        "NCT00000002", "NCT00000003"
    ]
    assert connection.execute_read.call_count == 5
    connection.close.assert_called_once()


def test_find_related_trials_bounded_selects_entities_before_expansion() -> None:
    from trialiq.chains.cypher_qa import (
        RELATED_ENTITY_LIMIT_PER_TYPE,
        find_related_trials_bounded,
    )

    connection = MagicMock()
    connection.execute_read.side_effect = [[{"trial": {"nct_id": NCT_ID}}], []]
    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        find_related_trials_bounded(NCT_ID, max_hops=1, per_hop_limit=7, limit=9)

    query, parameters = connection.execute_read.call_args.args
    assert "entity.loaded_trial_count" in query
    assert "[0..$entity_limit_per_type]" in query
    assert parameters["relationship_types"] == [
        "HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"
    ]
    assert parameters["entity_limit_per_type"] == RELATED_ENTITY_LIMIT_PER_TYPE


def test_find_related_trials_bounded_forwards_explicit_filters() -> None:
    from trialiq.chains.cypher_qa import find_related_trials_bounded

    connection = MagicMock()
    connection.execute_read.side_effect = [
        [{"trial": {"nct_id": NCT_ID}}],
        [{
            "source_nct_id": NCT_ID,
            "relationship_type": "HAS_INTERVENTION",
            "canonical_key": "drug a|drug",
            "entity": {"name": "Drug A", "canonical_key": "drug a|drug"},
            "fanout": 3,
        }],
        [],
    ]
    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        find_related_trials_bounded(
            NCT_ID,
            max_hops=1,
            per_hop_limit=7,
            limit=9,
            relationship_types=["HAS_CONDITION", "HAS_INTERVENTION"],
            overall_statuses=["COMPLETED"],
        )

    candidate_query, candidate_parameters = connection.execute_read.call_args.args
    assert "related.overall_status IN $overall_statuses" in candidate_query
    assert candidate_parameters["overall_statuses"] == ["COMPLETED"]
    select_parameters = connection.execute_read.call_args_list[1].args[1]
    assert select_parameters["relationship_types"] == [
        "HAS_CONDITION", "HAS_INTERVENTION"
    ]


def test_find_related_trials_bounded_prefers_specific_entity_over_hub() -> None:
    from trialiq.chains.cypher_qa import find_related_trials_bounded

    connection = MagicMock()
    connection.execute_read.side_effect = [
        [{"trial": {"nct_id": NCT_ID}}],
        [
            {
                "source_nct_id": NCT_ID,
                "relationship_type": "HAS_CONDITION",
                "canonical_key": "rare condition",
                "entity": {
                    "name": "Rare Condition",
                    "canonical_key": "rare condition",
                    "loaded_trial_count": 2,
                },
                "fanout": 2,
            },
            {
                "source_nct_id": NCT_ID,
                "relationship_type": "SPONSORED_BY",
                "canonical_key": "large sponsor",
                "entity": {
                    "name": "Large Sponsor",
                    "canonical_key": "large sponsor",
                    "loaded_trial_count": 10000,
                },
                "fanout": 10000,
            },
        ],
        [{
            "canonical_key": "rare condition",
            "related": {"nct_id": "NCT00000009"},
        }],
        [{
            "canonical_key": "large sponsor",
            "related": {"nct_id": "NCT00000002"},
        }],
    ]
    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        result = find_related_trials_bounded(
            NCT_ID, max_hops=1, per_hop_limit=1, limit=1
        )

    assert [item["nct_id"] for item in result["matches"]] == ["NCT00000009"]
    assert result["matches"][0]["connected_via"][0]["entity"]["canonical_key"] == (
        "rare condition"
    )


def test_list_trial_catalog_uses_parameterized_bounded_queries() -> None:
    from trialiq.chains.cypher_qa import list_trial_catalog

    connection = MagicMock()
    connection.execute_read.side_effect = [
        [{"total_count": 2}],
        [
            {
                "nct_id": "NCT03416088",
                "brief_title": "Connected demo trial",
                "official_title": None,
                "overall_status": "COMPLETED",
                "related_trial_count": 200,
                "related_trial_count_capped": True,
                "relationship_types": [
                    "SPONSORED_BY",
                    "HAS_CONDITION",
                    "HAS_CONDITION",
                ],
            },
            {
                "nct_id": "NCT09999999",
                "brief_title": "Isolated trial",
                "official_title": None,
                "overall_status": "RECRUITING",
                "related_trial_count": 0,
                "related_trial_count_capped": False,
                "relationship_types": [],
            },
        ],
    ]

    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        result = list_trial_catalog("Retinal", limit=25, offset=5)

    assert connection.execute_read.call_count == 2
    count_query, count_parameters = connection.execute_read.call_args_list[0].args
    page_query, page_parameters = connection.execute_read.call_args_list[1].args
    assert "Retinal" not in count_query
    assert "Retinal" not in page_query
    assert count_parameters["search"] == "retinal"
    assert page_parameters["limit"] == 25
    assert page_parameters["offset"] == 5
    assert page_parameters["relationship_types"] == [
        "HAS_CONDITION",
        "HAS_INTERVENTION",
        "SPONSORED_BY",
    ]
    assert page_parameters["related_count_cap"] == 200
    assert page_parameters["related_probe_limit"] == 201
    assert "LIMIT $related_probe_limit" in page_query
    assert "SKIP $offset" in page_query
    assert "LIMIT $limit" in page_query
    assert result["total_count"] == 2
    assert result["trials"][0]["relationship_types"] == [
        "HAS_CONDITION",
        "SPONSORED_BY",
    ]
    assert result["trials"][0]["related_trial_count"] == 200
    assert result["trials"][0]["related_trial_count_capped"] is True
    assert result["trials"][1]["related_trial_count"] == 0
    connection.close.assert_called_once()


def test_exact_condition_search_uses_canonical_normalized_name() -> None:
    from trialiq.chains.cypher_qa import search_trials_by_condition

    connection = MagicMock()
    connection.execute_read.return_value = []
    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        search_trials_by_condition(" Breast Cancer ", limit=7)

    query, parameters = connection.execute_read.call_args.args
    assert "Condition {normalized_name: $condition}" in query
    assert "condition.canonical = true" in query
    assert "downcase_name" not in query
    assert parameters == {"condition": "breast cancer", "limit": 7}


def test_exact_intervention_search_uses_canonical_normalized_name() -> None:
    from trialiq.chains.cypher_qa import search_trials_by_intervention

    connection = MagicMock()
    connection.execute_read.return_value = []
    with patch("trialiq.chains.cypher_qa.Neo4jConnection", return_value=connection):
        search_trials_by_intervention(" Placebo ", limit=5)

    query, parameters = connection.execute_read.call_args.args
    assert "Intervention {normalized_name: $name}" in query
    assert "entity.canonical = true" in query
    assert parameters == {"name": "placebo", "limit": 5}
