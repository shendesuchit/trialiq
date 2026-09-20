# Change Start: Add deterministic evidence validation tests

from trialiq.validation.evidence import validate_trial_evidence


def _valid_evidence() -> dict:
    return {
        "found": True,
        "nct_id": "NCT00000102",
        "trial": {
            "nct_id": "NCT00000102",
            "source_key": "NCT00000102",
        },
        "conditions": [],
        "interventions": [],
        "sponsors": [],
        "facilities": [],
        "designs": [],
        "eligibilities": [],
    }


def test_valid_trial_evidence_passes():
    result = validate_trial_evidence(
        _valid_evidence(),
        "NCT00000102",
    )

    assert result["valid"] is True
    assert result["errors"] == []


def test_missing_trial_is_rejected():
    evidence = _valid_evidence()
    evidence["found"] = False

    result = validate_trial_evidence(
        evidence,
        "NCT00000102",
    )

    assert result["valid"] is False
    assert "Requested trial was not found." in result["errors"]


def test_mismatched_nct_id_is_rejected():
    evidence = _valid_evidence()
    evidence["nct_id"] = "NCT99999999"

    result = validate_trial_evidence(
        evidence,
        "NCT00000102",
    )

    assert result["valid"] is False
    assert (
        "Evidence NCT ID does not match the requested NCT ID."
        in result["errors"]
    )


def test_missing_collection_is_rejected():
    evidence = _valid_evidence()
    del evidence["facilities"]

    result = validate_trial_evidence(
        evidence,
        "NCT00000102",
    )

    assert result["valid"] is False
    assert (
        "Missing evidence collection: facilities."
        in result["errors"]
    )


def test_collection_with_invalid_record_is_rejected():
    evidence = _valid_evidence()
    evidence["conditions"] = ["invalid-record"]

    result = validate_trial_evidence(
        evidence,
        "NCT00000102",
    )

    assert result["valid"] is False
    assert "conditions[0] must be a dictionary." in result["errors"]


def test_missing_source_metadata_generates_warnings():
    evidence = _valid_evidence()
    evidence["trial"] = {
        "nct_id": "NCT00000102",
    }
    evidence["conditions"] = [
        {
            "nct_id": "NCT00000102",
        }
    ]

    result = validate_trial_evidence(
        evidence,
        "NCT00000102",
    )

    assert result["valid"] is True
    assert "Trial record has no source_key." in result["warnings"]
    assert "conditions[0] has no source_key." in result["warnings"]
    assert "conditions[0] has no source_table." in result["warnings"]


# Change End