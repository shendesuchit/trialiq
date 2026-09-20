from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from trialiq.services.answer_service import (
    answer_trial_overview_by_nct_id,
    answer_trials_by_condition,
)
from trialiq.services.models import (
    AnswerStatus,
    EvidenceGroundedAnswer,
)


router = APIRouter(
    prefix="/trials",
    tags=["trials"],
)


class TrialOverviewRequest(BaseModel):
    nct_id: str = Field(
        ...,
        min_length=1,
        description="ClinicalTrials.gov NCT identifier.",
    )


@router.post(
    "/overview",
    response_model=EvidenceGroundedAnswer,
)
def get_trial_overview(
    request: TrialOverviewRequest,
) -> EvidenceGroundedAnswer:
    try:
        result = answer_trial_overview_by_nct_id(
            request.nct_id
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving trial overview.",
        )

    if result.status == AnswerStatus.EXECUTION_ERROR:
        raise HTTPException(
            status_code=500,
            detail=result.model_dump(),
        )

    return result


class TrialConditionSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


@router.post(
    "/search-by-condition",
    response_model=EvidenceGroundedAnswer,
)
def search_trials_by_condition_route(
    request: TrialConditionSearchRequest,
) -> EvidenceGroundedAnswer:
    try:
        result = answer_trials_by_condition(
            condition=request.condition,
            limit=request.limit,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error while searching trials by condition.",
        )

    if result.status == AnswerStatus.EXECUTION_ERROR:
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result
