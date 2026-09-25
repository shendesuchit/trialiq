from trialiq.qualification.scenarios import (
    discover_batch15_candidates,
    graph_inventory,
    summarize_related_response,
    validate_related_response,
)
from trialiq.services.models import (
    GraphQueryStatus,
    RelatedTrialAggregateMetrics,
    RelatedTrialMetrics,
    RelatedTrialSearchResponse,
    ValidationResult,
)


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute_read(self, query, parameters=None):
        parameters = parameters or {}
        self.calls.append((query, parameters))

        if "MATCH (node:Trial)" in query:
            return [{"count": 602891}]
        if "MATCH (node:Condition)" in query:
            return [{"count": 131245}]
        if "MATCH (node:Intervention)" in query:
            return [{"count": 526899}]
        if "MATCH (node:Sponsor)" in query:
            return [{"count": 102617}]
        if "rel:HAS_CONDITION" in query and "RETURN count(rel)" in query:
            return [{"count": 1083806}]
        if "rel:HAS_INTERVENTION" in query and "RETURN count(rel)" in query:
            return [{"count": 1001094}]
        if "rel:SPONSORED_BY" in query and "RETURN count(rel)" in query:
            return [{"count": 961152}]

        if parameters.get("preferred_names"):
            name = parameters["preferred_names"][0]
            if "Condition" in query:
                canonical_key = name
            elif "Intervention" in query:
                canonical_key = f"{name}|drug"
            else:
                canonical_key = name
            return [
                {
                    "entity_name": name,
                    "canonical_key": canonical_key,
                    "entity_fanout": 100,
                    "seed_nct_id": "NCT00000001",
                    "brief_title": f"{name} study",
                    "overall_status": "COMPLETED",
                    "study_type": "INTERVENTIONAL",
                    "phase": "PHASE2",
                    "enrollment": 100,
                }
            ]

        if "intervention_type" in query and "BEHAVIORAL" in query:
            return [
                {
                    "entity_name": "behavioral counseling",
                    "canonical_key": "behavioral counseling|behavioral",
                    "entity_fanout": 75,
                    "seed_nct_id": "NCT00000002",
                    "brief_title": "Behavioral study",
                    "overall_status": "COMPLETED",
                    "study_type": "INTERVENTIONAL",
                    "phase": "NA",
                    "enrollment": 80,
                }
            ]
        if "trial.study_type = 'OBSERVATIONAL'" in query:
            return [
                {
                    "entity_name": "observational condition",
                    "canonical_key": "observational condition",
                    "entity_fanout": 250,
                    "seed_nct_id": "NCT00000003",
                    "brief_title": "Observational study",
                    "overall_status": "RECRUITING",
                    "study_type": "OBSERVATIONAL",
                    "phase": None,
                    "enrollment": 120,
                }
            ]
        if "loaded_trial_count, 0) >= 2" in query:
            return [
                {
                    "entity_name": "rare condition",
                    "canonical_key": "rare condition",
                    "entity_fanout": 2,
                    "seed_nct_id": "NCT00000004",
                    "brief_title": "Rare study",
                    "overall_status": "COMPLETED",
                    "study_type": "INTERVENTIONAL",
                    "phase": "PHASE1",
                    "enrollment": 20,
                }
            ]
        if "placebo|drug" in query:
            return [
                {
                    "entity_name": "placebo",
                    "canonical_key": "placebo|drug",
                    "entity_fanout": 28950,
                    "seed_nct_id": "NCT00000005",
                    "brief_title": "Placebo hub study",
                    "overall_status": "COMPLETED",
                    "study_type": "INTERVENTIONAL",
                    "phase": "PHASE2",
                    "enrollment": 150,
                }
            ]
        return []


def _related_response(*, bad_aggregate=False):
    return RelatedTrialSearchResponse(
        status=GraphQueryStatus.SUCCESS,
        seed_nct_id="NCT00000001",
        max_hops=1,
        per_hop_limit=10,
        limit=10,
        relationship_types=["HAS_CONDITION"],
        matches=[
            {
                "nct_id": "NCT00000002",
                "trial": {
                    "nct_id": "NCT00000002",
                    "overall_status": "COMPLETED",
                },
                "discovery_hop": 1,
                "connected_via": [
                    {
                        "source_nct_id": "NCT00000001",
                        "relationship_type": "HAS_CONDITION",
                        "entity": {
                            "canonical_key": "heart failure",
                            "normalized_name": "heart failure",
                            "loaded_trial_count": 25,
                        },
                        "entity_id": "HAS_CONDITION:heart failure",
                    }
                ],
                "metrics": RelatedTrialMetrics(
                    shared_condition_count=1,
                    total_shared_entity_count=1,
                    evidence_path_count=1,
                    entity_ids=["HAS_CONDITION:heart failure"],
                ),
            }
        ],
        metrics=RelatedTrialAggregateMetrics(
            related_trial_count=2 if bad_aggregate else 1,
            unique_shared_entity_count=1,
            evidence_path_count=1,
            condition_linked_trial_count=1,
        ),
        validation=ValidationResult(valid=True),
    )


def test_graph_inventory_returns_canonical_full_graph_counts():
    counts = graph_inventory(FakeConnection())
    assert counts["trials"] == 602891
    assert counts["conditions"] == 131245
    assert counts["interventions"] == 526899
    assert counts["sponsors"] == 102617
    assert counts["condition_relationships"] == 1083806


def test_discover_batch15_candidates_covers_all_realistic_families():
    candidates = discover_batch15_candidates(FakeConnection())
    names = {item.scenario for item in candidates}
    assert names == {
        "oncology_condition",
        "cardiovascular_condition",
        "metabolic_condition",
        "infectious_condition",
        "major_sponsor",
        "common_drug",
        "behavioral_intervention",
        "observational_study",
        "rare_specific_condition",
        "high_fanout_placebo",
    }
    placebo = next(item for item in candidates if item.scenario == "high_fanout_placebo")
    assert placebo.entity_fanout == 28950
    assert placebo.canonical_key == "placebo|drug"


def test_validate_related_response_accepts_consistent_metrics():
    assert validate_related_response(_related_response()) == []


def test_validate_related_response_rejects_aggregate_mismatch():
    errors = validate_related_response(_related_response(bad_aggregate=True))
    assert any("related_trial_count mismatch" in error for error in errors)


def test_summarize_related_response_keeps_evidence_fanout_and_metrics():
    summary = summarize_related_response(_related_response())
    assert summary["returned"] == 1
    assert summary["matches"][0]["shared_entities"][0]["fanout"] == 25
    assert summary["matches"][0]["metrics"]["shared_condition_count"] == 1
