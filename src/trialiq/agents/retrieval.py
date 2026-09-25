"""Read-only retrieval agent built on controlled TrialIQ retrieval clients."""
import logging

from trialiq.services.query_intent import QueryIntent

from .mcp_client import DirectRetrievalClient, FastMCPRetrievalClient, RetrievalClient
from .models import AgentRequest, AgentStatus, RetrievalResult

logger = logging.getLogger(__name__)


class RetrievalAgent:
    def __init__(self, client: RetrievalClient | None = None):
        self.client = client or FastMCPRetrievalClient()

    def _transport(self) -> str:
        transport = getattr(self.client, "transport", None)
        if isinstance(transport, str) and transport.strip():
            return transport.strip()

        if isinstance(self.client, FastMCPRetrievalClient):
            return "mcp"

        if isinstance(self.client, DirectRetrievalClient):
            return "direct"

        return "custom"

    def run(self, request: AgentRequest) -> RetrievalResult:
        try:
            if request.intent == QueryIntent.TRIAL_OVERVIEW:
                if not request.nct_id:
                    return RetrievalResult(
                        status=AgentStatus.VALIDATION_FAILED,
                        transport=self._transport(),
                        errors=["NCT ID is required."],
                    )
                response = self.client.get_trial_evidence(request.nct_id)
                return RetrievalResult(
                    status=AgentStatus(response.status.value),
                    graph_response=response,
                    tool_name="get_trial_evidence",
                    transport=self._transport(),
                    errors=response.validation.errors,
                    warnings=response.validation.warnings,
                )

            if request.intent == QueryIntent.TRIALS_BY_CONDITION:
                if not request.condition:
                    return RetrievalResult(
                        status=AgentStatus.VALIDATION_FAILED,
                        transport=self._transport(),
                        errors=["Condition is required."],
                    )
                response = self.client.search_trials_by_condition(
                    request.condition,
                    request.limit,
                )
                return RetrievalResult(
                    status=AgentStatus(response.status.value),
                    condition_search_response=response,
                    tool_name="search_trials_by_condition",
                    transport=self._transport(),
                    errors=response.validation.errors,
                    warnings=response.validation.warnings,
                )

            if request.intent == QueryIntent.TRIALS_BY_INTERVENTION:
                if not request.intervention:
                    return RetrievalResult(status=AgentStatus.VALIDATION_FAILED, transport=self._transport(), errors=["Intervention is required."])
                response = self.client.search_trials_by_intervention(request.intervention, request.limit)
                return RetrievalResult(status=AgentStatus(response.status.value), entity_search_response=response, tool_name="search_trials_by_intervention", transport=self._transport(), errors=response.validation.errors, warnings=response.validation.warnings)

            if request.intent == QueryIntent.TRIALS_BY_SPONSOR:
                if not request.sponsor:
                    return RetrievalResult(status=AgentStatus.VALIDATION_FAILED, transport=self._transport(), errors=["Sponsor is required."])
                response = self.client.search_trials_by_sponsor(request.sponsor, request.limit)
                return RetrievalResult(status=AgentStatus(response.status.value), entity_search_response=response, tool_name="search_trials_by_sponsor", transport=self._transport(), errors=response.validation.errors, warnings=response.validation.warnings)

            if request.intent == QueryIntent.RELATED_TRIALS:
                if not request.nct_id:
                    return RetrievalResult(status=AgentStatus.VALIDATION_FAILED, transport=self._transport(), errors=["NCT ID is required."])
                response = self.client.find_related_trials(
                    request.nct_id, request.max_hops, request.per_hop_limit, request.limit,
                    request.relationship_types, request.overall_statuses,
                )
                return RetrievalResult(status=AgentStatus(response.status.value), related_trial_response=response, tool_name="find_related_trials", transport=self._transport(), errors=response.validation.errors, warnings=response.validation.warnings)

            if request.intent == QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS:
                if not request.nct_id or not request.nct_id_b:
                    return RetrievalResult(status=AgentStatus.VALIDATION_FAILED, transport=self._transport(), errors=["Two NCT IDs are required."])
                response = self.client.compare_trial_shared_entities(request.nct_id, request.nct_id_b, request.limit)
                return RetrievalResult(status=AgentStatus(response.status.value), shared_entity_response=response, tool_name="compare_trial_shared_entities", transport=self._transport(), errors=response.validation.errors, warnings=response.validation.warnings)

            return RetrievalResult(
                status=AgentStatus.UNSUPPORTED,
                transport=self._transport(),
                errors=["The requested query intent is not supported by the agent workflow."],
            )
        except Exception:
            logger.exception("Unexpected failure in agent retrieval")
            return RetrievalResult(
                status=AgentStatus.EXECUTION_ERROR,
                transport=self._transport(),
                errors=["Retrieval failed because of an unexpected internal error."],
            )
