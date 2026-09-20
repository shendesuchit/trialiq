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
