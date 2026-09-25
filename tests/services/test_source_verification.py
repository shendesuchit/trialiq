from trialiq.services.models import GraphQueryResponse, GraphQueryStatus, ValidationResult
from trialiq.services.source_verification import (
    VerificationStatus,
    verify_graph_response_against_source,
)

NCT_ID = "NCT00000102"


def graph_response() -> GraphQueryResponse:
    return GraphQueryResponse(
        status=GraphQueryStatus.SUCCESS,
        nct_id=NCT_ID,
        evidence={
            "found": True,
            "trial": {
                "nct_id": NCT_ID,
                "brief_title": "Trial A",
                "overall_status": "COMPLETED",
                "start_date": "2020-01-01",
                "completion_date": "2020-06-01",
                "enrollment": 120,
            },
            "conditions": [{"name": "Diabetes"}],
            "interventions": [{"name": "Drug A"}],
            "sponsors": [{"name": "Sponsor A"}],
        },
        validation=ValidationResult(valid=True),
    )


class Reader:
    def __init__(self, snapshot): self.snapshot = snapshot
    def get_trial_snapshot(self, nct_id):
        assert nct_id == NCT_ID
        if isinstance(self.snapshot, Exception): raise self.snapshot
        return self.snapshot


def source_snapshot():
    return {
        "nct_id": NCT_ID,
        "brief_title": "Trial A",
        "overall_status": "COMPLETED",
        "start_date": "2020-01-01",
        "completion_date": "2020-06-01",
        "enrollment": 120,
        "conditions": ["Diabetes"],
        "interventions": ["Drug A"],
        "sponsors": ["Sponsor A"],
    }


def test_matching_graph_and_source_are_verified():
    result = verify_graph_response_against_source(graph_response(), source_reader=Reader(source_snapshot()))
    assert result.status == VerificationStatus.VERIFIED
    assert result.validation.valid is True
    assert len(result.fields) == 9
    assert not result.discrepancies


def test_collection_comparison_is_case_order_and_duplicate_insensitive():
    response = graph_response()
    response.evidence["conditions"] = [{"name": "DIABETES"}, {"name": "diabetes"}]
    result = verify_graph_response_against_source(response, source_reader=Reader(source_snapshot()))
    condition = next(item for item in result.fields if item.field == "conditions")
    assert condition.status == VerificationStatus.VERIFIED


def test_conflict_is_explicit_and_does_not_choose_a_winner():
    source = source_snapshot()
    source["overall_status"] = "RECRUITING"
    result = verify_graph_response_against_source(graph_response(), source_reader=Reader(source))
    assert result.status == VerificationStatus.CONFLICT
    assert result.validation.valid is False
    assert result.discrepancies == ["Graph/source mismatch for field: overall_status."]
    status = next(item for item in result.fields if item.field == "overall_status")
    assert status.graph_value == "COMPLETED"
    assert status.source_value == "RECRUITING"


def test_study_date_and_enrollment_conflicts_are_explicit():
    source = source_snapshot()
    source["completion_date"] = "2020-06-02"
    source["enrollment"] = 121

    result = verify_graph_response_against_source(
        graph_response(), source_reader=Reader(source)
    )

    assert result.status == VerificationStatus.CONFLICT
    assert result.discrepancies == [
        "Graph/source mismatch for field: completion_date.",
        "Graph/source mismatch for field: enrollment.",
    ]


def test_missing_source_is_reported_without_guessing():
    result = verify_graph_response_against_source(graph_response(), source_reader=Reader(None))
    assert result.status == VerificationStatus.MISSING_SOURCE
    assert result.validation.valid is False


def test_source_exception_is_sanitized():
    result = verify_graph_response_against_source(graph_response(), source_reader=Reader(RuntimeError("secret db detail")))
    assert result.status == VerificationStatus.NOT_CHECKED
    assert "secret db detail" not in " ".join(result.validation.errors)


def test_unsuccessful_graph_response_is_not_checked():
    response = graph_response()
    response.status = GraphQueryStatus.NOT_FOUND
    response.evidence = None
    result = verify_graph_response_against_source(response, source_reader=Reader(source_snapshot()))
    assert result.status == VerificationStatus.NOT_CHECKED
