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


class EntitySearchStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class EntityTrialMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str
    trial: dict
    matched_entities: list[dict] = Field(default_factory=list)


class EntitySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EntitySearchStatus
    entity_type: str
    query: str
    limit: int
    matches: list[EntityTrialMatch] = Field(default_factory=list)
    validation: ValidationResult


class SharedEntityMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    normalized_name: str
    trial_a_entities: list[dict] = Field(default_factory=list)
    trial_b_entities: list[dict] = Field(default_factory=list)


class SharedEntityComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GraphQueryStatus
    nct_id_a: str
    nct_id_b: str
    limit_per_type: int
    shared_entities: list[SharedEntityMatch] = Field(default_factory=list)
    validation: ValidationResult


class RelatedTrialPathEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_nct_id: str
    relationship_type: str
    entity: dict
    entity_id: str | None = None


class RelatedTrialMetrics(BaseModel):
    """Transparent deterministic comparison metrics for one related trial."""

    model_config = ConfigDict(extra="forbid")

    shared_condition_count: int = Field(default=0, ge=0)
    shared_intervention_count: int = Field(default=0, ge=0)
    shared_sponsor_count: int = Field(default=0, ge=0)
    total_shared_entity_count: int = Field(default=0, ge=0)
    evidence_path_count: int = Field(default=0, ge=0)
    entity_ids: list[str] = Field(default_factory=list)
    start_date_difference_days: int | None = None
    start_date_comparison: str | None = None
    completion_date_difference_days: int | None = None
    completion_date_comparison: str | None = None
    anchor_duration_days: int | None = Field(default=None, ge=0)
    related_duration_days: int | None = Field(default=None, ge=0)
    duration_difference_days: int | None = None
    duration_comparison: str | None = None
    anchor_enrollment: int | None = Field(default=None, ge=0)
    related_enrollment: int | None = Field(default=None, ge=0)
    enrollment_difference: int | None = None
    enrollment_comparison: str | None = None


class RelatedTrialMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str
    trial: dict
    discovery_hop: int = Field(ge=1, le=2)
    connected_via: list[RelatedTrialPathEvidence] = Field(default_factory=list)
    metrics: RelatedTrialMetrics | None = None


class RelatedTrialAggregateMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    related_trial_count: int = Field(default=0, ge=0)
    unique_shared_entity_count: int = Field(default=0, ge=0)
    evidence_path_count: int = Field(default=0, ge=0)
    condition_linked_trial_count: int = Field(default=0, ge=0)
    intervention_linked_trial_count: int = Field(default=0, ge=0)
    sponsor_linked_trial_count: int = Field(default=0, ge=0)
    multi_factor_trial_count: int = Field(default=0, ge=0)
    completion_comparable_trial_count: int = Field(default=0, ge=0)
    duration_comparable_trial_count: int = Field(default=0, ge=0)
    enrollment_comparable_trial_count: int = Field(default=0, ge=0)


class RelatedTrialSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GraphQueryStatus
    seed_nct_id: str
    anchor_trial: dict | None = None
    max_hops: int
    per_hop_limit: int
    limit: int
    relationship_types: list[str] = Field(default_factory=list)
    overall_statuses: list[str] = Field(default_factory=list)
    matches: list[RelatedTrialMatch] = Field(default_factory=list)
    metrics: RelatedTrialAggregateMetrics = Field(default_factory=RelatedTrialAggregateMetrics)
    validation: ValidationResult


class TrialQuestionSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    label: str
    question: str


class TrialCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str
    brief_title: str | None = None
    official_title: str | None = None
    overall_status: str | None = None
    related_trial_count: int = Field(ge=0)
    related_trial_count_capped: bool = False
    has_graph_neighbors: bool
    relationship_types: list[str] = Field(default_factory=list)
    suggested_questions: list[TrialQuestionSuggestion] = Field(default_factory=list)


class TrialCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = ""
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total_count: int = Field(ge=0)
    has_more: bool
    trials: list[TrialCatalogItem] = Field(default_factory=list)


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
    entity_search_response: EntitySearchResponse | None = None
    shared_entity_response: SharedEntityComparisonResponse | None = None
    related_trial_response: RelatedTrialSearchResponse | None = None
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
