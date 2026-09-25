"""Lineage extraction service for TrialIQ."""

import re
from typing import Any

from trialiq.services.graph_query_service import query_related_trials, query_trial_by_nct_id
from trialiq.services.graph_view_models import (
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphRelationshipType,
    GraphView,
)
from trialiq.services.models import GraphQueryStatus
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

_RELATIONSHIP_TO_NODE_TYPE = {
    GraphRelationshipType.HAS_CONDITION.value: GraphNodeType.CONDITION,
    GraphRelationshipType.HAS_INTERVENTION.value: GraphNodeType.INTERVENTION,
    GraphRelationshipType.SPONSORED_BY.value: GraphNodeType.SPONSOR,
}


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


def _slug(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return normalized[:96] or "unknown"


def _provenance_keys(record: dict[str, Any]) -> list[str]:
    value = record.get("source_key")
    return [str(value)] if value not in (None, "") else []


def _trial_node(nct_id: str, trial: dict[str, Any] | None, hop: int) -> GraphNode:
    metadata = dict(trial or {})
    metadata.setdefault("nct_id", nct_id)
    return GraphNode(
        id=f"trial:{nct_id}",
        type=GraphNodeType.TRIAL,
        label=nct_id,
        hop=hop,
        metadata=metadata,
        provenance_keys=_provenance_keys(metadata),
    )


def _entity_identity(relationship_type: str, entity: dict[str, Any]) -> tuple[GraphNodeType, str, str]:
    node_type = _RELATIONSHIP_TO_NODE_TYPE[relationship_type]
    identity = (
        entity.get("normalized_name")
        or entity.get("downcase_name")
        or entity.get("name")
        or entity.get("source_key")
        or entity.get("source_id")
        or "unknown"
    )
    label = str(entity.get("name") or entity.get("normalized_name") or entity.get("downcase_name") or identity)
    return node_type, f"{node_type.value}:{_slug(identity)}", label


def get_trial_graph_view(
    nct_id: str,
    *,
    max_hops: int = 1,
    per_hop_limit: int = 20,
    limit: int = 40,
) -> GraphView:
    """Return a stable node/edge DTO for bounded related-trial visualization.

    The browser receives only evidence-backed nodes and edges. Traversal remains
    deterministic and bounded in the existing graph query service.
    """
    validated = QueryIntentRequest(
        intent=QueryIntent.RELATED_TRIALS,
        nct_id=nct_id,
        max_hops=max_hops,
        per_hop_limit=per_hop_limit,
        limit=limit,
    )
    normalized_nct_id = validated.nct_id

    seed_response = query_trial_by_nct_id(normalized_nct_id)
    seed_evidence = seed_response.evidence if isinstance(seed_response.evidence, dict) else None
    seed_trial = seed_evidence.get("trial") if seed_evidence else None

    if seed_response.status != GraphQueryStatus.SUCCESS or not isinstance(seed_trial, dict):
        return GraphView(
            status=seed_response.status,
            seed_node=None,
            max_hops=max_hops,
            per_hop_limit=per_hop_limit,
            limit=limit,
            match_count=0,
            truncated=False,
            validation=seed_response.validation,
            limitations=["The seed trial was not available for graph visualization."],
        )

    seed_node = _trial_node(normalized_nct_id, seed_trial, 0)
    nodes: dict[str, GraphNode] = {seed_node.id: seed_node}
    edges: dict[str, GraphEdge] = {}
    limitations: list[str] = []

    related = query_related_trials(
        normalized_nct_id,
        max_hops=max_hops,
        per_hop_limit=per_hop_limit,
        limit=limit,
    )

    if related.status in {GraphQueryStatus.EXECUTION_ERROR, GraphQueryStatus.VALIDATION_FAILED}:
        return GraphView(
            status=related.status,
            seed_node=seed_node.id,
            nodes=list(nodes.values()),
            max_hops=max_hops,
            per_hop_limit=per_hop_limit,
            limit=limit,
            match_count=0,
            truncated=False,
            related_status=related.status,
            validation=related.validation,
            limitations=["Related-trial graph traversal could not be completed."],
        )

    for match in related.matches:
        related_node = _trial_node(match.nct_id, match.trial, match.discovery_hop)
        nodes[related_node.id] = related_node

        for path_index, path in enumerate(match.connected_via):
            relationship_type = path.relationship_type
            if relationship_type not in _RELATIONSHIP_TO_NODE_TYPE:
                continue
            entity = dict(path.entity or {})
            node_type, entity_id, entity_label = _entity_identity(relationship_type, entity)
            entity_node = GraphNode(
                id=entity_id,
                type=node_type,
                label=entity_label,
                hop=match.discovery_hop,
                metadata=entity,
                provenance_keys=_provenance_keys(entity),
            )
            nodes.setdefault(entity_id, entity_node)

            source_trial_id = f"trial:{path.source_nct_id}"
            if source_trial_id not in nodes:
                nodes[source_trial_id] = _trial_node(
                    path.source_nct_id,
                    None,
                    max(match.discovery_hop - 1, 0),
                )

            evidence_keys = _provenance_keys(entity)
            relationship = GraphRelationshipType(relationship_type)
            for trial_id, suffix in ((source_trial_id, "source"), (related_node.id, "target")):
                edge_id = f"{trial_id}|{relationship.value}|{entity_id}|{match.discovery_hop}|{suffix}"
                edges.setdefault(
                    edge_id,
                    GraphEdge(
                        id=edge_id,
                        source=trial_id,
                        target=entity_id,
                        relationship=relationship,
                        hop=match.discovery_hop,
                        evidence_keys=evidence_keys,
                    ),
                )

    if not related.matches:
        limitations.append("No related trials were found within the configured graph search bounds.")

    return GraphView(
        status=GraphQueryStatus.SUCCESS,
        seed_node=seed_node.id,
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        max_hops=max_hops,
        per_hop_limit=per_hop_limit,
        limit=limit,
        match_count=len(related.matches),
        truncated=len(related.matches) >= limit,
        related_status=related.status,
        validation=related.validation,
        limitations=limitations,
    )
