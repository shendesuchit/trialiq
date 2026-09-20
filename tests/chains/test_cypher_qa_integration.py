from __future__ import annotations

import pytest

from trialiq.chains.cypher_qa import get_trial_graph
from trialiq.graph.connection import Neo4jConnection


TRIAL_A = "NCT99999801"
TRIAL_B = "NCT99999802"

TRIAL_IDS = (TRIAL_A, TRIAL_B)


pytestmark = pytest.mark.integration


def cleanup_fixture_data(connection: Neo4jConnection) -> None:
    connection.execute_write(
        """
        MATCH (n)
        WHERE n.nct_id IN $nct_ids
        DETACH DELETE n
        """,
        {"nct_ids": list(TRIAL_IDS)},
    )


def create_fixture_data(connection: Neo4jConnection) -> None:
    connection.execute_write(
        """
        CREATE (trial_a:Trial {
            nct_id: $trial_a,
            brief_title: "Trial A"
        })

        CREATE (trial_b:Trial {
            nct_id: $trial_b,
            brief_title: "Trial B"
        })

        CREATE (condition_a:Condition {
            source_key: "Condition:NCT99999801:1",
            nct_id: $trial_a,
            name: "Condition A"
        })

        CREATE (condition_b:Condition {
            source_key: "Condition:NCT99999802:1",
            nct_id: $trial_b,
            name: "Condition B"
        })

        CREATE (intervention_a:Intervention {
            source_key: "Intervention:NCT99999801:1",
            nct_id: $trial_a,
            name: "Intervention A"
        })

        CREATE (intervention_b:Intervention {
            source_key: "Intervention:NCT99999802:1",
            nct_id: $trial_b,
            name: "Intervention B"
        })

        CREATE (sponsor_a:Sponsor {
            source_key: "Sponsor:NCT99999801:1",
            nct_id: $trial_a,
            name: "Sponsor A"
        })

        CREATE (sponsor_b:Sponsor {
            source_key: "Sponsor:NCT99999802:1",
            nct_id: $trial_b,
            name: "Sponsor B"
        })

        CREATE (facility_a:Facility {
            source_key: "Facility:NCT99999801:1",
            nct_id: $trial_a,
            name: "Facility A"
        })

        CREATE (facility_b:Facility {
            source_key: "Facility:NCT99999802:1",
            nct_id: $trial_b,
            name: "Facility B"
        })

        CREATE (design_a:Design {
            source_key: "Design:NCT99999801:1",
            nct_id: $trial_a,
            design_type: "Design A"
        })

        CREATE (design_b:Design {
            source_key: "Design:NCT99999802:1",
            nct_id: $trial_b,
            design_type: "Design B"
        })

        CREATE (eligibility_a:Eligibility {
            source_key: "Eligibility:NCT99999801:1",
            nct_id: $trial_a,
            criteria: "Eligibility A"
        })

        CREATE (eligibility_b:Eligibility {
            source_key: "Eligibility:NCT99999802:1",
            nct_id: $trial_b,
            criteria: "Eligibility B"
        })

        CREATE (condition_a)-[:HAS_CONDITION]->(trial_a)
        CREATE (condition_b)-[:HAS_CONDITION]->(trial_b)

        CREATE (intervention_a)-[:HAS_INTERVENTION]->(trial_a)
        CREATE (intervention_b)-[:HAS_INTERVENTION]->(trial_b)

        CREATE (sponsor_a)-[:SPONSORED_BY]->(trial_a)
        CREATE (sponsor_b)-[:SPONSORED_BY]->(trial_b)

        CREATE (facility_a)-[:HAS_FACILITY]->(trial_a)
        CREATE (facility_b)-[:HAS_FACILITY]->(trial_b)

        CREATE (design_a)-[:HAS_DESIGN]->(trial_a)
        CREATE (design_b)-[:HAS_DESIGN]->(trial_b)

        CREATE (eligibility_a)-[:HAS_ELIGIBILITY]->(trial_a)
        CREATE (eligibility_b)-[:HAS_ELIGIBILITY]->(trial_b)
        """,
        {
            "trial_a": TRIAL_A,
            "trial_b": TRIAL_B,
        },
    )


@pytest.fixture
def neo4j_fixture():
    connection = Neo4jConnection()
    connection.verify_connectivity()

    try:
        cleanup_fixture_data(connection)
        create_fixture_data(connection)
        yield connection
    finally:
        cleanup_fixture_data(connection)
        connection.close()


def test_get_trial_graph_isolates_requested_trial(neo4j_fixture):
    result = get_trial_graph(TRIAL_A)

    assert result["found"] is True
    assert result["nct_id"] == TRIAL_A
    assert result["trial"]["nct_id"] == TRIAL_A

    assert all(
        entity["nct_id"] == TRIAL_A
        for collection_name in (
            "conditions",
            "interventions",
            "sponsors",
            "facilities",
            "designs",
            "eligibilities",
        )
        for entity in result[collection_name]
    )


def test_get_trial_graph_does_not_return_other_trial_entities(
    neo4j_fixture,
):
    result = get_trial_graph(TRIAL_A)

    for collection_name in (
        "conditions",
        "interventions",
        "sponsors",
        "facilities",
        "designs",
        "eligibilities",
    ):
        returned_source_keys = {
            entity.get("source_key")
            for entity in result[collection_name]
        }

        assert not any(
            TRIAL_B in source_key
            for source_key in returned_source_keys
            if source_key is not None
        )


def test_get_trial_graph_returns_second_trial_independently(
    neo4j_fixture,
):
    result = get_trial_graph(TRIAL_B)

    assert result["found"] is True
    assert result["nct_id"] == TRIAL_B
    assert result["trial"]["nct_id"] == TRIAL_B

    assert result["conditions"] == [
        {
            "source_key": "Condition:NCT99999802:1",
            "nct_id": TRIAL_B,
            "name": "Condition B",
        }
    ]

    assert result["interventions"] == [
        {
            "source_key": "Intervention:NCT99999802:1",
            "nct_id": TRIAL_B,
            "name": "Intervention B",
        }
    ]


def test_get_trial_graph_returns_not_found_for_unknown_trial(
    neo4j_fixture,
):
    result = get_trial_graph("NCT99999899")

    assert result == {
        "found": False,
        "nct_id": "NCT99999899",
        "trial": None,
        "conditions": [],
        "interventions": [],
        "sponsors": [],
        "facilities": [],
        "designs": [],
        "eligibilities": [],
    }
