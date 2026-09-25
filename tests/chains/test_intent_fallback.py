from trialiq.chains.intent_fallback import extract_supported_intent_fallback
from trialiq.services.query_intent import QueryIntent


def test_demo_related_query_fallback_preserves_explicit_filters():
    result = extract_supported_intent_fallback(
        "Find completed trials connected to NCT03416088 through its conditions or interventions. "
        "Explain exactly why they are connected."
    )

    assert result is not None
    assert result.intent == QueryIntent.RELATED_TRIALS
    assert result.nct_id == "NCT03416088"
    assert result.relationship_types == ["HAS_CONDITION", "HAS_INTERVENTION"]
    assert result.overall_statuses == ["COMPLETED"]


def test_fallback_stays_bounded_for_unsupported_general_question():
    assert extract_supported_intent_fallback("What trial should I choose?") is None


def test_full_demo_question_is_supported_by_bounded_fallback():
    result = extract_supported_intent_fallback(
        "Find completed trials connected to NCT03416088 through its conditions or interventions. "
        "Explain exactly why they are connected, compare their completion timelines and enrollment, "
        "and show the evidence supporting each conclusion."
    )

    assert result is not None
    assert result.intent == QueryIntent.RELATED_TRIALS
    assert result.nct_id == "NCT03416088"
    assert result.relationship_types == ["HAS_CONDITION", "HAS_INTERVENTION"]
    assert result.overall_statuses == ["COMPLETED"]
