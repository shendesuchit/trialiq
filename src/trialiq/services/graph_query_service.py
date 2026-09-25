"""Read-only graph query service for TrialIQ."""

import logging

from trialiq.chains.cypher_qa import (
    find_related_trials_bounded,
    find_shared_trial_entities,
    get_trial_graph,
    search_trials_by_condition,
    search_trials_by_intervention,
    search_trials_by_sponsor,
)
from trialiq.services.models import (
    ConditionSearchResponse,
    ConditionSearchStatus,
    ConditionTrialMatch,
    EntitySearchResponse,
    EntitySearchStatus,
    EntityTrialMatch,
    GraphQueryResponse,
    GraphQueryStatus,
    RelatedTrialAggregateMetrics,
    RelatedTrialMatch,
    RelatedTrialSearchResponse,
    SharedEntityComparisonResponse,
    SharedEntityMatch,
    ValidationResult,
)
from trialiq.services.related_trial_metrics import (
    build_related_trial_metrics,
    stable_entity_id,
)
from trialiq.validation.evidence import validate_trial_evidence


logger = logging.getLogger(__name__)


def query_trial_by_nct_id(nct_id: str) -> GraphQueryResponse:
    """Retrieve and validate graph evidence for a clinical trial."""
    try:
        evidence = get_trial_graph(nct_id)
        validation = validate_trial_evidence(
            evidence=evidence,
            requested_nct_id=nct_id,
        )
        validation_result = ValidationResult(**validation)
        if evidence.get("found") is not True:
            status = GraphQueryStatus.NOT_FOUND
        elif not validation_result.valid:
            status = GraphQueryStatus.VALIDATION_FAILED
        else:
            status = GraphQueryStatus.SUCCESS
        return GraphQueryResponse(
            status=status,
            nct_id=nct_id,
            evidence=evidence,
            validation=validation_result,
        )
    except Exception as exc:
        return GraphQueryResponse(
            status=GraphQueryStatus.EXECUTION_ERROR,
            nct_id=nct_id,
            evidence=None,
            validation=ValidationResult(
                valid=False,
                errors=[f"Graph query execution failed: {exc}"],
                warnings=[],
            ),
        )


def query_trials_by_condition(
    condition: str,
    limit: int = 20,
) -> ConditionSearchResponse:
    """Retrieve trials using deterministic exact condition matching."""
    normalized = condition.strip().casefold()
    if not normalized:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.VALIDATION_FAILED,
            condition=normalized,
            limit=limit,
            matches=[],
            validation=ValidationResult(
                valid=False,
                errors=["Condition cannot be empty."],
                warnings=[],
            ),
        )
    if not 1 <= limit <= 100:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.VALIDATION_FAILED,
            condition=normalized,
            limit=limit,
            matches=[],
            validation=ValidationResult(
                valid=False,
                errors=["Limit must be between 1 and 100."],
                warnings=[],
            ),
        )
    try:
        result = search_trials_by_condition(normalized, limit)
        matches = [
            ConditionTrialMatch(**match)
            for match in result["matches"]
        ]
        found = bool(matches)
        return ConditionSearchResponse(
            status=(
                ConditionSearchStatus.SUCCESS
                if found
                else ConditionSearchStatus.NOT_FOUND
            ),
            condition=normalized,
            limit=limit,
            matches=matches,
            validation=ValidationResult(valid=True, errors=[], warnings=[]),
        )
    except Exception as exc:
        return ConditionSearchResponse(
            status=ConditionSearchStatus.EXECUTION_ERROR,
            condition=normalized,
            limit=limit,
            matches=[],
            validation=ValidationResult(
                valid=False,
                errors=[f"Condition search execution failed: {exc}"],
                warnings=[],
            ),
        )


def _query_trials_by_named_entity(
    entity_type: str,
    value: str,
    limit: int,
) -> EntitySearchResponse:
    normalized = value.strip().casefold()
    if not normalized:
        return EntitySearchResponse(
            status=EntitySearchStatus.VALIDATION_FAILED,
            entity_type=entity_type,
            query=normalized,
            limit=limit,
            validation=ValidationResult(
                valid=False,
                errors=[f"{entity_type.title()} cannot be empty."],
            ),
        )
    if not 1 <= limit <= 100:
        return EntitySearchResponse(
            status=EntitySearchStatus.VALIDATION_FAILED,
            entity_type=entity_type,
            query=normalized,
            limit=limit,
            validation=ValidationResult(
                valid=False,
                errors=["Limit must be between 1 and 100."],
            ),
        )

    lookup = {
        "intervention": search_trials_by_intervention,
        "sponsor": search_trials_by_sponsor,
    }[entity_type]
    try:
        result = lookup(normalized, limit)
        matches = [EntityTrialMatch(**match) for match in result["matches"]]
        return EntitySearchResponse(
            status=(EntitySearchStatus.SUCCESS if matches else EntitySearchStatus.NOT_FOUND),
            entity_type=entity_type,
            query=normalized,
            limit=limit,
            matches=matches,
            validation=ValidationResult(valid=True),
        )
    except Exception:
        logger.exception("Graph entity search failed for %s", entity_type)
        return EntitySearchResponse(
            status=EntitySearchStatus.EXECUTION_ERROR,
            entity_type=entity_type,
            query=normalized,
            limit=limit,
            validation=ValidationResult(
                valid=False,
                errors=["Graph entity search failed because of an unexpected internal error."],
            ),
        )


