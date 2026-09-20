from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GraphQueryStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GraphQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GraphQueryStatus
    nct_id: str
    evidence: dict | None = None
    validation: ValidationResult


class ConditionSearchStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ConditionTrialMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str
    trial: dict
    matched_conditions: list[dict] = Field(default_factory=list)


class ConditionSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ConditionSearchStatus
    condition: str
    limit: int
    matches: list[ConditionTrialMatch] = Field(default_factory=list)
    validation: ValidationResult


class AnswerStatus(str, Enum):
    GROUNDED = "GROUNDED"
    NOT_FOUND = "NOT_FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNSUPPORTED = "UNSUPPORTED"
    MISSING_NCT_ID = "MISSING_NCT_ID"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_table: str | None = None
    source_key: str | None = None
    source_id: int | str | None = None


class EvidenceGroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AnswerStatus
    question: str
    answer: str
    graph_response: GraphQueryResponse | None = None
    condition_search_response: ConditionSearchResponse | None = None
    limitations: list[str] = Field(default_factory=list)
    sources: list[EvidenceSource] = Field(default_factory=list)


class OrchestrationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    UNSUPPORTED = "UNSUPPORTED"
    MISSING_NCT_ID = "MISSING_NCT_ID"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class OrchestrationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrchestrationStatus
    message: str
    intent: str | None = None
    nct_id: str | None = None
    graph_response: GraphQueryResponse | None = None
    condition_search_response: ConditionSearchResponse | None = None
