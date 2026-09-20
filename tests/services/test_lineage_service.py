"""Unit tests for the TrialIQ lineage extraction service."""

from unittest.mock import patch

from trialiq.services.lineage_service import get_trial_lineage
from trialiq.services.models import GraphQueryResponse, GraphQueryStatus, ValidationResult


def _graph_response(evidence: dict) -> GraphQueryResponse:
    return GraphQueryResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id="NCT00000102",
        evidence=evidence,
        validation=ValidationResult(valid=True, errors=[], warnings=[]),
    )


def test_get_trial_lineage_extracts_source_metadata():
    evidence = {
        "found": True,
        "nct_id": "NCT00000102",
        "trial": {
            "nct_id": "NCT00000102",
            "source_table": "studies",
            "source_key": "study-NCT00000102",
            "source_id": None,
        },
        "conditions": [
            {
                "nct_id": "NCT00000102",
                "source_table": "conditions",
                "source_key": "condition-1",
                "source_id": 1,
            }
        ],
    }

    with patch(
        "trialiq.services.lineage_service.query_trial_by_nct_id",
        return_value=_graph_response(evidence),
    ):
        result = get_trial_lineage("nCT00000102")

    assert result["status"] == "SUCCESS"
    assert result["nct_id"] == "NCT00000102"
    assert result["source_count"] == 2
    assert result["records"][0]["collection"] == "trial"
    assert result["records"][1]["source_table"] == "conditions"


def test_get_trial_lineage_preserves_validation_metadata():
    evidence = {
        "found": True,
        "nct_id": "NCT00000102",
        "trial": {},
    }

    with patch(
        "trialiq.services.lineage_service.query_trial_by_nct_id",
        return_value=_graph_response(evidence),
    ):
        result = get_trial_lineage("NCT00000102")

    assert result["validation"] == {
        "valid": True,
        "errors": [],
        "warnings": [],
    }
