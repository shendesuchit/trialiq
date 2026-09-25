"""Natural-language query API routes for TrialIQ."""

from enum import Enum
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from trialiq.agents.api import run_agent_question
from trialiq.agents.models import AgentRunResult
from trialiq.services.answer_service import answer_trial_overview
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer


router = APIRouter(
    prefix="/query",
    tags=["query"],
)


class QueryMode(str, Enum):
    STANDARD = "standard"
    AGENT = "agent"


class QueryRequest(BaseModel):
    """Request contract for a natural-language TrialIQ query."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about a supported clinical-trial query.",
    )
    mode: QueryMode = QueryMode.STANDARD
    limit: int = Field(default=20, ge=1, le=100)


class AgentQueryRequest(BaseModel):
    """Explicit request contract for the observable experimental agent path."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


def _raise_for_execution_error(answer: EvidenceGroundedAnswer) -> None:
    if answer.status == AnswerStatus.EXECUTION_ERROR:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=answer.model_dump(),
        )


@router.post(
    "",
    response_model=EvidenceGroundedAnswer,
)
def process_query(request: QueryRequest, response: Response) -> EvidenceGroundedAnswer:
    """Process a question through the selected TrialIQ workflow."""

    response.headers["X-TrialIQ-Workflow-Mode"] = request.mode.value

    if request.mode == QueryMode.AGENT:
        run = run_agent_question(request.question, limit=request.limit)
        response.headers["X-TrialIQ-Run-ID"] = run.run_id
        _raise_for_execution_error(run.answer)
        return run.answer

    response.headers["X-TrialIQ-Run-ID"] = str(uuid4())
    try:
        result = answer_trial_overview(request.question)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing the query.",
        )

    _raise_for_execution_error(result)
    return result


@router.post(
    "/agent",
    response_model=AgentRunResult,
)
def process_agent_query(request: AgentQueryRequest) -> AgentRunResult:
    """Run the experimental agent workflow and return its observable run state.

    Workflow failures remain represented in the typed response so callers can
    inspect the run ID and trace. The backward-compatible ``/query`` endpoint
    continues to translate execution failures to HTTP 500.
    """
    return run_agent_question(request.question, limit=request.limit)
