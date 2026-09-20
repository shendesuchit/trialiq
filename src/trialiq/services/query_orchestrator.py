"""Natural-language query orchestration for TrialIQ."""

import re

from trialiq.chains.intent_extraction import extract_query_intent
from trialiq.services.models import OrchestrationResponse, OrchestrationStatus
from trialiq.services.query_intent import QueryIntent, QueryIntentRequest, dispatch_query


def answer_question(question: str) -> OrchestrationResponse:
    if not question or not question.strip():
        return OrchestrationResponse(
            status=OrchestrationStatus.VALIDATION_FAILED,
            message="The question cannot be empty.",
        )

    malformed_nct = re.search(r"\bNCT\d+\b", question, flags=re.IGNORECASE)
    if malformed_nct and not re.search(r"\bNCT\d{8}\b", question, flags=re.IGNORECASE):
        return OrchestrationResponse(
            status=OrchestrationStatus.VALIDATION_FAILED,
            message="The supplied NCT ID is invalid. Use the format NCT followed by 8 digits.",
        )

    try:
        extracted = extract_query_intent(question)

        if extracted.intent == QueryIntent.UNSUPPORTED:
            return OrchestrationResponse(
                status=OrchestrationStatus.UNSUPPORTED,
                message="The requested question is outside the supported query capabilities.",
                intent=extracted.intent.value,
                nct_id=extracted.nct_id,
            )

        if extracted.intent == QueryIntent.TRIALS_BY_CONDITION:
            if not extracted.condition:
                return OrchestrationResponse(
                    status=OrchestrationStatus.VALIDATION_FAILED,
                    message="No condition was found in the question.",
                    intent=extracted.intent.value,
                )
            request = QueryIntentRequest(
                intent=extracted.intent,
                condition=extracted.condition,
            )
        else:
            if not extracted.nct_id:
                return OrchestrationResponse(
                    status=OrchestrationStatus.MISSING_NCT_ID,
                    message="No NCT ID was found in the question. Please provide a specific clinical trial NCT ID.",
                    intent=extracted.intent.value,
                )
            request = QueryIntentRequest(
                intent=extracted.intent,
                nct_id=extracted.nct_id,
            )

        response = dispatch_query(request)
        status_mapping = {
            "SUCCESS": OrchestrationStatus.SUCCESS,
            "NOT_FOUND": OrchestrationStatus.NOT_FOUND,
            "VALIDATION_FAILED": OrchestrationStatus.VALIDATION_FAILED,
            "EXECUTION_ERROR": OrchestrationStatus.EXECUTION_ERROR,
        }
        orchestration_status = status_mapping.get(
            response.status.value,
            OrchestrationStatus.EXECUTION_ERROR,
        )
        messages = {
            OrchestrationStatus.SUCCESS: "The query was processed successfully.",
            OrchestrationStatus.NOT_FOUND: "No matching trial evidence was found.",
            OrchestrationStatus.VALIDATION_FAILED: "The query evidence failed validation.",
            OrchestrationStatus.EXECUTION_ERROR: "The graph query encountered an execution error.",
        }
        kwargs = {
            "status": orchestration_status,
            "message": messages[orchestration_status],
            "intent": extracted.intent.value,
            "nct_id": extracted.nct_id,
        }
        if extracted.intent == QueryIntent.TRIALS_BY_CONDITION:
            kwargs["condition_search_response"] = response
        else:
            kwargs["graph_response"] = response
        return OrchestrationResponse(**kwargs)

    except ValueError:
        return OrchestrationResponse(
            status=OrchestrationStatus.VALIDATION_FAILED,
            message="The supplied query failed validation.",
        )
    except Exception:
        return OrchestrationResponse(
            status=OrchestrationStatus.EXECUTION_ERROR,
            message="An unexpected error occurred while processing the query.",
        )
