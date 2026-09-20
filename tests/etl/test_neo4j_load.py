
import json
from unittest.mock import patch

import pytest

from trialiq.etl.neo4j_load import load_transformed_artifact
import pytest

from trialiq.etl.neo4j_load import (
    _validate_transformed_artifact,
)


def write_artifact(tmp_path, artifact):
    """Write a transformed artifact to a temporary JSON file."""
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(
        json.dumps(artifact),
        encoding="utf-8",
    )
    return artifact_path


def test_invalid_artifact_is_rejected_before_neo4j_connection(
    tmp_path,
):
    """Reject a node without a key before initializing Neo4j."""

    artifact = {
        "metadata": {
            "nct_ids": ["NCT00000102"],
        },
        "nodes": [
            {
                "label": "Trial",
                "properties": {
                    "nct_id": "NCT00000102",
                },
            },
        ],
        "relationships": [],
    }

    artifact_path = write_artifact(tmp_path, artifact)

    with patch(
        "trialiq.etl.neo4j_load.Neo4jConnection"
    ) as neo4j_connection:
        with pytest.raises(
            ValueError,
            match="Node is missing key",
        ):
            load_transformed_artifact(artifact_path)

    neo4j_connection.assert_not_called()


def test_unsupported_node_label_is_rejected(tmp_path):
    """Reject nodes using labels outside the approved set."""

    artifact = {
        "metadata": {
            "nct_ids": ["NCT00000102"],
        },
        "nodes": [
            {
                "key": "Trial:NCT00000102",
                "label": "UnsupportedLabel",
                "properties": {
                    "nct_id": "NCT00000102",
                },
            },
        ],
        "relationships": [],
    }

    artifact_path = write_artifact(tmp_path, artifact)

    with patch(
        "trialiq.etl.neo4j_load.Neo4jConnection"
    ) as neo4j_connection:
        with pytest.raises(
            ValueError,
            match="Unsupported node label",
        ):
            load_transformed_artifact(artifact_path)

    neo4j_connection.assert_not_called()


def test_duplicate_node_key_is_rejected(tmp_path):
    """Reject duplicate node keys in the transformed artifact."""

    duplicate_node = {
        "key": "Trial:NCT00000102",
        "label": "Trial",
        "properties": {
            "nct_id": "NCT00000102",
        },
    }

    artifact = {
        "metadata": {
            "nct_ids": ["NCT00000102"],
        },
        "nodes": [
            duplicate_node,
            duplicate_node.copy(),
        ],
        "relationships": [],
    }

    artifact_path = write_artifact(tmp_path, artifact)

    with patch(
        "trialiq.etl.neo4j_load.Neo4jConnection"
    ) as neo4j_connection:
        with pytest.raises(
            ValueError,
            match="Duplicate",
        ):
            load_transformed_artifact(artifact_path)

    neo4j_connection.assert_not_called()


def test_unsupported_relationship_type_is_rejected(tmp_path):
    """Reject relationships outside the approved set."""

    artifact = {
        "metadata": {
            "nct_ids": ["NCT00000102"],
        },
        "nodes": [
            {
                "key": "Trial:NCT00000102",
                "label": "Trial",
                "properties": {
                    "nct_id": "NCT00000102",
                },
            },
            {
                "key": "Condition:1",
                "label": "Condition",
                "properties": {
                    "nct_id": "NCT00000102",
                },
            },
        ],
        "relationships": [
            {
                "type": "UNSUPPORTED_RELATIONSHIP",
                "source": "Condition:1",
                "target": "Trial:NCT00000102",
                "properties": {},
            },
        ],
    }

    artifact_path = write_artifact(tmp_path, artifact)

    with patch(
        "trialiq.etl.neo4j_load.Neo4jConnection"
    ) as neo4j_connection:
        with pytest.raises(
            ValueError,
            match="Unsupported relationship type",
        ):
            load_transformed_artifact(artifact_path)

    neo4j_connection.assert_not_called()


