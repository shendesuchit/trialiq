# Change Start: Add deterministic answer formatter tests

from trialiq.services.answer_formatter import (
    extract_evidence_sources,
    format_trial_overview,
)
from trialiq.services.models import (
    AnswerStatus,
    GraphQueryResponse,
    GraphQueryStatus,
    ValidationResult,
)


def _valid_graph_response() -> GraphQueryResponse:
    return GraphQueryResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id="NCT00000102",
        evidence={
            "found": True,
            "nct_id": "NCT00000102",
            "trial": {
                "nct_id": "NCT00000102",
                "brief_title": "Test clinical trial",
                "overall_status": "COMPLETED",
                "study_type": "INTERVENTIONAL",
                "phase": "PHASE1",
                "enrollment": 100,
                "start_date": "2000-01-01",
                "completion_date": "2001-01-01",
                "why_stopped": None,
                "source_table": "studies",
                "source_key": "NCT00000102",
                "source_id": 1,
            },
            "conditions": [
                {
                    "nct_id": "NCT00000102",
                    "name": "Test condition",
                    "source_table": "conditions",
                    "source_key": "condition-1",
                    "source_id": 2,
                }
            ],
            "interventions": [],
            "sponsors": [],
            "facilities": [],
            "designs": [
                {
                    "nct_id": "NCT00000102",
                    "allocation": "RANDOMIZED",
                    "masking": "NONE",
                    "intervention_model": "PARALLEL",
                    "observational_model": None,
                    "time_perspective": None,
                }
            ],
            "eligibilities": [],
        },
        validation=ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
        ),
    )


def test_format_trial_overview_returns_grounded_answer():
    result = format_trial_overview(
        _valid_graph_response(),
        "Give me an overview of NCT00000102",
    )

    assert result.status == AnswerStatus.GROUNDED
    assert "Trial ID: NCT00000102" in result.answer
    assert "Brief title: Test clinical trial" in result.answer
    assert "Overall status: COMPLETED" in result.answer
    assert "Conditions: Test condition" in result.answer


def test_format_trial_overview_rejects_invalid_validation():
    graph_response = _valid_graph_response()
    graph_response.validation = ValidationResult(
        valid=False,
        errors=["Evidence failed validation."],
        warnings=[],
    )

    result = format_trial_overview(
        graph_response,
        "Give me an overview of NCT00000102",
    )

    assert result.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert "validated graph evidence is unavailable" in result.answer
    assert result.limitations == [
        "Graph evidence was not validated successfully."
    ]


def test_format_trial_overview_reports_missing_fields():
    graph_response = _valid_graph_response()
    graph_response.evidence["trial"]["brief_title"] = None
    graph_response.evidence["trial"]["phase"] = None

    result = format_trial_overview(
        graph_response,
        "Give me an overview of NCT00000102",
    )

    assert result.status == AnswerStatus.GROUNDED
    assert "Brief title: Not available" in result.answer
    assert "Phase: Not available" in result.answer
    assert "Brief title was not available." in result.limitations
    assert "Phase was not available." in result.limitations


def test_extract_evidence_sources_deduplicates_source_keys():
    evidence = {
        "trial": {
            "source_table": "studies",
            "source_key": "study-1",
            "source_id": 1,
        },
        "conditions": [
            {
                "source_table": "conditions",
                "source_key": "condition-1",
                "source_id": 2,
            },
            {
                "source_table": "conditions",
                "source_key": "condition-1",
                "source_id": 2,
            },
        ],
    }

    sources = extract_evidence_sources(evidence)

    assert len(sources) == 2
    assert sources[0].source_key == "study-1"
    assert sources[1].source_key == "condition-1"


def test_format_trial_overview_rejects_missing_trial_evidence():
    graph_response = _valid_graph_response()
    graph_response.evidence["trial"] = None

    result = format_trial_overview(
        graph_response,
        "Give me an overview of NCT00000102",
    )

    assert result.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert result.answer == "No trial evidence was available for this request."


# Change End