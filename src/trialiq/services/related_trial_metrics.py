"""Deterministic metrics and stable entity identity for related-trial evidence."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


_RELATIONSHIP_ENTITY_TYPE = {
    "HAS_CONDITION": "condition",
    "HAS_INTERVENTION": "intervention",
    "SPONSORED_BY": "sponsor",
}


def stable_entity_id(relationship_type: str, entity: dict[str, Any]) -> str | None:
    """Return a durable TrialIQ entity identifier without Neo4j internal IDs."""
    entity_type = _RELATIONSHIP_ENTITY_TYPE.get(relationship_type)
    if entity_type is None:
        return None

    canonical_key = entity.get("canonical_key")
    if not isinstance(canonical_key, str) or not canonical_key.strip():
        canonical_key = entity.get("normalized_name")
    if not isinstance(canonical_key, str) or not canonical_key.strip():
        name = entity.get("name")
        canonical_key = name.strip().casefold() if isinstance(name, str) and name.strip() else None
    if not canonical_key:
        return None
    return f"{entity_type}:{str(canonical_key).strip()}"


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    # AACT/Neo4j values are expected to be ISO-like. Accept a datetime suffix
    # without guessing locale-specific formats.
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _days_between(later: Any, earlier: Any) -> int | None:
    later_date = _as_date(later)
    earlier_date = _as_date(earlier)
    if later_date is None or earlier_date is None:
        return None
    return (later_date - earlier_date).days


def _duration_days(trial: dict[str, Any]) -> int | None:
    return _days_between(trial.get("completion_date"), trial.get("start_date"))


def _study_of_interest_label(anchor_trial: dict[str, Any]) -> str:
    nct_id = str(anchor_trial.get("nct_id") or "").strip()
    return f"the study of interest ({nct_id})" if nct_id else "the study of interest"


def _directional_days(
    label: str,
    value: int | None,
    reference_label: str,
) -> str | None:
    if value is None:
        return None
    if value == 0:
        return f"{label} on the same date as {reference_label}."
    relation = "after" if value > 0 else "before"
    return f"{label} {abs(value)} days {relation} {reference_label}."


def _duration_text(
    value: int | None,
    reference_label: str,
) -> str | None:
    if value is None:
        return None
    if value == 0:
        return f"Study duration matched {reference_label}."
    relation = "longer than" if value > 0 else "shorter than"
    return f"Study duration was {abs(value)} days {relation} {reference_label}."


def _enrollment_text(
    value: int | None,
    reference_label: str,
) -> str | None:
    if value is None:
        return None
    if value == 0:
        return f"Enrollment matched {reference_label}."
    relation = "more participants than" if value > 0 else "fewer participants than"
    return f"Enrollment was {abs(value)} {relation} {reference_label}."


def build_related_trial_metrics(
    anchor_trial: dict[str, Any],
    related_trial: dict[str, Any],
    connected_via: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute transparent, deterministic metrics for one related trial."""
    relationship_entity_ids = {
        "HAS_CONDITION": set(),
        "HAS_INTERVENTION": set(),
        "SPONSORED_BY": set(),
    }
    entity_ids: list[str] = []
    for path in connected_via:
        relationship_type = str(path.get("relationship_type") or "")
        entity = path.get("entity")
        if isinstance(entity, dict):
            entity_id = stable_entity_id(relationship_type, entity)
            if entity_id:
                if relationship_type in relationship_entity_ids:
                    relationship_entity_ids[relationship_type].add(entity_id)
                if entity_id not in entity_ids:
                    entity_ids.append(entity_id)

    reference_label = _study_of_interest_label(anchor_trial)
    start_difference = _days_between(
        related_trial.get("start_date"), anchor_trial.get("start_date")
    )
    completion_difference = _days_between(
        related_trial.get("completion_date"), anchor_trial.get("completion_date")
    )
    anchor_duration = _duration_days(anchor_trial)
    related_duration = _duration_days(related_trial)
    duration_difference = (
        related_duration - anchor_duration
        if related_duration is not None and anchor_duration is not None
        else None
    )
    anchor_enrollment = _as_int(anchor_trial.get("enrollment"))
    related_enrollment = _as_int(related_trial.get("enrollment"))
    enrollment_difference = (
        related_enrollment - anchor_enrollment
        if related_enrollment is not None and anchor_enrollment is not None
        else None
    )

    return {
        "shared_condition_count": len(relationship_entity_ids["HAS_CONDITION"]),
        "shared_intervention_count": len(relationship_entity_ids["HAS_INTERVENTION"]),
        "shared_sponsor_count": len(relationship_entity_ids["SPONSORED_BY"]),
        "total_shared_entity_count": len(entity_ids),
        "evidence_path_count": len(connected_via),
        "entity_ids": entity_ids,
        "start_date_difference_days": start_difference,
        "start_date_comparison": _directional_days(
            "Started", start_difference, reference_label
        ),
        "completion_date_difference_days": completion_difference,
        "completion_date_comparison": _directional_days(
            "Completed"
            if str(related_trial.get("overall_status") or "").upper() == "COMPLETED"
            else "Completion date is",
            completion_difference,
            reference_label,
        ),
        "anchor_duration_days": anchor_duration,
        "related_duration_days": related_duration,
        "duration_difference_days": duration_difference,
        "duration_comparison": _duration_text(duration_difference, reference_label),
        "anchor_enrollment": anchor_enrollment,
        "related_enrollment": related_enrollment,
        "enrollment_difference": enrollment_difference,
        "enrollment_comparison": _enrollment_text(enrollment_difference, reference_label),
    }
