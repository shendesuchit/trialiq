from trialiq.services.related_trial_metrics import (
    build_related_trial_metrics,
    stable_entity_id,
)


def test_stable_entity_id_prefers_canonical_key():
    entity = {
        "name": "Beverage consumption",
        "normalized_name": "beverage consumption",
        "canonical_key": "beverage consumption|behavioral",
        "source_id": 123,
    }
    assert (
        stable_entity_id("HAS_INTERVENTION", entity)
        == "intervention:beverage consumption|behavioral"
    )


def test_related_trial_metrics_are_signed_and_precisely_worded():
    anchor = {
        "nct_id": "NCT00000001",
        "start_date": "2020-01-10",
        "completion_date": "2020-06-10",
        "enrollment": 100,
    }
    related = {
        "nct_id": "NCT00000002",
        "start_date": "2020-01-05",
        "completion_date": "2020-05-01",
        "enrollment": 80,
        "overall_status": "COMPLETED",
    }
    paths = [
        {
            "relationship_type": "HAS_CONDITION",
            "entity": {
                "name": "Condition A",
                "canonical_key": "condition a",
            },
        },
        {
            "relationship_type": "HAS_INTERVENTION",
            "entity": {
                "name": "Drug A",
                "canonical_key": "drug a|drug",
            },
        },
    ]

    metrics = build_related_trial_metrics(anchor, related, paths)

    assert metrics["shared_condition_count"] == 1
    assert metrics["shared_intervention_count"] == 1
    assert metrics["shared_sponsor_count"] == 0
    assert metrics["total_shared_entity_count"] == 2
    assert metrics["evidence_path_count"] == 2
    assert metrics["start_date_difference_days"] == -5
    assert metrics["start_date_comparison"] == "Started 5 days before the study of interest (NCT00000001)."
    assert metrics["completion_date_difference_days"] == -40
    assert metrics["completion_date_comparison"] == "Completed 40 days before the study of interest (NCT00000001)."
    assert metrics["duration_difference_days"] == -35
    assert metrics["duration_comparison"] == "Study duration was 35 days shorter than the study of interest (NCT00000001)."
    assert metrics["enrollment_difference"] == -20
    assert metrics["enrollment_comparison"] == "Enrollment was 20 fewer participants than the study of interest (NCT00000001)."


def test_related_trial_metrics_leave_unavailable_values_null():
    metrics = build_related_trial_metrics(
        {"nct_id": "NCT00000001"},
        {"nct_id": "NCT00000002"},
        [],
    )
    assert metrics["start_date_difference_days"] is None
    assert metrics["completion_date_comparison"] is None
    assert metrics["duration_difference_days"] is None
    assert metrics["enrollment_difference"] is None


def test_related_trial_metrics_handle_same_day_same_duration_and_same_enrollment():
    anchor = {
        "nct_id": "NCT00000001",
        "start_date": "2020-01-01",
        "completion_date": "2020-01-11",
        "enrollment": "100",
    }
    related = {
        "nct_id": "NCT00000002",
        "start_date": "2020-01-01T00:00:00",
        "completion_date": "2020-01-11",
        "enrollment": 100,
        "overall_status": "COMPLETED",
    }

    metrics = build_related_trial_metrics(anchor, related, [])

    assert metrics["start_date_difference_days"] == 0
    assert metrics["start_date_comparison"] == "Started on the same date as the study of interest (NCT00000001)."
    assert metrics["completion_date_difference_days"] == 0
    assert metrics["completion_date_comparison"] == "Completed on the same date as the study of interest (NCT00000001)."
    assert metrics["duration_difference_days"] == 0
    assert metrics["duration_comparison"] == "Study duration matched the study of interest (NCT00000001)."
    assert metrics["enrollment_difference"] == 0
    assert metrics["enrollment_comparison"] == "Enrollment matched the study of interest (NCT00000001)."


def test_related_trial_metrics_do_not_guess_invalid_dates_or_enrollment():
    metrics = build_related_trial_metrics(
        {
            "start_date": "not-a-date",
            "completion_date": "2020-01-10",
            "enrollment": 100,
        },
        {
            "start_date": "2020-01-01",
            "completion_date": "also-not-a-date",
            "enrollment": "unknown",
        },
        [],
    )

    assert metrics["start_date_difference_days"] is None
    assert metrics["completion_date_difference_days"] is None
    assert metrics["duration_difference_days"] is None
    assert metrics["enrollment_difference"] is None


def test_related_trial_metrics_use_neutral_completion_wording_for_active_trial():
    metrics = build_related_trial_metrics(
        {
            "nct_id": "NCT03416088",
            "completion_date": "2020-12-31",
        },
        {
            "nct_id": "NCT07764198",
            "overall_status": "RECRUITING",
            "completion_date": "2026-12-31",
        },
        [],
    )

    assert metrics["completion_date_comparison"] == (
        "Completion date is 2191 days after the study of interest (NCT03416088)."
    )
