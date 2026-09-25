"""Controlled MCP retrieval client adapters for the experimental agent workflow."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Protocol

from fastmcp import Client

from trialiq.mcp.server import mcp as trialiq_mcp
from trialiq.services.graph_query_service import (
    query_related_trials,
    query_shared_entities_between_trials,
    query_trial_by_nct_id,
    query_trials_by_condition,
    query_trials_by_intervention,
    query_trials_by_sponsor,
)
from trialiq.services.models import (
    ConditionSearchResponse,
    EntitySearchResponse,
    GraphQueryResponse,
    RelatedTrialSearchResponse,
    SharedEntityComparisonResponse,
)


class RetrievalClient(Protocol):
    """Minimal retrieval interface consumed by ``RetrievalAgent``."""

    transport: str

    def get_trial_evidence(self, nct_id: str) -> GraphQueryResponse:
        ...

    def search_trials_by_condition(
        self,
        condition: str,
        limit: int,
    ) -> ConditionSearchResponse:
        ...

    def search_trials_by_intervention(
        self, intervention: str, limit: int
    ) -> EntitySearchResponse:
        ...

    def search_trials_by_sponsor(
        self, sponsor: str, limit: int
    ) -> EntitySearchResponse:
        ...

    def compare_trial_shared_entities(
        self, nct_id_a: str, nct_id_b: str, limit_per_type: int
    ) -> SharedEntityComparisonResponse:
        ...


    def find_related_trials(
        self, seed_nct_id: str, max_hops: int, per_hop_limit: int, limit: int,
        relationship_types: list[str] | None = None, overall_statuses: list[str] | None = None,
    ) -> RelatedTrialSearchResponse:
        ...

class DirectRetrievalClient:
    """Deterministic service-backed client retained for explicit injection."""

    transport = "direct"

    def get_trial_evidence(self, nct_id: str) -> GraphQueryResponse:
        return query_trial_by_nct_id(nct_id)

    def search_trials_by_condition(
        self,
        condition: str,
        limit: int,
    ) -> ConditionSearchResponse:
        return query_trials_by_condition(condition, limit)

    def search_trials_by_intervention(
        self, intervention: str, limit: int
    ) -> EntitySearchResponse:
        return query_trials_by_intervention(intervention, limit)

    def search_trials_by_sponsor(
        self, sponsor: str, limit: int
    ) -> EntitySearchResponse:
        return query_trials_by_sponsor(sponsor, limit)

    def compare_trial_shared_entities(
        self, nct_id_a: str, nct_id_b: str, limit_per_type: int
    ) -> SharedEntityComparisonResponse:
        return query_shared_entities_between_trials(nct_id_a, nct_id_b, limit_per_type)


    def find_related_trials(
        self, seed_nct_id: str, max_hops: int, per_hop_limit: int, limit: int,
        relationship_types: list[str] | None = None, overall_statuses: list[str] | None = None,
    ) -> RelatedTrialSearchResponse:
        return query_related_trials(
            seed_nct_id, max_hops, per_hop_limit, limit,
            relationship_types=relationship_types, overall_statuses=overall_statuses,
        )

class FastMCPRetrievalClient:
    """Invoke TrialIQ's controlled retrieval tools through the FastMCP client."""

    transport = "mcp"

    def __init__(self, server: Any = None, *, timeout: float = 30.0):
        if not 0 < timeout <= 60:
            raise ValueError("MCP timeout must be greater than 0 and at most 60 seconds.")
        self.server = trialiq_mcp if server is None else server
        self.timeout = timeout

    def check_health(self) -> bool:
        data = self._call_tool("health_check", {})
        return isinstance(data, dict) and data.get("status") == "ok"

    def get_trial_evidence(self, nct_id: str) -> GraphQueryResponse:
        data = self._call_tool("get_trial_evidence", {"nct_id": nct_id})
        return GraphQueryResponse.model_validate(data)

    def search_trials_by_condition(
        self,
        condition: str,
        limit: int,
    ) -> ConditionSearchResponse:
        data = self._call_tool(
            "search_trials_by_condition",
            {"condition": condition, "limit": limit},
        )
        return ConditionSearchResponse.model_validate(data)

    def search_trials_by_intervention(
        self, intervention: str, limit: int
    ) -> EntitySearchResponse:
        data = self._call_tool(
            "search_trials_by_intervention",
            {"intervention": intervention, "limit": limit},
        )
        return EntitySearchResponse.model_validate(data)

    def search_trials_by_sponsor(
        self, sponsor: str, limit: int
    ) -> EntitySearchResponse:
        data = self._call_tool(
            "search_trials_by_sponsor",
            {"sponsor": sponsor, "limit": limit},
        )
        return EntitySearchResponse.model_validate(data)

    def compare_trial_shared_entities(
        self, nct_id_a: str, nct_id_b: str, limit_per_type: int
    ) -> SharedEntityComparisonResponse:
        data = self._call_tool(
            "compare_trial_shared_entities",
            {
                "nct_id_a": nct_id_a,
                "nct_id_b": nct_id_b,
                "limit_per_type": limit_per_type,
            },
        )
        return SharedEntityComparisonResponse.model_validate(data)

    def find_related_trials(
        self, seed_nct_id: str, max_hops: int, per_hop_limit: int, limit: int,
        relationship_types: list[str] | None = None, overall_statuses: list[str] | None = None,
    ) -> RelatedTrialSearchResponse:
        data = self._call_tool(
            "find_related_trials",
            {
                "seed_nct_id": seed_nct_id,
                "max_hops": max_hops,
                "per_hop_limit": per_hop_limit,
                "limit": limit,
                "relationship_types": relationship_types or [
                    "HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"
                ],
                "overall_statuses": overall_statuses or [],
            },
        )
        return RelatedTrialSearchResponse.model_validate(data)

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        async def invoke() -> Any:
            async with Client(self.server, timeout=self.timeout) as client:
                result = await client.call_tool(name, arguments)

                # Validate against FastMCP's raw structured payload rather than
                # its hydrated convenience object. Typed tool outputs may be
                # represented in ``result.data`` by a generated Root wrapper.
                if result.structured_content is not None:
                    return result.structured_content

                data = result.data
                if hasattr(data, "root"):
                    return data.root
                return data

        return _run_async(invoke())


def _run_async(coroutine):
    """Run an MCP coroutine safely from the workflow's synchronous API."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coroutine).result()
