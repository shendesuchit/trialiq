"""TrialIQ-owned LLM runtime contracts.

These models intentionally hide vendor-specific response structures from the rest
of the application.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class LLMProviderHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str | None = None
    configured: bool = False
    healthy: bool = False
    latency_ms: float | None = Field(default=None, ge=0)
    error_category: str | None = None


class LLMRuntimeStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    healthy: bool = False
    selected_provider: str | None = None
    selected_model: str | None = None
    providers: list[LLMProviderHealth] = Field(default_factory=list)
    checked_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class LLMInvocationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    attempted_providers: list[str] = Field(default_factory=list)
    failover_reason: str | None = None
    latency_ms: float = Field(ge=0)
    error_category: str | None = None


class LLMTextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    metadata: LLMInvocationMetadata
