"""Controlled query intent contract for TrialIQ."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trialiq.services.models import (
    ConditionSearchResponse,
    EntitySearchResponse,
    GraphQueryResponse,
    RelatedTrialSearchResponse,
    SharedEntityComparisonResponse,
)


class QueryIntent(str, Enum):
    TRIAL_OVERVIEW = "TRIAL_OVERVIEW"
    TRIALS_BY_CONDITION = "TRIALS_BY_CONDITION"
    TRIALS_BY_INTERVENTION = "TRIALS_BY_INTERVENTION"
    TRIALS_BY_SPONSOR = "TRIALS_BY_SPONSOR"
    SHARED_ENTITIES_BETWEEN_TRIALS = "SHARED_ENTITIES_BETWEEN_TRIALS"
    RELATED_TRIALS = "RELATED_TRIALS"
    UNSUPPORTED = "UNSUPPORTED"


class QueryIntentRequest(BaseModel):
    """Validated request for a supported graph query intent."""

    model_config = ConfigDict(extra="forbid")

    intent: QueryIntent
    nct_id: str | None = None
    condition: str | None = None
    intervention: str | None = None
    sponsor: str | None = None
    nct_id_b: str | None = None
    limit: int = 20
    max_hops: int = 1
    per_hop_limit: int = 10
    relationship_types: list[str] = Field(
        default_factory=lambda: [
            "HAS_CONDITION",
            "HAS_INTERVENTION",
            "SPONSORED_BY",
        ]
    )
    overall_statuses: list[str] = Field(default_factory=list)

    @field_validator("nct_id", "nct_id_b")
    @classmethod
    def validate_nct_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("NCT ID cannot be empty.")
        if not normalized.startswith("NCT"):
            raise ValueError("NCT ID must start with 'NCT'.")
        if not normalized[3:].isdigit() or len(normalized[3:]) != 8:
            raise ValueError("NCT ID must contain exactly 8 digits after 'NCT'.")
        return normalized

    @field_validator("condition", "intervention", "sponsor")
    @classmethod
    def validate_condition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Search term cannot be empty.")
        return normalized

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if not 1 <= value <= 100:
            raise ValueError("Limit must be between 1 and 100.")
        return value

    @field_validator("max_hops")
    @classmethod
    def validate_max_hops(cls, value: int) -> int:
        if value not in (1, 2):
            raise ValueError("max_hops must be 1 or 2.")
        return value

    @field_validator("per_hop_limit")
    @classmethod
    def validate_per_hop_limit(cls, value: int) -> int:
        if not 1 <= value <= 25:
            raise ValueError("per_hop_limit must be between 1 and 25.")
        return value

    @field_validator("relationship_types")
    @classmethod
    def validate_relationship_types(cls, value: list[str]) -> list[str]:
        allowed = {"HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"}
        normalized = list(dict.fromkeys(item.strip().upper() for item in value if item.strip()))
        invalid = [item for item in normalized if item not in allowed]
        if invalid:
            raise ValueError("Unsupported related-trial relationship type.")
        return normalized

    @field_validator("overall_statuses")
    @classmethod
    def validate_overall_statuses(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip().upper() for item in value if item.strip()))
        if any(not item.replace("_", "").isalnum() for item in normalized):
            raise ValueError("Trial status filters must contain letters, numbers, or underscores only.")
        return normalized

    @model_validator(mode="after")
    def validate_fields_for_intent(self):
        if self.intent == QueryIntent.TRIAL_OVERVIEW and not self.nct_id:
            raise ValueError("NCT ID is required for trial overview.")
        if self.intent == QueryIntent.TRIALS_BY_CONDITION and not self.condition:
            raise ValueError("Condition is required for condition search.")
        if self.intent == QueryIntent.TRIALS_BY_INTERVENTION and not self.intervention:
            raise ValueError("Intervention is required for intervention search.")
        if self.intent == QueryIntent.TRIALS_BY_SPONSOR and not self.sponsor:
            raise ValueError("Sponsor is required for sponsor search.")
        if self.intent == QueryIntent.RELATED_TRIALS:
            if not self.nct_id:
                raise ValueError("NCT ID is required for related-trial traversal.")
            if not self.relationship_types:
                raise ValueError("At least one related-trial relationship type is required.")
        if self.intent == QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS:
            if not self.nct_id or not self.nct_id_b:
                raise ValueError("Two NCT IDs are required for shared-entity comparison.")
            if self.nct_id == self.nct_id_b:
                raise ValueError("Shared-entity comparison requires two different NCT IDs.")
        return self


def dispatch_query(
    request: QueryIntentRequest,
) -> GraphQueryResponse | ConditionSearchResponse | EntitySearchResponse | SharedEntityComparisonResponse | RelatedTrialSearchResponse:
    """Route a validated intent to its approved query service."""
    from trialiq.services.graph_query_service import (
        query_trial_by_nct_id,
        query_trials_by_condition,
        query_trials_by_intervention,
        query_trials_by_sponsor,
        query_shared_entities_between_trials,
        query_related_trials,
    )

    if request.intent == QueryIntent.TRIAL_OVERVIEW:
        return query_trial_by_nct_id(request.nct_id)
    if request.intent == QueryIntent.TRIALS_BY_CONDITION:
        return query_trials_by_condition(request.condition, request.limit)
    if request.intent == QueryIntent.TRIALS_BY_INTERVENTION:
        return query_trials_by_intervention(request.intervention, request.limit)
    if request.intent == QueryIntent.TRIALS_BY_SPONSOR:
        return query_trials_by_sponsor(request.sponsor, request.limit)
    if request.intent == QueryIntent.RELATED_TRIALS:
        return query_related_trials(
            request.nct_id,
            request.max_hops,
            request.per_hop_limit,
            request.limit,
            relationship_types=request.relationship_types,
            overall_statuses=request.overall_statuses,
        )
    if request.intent == QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS:
        return query_shared_entities_between_trials(request.nct_id, request.nct_id_b, request.limit)
    if request.intent == QueryIntent.UNSUPPORTED:
        raise ValueError(
            "The requested question is outside the supported query capabilities."
        )
    raise ValueError(f"Unsupported query intent: {request.intent}")