def query_trials_by_intervention(
    intervention: str,
    limit: int = 20,
) -> EntitySearchResponse:
    """Retrieve trials by a bounded exact intervention-name match."""
    return _query_trials_by_named_entity("intervention", intervention, limit)


def query_trials_by_sponsor(
    sponsor: str,
    limit: int = 20,
) -> EntitySearchResponse:
    """Retrieve trials by a bounded exact sponsor-name match."""
    return _query_trials_by_named_entity("sponsor", sponsor, limit)


def query_shared_entities_between_trials(
    nct_id_a: str,
    nct_id_b: str,
    limit_per_type: int = 20,
) -> SharedEntityComparisonResponse:
    """Retrieve bounded shared named entities between two trials."""
    normalized_a = nct_id_a.strip().upper()
    normalized_b = nct_id_b.strip().upper()
    nct_pattern_error = "NCT ID must use the format NCT followed by exactly 8 digits."
    for value in (normalized_a, normalized_b):
        if not (len(value) == 11 and value.startswith("NCT") and value[3:].isdigit()):
            return SharedEntityComparisonResponse(
                status=GraphQueryStatus.VALIDATION_FAILED,
                nct_id_a=normalized_a,
                nct_id_b=normalized_b,
                limit_per_type=limit_per_type,
                validation=ValidationResult(valid=False, errors=[nct_pattern_error]),
            )
    if normalized_a == normalized_b:
        return SharedEntityComparisonResponse(
            status=GraphQueryStatus.VALIDATION_FAILED,
            nct_id_a=normalized_a,
            nct_id_b=normalized_b,
            limit_per_type=limit_per_type,
            validation=ValidationResult(
                valid=False,
                errors=["Two different NCT IDs are required for comparison."],
            ),
        )
    if not 1 <= limit_per_type <= 50:
        return SharedEntityComparisonResponse(
            status=GraphQueryStatus.VALIDATION_FAILED,
            nct_id_a=normalized_a,
            nct_id_b=normalized_b,
            limit_per_type=limit_per_type,
            validation=ValidationResult(
                valid=False,
                errors=["limit_per_type must be between 1 and 50."],
            ),
        )

    try:
        result = find_shared_trial_entities(normalized_a, normalized_b, limit_per_type)
        if not result["found_a"] or not result["found_b"]:
            missing = []
            if not result["found_a"]:
                missing.append(normalized_a)
            if not result["found_b"]:
                missing.append(normalized_b)
            return SharedEntityComparisonResponse(
                status=GraphQueryStatus.NOT_FOUND,
                nct_id_a=normalized_a,
                nct_id_b=normalized_b,
                limit_per_type=limit_per_type,
                validation=ValidationResult(
                    valid=False,
                    errors=[f"Trial not found: {', '.join(missing)}."],
                ),
            )

        shared = [SharedEntityMatch(**item) for item in result["shared_entities"]]
        return SharedEntityComparisonResponse(
            status=GraphQueryStatus.SUCCESS,
            nct_id_a=normalized_a,
            nct_id_b=normalized_b,
            limit_per_type=limit_per_type,
            shared_entities=shared,
            validation=ValidationResult(valid=True),
        )
    except Exception:
        logger.exception("Shared trial entity comparison failed")
        return SharedEntityComparisonResponse(
            status=GraphQueryStatus.EXECUTION_ERROR,
            nct_id_a=normalized_a,
            nct_id_b=normalized_b,
            limit_per_type=limit_per_type,
            validation=ValidationResult(
                valid=False,
                errors=["Shared-entity comparison failed because of an unexpected internal error."],
            ),
        )


