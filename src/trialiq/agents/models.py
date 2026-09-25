"""Typed contracts for the experimental TrialIQ agent workflow."""
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from trialiq.services.models import (
    AnswerStatus, ConditionSearchResponse, EvidenceGroundedAnswer, EntitySearchResponse,
    GraphQueryResponse, RelatedTrialSearchResponse, SharedEntityComparisonResponse,
)
from trialiq.services.query_intent import QueryIntent


class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNSUPPORTED = "UNSUPPORTED"


class GenerationMethod(str, Enum):
    LLM = "LLM"
    DETERMINISTIC = "DETERMINISTIC"


class GenerationMetadata(BaseModel):
    """How the final answer text was produced after evidence retrieval."""

    model_config = ConfigDict(extra="forbid")

    method: GenerationMethod
    grounded: bool
    provider: str | None = None
    model: str | None = None
    source_count: int = Field(default=0, ge=0)
    attempted_providers: list[str] = Field(default_factory=list)
    failover_reason: str | None = None
    error_category: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    degraded: bool = False
    grounding_errors: list[str] = Field(default_factory=list)
    rejected_claim_count: int = Field(default=0, ge=0)


class StructuredFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class StructuredSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    key_findings: list[StructuredFinding] = Field(min_length=1, max_length=8)


class SynthesisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: EvidenceGroundedAnswer
    structured: StructuredSynthesis | None = None
    generation: GenerationMetadata

    @property
    def status(self) -> AnswerStatus:
        """Backward-compatible access for callers that previously received the answer."""
        return self.answer.status

    @property
    def limitations(self) -> list[str]:
        return self.answer.limitations

    @property
    def related_trial_response(self) -> RelatedTrialSearchResponse | None:
        return self.answer.related_trial_response


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    intent: QueryIntent
    nct_id: str | None = None
    condition: str | None = None
    intervention: str | None = None
    sponsor: str | None = None
    nct_id_b: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    max_hops: int = Field(default=1, ge=1, le=2)
    per_hop_limit: int = Field(default=10, ge=1, le=25)
    relationship_types: list[str] = Field(
        default_factory=lambda: [
            "HAS_CONDITION",
            "HAS_INTERVENTION",
            "SPONSORED_BY",
        ]
    )
    overall_statuses: list[str] = Field(default_factory=list)
    intent_source: str = "typed"


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AgentStatus
    graph_response: GraphQueryResponse | None = None
    condition_search_response: ConditionSearchResponse | None = None
    entity_search_response: EntitySearchResponse | None = None
    shared_entity_response: SharedEntityComparisonResponse | None = None
    related_trial_response: RelatedTrialSearchResponse | None = None
    tool_name: str | None = None
    transport: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AgentStatus
    can_synthesize: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AgentStageTrace(BaseModel):
    """Compact observability record for one workflow stage."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    status: AgentStatus
    duration_ms: float = Field(ge=0)
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AgentRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: AgentStatus
    answer: EvidenceGroundedAnswer
    retrieval: RetrievalResult | None = None
    validation: ValidationResult | None = None
    generation: GenerationMetadata | None = None
    structured_synthesis: StructuredSynthesis | None = None
    trace: list[AgentStageTrace] = Field(default_factory=list)
