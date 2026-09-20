
# Change Start
"""LLM-based structured intent extraction for TrialIQ."""

from pydantic import BaseModel, ConfigDict, Field

from trialiq.llm.factory import create_llm
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
    condition: Optional[str] = Field(
        default=None,
        description=(
            "The medical condition or disease term used to search for "
            "clinical trials. Preserve the wording from the question. "
            "Return null when no condition is present."
        ),
    )



SYSTEM_PROMPT = """You are a clinical trial metadata query-intent extractor.

Your task is to extract the supported query intent, NCT ID, and condition term
from the user's question.

Supported intents:

- TRIAL_OVERVIEW:
  Requests an overview or metadata summary of one specific clinical trial
  identified by an NCT ID.

- TRIALS_BY_CONDITION:
  Requests a list or discovery of clinical trials associated with a named
  medical condition, disease, disorder, or health topic.

- UNSUPPORTED:
  Requests information outside the supported metadata capabilities.

Important classification rules:

1. Classify requests to FIND, SEARCH, LIST, SHOW, or DISCOVER clinical trials
   for a named condition as TRIALS_BY_CONDITION.

2. The following examples MUST be classified as TRIALS_BY_CONDITION:

   User: "Find clinical trials for Cancer"
   Output intent: TRIALS_BY_CONDITION
   Output condition: "Cancer"

   User: "Show me trials studying diabetes"
   Output intent: TRIALS_BY_CONDITION
   Output condition: "diabetes"

   User: "Search for clinical trials related to obesity"
   Output intent: TRIALS_BY_CONDITION
   Output condition: "obesity"

   User: "List studies for breast cancer"
   Output intent: TRIALS_BY_CONDITION
   Output condition: "breast cancer"

3. For TRIALS_BY_CONDITION:
   - Extract the condition phrase from the user's question.
   - Preserve the user's wording.
   - Do not invent synonyms.
   - Do not apply clinical normalization.
   - Do not broaden or narrow the condition.
   - Set nct_id to null unless an NCT ID is explicitly present.
   - Set condition to null only when no condition can be extracted.

4. For TRIAL_OVERVIEW:
   - Extract the NCT identifier exactly when present.
   - Return null for nct_id when no NCT identifier is present.
   - Do not infer an NCT ID.
   - Use this intent only for a specific trial overview request.

5. Use UNSUPPORTED for:
   - Efficacy assessments.
   - Treatment recommendations.
   - Clinical advice.
   - Comparisons between trials.
   - Cross-trial analysis.
   - Outcome interpretation.
   - Requests outside the supported metadata capabilities.

6. Never return placeholder values such as:
   NOT_FOUND, UNKNOWN, NONE, or N/A.

7. Do not generate Cypher.

8. Do not answer the user's clinical question.

9. Return only the structured fields defined by the output schema.
"""


def extract_query_intent(
    question: str,
) -> ExtractedQueryIntent:
    """Extract a validated structured intent from a user question."""

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    llm = create_llm()
    structured_llm = llm.with_structured_output(ExtractedQueryIntent)

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", question.strip()),
    ]

    result = structured_llm.invoke(messages)

    if not isinstance(result, ExtractedQueryIntent):
        raise TypeError(
            "LLM returned an unexpected structured-output type."
        )

    return result
# Change End