from fastmcp import FastMCP

from trialiq.services.answer_service import answer_trial_overview_by_nct_id
from trialiq.services.graph_query_service import (
    query_related_trials,
    query_shared_entities_between_trials,
    query_trial_by_nct_id,
    query_trials_by_condition,
    query_trials_by_intervention,
    query_trials_by_sponsor,
)
from trialiq.services.source_verification import TrialVerificationResponse, verify_trial_evidence
from trialiq.services.models import (
    AnswerStatus,
    ConditionSearchResponse,
    EntitySearchResponse,
    EvidenceGroundedAnswer,
    GraphQueryResponse,
    RelatedTrialSearchResponse,
    SharedEntityComparisonResponse,
)


mcp = FastMCP("TrialIQ")


@mcp.tool(
    name="health_check",
    description="Verify that the TrialIQ MCP transport is available.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "trialiq-mcp"}


@mcp.tool(
    name="get_trial_evidence",
    description=(
        "Retrieve structured, validated, read-only graph evidence for a clinical "
        "trial identified by an NCT ID."
    ),
)
def get_trial_evidence(nct_id: str) -> GraphQueryResponse:
    """Return the deterministic graph-query response for the supplied NCT ID."""
    return query_trial_by_nct_id(nct_id)


@mcp.tool(
    name="search_trials_by_condition",
    description=(
        "Retrieve a bounded, deterministic, read-only set of trials matching an "
        "exact case-insensitive condition name."
    ),
)
def search_trials_by_condition(condition: str, limit: int = 20) -> ConditionSearchResponse:
    """Return the deterministic condition-search response."""
    return query_trials_by_condition(condition, limit)


@mcp.tool(
    name="search_trials_by_intervention",
    description=(
        "Retrieve a bounded, deterministic, read-only set of trials matching an "
        "exact case-insensitive intervention name."
    ),
)
def search_trials_by_intervention(intervention: str, limit: int = 20) -> EntitySearchResponse:
    return query_trials_by_intervention(intervention, limit)


@mcp.tool(
    name="search_trials_by_sponsor",
    description=(
        "Retrieve a bounded, deterministic, read-only set of trials matching an "
        "exact case-insensitive sponsor name."
    ),
)
def search_trials_by_sponsor(sponsor: str, limit: int = 20) -> EntitySearchResponse:
    return query_trials_by_sponsor(sponsor, limit)


@mcp.tool(
    name="compare_trial_shared_entities",
    description=(
        "Compare two trials using bounded shared condition, intervention, and sponsor names."
    ),
)
def compare_trial_shared_entities(
    nct_id_a: str,
    nct_id_b: str,
    limit_per_type: int = 20,
) -> SharedEntityComparisonResponse:
    return query_shared_entities_between_trials(nct_id_a, nct_id_b, limit_per_type)


@mcp.tool(
    name="find_related_trials",
    description=(
        "Discover related trials through a bounded one- or two-hop traversal over "
        "allowlisted condition, intervention, and sponsor relationships."
    ),
)
def find_related_trials(
    seed_nct_id: str,
    max_hops: int = 2,
    per_hop_limit: int = 20,
    limit: int = 50,
    relationship_types: list[str] | None = None,
    overall_statuses: list[str] | None = None,
) -> RelatedTrialSearchResponse:
    return query_related_trials(
        seed_nct_id, max_hops, per_hop_limit, limit,
        relationship_types=relationship_types, overall_statuses=overall_statuses,
    )


@mcp.tool(
    name="verify_trial_evidence",
    description=(
        "Compare validated graph evidence for one NCT ID against the canonical "
        "AACT PostgreSQL source and report explicit field-level discrepancies."
    ),
)
def verify_trial_evidence_tool(nct_id: str) -> TrialVerificationResponse:
    return verify_trial_evidence(nct_id)


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
