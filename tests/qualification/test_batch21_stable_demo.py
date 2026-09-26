from trialiq.qualification.stable_demo import (
    ProbeSummary,
    comparison_coverage,
    is_advanced_probe,
    is_hitl_probe,
    is_intermediate_probe,
    select_best_advanced,
    select_best_hitl,
    select_best_intermediate,
)


def _probe(
    seed: str,
    *,
    returned: int,
    completion: int,
    duration: int,
    enrollment: int,
    relationship: str = "HAS_CONDITION",
    statuses: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> ProbeSummary:
    return ProbeSummary(
        scenario=seed,
        seed_nct_id=seed,
        relationship_types=(relationship,),
        overall_statuses=statuses,
        returned=returned,
        aggregate_metrics={
            "completion_comparable_trial_count": completion,
            "duration_comparable_trial_count": duration,
            "enrollment_comparable_trial_count": enrollment,
        },
        metric_errors=errors,
    )


def test_intermediate_requires_final_candidate_set_between_two_and_six():
    assert is_intermediate_probe(_probe("NCT00000001", returned=2, completion=0, duration=0, enrollment=0))
    assert is_intermediate_probe(_probe("NCT00000002", returned=6, completion=0, duration=0, enrollment=0))
    assert not is_intermediate_probe(_probe("NCT00000003", returned=1, completion=0, duration=0, enrollment=0))
    assert not is_intermediate_probe(_probe("NCT00000004", returned=7, completion=0, duration=0, enrollment=0))


def test_intermediate_rejects_metric_consistency_errors():
    probe = _probe(
        "NCT00000001",
        returned=4,
        completion=4,
        duration=4,
        enrollment=4,
        errors=("aggregate mismatch",),
    )
    assert not is_intermediate_probe(probe)


def test_advanced_requires_two_comparison_dimensions_at_eighty_percent():
    strong = _probe("NCT00000001", returned=5, completion=5, duration=4, enrollment=4)
    weak = _probe("NCT00000002", returned=5, completion=5, duration=3, enrollment=3)

    coverage = comparison_coverage(strong)
    assert coverage.completion == 1.0
    assert coverage.duration == 0.8
    assert coverage.enrollment == 0.8
    assert is_advanced_probe(strong)
    assert not is_advanced_probe(weak)


def test_hitl_requires_more_than_six_candidates():
    assert not is_hitl_probe(_probe("NCT00000001", returned=6, completion=6, duration=6, enrollment=6))
    assert is_hitl_probe(_probe("NCT00000002", returned=7, completion=7, duration=7, enrollment=7))


def test_selectors_honor_seed_exclusions_and_prefer_high_quality_probes():
    advanced_best = _probe("NCT00000001", returned=5, completion=5, duration=5, enrollment=5)
    intermediate_best = _probe("NCT00000002", returned=4, completion=2, duration=2, enrollment=2)
    hitl_best = _probe("NCT00000003", returned=10, completion=10, duration=10, enrollment=10)
    probes = [advanced_best, intermediate_best, hitl_best]

    assert select_best_advanced(probes) == advanced_best
    assert select_best_intermediate(probes, excluded_seed_ids={"NCT00000001"}) == intermediate_best
    assert select_best_hitl(probes) == hitl_best
