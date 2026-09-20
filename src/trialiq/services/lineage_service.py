"""Lineage extraction service for TrialIQ."""

from typing import Any

from trialiq.services.graph_query_service import query_trial_by_nct_id
from trialiq.services.query_intent import QueryIntent, QueryIntentRequest


LINEAGE_COLLECTIONS = (
    "trial",
    "conditions",
    "interventions",
    "sponsors",
    "facilities",
    "designs",
    "eligibilities",
)


def _as_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _lineage_record(collection: str, record: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "collection": collection,
        "record_index": index,
        "nct_id": record.get("nct_id"),
        "source_table": record.get("source_table"),
        "source_key": record.get("source_key"),
        "source_id": record.get("source_id"),
        "provenance_version": record.get("provenance_version"),
        "pipeline_run_id": record.get("pipeline_run_id"),
        "source_database": record.get("source_database"),
        "source_schema": record.get("source_schema"),
        "source_nct_id": record.get("source_nct_id"),
        "extracted_at_utc": record.get("extracted_at_utc"),
        "transformed_at_utc": record.get("transformed_at_utc"),
        "transformation_version": record.get("transformation_version"),
    }


def get_trial_lineage(nct_id: str) -> dict[str, Any]:
    """Return source-level lineage records for one validated trial."""
    validated = QueryIntentRequest(
        intent=QueryIntent.TRIAL_OVERVIEW,
        nct_id=nct_id,
    )
    normalized_nct_id = validated.nct_id
    graph_response = query_trial_by_nct_id(normalized_nct_id)

    records: list[dict[str, Any]] = []
    limitations: list[str] = []
    evidence = graph_response.evidence

    if isinstance(evidence, dict):
        for collection in LINEAGE_COLLECTIONS:
            for index, record in enumerate(_as_records(evidence.get(collection))):
                records.append(_lineage_record(collection, record, index))
    else:
        limitations.append("No graph evidence was available for lineage extraction.")

    if not records and graph_response.status.value == "SUCCESS":
        limitations.append("The validated graph response contained no lineage records.")

    return {
        "status": graph_response.status.value,
        "nct_id": normalized_nct_id,
        "source_count": len(records),
        "records": records,
        "validation": graph_response.validation.model_dump(),
        "limitations": limitations,
    }
