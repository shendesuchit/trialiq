
# AACT Transformation Pipeline

# Change Start
import json
from pathlib import Path
from typing import Any


ENTITY_RELATIONSHIPS = {
    "conditions": (
        "Condition",
        "HAS_CONDITION",
    ),
    "interventions": (
        "Intervention",
        "HAS_INTERVENTION",
    ),
    "sponsors": (
        "Sponsor",
        "SPONSORED_BY",
    ),
    "facilities": (
        "Facility",
        "HAS_FACILITY",
    ),
    "designs": (
        "Design",
        "HAS_DESIGN",
    ),
    "eligibilities": (
        "Eligibility",
        "HAS_ELIGIBILITY",
    ),
}


def _load_artifact(
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Load an extracted AACT artifact."""
    path = Path(artifact_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Artifact not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def _entity_key(
    table: str,
    nct_id: str,
    source_id: Any,
) -> str:
    """Build a deterministic, trial-scoped entity key."""
    return f"{table}:{nct_id}:{source_id}"


def _build_trial_node(
    row: dict[str, Any],
) -> dict[str, Any]:
    """Build a Trial node from a source record."""
    nct_id = row["nct_id"]

    return {
        "key": f"trial:{nct_id}",
        "label": "Trial",
        "properties": {
            "nct_id": nct_id,
            **row,
        },
    }


def _build_entity_node(
    table: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    """Build a trial-scoped entity node."""
    nct_id = row["nct_id"]
    source_id = row.get("id")

    if source_id is None:
        raise ValueError(
            f"Missing source ID in {table} "
            f"for trial {nct_id}"
        )

    label, _ = ENTITY_RELATIONSHIPS[table]

    return {
        "key": _entity_key(
            table,
            nct_id,
            source_id,
        ),
        "label": label,
        "properties": {
            "source_table": table,
            "source_id": source_id,
            "nct_id": nct_id,
            **row,
        },
    }


def _build_relationship(
    table: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    """Build a relationship from an entity to its Trial."""
    nct_id = row["nct_id"]
    source_id = row.get("id")

    if source_id is None:
        raise ValueError(
            f"Missing source ID in {table} "
            f"for trial {nct_id}"
        )

    _, relationship_type = ENTITY_RELATIONSHIPS[table]

    return {
        "type": relationship_type,
        "source": _entity_key(
            table,
            nct_id,
            source_id,
        ),
        "target": f"trial:{nct_id}",
        "properties": {
            "source_table": table,
            "source_id": source_id,
            "nct_id": nct_id,
        },
    }


def transform_aact_artifact(
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Transform an extracted AACT artifact into graph-ready data."""
    artifact = _load_artifact(artifact_path)

    metadata = artifact.get("metadata", {})
    tables = artifact.get("tables", {})

    nct_ids = set(metadata.get("nct_ids", []))
    study_rows = tables.get("studies", [])

    nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    node_keys: set[str] = set()
    relationship_keys: set[tuple[str, str, str]] = set()

    for row in study_rows:
        nct_id = row.get("nct_id")

        if nct_id not in nct_ids:
            raise ValueError(
                f"Unexpected trial ID in studies: {nct_id}"
            )

        node = _build_trial_node(row)
        node_key = node["key"]

        if node_key in node_keys:
            raise ValueError(
                f"Duplicate Trial node: {node_key}"
            )

        node_keys.add(node_key)
        nodes.append(node)

    for table in ENTITY_RELATIONSHIPS:
        for row in tables.get(table, []):
            nct_id = row.get("nct_id")

            if nct_id not in nct_ids:
                raise ValueError(
                    f"Unexpected trial ID in {table}: {nct_id}"
                )

            node = _build_entity_node(table, row)
            node_key = node["key"]

            if node_key in node_keys:
                raise ValueError(
                    f"Duplicate entity node: {node_key}"
                )

            node_keys.add(node_key)
            nodes.append(node)

            relationship = _build_relationship(table, row)

            relationship_key = (
                relationship["type"],
                relationship["source"],
                relationship["target"],
            )

            if relationship_key in relationship_keys:
                raise ValueError(
                    f"Duplicate relationship: {relationship_key}"
                )

            relationship_keys.add(relationship_key)
            relationships.append(relationship)

    return {
        "metadata": {
            "source_database": metadata.get(
                "source_database"
            ),
            "source_schema": metadata.get(
                "source_schema"
            ),
            "scope_limit": metadata.get(
                "scope_limit"
            ),
            "nct_ids": metadata.get("nct_ids", []),
        },
        "nodes": nodes,
        "relationships": relationships,
    }

# Change Start
def validate_transformation_preservation(
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Validate source field and null preservation."""
    artifact = _load_artifact(artifact_path)
    transformed = transform_aact_artifact(artifact_path)

    source_tables = artifact["tables"]
    nodes = transformed["nodes"]

    errors: list[dict[str, Any]] = []
    validated_records = 0

    for node in nodes:
        properties = node["properties"]
        label = node["label"]

        if label == "Trial":
            table = "studies"
            source_id = properties["nct_id"]
            source_rows = source_tables[table]

            matching_rows = [
                row
                for row in source_rows
                if row.get("nct_id") == source_id
            ]
        else:
            table = properties["source_table"]
            source_id = properties["source_id"]
            source_rows = source_tables[table]

            matching_rows = [
                row
                for row in source_rows
                if row.get("id") == source_id
                and row.get("nct_id") == properties["nct_id"]
            ]

        if len(matching_rows) != 1:
            errors.append({
                "node_key": node["key"],
                "error": "Expected exactly one source row",
                "matching_rows": len(matching_rows),
            })
            continue

        source_row = matching_rows[0]

        for field, source_value in source_row.items():
            transformed_value = properties.get(field)

            if field not in properties:
                errors.append({
                    "node_key": node["key"],
                    "field": field,
                    "error": "Missing transformed field",
                })
            elif transformed_value != source_value:
                errors.append({
                    "node_key": node["key"],
                    "field": field,
                    "error": "Value mismatch",
                    "source_value": source_value,
                    "transformed_value": transformed_value,
                })

        validated_records += 1

    return {
        "passed": not errors,
        "validated_records": validated_records,
        "error_count": len(errors),
        "errors": errors[:20],
    }
# Change End
# Change End