def query_related_trials(
    seed_nct_id: str,
    max_hops: int = 2,
    per_hop_limit: int = 20,
    limit: int = 50,
    *,
    relationship_types: list[str] | None = None,
    overall_statuses: list[str] | None = None,
) -> RelatedTrialSearchResponse:
    """Run a bounded, allowlisted multi-hop related-trial traversal."""
    normalized = seed_nct_id.strip().upper()
    allowed_relationships = {"HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"}
    resolved_relationships = list(dict.fromkeys(
        item.strip().upper()
        for item in (relationship_types or sorted(allowed_relationships))
        if item and item.strip()
    ))
    resolved_statuses = list(dict.fromkeys(
        item.strip().upper()
        for item in (overall_statuses or [])
        if item and item.strip()
    ))

    def response_kwargs() -> dict:
        return {
            "seed_nct_id": normalized,
            "max_hops": max_hops,
            "per_hop_limit": per_hop_limit,
            "limit": limit,
            "relationship_types": resolved_relationships,
            "overall_statuses": resolved_statuses,
        }

    if not (len(normalized) == 11 and normalized.startswith("NCT") and normalized[3:].isdigit()):
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.VALIDATION_FAILED, **response_kwargs(),
            validation=ValidationResult(valid=False, errors=[
                "NCT ID must use the format NCT followed by exactly 8 digits."
            ]),
        )
    if max_hops not in (1, 2):
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.VALIDATION_FAILED, **response_kwargs(),
            validation=ValidationResult(valid=False, errors=["max_hops must be 1 or 2."]),
        )
    if not 1 <= per_hop_limit <= 50 or not 1 <= limit <= 100:
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.VALIDATION_FAILED, **response_kwargs(),
            validation=ValidationResult(valid=False, errors=[
                "per_hop_limit must be 1..50 and limit must be 1..100."
            ]),
        )
    if not resolved_relationships or any(
        item not in allowed_relationships for item in resolved_relationships
    ):
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.VALIDATION_FAILED, **response_kwargs(),
            validation=ValidationResult(valid=False, errors=[
                "Related-trial relationship types must use the allowlisted relationships."
            ]),
        )
    if any(not item.replace("_", "").isalnum() for item in resolved_statuses):
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.VALIDATION_FAILED, **response_kwargs(),
            validation=ValidationResult(valid=False, errors=[
                "Trial status filters contain unsupported characters."
            ]),
        )
    try:
        result = find_related_trials_bounded(
            normalized,
            max_hops,
            per_hop_limit,
            limit,
            relationship_types=resolved_relationships,
            overall_statuses=resolved_statuses,
        )
        if not result["found"]:
            return RelatedTrialSearchResponse(
                status=GraphQueryStatus.NOT_FOUND,
                **response_kwargs(),
                anchor_trial=None,
                validation=ValidationResult(
                    valid=False,
                    errors=[f"Trial not found: {normalized}."],
                ),
            )

        anchor_trial = result.get("anchor_trial") or {"nct_id": normalized}
        enriched_matches = []
        all_entity_ids: set[str] = set()
        evidence_path_count = 0
        for item in result["matches"]:
            related_trial = item.get("trial") or {"nct_id": item.get("nct_id")}
            enriched_paths = []
            for path in item.get("connected_via") or []:
                entity = path.get("entity") or {}
                entity_id = stable_entity_id(
                    str(path.get("relationship_type") or ""), entity
                )
                enriched_path = {**path, "entity_id": entity_id}
                enriched_paths.append(enriched_path)
                if entity_id:
                    all_entity_ids.add(entity_id)
            metric_values = build_related_trial_metrics(
                anchor_trial,
                related_trial,
                enriched_paths,
            )
            evidence_path_count += metric_values["evidence_path_count"]
            enriched_matches.append(
                {
                    **item,
                    "trial": related_trial,
                    "connected_via": enriched_paths,
                    "metrics": metric_values,
                }
            )

        matches = [RelatedTrialMatch(**item) for item in enriched_matches]
        aggregate_metrics = RelatedTrialAggregateMetrics(
            related_trial_count=len(matches),
            unique_shared_entity_count=len(all_entity_ids),
            evidence_path_count=evidence_path_count,
            condition_linked_trial_count=sum(
                1 for match in matches
                if match.metrics is not None and match.metrics.shared_condition_count > 0
            ),
            intervention_linked_trial_count=sum(
                1 for match in matches
                if match.metrics is not None and match.metrics.shared_intervention_count > 0
            ),
            sponsor_linked_trial_count=sum(
                1 for match in matches
                if match.metrics is not None and match.metrics.shared_sponsor_count > 0
            ),
            multi_factor_trial_count=sum(
                1 for match in matches
                if match.metrics is not None and match.metrics.total_shared_entity_count > 1
            ),
            completion_comparable_trial_count=sum(
                1 for match in matches
                if match.metrics is not None
                and match.metrics.completion_date_difference_days is not None
            ),
            duration_comparable_trial_count=sum(
                1 for match in matches
                if match.metrics is not None
                and match.metrics.duration_difference_days is not None
            ),
            enrollment_comparable_trial_count=sum(
                1 for match in matches
                if match.metrics is not None
                and match.metrics.enrollment_difference is not None
            ),
        )
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.SUCCESS if matches else GraphQueryStatus.NOT_FOUND,
            **response_kwargs(),
            anchor_trial=anchor_trial,
            matches=matches,
            metrics=aggregate_metrics,
            validation=ValidationResult(valid=True),
        )
    except Exception:
        logger.exception("Bounded related-trial traversal failed")
        return RelatedTrialSearchResponse(
            status=GraphQueryStatus.EXECUTION_ERROR, **response_kwargs(),
            validation=ValidationResult(valid=False, errors=[
                "Related-trial traversal failed because of an unexpected internal error."
            ]),
        )
