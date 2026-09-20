from fastmcp import FastMCP

from trialiq.services.answer_service import (
    answer_trial_overview_by_nct_id,
)
from trialiq.services.models import (
    AnswerStatus,
    EvidenceGroundedAnswer,
)


mcp = FastMCP("TrialIQ")


@mcp.tool(
    name="get_trial_overview",
    description=(
        "Retrieve a validated, evidence-grounded overview "
        "of a clinical trial identified by an NCT ID."
    ),
)
def get_trial_overview(nct_id: str) -> EvidenceGroundedAnswer:
    """Return a validated trial overview for the supplied NCT ID."""

    try:
        return answer_trial_overview_by_nct_id(nct_id)
    except Exception:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.EXECUTION_ERROR,
            question=f"Give me an overview of {nct_id}",
            answer="The trial evidence could not be retrieved.",
            limitations=[
                "An unexpected error occurred while retrieving graph evidence."
            ],
        )


if __name__ == "__main__":
    mcp.run()
