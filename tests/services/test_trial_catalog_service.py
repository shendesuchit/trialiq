from unittest.mock import patch

from trialiq.services.trial_catalog_service import get_trial_catalog


def test_catalog_builds_related_trial_questions_for_connected_nodes():
    raw = {
        "search": "",
        "limit": 50,
        "offset": 0,
        "total_count": 1,
        "trials": [
            {
                "nct_id": "NCT03416088",
                "brief_title": "Demo seed",
                "official_title": None,
                "overall_status": "COMPLETED",
                "related_trial_count": 3,
                "relationship_types": [
                    "HAS_CONDITION",
                    "HAS_INTERVENTION",
                    "SPONSORED_BY",
                ],
            }
        ],
    }

    with patch(
        "trialiq.services.trial_catalog_service.list_trial_catalog",
        return_value=raw,
    ):
        result = get_trial_catalog()

    trial = result.trials[0]
    assert trial.has_graph_neighbors is True
    assert trial.related_trial_count == 3
    assert trial.suggested_questions[0].kind == "related_trials"
    assert "NCT03416088" in trial.suggested_questions[0].question
    assert "Do not infer" in trial.suggested_questions[0].question


def test_catalog_builds_overview_questions_for_trial_without_graph_neighbors():
    raw = {
        "search": "",
        "limit": 50,
        "offset": 0,
        "total_count": 1,
        "trials": [
            {
                "nct_id": "NCT09999999",
                "brief_title": "Isolated trial",
                "official_title": None,
                "overall_status": "RECRUITING",
                "related_trial_count": 0,
                "relationship_types": [],
            }
        ],
    }

    with patch(
        "trialiq.services.trial_catalog_service.list_trial_catalog",
        return_value=raw,
    ):
        result = get_trial_catalog()

    trial = result.trials[0]
    assert trial.has_graph_neighbors is False
    assert trial.related_trial_count == 0
    assert {item.kind for item in trial.suggested_questions} == {
        "overview",
        "metadata",
        "source_evidence",
    }
    assert all("NCT09999999" in item.question for item in trial.suggested_questions)


def test_catalog_reports_has_more_for_paginated_results():
    raw = {
        "search": "trial",
        "limit": 2,
        "offset": 2,
        "total_count": 8,
        "trials": [
            {
                "nct_id": "NCT00000003",
                "related_trial_count": 0,
                "relationship_types": [],
            },
            {
                "nct_id": "NCT00000004",
                "related_trial_count": 0,
                "relationship_types": [],
            },
        ],
    }

    with patch(
        "trialiq.services.trial_catalog_service.list_trial_catalog",
        return_value=raw,
    ) as lookup:
        result = get_trial_catalog(" trial ", limit=2, offset=2)

    lookup.assert_called_once_with("trial", limit=2, offset=2)
    assert result.query == "trial"
    assert result.has_more is True


def test_catalog_preserves_capped_count_signal_for_presentation():
    raw = {
        "search": "",
        "limit": 50,
        "offset": 0,
        "total_count": 1,
        "trials": [
            {
                "nct_id": "NCT00000001",
                "related_trial_count": 200,
                "related_trial_count_capped": True,
                "relationship_types": ["HAS_INTERVENTION"],
            }
        ],
    }
    with patch(
        "trialiq.services.trial_catalog_service.list_trial_catalog",
        return_value=raw,
    ):
        result = get_trial_catalog()

    assert result.trials[0].related_trial_count == 200
    assert result.trials[0].related_trial_count_capped is True
    assert result.trials[0].has_graph_neighbors is True
