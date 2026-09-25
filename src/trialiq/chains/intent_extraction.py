
# Change Start
"""LLM-based structured intent extraction for TrialIQ."""

from pydantic import BaseModel, ConfigDict, Field

from trialiq.llm.service import get_llm_service
from trialiq.services.query_intent import QueryIntent
from typing import Optional



class ExtractedQueryIntent(BaseModel):
    """Structured output expected from the LLM."""

    model_config = ConfigDict(extra="forbid")

    intent: QueryIntent = Field(
        description="The supported query intent."
    )
    nct_id: Optional[str] = Field(
        default=None,
        description=(
            "The clinical trial identifier, such as NCT00000105. "
            "Return null when no NCT identifier is present."
        ),
    )
    condition: Optional[str] = Field(default=None, description="Condition term for condition search, otherwise null.")
    intervention: Optional[str] = Field(default=None, description="Intervention name for intervention search, otherwise null.")
    sponsor: Optional[str] = Field(default=None, description="Sponsor name for sponsor search, otherwise null.")
    nct_id_b: Optional[str] = Field(default=None, description="Second NCT ID for shared-entity comparison, otherwise null.")
    max_hops: int = Field(default=1, ge=1, le=2, description="For RELATED_TRIALS only: requested trial-to-trial hops, default 1 and never above 2.")
    per_hop_limit: int = Field(default=10, ge=1, le=25, description="For RELATED_TRIALS only: maximum discoveries expanded per hop; default 10.")
    relationship_types: list[str] = Field(
        default_factory=lambda: ["HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"],
        description="For RELATED_TRIALS only: the allowlisted connection types explicitly requested.",
    )
    overall_statuses: list[str] = Field(
        default_factory=list,
        description="For RELATED_TRIALS only: explicit trial status filters, e.g. COMPLETED.",
    )



SYSTEM_PROMPT = """You are a clinical trial metadata query-intent extractor.

Return only the structured fields in the output schema. Supported intents:
- TRIAL_OVERVIEW: overview of one specific NCT trial.
- TRIALS_BY_CONDITION: find/list trials for a named condition.
- TRIALS_BY_INTERVENTION: find/list trials studying a named intervention, drug, device, or procedure.
- TRIALS_BY_SPONSOR: find/list trials associated with a named sponsor or organization.
- SHARED_ENTITIES_BETWEEN_TRIALS: compare exactly two NCT trials for shared conditions, interventions, or sponsors.
- RELATED_TRIALS: find trials connected to one explicit NCT trial through shared condition, intervention, or sponsor metadata, within one or two hops.
- UNSUPPORTED: requests outside these metadata capabilities.

Extraction rules:
1. Preserve condition, intervention, and sponsor wording from the question; do not invent synonyms or normalize clinically.
2. For TRIAL_OVERVIEW set nct_id to the explicit NCT ID.
3. For SHARED_ENTITIES_BETWEEN_TRIALS set nct_id and nct_id_b to the two explicit NCT IDs in question order.
4. For RELATED_TRIALS set nct_id to the explicit seed trial. Set max_hops to 2 only when the user explicitly requests two hops; otherwise use 1.
5. For RELATED_TRIALS, relationship_types may contain only HAS_CONDITION, HAS_INTERVENTION, SPONSORED_BY. Include only explicitly requested relationship types; if the question does not restrict them, include all three.
6. For RELATED_TRIALS, put explicit overall-status filters in overall_statuses using uppercase source values such as COMPLETED. Otherwise return an empty list.
7. Set unused entity fields to null. Never invent identifiers or placeholder values.
8. RELATED_TRIALS may also request explanation of the connection plus deterministic comparison of returned trial metadata such as study dates, completion timing, duration, status, or enrollment. Keep the intent as RELATED_TRIALS; downstream deterministic logic owns those comparisons.
9. Use UNSUPPORTED for efficacy assessments, treatment recommendations, clinical advice, outcome interpretation, or other requests that require unsupported clinical inference.
10. Do not generate Cypher and do not answer the user's question.
"""


def extract_query_intent_with_metadata(question: str):
    """Extract structured intent and return the normalized invocation metadata."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", question.strip()),
    ]
    return get_llm_service().invoke_structured(messages, ExtractedQueryIntent)


def extract_query_intent(
    question: str,
) -> ExtractedQueryIntent:
    """Extract a validated structured intent from a user question."""
    result, _metadata = extract_query_intent_with_metadata(question)
    return result
# Change End