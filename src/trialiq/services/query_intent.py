"""Controlled query intent contract for TrialIQ."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator, field_validator

from trialiq.services.models import (
    ConditionSearchResponse,
    GraphQueryResponse,
)


class QueryIntent(str, Enum):
    TRIAL_OVERVIEW = "TRIAL_OVERVIEW"
    TRIALS_BY_CONDITION = "TRIALS_BY_CONDITION"
    UNSUPPORTED = "UNSUPPORTED"


class QueryIntentRequest(BaseModel):
    """Validated request for a supported graph query intent."""

    model_config = ConfigDict(extra="forbid")

    intent: QueryIntent
    nct_id: str | None = None
    condition: str | None = None
    limit: int = 20

    @field_validator("nct_id")
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

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Condition cannot be empty.")
        return normalized

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if not 1 <= value <= 100:
            raise ValueError("Limit must be between 1 and 100.")
        return value

    @model_validator(mode="after")
    def validate_fields_for_intent(self):
        if self.intent == QueryIntent.TRIAL_OVERVIEW and not self.nct_id:
            raise ValueError("NCT ID is required for trial overview.")
        if self.intent == QueryIntent.TRIALS_BY_CONDITION and not self.condition:
            raise ValueError("Condition is required for condition search.")
        return self


def dispatch_query(
    request: QueryIntentRequest,
) -> GraphQueryResponse | ConditionSearchResponse:
    """Route a validated intent to its approved query service."""
    from trialiq.services.graph_query_service import (
        query_trial_by_nct_id,
        query_trials_by_condition,
    )

    if request.intent == QueryIntent.TRIAL_OVERVIEW:
        return query_trial_by_nct_id(request.nct_id)
    if request.intent == QueryIntent.TRIALS_BY_CONDITION:
        return query_trials_by_condition(request.condition, request.limit)
    if request.intent == QueryIntent.UNSUPPORTED:
        raise ValueError(
            "The requested question is outside the supported query capabilities."
        )
    raise ValueError(f"Unsupported query intent: {request.intent}")