def test_invalid_property_value_is_rejected(tmp_path):
    """Reject nested dictionaries as Neo4j property values."""

    artifact = {
        "metadata": {
            "nct_ids": ["NCT00000102"],
        },
        "nodes": [
            {
                "key": "Trial:NCT00000102",
                "label": "Trial",
                "properties": {
                    "nct_id": "NCT00000102",
                    "invalid_field": {
                        "nested": "value",
                    },
                },
            },
        ],
        "relationships": [],
    }

    artifact_path = write_artifact(tmp_path, artifact)

    with patch(
        "trialiq.etl.neo4j_load.Neo4jConnection"
    ) as neo4j_connection:
        with pytest.raises(
            (TypeError, ValueError),
            match="Unsupported|Nested",
        ):
            load_transformed_artifact(artifact_path)

    neo4j_connection.assert_not_called()


from unittest.mock import Mock

import pytest

from trialiq.etl.neo4j_load import _load_relationships


def sample_relationship():
    """Return a valid transformed relationship."""
    return {
        "type": "HAS_CONDITION",
        "source": "Trial:NCT00000102",
        "target": "Condition:1",
        "properties": {
            "source_table": "conditions",
            "source_key": "condition_1",
        },
    }


def test_load_relationships_rejects_empty_write_result():
    """Reject a relationship write that returns no result."""

    connection = Mock()
    connection.execute_write.return_value = []

    with pytest.raises(
        ValueError,
        match="Relationship query returned no result",
    ):
        _load_relationships(
            connection,
            [sample_relationship()],
        )

    connection.execute_write.assert_called_once()


def test_load_relationships_rejects_missing_relationship_endpoints():
    """Reject a relationship when Neo4j reports a zero count."""

    connection = Mock()
    connection.execute_write.return_value = [
        {"relationship_count": 0},
    ]

    with pytest.raises(
        ValueError,
        match="not found or relationship was not created exactly once",
    ):
        _load_relationships(
            connection,
            [sample_relationship()],
        )

    connection.execute_write.assert_called_once()


def test_load_relationships_rejects_ambiguous_relationship_count():
    """Reject a relationship when Neo4j reports a count other than one."""

    connection = Mock()
    connection.execute_write.return_value = [
        {"relationship_count": 2},
    ]

    with pytest.raises(
        ValueError,
        match="not found or relationship was not created exactly once",
    ):
        _load_relationships(
            connection,
            [sample_relationship()],
        )

    connection.execute_write.assert_called_once()


def test_load_relationships_accepts_exactly_one_relationship():
    """Accept a relationship write when exactly one relationship is returned."""

    connection = Mock()
    connection.execute_write.return_value = [
        {"relationship_count": 1},
    ]

    _load_relationships(
        connection,
        [sample_relationship()],
    )

    connection.execute_write.assert_called_once()


def test_load_relationships_uses_deterministic_relationship_key():
    """Verify that the relationship source key is deterministic."""

    connection = Mock()
    connection.execute_write.return_value = [
        {"relationship_count": 1},
    ]

    relationship = sample_relationship()

    _load_relationships(
        connection,
        [relationship],
    )

    query, parameters = connection.execute_write.call_args.args

    expected_key = (
        "HAS_CONDITION:"
        "Trial:NCT00000102:"
        "Condition:1"
    )

    assert parameters["relationship_key"] == expected_key
    assert parameters["properties"]["source_key"] == expected_key
    assert "MERGE" in query
    assert "RETURN count(r) AS relationship_count" in query

def test_validate_transformed_artifact_rejects_missing_relationship_source():
    transformed = {
        "nodes": [
            {
                "key": "trial:NCT00000001",
                "label": "Trial",
                "properties": {
                    "nct_id": "NCT00000001",
                },
            },
        ],
        "relationships": [
            {
                "type": "HAS_CONDITION",
                "source": "condition:missing",
                "target": "trial:NCT00000001",
                "properties": {},
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="Relationship source node not found",
    ):
        _validate_transformed_artifact(transformed)


def test_validate_transformed_artifact_rejects_missing_relationship_target():
    transformed = {
        "nodes": [
            {
                "key": "condition:diabetes",
                "label": "Condition",
                "properties": {
                    "name": "Diabetes",
                },
            },
        ],
        "relationships": [
            {
                "type": "HAS_CONDITION",
                "source": "condition:diabetes",
                "target": "trial:missing",
                "properties": {},
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="Relationship target node not found",
    ):
        _validate_transformed_artifact(transformed)