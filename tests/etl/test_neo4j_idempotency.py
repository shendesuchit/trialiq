import json

import pytest

from trialiq.etl.neo4j_load import load_transformed_artifact
from trialiq.graph.connection import Neo4jConnection
from trialiq.etl.neo4j_load import reconcile_loaded_graph
from unittest.mock import patch

TEST_NCT_ID = "NCT99999901"

TRIAL_SOURCE_KEY = f"Trial:{TEST_NCT_ID}"
CONDITION_SOURCE_KEY = f"Condition:{TEST_NCT_ID}:1"

RELATIONSHIP_SOURCE_KEY = (
    f"HAS_CONDITION:{CONDITION_SOURCE_KEY}:{TRIAL_SOURCE_KEY}"
)


pytestmark = pytest.mark.integration


def build_test_artifact():
    """Build a minimal deterministic transformed artifact."""

    return {
        "metadata": {
            "nct_ids": [TEST_NCT_ID],
        },
        "nodes": [
            {
                "key": TRIAL_SOURCE_KEY,
                "label": "Trial",
                "properties": {
                    "nct_id": TEST_NCT_ID,
                    "brief_title": "TrialIQ idempotency test",
                },
            },
            {
                "key": CONDITION_SOURCE_KEY,
                "label": "Condition",
                "properties": {
                    "nct_id": TEST_NCT_ID,
                    "name": "Idempotency Test Condition",
                },
            },
        ],
        "relationships": [
            {
                "type": "HAS_CONDITION",
                "source": CONDITION_SOURCE_KEY,
                "target": TRIAL_SOURCE_KEY,
                "properties": {
                    "source_table": "conditions",
                    "source_key": "idempotency_test_condition",
                },
            },
        ],
    }


def write_artifact(tmp_path):
    """Write the test artifact to a temporary JSON file."""

    artifact_path = tmp_path / "idempotency_artifact.json"

    artifact_path.write_text(
        json.dumps(build_test_artifact()),
        encoding="utf-8",
    )

    return artifact_path


def cleanup_test_data(connection):
    """Remove only the deterministic test fixture."""

    connection.execute_write(
        """
        MATCH (n)
        WHERE n.source_key IN $node_source_keys
        DETACH DELETE n
        """,
        {
            "node_source_keys": [
                TRIAL_SOURCE_KEY,
                CONDITION_SOURCE_KEY,
            ],
        },
    )


def read_fixture_counts(connection):
    """Return the fixture node and relationship counts."""

    node_result = connection.execute_read(
        """
        MATCH (n)
        WHERE n.source_key IN $node_source_keys
        RETURN count(n) AS node_count
        """,
        {
            "node_source_keys": [
                TRIAL_SOURCE_KEY,
                CONDITION_SOURCE_KEY,
            ],
        },
    )

    relationship_result = connection.execute_read(
        """
        MATCH (source)-[r:HAS_CONDITION]->(target)
        WHERE r.source_key = $relationship_source_key
        RETURN count(r) AS relationship_count
        """,
        {
            "relationship_source_key": RELATIONSHIP_SOURCE_KEY,
        },
    )

    return {
        "node_count": node_result[0]["node_count"],
        "relationship_count": relationship_result[0][
            "relationship_count"
        ],
    }


def test_reloading_same_artifact_is_idempotent(tmp_path):
    """Loading the same artifact twice must not create duplicates."""

    artifact_path = write_artifact(tmp_path)
    connection = Neo4jConnection()

    try:
        cleanup_test_data(connection)

        first_load = load_transformed_artifact(artifact_path)

        assert first_load["passed"] is True
        assert first_load["nodes_loaded"] == 2
        assert first_load["relationships_loaded"] == 1

        first_counts = read_fixture_counts(connection)

        assert first_counts == {
            "node_count": 2,
            "relationship_count": 1,
        }

        second_load = load_transformed_artifact(artifact_path)

        assert second_load["passed"] is True
        assert second_load["nodes_loaded"] == 2
        assert second_load["relationships_loaded"] == 1

        second_counts = read_fixture_counts(connection)

        assert second_counts == first_counts
        assert second_counts == {
            "node_count": 2,
            "relationship_count": 1,
        }

    finally:
        cleanup_test_data(connection)
        connection.close()

def test_reconciliation_matches_loaded_fixture(tmp_path):
    """Reconciliation should pass for the loaded test artifact."""

    artifact_path = write_artifact(tmp_path)
    connection = Neo4jConnection()

    try:
        cleanup_test_data(connection)

        load_result = load_transformed_artifact(artifact_path)

        assert load_result["passed"] is True

        reconciliation = reconcile_loaded_graph(
            str(artifact_path),
        )

        assert reconciliation["passed"] is True
        assert reconciliation["scope_nct_ids"] == [
            TEST_NCT_ID,
        ]
        assert reconciliation["node_mismatches"] == []
        assert reconciliation["relationship_mismatches"] == []

    finally:
        cleanup_test_data(connection)
        connection.close()

