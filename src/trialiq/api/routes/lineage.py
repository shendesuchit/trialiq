"""Trial-level lineage API routes for TrialIQ."""

from fastapi import APIRouter, HTTPException, Query, status

from trialiq.services.graph_view_models import GraphView
from trialiq.services.lineage_service import get_trial_graph_view, get_trial_lineage


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


@router.get("/trials/{nct_id}/graph", response_model=GraphView)
def get_trial_graph_route(
    nct_id: str,
    max_hops: int = Query(default=1, ge=1, le=2),
    per_hop_limit: int = Query(default=20, ge=1, le=25),
    limit: int = Query(default=40, ge=1, le=100),
) -> GraphView:
    """Return a bounded visualization DTO for related-trial graph evidence."""
    try:
        return get_trial_graph_view(
            nct_id,
            max_hops=max_hops,
            per_hop_limit=per_hop_limit,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving trial graph lineage.",
        ) from exc
