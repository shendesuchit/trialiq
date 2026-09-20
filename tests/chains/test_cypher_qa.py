
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
    assert "OPTIONAL MATCH (condition:Condition)-[:HAS_CONDITION]->(trial)" in query
    assert "OPTIONAL MATCH (intervention:Intervention)-[:HAS_INTERVENTION]->(trial)" in query
    assert "OPTIONAL MATCH (sponsor:Sponsor)-[:SPONSORED_BY]->(trial)" in query
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