"""Natural-language query API routes for TrialIQ."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from trialiq.services.answer_service import answer_trial_overview, answer_trials_by_condition
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer


router = APIRouter(
    prefix="/query",
    tags=["query"],
)


class QueryRequest(BaseModel):
    """Request contract for a natural-language TrialIQ query."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about a supported clinical-trial query.",
    )


@router.post(
    "",
    response_model=EvidenceGroundedAnswer,
)
def process_query(request: QueryRequest) -> EvidenceGroundedAnswer:
    """Process a natural-language question through the validated answer service."""

    try:
        result = answer_trial_overview(request.question)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing the query.",
        )

    if result.status == AnswerStatus.EXECUTION_ERROR:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.model_dump(),
        )

    return result
