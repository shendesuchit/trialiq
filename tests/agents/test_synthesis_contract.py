from trialiq.agents.models import RetrievalResult, StructuredFinding, StructuredSynthesis, AgentStatus
from trialiq.agents.synthesis_contract import validate_structured_synthesis
from trialiq.services.models import GraphQueryStatus, RelatedTrialSearchResponse, ValidationResult


def _retrieval():
    return RetrievalResult(
        status=AgentStatus.SUCCESS,
        related_trial_response=RelatedTrialSearchResponse(
            status=GraphQueryStatus.SUCCESS,
            seed_nct_id="NCT03416088",
            max_hops=1,
            per_hop_limit=5,
            limit=10,
            relationship_types=["HAS_CONDITION"],
            overall_statuses=["COMPLETED"],
            matches=[
                {
                    "nct_id": "NCT04214743",
                    "trial": {"nct_id": "NCT04214743", "brief_title": "Related trial"},
                    "discovery_hop": 1,
                    "connected_via": [
                        {
                            "source_nct_id": "NCT03416088",
                            "relationship_type": "HAS_CONDITION",
                            "entity": {"name": "Retinal Microcirculation Disorder"},
                        }
                    ],
                }
            ],
            validation=ValidationResult(valid=True),
        ),
    )


def test_structured_synthesis_accepts_known_evidence_ids():
    synthesis = StructuredSynthesis(
        headline="Connected trial found",
        summary="The trial shares a condition with the anchor.",
        key_findings=[
            StructuredFinding(
                statement="The trials share a condition.",
                evidence_ids=["path:NCT04214743:0"],
            )
        ],
    )
    assert validate_structured_synthesis(synthesis, _retrieval()) == []


def test_structured_synthesis_rejects_unknown_evidence_ids():
    synthesis = StructuredSynthesis(
        headline="Connected trial found",
        summary="The trial shares a condition with the anchor.",
        key_findings=[
            StructuredFinding(
                statement="Unsupported claim.",
                evidence_ids=["path:invented:999"],
            )
        ],
    )
    errors = validate_structured_synthesis(synthesis, _retrieval())
    assert errors
    assert "unknown evidence IDs" in errors[0]


def test_metric_findings_must_reproduce_deterministic_comparison_text():
    from trialiq.agents.synthesis_contract import build_evidence_catalog
    from trialiq.services.models import RelatedTrialMetrics

    retrieval = _retrieval()
    response = retrieval.related_trial_response
    assert response is not None
    response.matches[0].metrics = RelatedTrialMetrics(
        shared_condition_count=1,
        total_shared_entity_count=1,
        evidence_path_count=1,
        completion_date_difference_days=-40,
        completion_date_comparison="Completed 40 days before the study of interest (NCT03416088).",
    )
    catalog = build_evidence_catalog(retrieval)
    metric_id = "metric:NCT04214743:completion_date_difference_days"
    assert any(item["evidence_id"] == metric_id for item in catalog)

    valid = StructuredSynthesis(
        headline="Timeline comparison",
        summary="The deterministic comparison is available.",
        key_findings=[
            StructuredFinding(
                statement="Completed 40 days before the study of interest (NCT03416088).",
                evidence_ids=[metric_id],
            )
        ],
    )
    assert validate_structured_synthesis(valid, retrieval) == []

    invalid = valid.model_copy(
        update={
            "key_findings": [
                StructuredFinding(
                    statement="Completed 41 days before the study of interest (NCT03416088).",
                    evidence_ids=[metric_id],
                )
            ]
        }
    )
    errors = validate_structured_synthesis(invalid, retrieval)
    assert errors
    assert "deterministic metric text" in errors[0]
