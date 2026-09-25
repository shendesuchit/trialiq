"""Typed visualization models for bounded TrialIQ graph evidence."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from trialiq.services.models import GraphQueryStatus, ValidationResult


class GraphNodeType(str, Enum):
    TRIAL = "trial"
    CONDITION = "condition"
    INTERVENTION = "intervention"
    SPONSOR = "sponsor"


class GraphRelationshipType(str, Enum):
    HAS_CONDITION = "HAS_CONDITION"
    HAS_INTERVENTION = "HAS_INTERVENTION"
    SPONSORED_BY = "SPONSORED_BY"


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: GraphNodeType
    label: str
    hop: int = Field(ge=0, le=2)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance_keys: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    relationship: GraphRelationshipType
    hop: int = Field(ge=1, le=2)
    evidence_keys: list[str] = Field(default_factory=list)


class GraphView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GraphQueryStatus
    seed_node: str | None = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    max_hops: int = Field(ge=1, le=2)
    per_hop_limit: int = Field(ge=1, le=25)
    limit: int = Field(ge=1, le=100)
    match_count: int = Field(ge=0)
    truncated: bool = False
    related_status: GraphQueryStatus | None = None
    validation: ValidationResult
    limitations: list[str] = Field(default_factory=list)
