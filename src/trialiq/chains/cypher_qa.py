
# Change Start
"""Deterministic Neo4j graph queries for TrialIQ."""

from typing import Any

from trialiq.graph.connection import Neo4jConnection


RELATIONSHIP_TYPES = (
    "HAS_CONDITION",
    "HAS_INTERVENTION",
    "SPONSORED_BY",
    "HAS_FACILITY",
    "HAS_DESIGN",
    "HAS_ELIGIBILITY",
)


def _serialize_node(node: Any) -> dict | None:
    """Convert a Neo4j node into a serializable dictionary."""

    if node is None:
        return None

    return dict(node)


def _serialize_nodes(nodes: list[Any]) -> list[dict]:
    """Convert Neo4j nodes into serializable dictionaries."""

    return [
        serialized
        for node in nodes
        if (serialized := _serialize_node(node)) is not None
    ]


def get_trial_graph(nct_id: str) -> dict:
    """Retrieve a Trial and its connected entities.

    Relationships are currently stored in the following direction:

        Entity -[RELATIONSHIP]-> Trial
    """

    query = """
    MATCH (trial:Trial {nct_id: $nct_id})

    CALL (trial) {
        OPTIONAL MATCH (condition:Condition)-[:HAS_CONDITION]->(trial)
        RETURN collect(condition) AS conditions
    }

    CALL (trial) {
        OPTIONAL MATCH (intervention:Intervention)-[:HAS_INTERVENTION]->(trial)
        RETURN collect(intervention) AS interventions
    }

    CALL (trial) {
        OPTIONAL MATCH (sponsor:Sponsor)-[:SPONSORED_BY]->(trial)
        RETURN collect(sponsor) AS sponsors
    }

    CALL (trial) {
        OPTIONAL MATCH (facility:Facility)-[:HAS_FACILITY]->(trial)
        RETURN collect(facility) AS facilities
    }

    CALL (trial) {
        OPTIONAL MATCH (design:Design)-[:HAS_DESIGN]->(trial)
        RETURN collect(design) AS designs
    }

    CALL (trial) {
        OPTIONAL MATCH (eligibility:Eligibility)-[:HAS_ELIGIBILITY]->(trial)
        RETURN collect(eligibility) AS eligibilities
    }

    RETURN
        trial,
        conditions,
        interventions,
        sponsors,
        facilities,
        designs,
        eligibilities
    """

    connection = Neo4jConnection()

    try:
        records = connection.execute_read(
            query,
            {"nct_id": nct_id},
        )
    finally:
        connection.close()

    if not records:
        return {
            "found": False,
            "nct_id": nct_id,
            "trial": None,
            "conditions": [],
            "interventions": [],
            "sponsors": [],
            "facilities": [],
            "designs": [],
            "eligibilities": [],
        }

    record = records[0]

    return {
        "found": True,
        "nct_id": nct_id,
        "trial": _serialize_node(record["trial"]),
        "conditions": _serialize_nodes(record["conditions"]),
        "interventions": _serialize_nodes(record["interventions"]),
        "sponsors": _serialize_nodes(record["sponsors"]),
        "facilities": _serialize_nodes(record["facilities"]),
        "designs": _serialize_nodes(record["designs"]),
        "eligibilities": _serialize_nodes(record["eligibilities"]),
    }


def count_trial_relationships(nct_id: str) -> dict:
    """Count all entity relationships connected to a Trial."""

    query = """
    MATCH (trial:Trial {nct_id: $nct_id})

    CALL (trial) {
        OPTIONAL MATCH (condition:Condition)-[:HAS_CONDITION]->(trial)
        RETURN count(condition) AS conditions
    }

    CALL (trial) {
        OPTIONAL MATCH (intervention:Intervention)-[:HAS_INTERVENTION]->(trial)
        RETURN count(intervention) AS interventions
    }

    CALL (trial) {
        OPTIONAL MATCH (sponsor:Sponsor)-[:SPONSORED_BY]->(trial)
        RETURN count(sponsor) AS sponsors
    }

    CALL (trial) {
        OPTIONAL MATCH (facility:Facility)-[:HAS_FACILITY]->(trial)
        RETURN count(facility) AS facilities
    }

    CALL (trial) {
        OPTIONAL MATCH (design:Design)-[:HAS_DESIGN]->(trial)
        RETURN count(design) AS designs
    }

    CALL (trial) {
        OPTIONAL MATCH (eligibility:Eligibility)-[:HAS_ELIGIBILITY]->(trial)
        RETURN count(eligibility) AS eligibilities
    }

    RETURN
        conditions,
        interventions,
        sponsors,
        facilities,
        designs,
        eligibilities
    """

    connection = Neo4jConnection()

    try:
        records = connection.execute_read(
            query,
            {"nct_id": nct_id},
        )
    finally:
        connection.close()

    if not records:
        return {
            "found": False,
            "nct_id": nct_id,
            "counts": {
                "conditions": 0,
                "interventions": 0,
                "sponsors": 0,
                "facilities": 0,
                "designs": 0,
                "eligibilities": 0,
            },
        }

    record = records[0]

    return {
        "found": True,
        "nct_id": nct_id,
        "counts": {
            "conditions": record["conditions"],
            "interventions": record["interventions"],
            "sponsors": record["sponsors"],
            "facilities": record["facilities"],
            "designs": record["designs"],
            "eligibilities": record["eligibilities"],
        },
    }


# Change End

def search_trials_by_condition(condition: str, limit: int = 20) -> dict:
    """Find trials with an exact, case-insensitive condition-name match."""
    normalized_condition = condition.strip().casefold()
    query = """
    MATCH (condition:Condition)-[:HAS_CONDITION]->(trial:Trial)
    WHERE condition.downcase_name = $condition
    WITH trial, collect(DISTINCT condition) AS matched_conditions
    RETURN trial, matched_conditions
    ORDER BY trial.nct_id
    LIMIT $limit
    """
    connection = Neo4jConnection()
    try:
        records = connection.execute_read(
            query,
            {"condition": normalized_condition, "limit": limit},
        )
    finally:
        connection.close()

    matches = []
    for record in records:
        trial = _serialize_node(record.get("trial"))
        conditions = _serialize_nodes(record.get("matched_conditions") or [])
        if trial and trial.get("nct_id"):
            matches.append(
                {
                    "nct_id": trial["nct_id"],
                    "trial": trial,
                    "matched_conditions": conditions,
                }
            )
    return {"condition": normalized_condition, "matches": matches}
