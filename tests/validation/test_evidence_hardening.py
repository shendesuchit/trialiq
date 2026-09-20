from trialiq.validation.evidence import validate_trial_evidence


def _evidence(nct_id: str = "NCT00000102") -> dict:
    return {
        "found": True,
        "nct_id": nct_id,
        "trial": {"nct_id": nct_id, "source_key": nct_id},
        "conditions": [],
        "interventions": [],
        "sponsors": [],
        "facilities": [],
        "designs": [],
        "eligibilities": [],
    }


def test_evidence_nct_comparison_is_case_insensitive_and_trimmed():
    result = validate_trial_evidence(_evidence(" nct00000102 "), "NCT00000102")
    assert result["valid"] is True
    assert result["errors"] == []


def test_evidence_nct_mismatch_is_rejected_after_normalization():
    result = validate_trial_evidence(_evidence("NCT00000103"), "nct00000102")
    assert result["valid"] is False
    assert "Evidence NCT ID does not match the requested NCT ID." in result["errors"]
