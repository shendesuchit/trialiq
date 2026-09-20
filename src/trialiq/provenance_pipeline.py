"""Coordinated AACT extraction, transformation, provenance, and loading."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trialiq.etl.aact_extract import extract_aact_dataset
from trialiq.etl.aact_transform import transform_aact_artifact
from trialiq.etl.neo4j_load import load_transformed_artifact
from trialiq.provenance import new_run_id, write_provenance_artifact


def run_provenance_pipeline(
    *,
    limit: int = 100,
    extracted_path: str | Path = "data/extracted/aact_provenance.json",
    transformed_path: str | Path = "data/transformed/aact_provenance.json",
    load_into_neo4j: bool = True,
) -> dict[str, Any]:
    """Run extraction -> transformation -> provenance -> optional Neo4j load."""
    run_id = new_run_id()
    extracted = extract_aact_dataset(limit=limit, output_path=extracted_path)
    with Path(extracted).open("r", encoding="utf-8") as handle:
        extracted_artifact = json.load(handle)

    transformed = transform_aact_artifact(extracted)
    transformed["metadata"]["extracted_at_utc"] = extracted_artifact.get("metadata", {}).get(
        "extracted_at_utc"
    )
    transformed_output = write_provenance_artifact(
        transformed,
        transformed_path,
        run_id=run_id,
    )

    result: dict[str, Any] = {
        "pipeline_run_id": run_id,
        "extracted_artifact": str(extracted),
        "transformed_artifact": str(transformed_output),
        "nodes": len(transformed.get("nodes", [])),
        "relationships": len(transformed.get("relationships", [])),
        "loaded": False,
    }

    if load_into_neo4j:
        result["load_result"] = load_transformed_artifact(transformed_output)
        result["loaded"] = True

    return result
