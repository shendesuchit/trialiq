import pytest

from trialiq.services.query_intent import QueryIntent, QueryIntentRequest


@pytest.mark.parametrize("nct_id", ["NCT123", "NCT1234567", "NCT123456789"])
def test_nct_id_requires_exactly_eight_digits(nct_id: str):
    with pytest.raises(ValueError, match="exactly 8 digits"):
        QueryIntentRequest(intent=QueryIntent.TRIAL_OVERVIEW, nct_id=nct_id)


def test_nct_id_is_normalized_to_uppercase():
    request = QueryIntentRequest(
        intent=QueryIntent.TRIAL_OVERVIEW,
        nct_id=" nct00000102 ",
    )
    assert request.nct_id == "NCT00000102"


def test_intervention_intent_requires_intervention_term():
    with pytest.raises(ValueError):
        QueryIntentRequest(intent=QueryIntent.TRIALS_BY_INTERVENTION)


def test_sponsor_intent_requires_sponsor_term():
    with pytest.raises(ValueError):
        QueryIntentRequest(intent=QueryIntent.TRIALS_BY_SPONSOR)


def test_shared_entity_intent_requires_two_distinct_nct_ids():
    with pytest.raises(ValueError):
        QueryIntentRequest(intent=QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS, nct_id="NCT00000102", nct_id_b="NCT00000102")
    request = QueryIntentRequest(intent=QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS, nct_id="nct00000102", nct_id_b="nct00000103", limit=4)
    assert request.nct_id == "NCT00000102"
    assert request.nct_id_b == "NCT00000103"


def test_related_trials_requires_seed_and_bounds_hops():
    with pytest.raises(ValueError):
        QueryIntentRequest(intent=QueryIntent.RELATED_TRIALS, max_hops=2)
    with pytest.raises(ValueError):
        QueryIntentRequest(intent=QueryIntent.RELATED_TRIALS, nct_id="NCT00000102", max_hops=3)


def test_related_trials_normalizes_bounded_request():
    request = QueryIntentRequest(
        intent=QueryIntent.RELATED_TRIALS,
        nct_id="nct00000102",
        max_hops=2,
        per_hop_limit=7,
        limit=12,
    )
    assert request.nct_id == "NCT00000102"
    assert request.max_hops == 2
    assert request.per_hop_limit == 7
    assert request.limit == 12


def test_related_trials_normalizes_allowlisted_relationships_and_statuses():
    request = QueryIntentRequest(
        intent=QueryIntent.RELATED_TRIALS,
        nct_id="NCT00000102",
        relationship_types=["has_intervention", "HAS_CONDITION", "has_intervention"],
        overall_statuses=["completed", "COMPLETED"],
    )
    assert request.relationship_types == ["HAS_INTERVENTION", "HAS_CONDITION"]
    assert request.overall_statuses == ["COMPLETED"]


def test_related_trials_rejects_non_allowlisted_relationship_type():
    with pytest.raises(ValueError, match="Unsupported related-trial relationship type"):
        QueryIntentRequest(
            intent=QueryIntent.RELATED_TRIALS,
            nct_id="NCT00000102",
            relationship_types=["HAS_FACILITY"],
        )


def test_non_related_intent_does_not_require_related_relationship_filters():
    request = QueryIntentRequest(
        intent=QueryIntent.TRIAL_OVERVIEW,
        nct_id="NCT00000102",
        relationship_types=[],
    )
    assert request.relationship_types == []
