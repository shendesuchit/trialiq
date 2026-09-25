"""Deterministic, read-only realistic-scenario discovery for Batch 15.

The qualification layer is intentionally outside the product request path.  It
uses fixed Cypher to discover representative source-backed seeds from the loaded
canonical graph, then the Batch-15 runner exercises those seeds through the real
MCP retrieval client and normal agent workflow.

No scenario uses an LLM to construct Cypher or choose graph topology.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from trialiq.services.models import GraphQueryStatus, RelatedTrialSearchResponse


CORE_RELATIONSHIP_TYPES = (
    "HAS_CONDITION",
    "HAS_INTERVENTION",
    "SPONSORED_BY",
)


class ReadConnection(Protocol):
    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class ScenarioCandidate:
    """One source-backed scenario seed selected from the canonical graph."""

    scenario: str
    scenario_family: str
    entity_type: str
    relationship_type: str
    entity_name: str
    canonical_key: str
    entity_fanout: int
    seed_nct_id: str
    brief_title: str | None
    overall_status: str | None
    study_type: str | None
    phase: str | None
    enrollment: int | None
    selection_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_NAMED_SPECS: tuple[dict[str, Any], ...] = (
    {
        "scenario": "oncology_condition",
        "scenario_family": "therapeutic_area",
        "entity_type": "condition",
        "relationship_type": "HAS_CONDITION",
        "preferred_names": [
            "breast cancer",
            "lung cancer",
            "prostate cancer",
            "colorectal cancer",
        ],
        "selection_reason": "Common oncology condition with many source-backed connected studies.",
    },
    {
        "scenario": "cardiovascular_condition",
        "scenario_family": "therapeutic_area",
        "entity_type": "condition",
        "relationship_type": "HAS_CONDITION",
        "preferred_names": [
            "heart failure",
            "hypertension",
            "coronary artery disease",
            "cardiovascular diseases",
        ],
        "selection_reason": "Cardiovascular condition suitable for related-study comparison.",
    },
    {
        "scenario": "metabolic_condition",
        "scenario_family": "therapeutic_area",
        "entity_type": "condition",
        "relationship_type": "HAS_CONDITION",
        "preferred_names": [
            "diabetes mellitus, type 2",
            "obesity",
            "diabetes",
        ],
        "selection_reason": "Metabolic condition with broad but bounded canonical connectivity.",
    },
    {
        "scenario": "infectious_condition",
        "scenario_family": "therapeutic_area",
        "entity_type": "condition",
        "relationship_type": "HAS_CONDITION",
        "preferred_names": [
            "covid-19",
            "hiv infections",
        ],
        "selection_reason": "Infectious-disease condition with multiple realistic study neighbors.",
    },
    {
        "scenario": "major_sponsor",
        "scenario_family": "sponsor",
        "entity_type": "sponsor",
        "relationship_type": "SPONSORED_BY",
        "preferred_names": [
            "national cancer institute (nci)",
            "pfizer",
            "astrazeneca",
            "mayo clinic",
        ],
        "selection_reason": "High-volume sponsor used to exercise hub-aware sponsor traversal.",
    },
    {
        "scenario": "common_drug",
        "scenario_family": "intervention",
        "entity_type": "intervention",
        "relationship_type": "HAS_INTERVENTION",
        "preferred_names": [
            "metformin",
            "pembrolizumab",
            "cisplatin",
            "paclitaxel",
        ],
        "selection_reason": "Common named intervention with many source-backed study connections.",
    },
)


_ENTITY_SPECS = {
    "condition": ("Condition", "HAS_CONDITION"),
    "intervention": ("Intervention", "HAS_INTERVENTION"),
    "sponsor": ("Sponsor", "SPONSORED_BY"),
}


def graph_inventory(connection: ReadConnection) -> dict[str, int]:
    """Return compact canonical graph counts used as Batch-15 preconditions."""
    queries = {
        "trials": "MATCH (node:Trial) RETURN count(node) AS count",
        "conditions": (
            "MATCH (node:Condition) WHERE node.canonical = true "
            "AND node.canonical_key IS NOT NULL RETURN count(node) AS count"
        ),
        "interventions": (
            "MATCH (node:Intervention) WHERE node.canonical = true "
            "AND node.canonical_key IS NOT NULL RETURN count(node) AS count"
        ),
        "sponsors": (
            "MATCH (node:Sponsor) WHERE node.canonical = true "
            "AND node.canonical_key IS NOT NULL RETURN count(node) AS count"
        ),
        "condition_relationships": (
            "MATCH (:Condition)-[rel:HAS_CONDITION]->(:Trial) "
            "RETURN count(rel) AS count"
        ),
        "intervention_relationships": (
            "MATCH (:Intervention)-[rel:HAS_INTERVENTION]->(:Trial) "
            "RETURN count(rel) AS count"
        ),
        "sponsor_relationships": (
            "MATCH (:Sponsor)-[rel:SPONSORED_BY]->(:Trial) "
            "RETURN count(rel) AS count"
        ),
    }
    counts: dict[str, int] = {}
    for key, query in queries.items():
        rows = connection.execute_read(query)
        counts[key] = int(rows[0]["count"]) if rows else 0
    return counts


def _trial_projection() -> str:
    return (
        "trial.nct_id AS seed_nct_id, "
        "trial.brief_title AS brief_title, "
        "trial.overall_status AS overall_status, "
        "trial.study_type AS study_type, "
        "trial.phase AS phase, "
        "trial.enrollment AS enrollment"
    )


def _named_entity_candidate(
    connection: ReadConnection,
    *,
    scenario: str,
    scenario_family: str,
    entity_type: str,
    relationship_type: str | None = None,
    preferred_names: list[str],
    selection_reason: str,
) -> ScenarioCandidate | None:
    label, relationship = _ENTITY_SPECS[entity_type]
    if relationship_type is not None and relationship_type != relationship:
        raise ValueError("Scenario relationship type does not match entity type.")
    query = f"""
    UNWIND range(0, size($preferred_names) - 1) AS preferred_index
    WITH preferred_index, $preferred_names[preferred_index] AS preferred_name
    MATCH (entity:{label} {{normalized_name: preferred_name}})-[:{relationship}]->(trial:Trial)
    WHERE entity.canonical = true
      AND entity.canonical_key IS NOT NULL
      AND coalesce(entity.loaded_trial_count, 0) > 1
    RETURN preferred_index,
           entity.normalized_name AS entity_name,
           entity.canonical_key AS canonical_key,
           coalesce(entity.loaded_trial_count, 0) AS entity_fanout,
           {_trial_projection()}
    ORDER BY preferred_index, trial.nct_id
    LIMIT 1
    """
    rows = connection.execute_read(query, {"preferred_names": preferred_names})
    if not rows:
        return None
    row = rows[0]
    return ScenarioCandidate(
        scenario=scenario,
        scenario_family=scenario_family,
        entity_type=entity_type,
        relationship_type=relationship,
        entity_name=str(row["entity_name"]),
        canonical_key=str(row["canonical_key"]),
        entity_fanout=int(row.get("entity_fanout") or 0),
        seed_nct_id=str(row["seed_nct_id"]),
        brief_title=row.get("brief_title"),
        overall_status=row.get("overall_status"),
        study_type=row.get("study_type"),
        phase=row.get("phase"),
        enrollment=(
            int(row["enrollment"]) if row.get("enrollment") is not None else None
        ),
        selection_reason=selection_reason,
    )


def _behavioral_candidate(connection: ReadConnection) -> ScenarioCandidate | None:
    query = f"""
    MATCH (entity:Intervention)-[:HAS_INTERVENTION]->(trial:Trial)
    WHERE entity.canonical = true
      AND entity.canonical_key IS NOT NULL
      AND toUpper(coalesce(entity.intervention_type, '')) = 'BEHAVIORAL'
      AND coalesce(entity.loaded_trial_count, 0) >= 5
      AND coalesce(entity.loaded_trial_count, 0) <= 500
    RETURN entity.normalized_name AS entity_name,
           entity.canonical_key AS canonical_key,
           coalesce(entity.loaded_trial_count, 0) AS entity_fanout,
           {_trial_projection()}
    ORDER BY entity_fanout DESC, canonical_key, trial.nct_id
    LIMIT 1
    """
    rows = connection.execute_read(query)
    if not rows:
        return None
    row = rows[0]
    return ScenarioCandidate(
        scenario="behavioral_intervention",
        scenario_family="intervention",
        entity_type="intervention",
        relationship_type="HAS_INTERVENTION",
        entity_name=str(row["entity_name"]),
        canonical_key=str(row["canonical_key"]),
        entity_fanout=int(row.get("entity_fanout") or 0),
        seed_nct_id=str(row["seed_nct_id"]),
        brief_title=row.get("brief_title"),
        overall_status=row.get("overall_status"),
        study_type=row.get("study_type"),
        phase=row.get("phase"),
        enrollment=(
            int(row["enrollment"]) if row.get("enrollment") is not None else None
        ),
        selection_reason=(
            "Behavioral intervention with moderate shared-study fan-out, selected "
            "from the loaded source rather than a hard-coded NCT ID."
        ),
    )


def _observational_candidate(connection: ReadConnection) -> ScenarioCandidate | None:
    query = f"""
    MATCH (entity:Condition)-[:HAS_CONDITION]->(trial:Trial)
    WHERE entity.canonical = true
      AND entity.canonical_key IS NOT NULL
      AND trial.study_type = 'OBSERVATIONAL'
      AND coalesce(entity.loaded_trial_count, 0) >= 10
      AND coalesce(entity.loaded_trial_count, 0) <= 500
    RETURN entity.normalized_name AS entity_name,
           entity.canonical_key AS canonical_key,
           coalesce(entity.loaded_trial_count, 0) AS entity_fanout,
           {_trial_projection()}
    ORDER BY entity_fanout DESC, canonical_key, trial.nct_id
    LIMIT 1
    """
    rows = connection.execute_read(query)
    if not rows:
        return None
    row = rows[0]
    return ScenarioCandidate(
        scenario="observational_study",
        scenario_family="study_design",
        entity_type="condition",
        relationship_type="HAS_CONDITION",
        entity_name=str(row["entity_name"]),
        canonical_key=str(row["canonical_key"]),
        entity_fanout=int(row.get("entity_fanout") or 0),
        seed_nct_id=str(row["seed_nct_id"]),
        brief_title=row.get("brief_title"),
        overall_status=row.get("overall_status"),
        study_type=row.get("study_type"),
        phase=row.get("phase"),
        enrollment=(
            int(row["enrollment"]) if row.get("enrollment") is not None else None
        ),
        selection_reason=(
            "Observational trial connected through a moderately shared condition, "
            "used to verify graceful comparison when intervention metadata may differ."
        ),
    )


def _rare_condition_candidate(connection: ReadConnection) -> ScenarioCandidate | None:
    query = f"""
    MATCH (entity:Condition)-[:HAS_CONDITION]->(trial:Trial)
    WHERE entity.canonical = true
      AND entity.canonical_key IS NOT NULL
      AND coalesce(entity.loaded_trial_count, 0) >= 2
      AND coalesce(entity.loaded_trial_count, 0) <= 5
    RETURN entity.normalized_name AS entity_name,
           entity.canonical_key AS canonical_key,
           coalesce(entity.loaded_trial_count, 0) AS entity_fanout,
           {_trial_projection()}
    ORDER BY entity_fanout ASC, canonical_key, trial.nct_id
    LIMIT 1
    """
    rows = connection.execute_read(query)
    if not rows:
        return None
    row = rows[0]
    return ScenarioCandidate(
        scenario="rare_specific_condition",
        scenario_family="specificity",
        entity_type="condition",
        relationship_type="HAS_CONDITION",
        entity_name=str(row["entity_name"]),
        canonical_key=str(row["canonical_key"]),
        entity_fanout=int(row.get("entity_fanout") or 0),
        seed_nct_id=str(row["seed_nct_id"]),
        brief_title=row.get("brief_title"),
        overall_status=row.get("overall_status"),
        study_type=row.get("study_type"),
        phase=row.get("phase"),
        enrollment=(
            int(row["enrollment"]) if row.get("enrollment") is not None else None
        ),
        selection_reason=(
            "Low-fan-out condition selected to demonstrate a highly specific graph connection."
        ),
    )


def _placebo_hub_candidate(connection: ReadConnection) -> ScenarioCandidate | None:
    query = f"""
    MATCH (entity:Intervention {{canonical_key: 'placebo|drug'}})-[:HAS_INTERVENTION]->(trial:Trial)
    WHERE entity.canonical = true
      AND coalesce(entity.loaded_trial_count, 0) > 1000
    MATCH (all_interventions:Intervention)-[:HAS_INTERVENTION]->(trial)
    WITH entity, trial, count(DISTINCT all_interventions) AS intervention_count
    WHERE intervention_count = 1
    RETURN entity.normalized_name AS entity_name,
           entity.canonical_key AS canonical_key,
           coalesce(entity.loaded_trial_count, 0) AS entity_fanout,
           {_trial_projection()}
    ORDER BY trial.nct_id
    LIMIT 1
    """
    rows = connection.execute_read(query)
    if not rows:
        return None
    row = rows[0]
    return ScenarioCandidate(
        scenario="high_fanout_placebo",
        scenario_family="hub_stress",
        entity_type="intervention",
        relationship_type="HAS_INTERVENTION",
        entity_name=str(row["entity_name"]),
        canonical_key=str(row["canonical_key"]),
        entity_fanout=int(row.get("entity_fanout") or 0),
        seed_nct_id=str(row["seed_nct_id"]),
        brief_title=row.get("brief_title"),
        overall_status=row.get("overall_status"),
        study_type=row.get("study_type"),
        phase=row.get("phase"),
        enrollment=(
            int(row["enrollment"]) if row.get("enrollment") is not None else None
        ),
        selection_reason=(
            "Known extreme intervention hub used to prove that Batch-14 bounds hold on the full graph."
        ),
    )


def discover_batch15_candidates(connection: ReadConnection) -> list[ScenarioCandidate]:
    """Discover the representative Batch-15 scenario set from the loaded graph."""
    candidates: list[ScenarioCandidate] = []
    for spec in _NAMED_SPECS:
        candidate = _named_entity_candidate(connection, **spec)
        if candidate is not None:
            candidates.append(candidate)

    for factory in (
        _behavioral_candidate,
        _observational_candidate,
        _rare_condition_candidate,
        _placebo_hub_candidate,
    ):
        candidate = factory(connection)
        if candidate is not None:
            candidates.append(candidate)

    return sorted(candidates, key=lambda item: item.scenario)


def validate_related_response(response: RelatedTrialSearchResponse) -> list[str]:
    """Return deterministic consistency errors for a related-trial response."""
    errors: list[str] = []
    if response.status not in {GraphQueryStatus.SUCCESS, GraphQueryStatus.NOT_FOUND}:
        errors.append(f"Unexpected related-trial status: {response.status.value}")
        return errors

    if len(response.matches) > response.limit:
        errors.append("Related-trial result exceeded its global limit.")
    if len(response.matches) > response.per_hop_limit * response.max_hops:
        errors.append("Related-trial result exceeded the configured per-hop bound.")

    nct_ids = [match.nct_id for match in response.matches]
    if len(nct_ids) != len(set(nct_ids)):
        errors.append("Related-trial response contains duplicate NCT IDs.")
    if response.seed_nct_id in nct_ids:
        errors.append("Related-trial response included the seed trial.")

    aggregate_evidence_paths = 0
    aggregate_entity_ids: set[str] = set()
    condition_linked = 0
    intervention_linked = 0
    sponsor_linked = 0
    multi_factor = 0

    for match in response.matches:
        metrics = match.metrics
        if metrics is None:
            errors.append(f"Missing deterministic metrics for {match.nct_id}.")
            continue
        expected_path_count = len(match.connected_via)
        if metrics.evidence_path_count != expected_path_count:
            errors.append(
                f"Evidence-path count mismatch for {match.nct_id}: "
                f"{metrics.evidence_path_count} != {expected_path_count}."
            )
        expected_total = (
            metrics.shared_condition_count
            + metrics.shared_intervention_count
            + metrics.shared_sponsor_count
        )
        if metrics.total_shared_entity_count != expected_total:
            errors.append(
                f"Shared-entity count mismatch for {match.nct_id}: "
                f"{metrics.total_shared_entity_count} != {expected_total}."
            )
        if len(metrics.entity_ids) != len(set(metrics.entity_ids)):
            errors.append(f"Duplicate metric entity IDs for {match.nct_id}.")

        aggregate_evidence_paths += metrics.evidence_path_count
        aggregate_entity_ids.update(metrics.entity_ids)
        condition_linked += int(metrics.shared_condition_count > 0)
        intervention_linked += int(metrics.shared_intervention_count > 0)
        sponsor_linked += int(metrics.shared_sponsor_count > 0)
        multi_factor += int(metrics.total_shared_entity_count > 1)

    aggregate = response.metrics
    expected_aggregate = {
        "related_trial_count": len(response.matches),
        "unique_shared_entity_count": len(aggregate_entity_ids),
        "evidence_path_count": aggregate_evidence_paths,
        "condition_linked_trial_count": condition_linked,
        "intervention_linked_trial_count": intervention_linked,
        "sponsor_linked_trial_count": sponsor_linked,
        "multi_factor_trial_count": multi_factor,
    }
    for field, expected in expected_aggregate.items():
        actual = int(getattr(aggregate, field))
        if actual != expected:
            errors.append(f"Aggregate {field} mismatch: {actual} != {expected}.")

    return errors


def summarize_related_response(response: RelatedTrialSearchResponse) -> dict[str, Any]:
    """Return a compact, non-sensitive diagnostic view for the Batch-15 report."""
    evidence: list[dict[str, Any]] = []
    for match in response.matches:
        evidence.append(
            {
                "nct_id": match.nct_id,
                "discovery_hop": match.discovery_hop,
                "overall_status": match.trial.get("overall_status"),
                "shared_entities": [
                    {
                        "relationship_type": path.relationship_type,
                        "canonical_key": path.entity.get("canonical_key"),
                        "normalized_name": path.entity.get("normalized_name"),
                        "fanout": path.entity.get("loaded_trial_count"),
                    }
                    for path in match.connected_via
                ],
                "metrics": match.metrics.model_dump() if match.metrics else None,
            }
        )
    return {
        "status": response.status.value,
        "seed_nct_id": response.seed_nct_id,
        "max_hops": response.max_hops,
        "per_hop_limit": response.per_hop_limit,
        "limit": response.limit,
        "returned": len(response.matches),
        "relationship_types": response.relationship_types,
        "overall_statuses": response.overall_statuses,
        "aggregate_metrics": response.metrics.model_dump(),
        "matches": evidence,
    }
