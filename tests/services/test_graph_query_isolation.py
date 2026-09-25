

def test_related_trial_service_rejects_unbounded_hops():
    from trialiq.services.graph_query_service import query_related_trials
    from trialiq.services.models import GraphQueryStatus

    result = query_related_trials("NCT00000001", max_hops=3)
    assert result.status == GraphQueryStatus.VALIDATION_FAILED
    assert result.validation.valid is False


def test_related_trial_service_sanitizes_execution_error():
    from unittest.mock import patch
    from trialiq.services.graph_query_service import query_related_trials
    from trialiq.services.models import GraphQueryStatus

    with patch(
        "trialiq.services.graph_query_service.find_related_trials_bounded",
        side_effect=RuntimeError("secret neo4j detail"),
    ):
        result = query_related_trials("NCT00000001")
    assert result.status == GraphQueryStatus.EXECUTION_ERROR
    assert "secret neo4j detail" not in " ".join(result.validation.errors)


def test_related_trial_service_forwards_normalized_filters():
    from unittest.mock import patch
    from trialiq.services.graph_query_service import query_related_trials
    from trialiq.services.models import GraphQueryStatus

    with patch(
        "trialiq.services.graph_query_service.find_related_trials_bounded",
        return_value={"found": True, "seed_nct_id": "NCT00000001", "matches": []},
    ) as traversal:
        result = query_related_trials(
            "NCT00000001",
            relationship_types=["has_intervention", "HAS_CONDITION"],
            overall_statuses=["completed"],
        )

    traversal.assert_called_once_with(
        "NCT00000001",
        2,
        20,
        50,
        relationship_types=["HAS_INTERVENTION", "HAS_CONDITION"],
        overall_statuses=["COMPLETED"],
    )
    assert result.status == GraphQueryStatus.NOT_FOUND
    assert result.relationship_types == ["HAS_INTERVENTION", "HAS_CONDITION"]
    assert result.overall_statuses == ["COMPLETED"]


def test_related_trial_service_adds_stable_entity_ids_and_deterministic_metrics():
    from unittest.mock import patch
    from trialiq.services.graph_query_service import query_related_trials
    from trialiq.services.models import GraphQueryStatus

    traversal_result = {
        "found": True,
        "seed_nct_id": "NCT00000001",
        "anchor_trial": {
            "nct_id": "NCT00000001",
            "start_date": "2020-01-10",
            "completion_date": "2020-06-10",
            "enrollment": 100,
        },
        "matches": [
            {
                "nct_id": "NCT00000002",
                "trial": {
                    "nct_id": "NCT00000002",
                    "brief_title": "Related trial",
                    "start_date": "2020-01-05",
                    "completion_date": "2020-05-01",
                    "enrollment": 80,
                    "overall_status": "COMPLETED",
                },
                "discovery_hop": 1,
                "connected_via": [
                    {
                        "source_nct_id": "NCT00000001",
                        "relationship_type": "HAS_CONDITION",
                        "entity": {
                            "name": "Condition A",
                            "canonical_key": "condition a",
                        },
                    }
                ],
            }
        ],
    }
    with patch(
        "trialiq.services.graph_query_service.find_related_trials_bounded",
        return_value=traversal_result,
    ):
        result = query_related_trials("NCT00000001", max_hops=1)

    assert result.status == GraphQueryStatus.SUCCESS
    assert result.anchor_trial is not None
    assert result.metrics.related_trial_count == 1
    assert result.metrics.unique_shared_entity_count == 1
    assert result.metrics.evidence_path_count == 1
    assert result.metrics.condition_linked_trial_count == 1
    assert result.metrics.intervention_linked_trial_count == 0
    assert result.metrics.sponsor_linked_trial_count == 0
    assert result.metrics.multi_factor_trial_count == 0
    assert result.metrics.completion_comparable_trial_count == 1
    assert result.metrics.duration_comparable_trial_count == 1
    assert result.metrics.enrollment_comparable_trial_count == 1
    match = result.matches[0]
    assert match.connected_via[0].entity_id == "condition:condition a"
    assert match.metrics is not None
    assert match.metrics.completion_date_difference_days == -40
    assert match.metrics.completion_date_comparison == "Completed 40 days before the study of interest (NCT00000001)."
    assert match.metrics.enrollment_difference == -20
