"""Trial-related API routes."""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from trialiq.services.answer_service import answer_trial_overview_by_nct_id
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer, TrialCatalogResponse
from trialiq.services.trial_catalog_service import get_trial_catalog

router = APIRouter(prefix="/trials", tags=["trials"])


class TrialOverviewRequest(BaseModel):
    nct_id: str = Field(
        ...,
        min_length=1,
        description="ClinicalTrials.gov NCT identifier.",
    )


@router.get("/catalog", response_model=TrialCatalogResponse)
def get_trial_catalog_route(
    query: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TrialCatalogResponse:
    """Return a bounded, searchable catalog of trials currently loaded in Neo4j."""
    try:
        return get_trial_catalog(
            query,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving the trial catalog.",
        ) from exc


@router.post("/overview", response_model=EvidenceGroundedAnswer)
def get_trial_overview(request: TrialOverviewRequest) -> EvidenceGroundedAnswer:
    result = answer_trial_overview_by_nct_id(request.nct_id)

    if result.status == AnswerStatus.EXECUTION_ERROR:
        raise HTTPException(status_code=500, detail=result.model_dump())

    return result
