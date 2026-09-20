
# Neo4j Ingestion Pipeline

import json
from pathlib import Path
from typing import Any

from trialiq.graph.connection import Neo4jConnection


APPROVED_LABELS = {
    "Trial",
    "Condition",
    "Intervention",
    "Sponsor",
    "Facility",
    "Design",
    "Eligibility",
}

APPROVED_RELATIONSHIP_TYPES = {
    "HAS_CONDITION",
    "HAS_INTERVENTION",
    "SPONSORED_BY",
    "HAS_FACILITY",
    "HAS_DESIGN",
    "HAS_ELIGIBILITY",
}


def _load_transformed_artifact(
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Load a transformed graph artifact."""

    path = Path(artifact_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Transformed artifact not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _validate_property_value(
    value: Any,
    property_path: str,
) -> None:
    """Validate values supported by Neo4j properties."""

    if value is None:
        return

    if isinstance(value, (str, int, float, bool)):
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            if item is None:
                raise ValueError(
                    f"Null list item at {property_path}[{index}]"
                )

            if isinstance(item, (list, dict)):
                raise ValueError(
                    "Nested lists/dictionaries are not supported "
                    f"at {property_path}[{index}]"
                )

            _validate_property_value(
                item,
                f"{property_path}[{index}]",
            )

        return

    raise TypeError(
        "Unsupported Neo4j property type at "
        f"{property_path}: {type(value).__name__}"
    )


def _prepare_properties(
    properties: dict[str, Any],
) -> dict[str, Any]:
    """Remove null properties and validate remaining values."""

    prepared: dict[str, Any] = {}

    for field, value in properties.items():
        _validate_property_value(
            value,
            f"properties.{field}",
        )

        if value is not None:
            prepared[field] = value

    return prepared


def _validate_transformed_artifact(
    transformed: dict[str, Any],
) -> None:
    """Validate labels, keys, and relationship types."""

    nodes = transformed.get("nodes", [])
    relationships = transformed.get("relationships", [])

    node_keys: set[str] = set()
    relationship_keys: set[tuple[str, str, str]] = set()
    for node in nodes:
        key = node.get("key")
        label = node.get("label")
        properties = node.get("properties")

        if not key:
            raise ValueError("Node is missing key")

        if label not in APPROVED_LABELS:
            raise ValueError(
                f"Unsupported node label: {label}"
            )

        if not isinstance(properties, dict):
            raise TypeError(
                f"Node properties must be a dictionary: {key}"
            )

        if key in node_keys:
            raise ValueError(
                f"Duplicate node key: {key}"
            )

        node_keys.add(key)

        _prepare_properties(properties)

    relationship_keys: set[tuple[str, str, str]] = set()

    for relationship in relationships:
        relationship_type = relationship.get("type")
        source = relationship.get("source")
        target = relationship.get("target")
        properties = relationship.get("properties")

        if relationship_type not in APPROVED_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unsupported relationship type: {relationship_type}"
            )

        if not source or not target:
            raise ValueError(
                "Relationship source and target are required."
            )

        if source not in node_keys:
            raise ValueError(
                f"Relationship source node not found: {source}"
            )

        if target not in node_keys:
            raise ValueError(
                f"Relationship target node not found: {target}"
            )

        if not isinstance(properties, dict):
            raise TypeError(
                "Relationship properties must be a dictionary."
            )

        relationship_key = (
            relationship_type,
            source,
            target,
        )

        if relationship_key in relationship_keys:
            raise ValueError(
                f"Duplicate relationship: "
                f"{relationship_type} {source} -> {target}"
            )

        relationship_keys.add(relationship_key)

        _prepare_properties(properties)


def _run_write(
    connection: Neo4jConnection,
    query: str,
    parameters: dict[str, Any],
    transaction: Any | None = None,
) -> list[dict]:
    """Run a write in the supplied transaction or a standalone session."""
    if transaction is not None:
        return transaction.run(query, parameters).data()
    return connection.execute_write(query, parameters)


def _load_nodes(
    connection: Neo4jConnection,
    nodes: list[dict[str, Any]],
    transaction: Any | None = None,
) -> None:
    """Load nodes using deterministic source keys."""

    for node in nodes:
        label = node["label"]

        properties = _prepare_properties(
            node["properties"]
        )

        properties["source_key"] = node["key"]

        query = f"""
        MERGE (n:{label} {{source_key: $source_key}})
        SET n += $properties
        """

        _run_write(
            connection,
            query,
            {
                "source_key": node["key"],
                "properties": properties,
            },
            transaction,
        )


def _load_relationships(
    connection: Neo4jConnection,
    relationships: list[dict[str, Any]],
    transaction: Any | None = None,
) -> None:
    """Load relationships using deterministic source keys."""

    for relationship in relationships:
        relationship_type = relationship["type"]

        properties = _prepare_properties(
            relationship.get("properties", {})
        )

        relationship_key = (
            f"{relationship_type}:"
            f"{relationship['source']}:"
            f"{relationship['target']}"
        )

        properties["source_key"] = relationship_key

        query = f"""
        MATCH (source {{source_key: $source_key_source}})
        MATCH (target {{source_key: $source_key_target}})
        MERGE (source)-[r:{relationship_type} {{source_key: $relationship_key}}]->(target)
        SET r += $properties
        """

        result = _run_write(
            connection,
            query + "\nRETURN count(r) AS relationship_count",
            {
                "source_key_source": relationship["source"],
                "source_key_target": relationship["target"],
                "relationship_key": relationship_key,
                "properties": properties,
            },
            transaction,
        )

        if not result:
            raise ValueError(
                "Relationship query returned no result: "
                f"{relationship['source']} -> "
                f"{relationship['target']}"
            )

        relationship_count = result[0].get(
            "relationship_count"
        )

        if relationship_count != 1:
            raise ValueError(
                "Relationship endpoints were not found or relationship "
                "was not created exactly once: "
                f"{relationship['source']} -> "
                f"{relationship['target']} "
                f"(count={relationship_count})"
            )


def load_transformed_artifact(
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Load a transformed artifact into Neo4j."""

    transformed = _load_transformed_artifact(
        artifact_path
    )

    _validate_transformed_artifact(transformed)

    nodes = transformed.get("nodes", [])
    relationships = transformed.get("relationships", [])

    connection = Neo4jConnection()

    try:
        connection.verify_connectivity()

        with connection.transaction() as transaction:
            _load_nodes(
                connection,
                nodes,
                transaction,
            )

            _load_relationships(
                connection,
                relationships,
                transaction,
            )

        return {
            "passed": True,
            "nodes_loaded": len(nodes),
            "relationships_loaded": len(relationships),
        }

    finally:
        connection.close()


def reconcile_loaded_graph(
    transformed_artifact_path: str,
) -> dict:
    """Compare artifact counts and relationship identities with Neo4j."""

    artifact = _load_transformed_artifact(
        transformed_artifact_path
    )

    expected_node_counts: dict[str, int] = {}
    expected_relationship_counts: dict[str, int] = {}

    for node in artifact["nodes"]:
        label = node["label"]

        expected_node_counts[label] = (
            expected_node_counts.get(label, 0) + 1
        )

    for relationship in artifact["relationships"]:
        relationship_type = relationship["type"]

        expected_relationship_counts[relationship_type] = (
            expected_relationship_counts.get(relationship_type, 0) + 1
        )

    expected_relationships = {
        (
            relationship["type"],
            f"{relationship['type']}:"
            f"{relationship['source']}:"
            f"{relationship['target']}",
            relationship["source"],
            relationship["target"],
        )
        for relationship in artifact["relationships"]
    }
    expected_relationship_keys = {
        relationship_key
        for _, relationship_key, _, _ in expected_relationships
    }

    nct_ids = artifact.get("metadata", {}).get("nct_ids", [])

    if not nct_ids:
        raise ValueError(
            "Artifact metadata must contain non-empty nct_ids "
            "for scoped reconciliation."
        )

    connection = Neo4jConnection()

    try:
        node_query = """
        MATCH (n)
        WHERE n.nct_id IN $nct_ids
        UNWIND labels(n) AS node_label
        WITH node_label, count(n) AS node_count
        WHERE node_label IN [
            "Trial",
            "Condition",
            "Intervention",
            "Sponsor",
            "Facility",
            "Design",
            "Eligibility"
        ]
        RETURN node_label, node_count
        ORDER BY node_label
        """

        relationship_query = """
        MATCH (source)-[r]->(target)
        WHERE source.nct_id IN $nct_ids
           OR target.nct_id IN $nct_ids
        WITH
            type(r) AS relationship_type,
            r.source_key AS relationship_key,
            source.source_key AS source_key,
            target.source_key AS target_key,
            count(r) AS relationship_count
        WHERE relationship_type IN [
            "HAS_CONDITION",
            "HAS_INTERVENTION",
            "SPONSORED_BY",
            "HAS_FACILITY",
            "HAS_DESIGN",
            "HAS_ELIGIBILITY"
        ]
        RETURN relationship_type, relationship_key, source_key, target_key,
               relationship_count
        ORDER BY relationship_type, relationship_key, source_key, target_key
        """

        parameters = {
            "nct_ids": nct_ids,
        }

        actual_node_records = connection.execute_read(
            node_query,
            parameters,
        )

        actual_relationship_records = connection.execute_read(
            relationship_query,
            parameters,
        )

    finally:
        connection.close()

    actual_node_counts = {
        record["node_label"]: record["node_count"]
        for record in actual_node_records
    }

    actual_relationship_counts: dict[str, int] = {}
    actual_relationship_keys: set[str] = set()
    actual_relationships: set[tuple[str, str, str | None, str | None]] = set()

    for record in actual_relationship_records:
        relationship_type = record["relationship_type"]
        relationship_key = record["relationship_key"]
        relationship_count = record["relationship_count"]

        actual_relationship_counts[relationship_type] = (
            actual_relationship_counts.get(relationship_type, 0)
            + relationship_count
        )

        if relationship_key is not None:
            actual_relationship_keys.add(relationship_key)

        actual_relationships.add(
            (
                relationship_type,
                relationship_key,
                record["source_key"],
                record["target_key"],
            )
        )

    node_mismatches = []
    relationship_mismatches = []

    for label in sorted(
        set(expected_node_counts)
        | set(actual_node_counts)
    ):
        expected = expected_node_counts.get(label, 0)
        actual = actual_node_counts.get(label, 0)

        if expected != actual:
            node_mismatches.append(
                {
                    "label": label,
                    "expected": expected,
                    "actual": actual,
                }
            )

    for relationship_type in sorted(
        set(expected_relationship_counts)
        | set(actual_relationship_counts)
    ):
        expected = expected_relationship_counts.get(
            relationship_type,
            0,
        )

        actual = actual_relationship_counts.get(
            relationship_type,
            0,
        )

        if expected != actual:
            relationship_mismatches.append(
                {
                    "relationship_type": relationship_type,
                    "expected": expected,
                    "actual": actual,
                }
            )

    missing_relationship_keys = sorted(
        expected_relationship_keys - actual_relationship_keys
    )

    unexpected_relationship_keys = sorted(
        actual_relationship_keys - expected_relationship_keys
    )

    if (
        missing_relationship_keys
        or unexpected_relationship_keys
    ):
        relationship_mismatches.append(
            {
                "relationship_identity": {
                    "missing": missing_relationship_keys,
                    "unexpected": unexpected_relationship_keys,
                },
            }
        )

    relationship_sort_key = lambda relationship: tuple(
        "" if value is None else value
        for value in relationship
    )
    missing_relationship_endpoints = sorted(
        expected_relationships - actual_relationships,
        key=relationship_sort_key,
    )
    unexpected_relationship_endpoints = sorted(
        actual_relationships - expected_relationships,
        key=relationship_sort_key,
    )

    if (
        missing_relationship_endpoints
        or unexpected_relationship_endpoints
    ):
        relationship_mismatches.append(
            {
                "relationship_endpoints": {
                    "missing": [
                        {
                            "relationship_type": relationship_type,
                            "relationship_key": relationship_key,
                            "source_key": source_key,
                            "target_key": target_key,
                        }
                        for (
                            relationship_type,
                            relationship_key,
                            source_key,
                            target_key,
                        ) in missing_relationship_endpoints
                    ],
                    "unexpected": [
                        {
                            "relationship_type": relationship_type,
                            "relationship_key": relationship_key,
                            "source_key": source_key,
                            "target_key": target_key,
                        }
                        for (
                            relationship_type,
                            relationship_key,
                            source_key,
                            target_key,
                        ) in unexpected_relationship_endpoints
                    ],
                },
            }
        )

    return {
        "passed": (
            not node_mismatches
            and not relationship_mismatches
        ),
        "scope_nct_ids": nct_ids,
        "expected_node_counts": expected_node_counts,
        "actual_node_counts": actual_node_counts,
        "expected_relationship_counts": expected_relationship_counts,
        "actual_relationship_counts": actual_relationship_counts,
        "expected_relationship_keys": sorted(
            expected_relationship_keys
        ),
        "actual_relationship_keys": sorted(
            actual_relationship_keys
        ),
        "expected_relationship_endpoints": [
            {
                "relationship_type": relationship_type,
                "relationship_key": relationship_key,
                "source_key": source_key,
                "target_key": target_key,
            }
            for (
                relationship_type,
                relationship_key,
                source_key,
                target_key,
            ) in sorted(
                expected_relationships,
                key=relationship_sort_key,
            )
        ],
        "actual_relationship_endpoints": [
            {
                "relationship_type": relationship_type,
                "relationship_key": relationship_key,
                "source_key": source_key,
                "target_key": target_key,
            }
            for (
                relationship_type,
                relationship_key,
                source_key,
                target_key,
            ) in sorted(
                actual_relationships,
                key=relationship_sort_key,
            )
        ],
        "missing_relationship_keys": missing_relationship_keys,
        "unexpected_relationship_keys": unexpected_relationship_keys,
        "node_mismatches": node_mismatches,
        "relationship_mismatches": relationship_mismatches,
    }
