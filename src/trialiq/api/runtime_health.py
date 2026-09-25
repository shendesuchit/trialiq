"""Runtime dependency health for the TrialIQ demo surface."""

from __future__ import annotations

import logging
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field

from trialiq.agents.mcp_client import FastMCPRetrievalClient
from trialiq.graph.connection import Neo4jConnection
from trialiq.llm.models import LLMRuntimeStatus
from trialiq.llm.service import get_llm_service

logger = logging.getLogger(__name__)


class RuntimeComponentHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    healthy: bool
    status: str
    latency_ms: float | None = Field(default=None, ge=0)
    provider: str | None = None
    model: str | None = None
    detail: str | None = None


class RuntimeReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str = "trialiq-api"
    components: dict[str, RuntimeComponentHealth]


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


def check_neo4j() -> RuntimeComponentHealth:
    started = perf_counter()
    connection: Neo4jConnection | None = None
    try:
        connection = Neo4jConnection()
        connection.verify_connectivity()
        return RuntimeComponentHealth(
            healthy=True,
            status="healthy",
            latency_ms=_elapsed_ms(started),
        )
    except Exception:
        logger.warning("Neo4j readiness probe failed", exc_info=True)
        return RuntimeComponentHealth(
            healthy=False,
            status="unavailable",
            latency_ms=_elapsed_ms(started),
            detail="Neo4j connectivity check failed.",
        )
    finally:
        if connection is not None:
            connection.close()


def check_mcp() -> RuntimeComponentHealth:
    started = perf_counter()
    try:
        healthy = FastMCPRetrievalClient(timeout=5.0).check_health()
        return RuntimeComponentHealth(
            healthy=healthy,
            status="healthy" if healthy else "unavailable",
            latency_ms=_elapsed_ms(started),
            detail=None if healthy else "MCP health tool returned an unexpected response.",
        )
    except Exception:
        logger.warning("MCP readiness probe failed", exc_info=True)
        return RuntimeComponentHealth(
            healthy=False,
            status="unavailable",
            latency_ms=_elapsed_ms(started),
            detail="MCP transport check failed.",
        )


def llm_component(status: LLMRuntimeStatus | None = None) -> RuntimeComponentHealth:
    resolved = status or get_llm_service().status()
    return RuntimeComponentHealth(
        healthy=resolved.healthy,
        status="healthy" if resolved.healthy else "unavailable",
        provider=resolved.selected_provider,
        model=resolved.selected_model,
        detail=None if resolved.healthy else "No usable configured LLM provider was selected.",
    )


def get_runtime_readiness() -> RuntimeReadiness:
    components = {
        "api": RuntimeComponentHealth(healthy=True, status="healthy"),
        "neo4j": check_neo4j(),
        "mcp": check_mcp(),
        "llm": llm_component(),
    }
    healthy = all(component.healthy for component in components.values())
    return RuntimeReadiness(
        status="ready" if healthy else "degraded",
        components=components,
    )
