"""Trial-level lineage API routes for TrialIQ."""

from fastapi import APIRouter, HTTPException, status

from trialiq.services.lineage_service import get_trial_lineage


router = APIRouter(
    prefix="/lineage",
    tags=["lineage"],
)


@router.get("/trials/{nct_id}")
def get_trial_lineage_route(nct_id: str) -> dict:
    """Return source-level lineage records for a clinical trial."""
    try:
        return get_trial_lineage(nct_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving trial lineage.",
        ) from exc
