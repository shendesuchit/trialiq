"""End-to-end provenance helpers for TrialIQ ETL artifacts.

This module enriches the existing transformed artifact without changing the
existing graph schema or query behavior. Provenance is stored as scalar
Neo4j-compatible properties on nodes and relationships.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROVENANCE_VERSION = "provenance-v1"


def new_run_id() -> str:
    """Create a unique identifier for one extraction/transformation/load run."""
    return str(uuid4())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_provenance(node: dict[str, Any], metadata: dict[str, Any], run_id: str) -> dict[str, Any]:
    properties = node.get("properties", {})
    label = node.get("label")
    if label == "Trial":
        source_table = "studies"
        source_id = properties.get("nct_id")
    else:
        source_table = properties.get("source_table")
        source_id = properties.get("source_id")

    return {
        "provenance_version": PROVENANCE_VERSION,
        "pipeline_run_id": run_id,
        "source_database": metadata.get("source_database"),
        "source_schema": metadata.get("source_schema"),
        "source_table": source_table,
        "source_id": source_id,
        "source_nct_id": properties.get("nct_id"),
        "source_key": node.get("key"),
        "extracted_at_utc": metadata.get("extracted_at_utc"),
        "transformed_at_utc": _utc_now(),
        "transformation_version": PROVENANCE_VERSION,
    }


def _relationship_provenance(
    relationship: dict[str, Any], metadata: dict[str, Any], run_id: str
) -> dict[str, Any]:
    properties = relationship.get("properties", {})
    return {
        "provenance_version": PROVENANCE_VERSION,
        "pipeline_run_id": run_id,
        "source_database": metadata.get("source_database"),
        "source_schema": metadata.get("source_schema"),
        "source_table": properties.get("source_table"),
        "source_id": properties.get("source_id"),
        "source_nct_id": properties.get("nct_id"),
        "source_key": relationship.get("source"),
        "transformed_at_utc": _utc_now(),
        "transformation_version": PROVENANCE_VERSION,
    }


def enrich_transformed_artifact(
    transformed: dict[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Return a provenance-enriched copy of a transformed artifact."""
    metadata = deepcopy(transformed.get("metadata", {}))
    resolved_run_id = run_id or new_run_id()
    enriched = deepcopy(transformed)
    enriched_metadata = {
        **metadata,
        "provenance_version": PROVENANCE_VERSION,
        "pipeline_run_id": resolved_run_id,
        "provenance_created_at_utc": _utc_now(),
    }
    enriched["metadata"] = enriched_metadata

    for node in enriched.get("nodes", []):
        node.setdefault("properties", {}).update(
            {
                key: value
                for key, value in _node_provenance(node, metadata, resolved_run_id).items()
                if value is not None
            }
        )

    for relationship in enriched.get("relationships", []):
        relationship.setdefault("properties", {}).update(
            {
                key: value
                for key, value in _relationship_provenance(
                    relationship, metadata, resolved_run_id
                ).items()
                if value is not None
            }
        )

    return enriched


def write_provenance_artifact(
    transformed: dict[str, Any],
    output_path: str | Path,
    *,
    run_id: str | None = None,
) -> Path:
    """Enrich and write a transformed artifact with provenance metadata."""
    import json

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    enriched = enrich_transformed_artifact(transformed, run_id=run_id)
    output.write_text(
        json.dumps(enriched, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return output