def test_reconciliation_detects_missing_relationship(tmp_path):
    """Reconciliation should detect a missing loaded relationship."""

    artifact_path = write_artifact(tmp_path)
    connection = Neo4jConnection()

    try:
        cleanup_test_data(connection)

        load_result = load_transformed_artifact(artifact_path)

        assert load_result["passed"] is True

        connection.execute_write(
            """
            MATCH (source)-[r:HAS_CONDITION]->(target)
            WHERE r.source_key = $relationship_source_key
            DELETE r
            """,
            {
                "relationship_source_key": RELATIONSHIP_SOURCE_KEY,
            },
        )

        reconciliation = reconcile_loaded_graph(
            str(artifact_path),
        )

        assert reconciliation["passed"] is False
        assert reconciliation["node_mismatches"] == []

        assert {
            "relationship_type": "HAS_CONDITION",
            "expected": 1,
            "actual": 0,
        } in reconciliation["relationship_mismatches"]

        assert {
            "relationship_identity": {
                "missing": [
                    RELATIONSHIP_SOURCE_KEY,
                ],
                "unexpected": [],
            },
        } in reconciliation["relationship_mismatches"]

    finally:
        cleanup_test_data(connection)
        connection.close()

def test_reconciliation_detects_wrong_relationship_identity(tmp_path):
    """Reconciliation should detect a relationship with the wrong key."""

    artifact_path = write_artifact(tmp_path)
    connection = Neo4jConnection()

    try:
        cleanup_test_data(connection)

        load_result = load_transformed_artifact(artifact_path)

        assert load_result["passed"] is True

        connection.execute_write(
            """
            MATCH (source)-[r:HAS_CONDITION]->(target)
            WHERE r.source_key = $relationship_source_key
            DELETE r
            """,
            {
                "relationship_source_key": RELATIONSHIP_SOURCE_KEY,
            },
        )

        wrong_relationship_key = (
            f"HAS_CONDITION:"
            f"{TRIAL_SOURCE_KEY}:Condition:wrong"
        )

        connection.execute_write(
            """
            MATCH (source), (target)
            WHERE source.source_key = $trial_source_key
              AND target.source_key = $condition_source_key
            CREATE (source)-[r:HAS_CONDITION {
                source_key: $wrong_relationship_key
            }]->(target)
            RETURN count(r) AS relationship_count
            """,
            {
                "trial_source_key": TRIAL_SOURCE_KEY,
                "condition_source_key": CONDITION_SOURCE_KEY,
                "wrong_relationship_key": wrong_relationship_key,
            },
        )

        reconciliation = reconcile_loaded_graph(
            str(artifact_path),
        )

        assert reconciliation["passed"] is False
        assert reconciliation["node_mismatches"] == []

        assert reconciliation["relationship_mismatches"] != []

    finally:
        cleanup_test_data(connection)
        connection.close()


def test_reconciliation_detects_wrong_relationship_endpoints(tmp_path):
    """A valid relationship key must not hide reversed endpoints."""

    artifact_path = write_artifact(tmp_path)
    connection = Neo4jConnection()

    try:
        cleanup_test_data(connection)
        load_transformed_artifact(artifact_path)

        connection.execute_write(
            """
            MATCH ()-[r:HAS_CONDITION]->()
            WHERE r.source_key = $relationship_source_key
            DELETE r
            """,
            {
                "relationship_source_key": RELATIONSHIP_SOURCE_KEY,
            },
        )
        connection.execute_write(
            """
            MATCH (trial {source_key: $trial_source_key})
            MATCH (condition {source_key: $condition_source_key})
            CREATE (trial)-[:HAS_CONDITION {
                source_key: $relationship_source_key
            }]->(condition)
            """,
            {
                "trial_source_key": TRIAL_SOURCE_KEY,
                "condition_source_key": CONDITION_SOURCE_KEY,
                "relationship_source_key": RELATIONSHIP_SOURCE_KEY,
            },
        )

        reconciliation = reconcile_loaded_graph(str(artifact_path))

        assert reconciliation["passed"] is False
        assert reconciliation["missing_relationship_keys"] == []
        assert reconciliation["unexpected_relationship_keys"] == []
        assert any(
            "relationship_endpoints" in mismatch
            for mismatch in reconciliation["relationship_mismatches"]
        )
    finally:
        cleanup_test_data(connection)
        connection.close()

def test_relationship_failure_rolls_back_all_changes(tmp_path):
    """A relationship failure must roll back nodes created in the same load."""
    artifact_path = write_artifact(tmp_path)
    connection = Neo4jConnection()

    try:
        cleanup_test_data(connection)

        with patch(
            "trialiq.etl.neo4j_load._load_relationships",
            side_effect=RuntimeError("Simulated relationship failure"),
        ):
            with pytest.raises(
                RuntimeError,
                match="Simulated relationship failure",
            ):
                load_transformed_artifact(artifact_path)

        counts = read_fixture_counts(connection)

        assert counts == {
            "node_count": 0,
            "relationship_count": 0,
        }

    finally:
        cleanup_test_data(connection)
        connection.close()
