"""Deterministic helpers for selecting the stable TrialIQ demo ladder.

These helpers operate only on qualification probe summaries. They do not perform
network, LLM, MCP, or database calls. Live probing stays in the Batch-21 runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


INTERMEDIATE_MIN = 2
INTERMEDIATE_MAX = 6
HITL_MIN = 7
ADVANCED_COVERAGE_MIN = 0.80


@dataclass(frozen=True)
class ProbeSummary:
    """Compact, deterministic view of one bounded related-trial probe."""

    scenario: str
    seed_nct_id: str
    relationship_types: tuple[str, ...]
    overall_statuses: tuple[str, ...]
    returned: int
    aggregate_metrics: dict[str, int]
    metric_errors: tuple[str, ...] = ()
    title: str | None = None
    overall_status: str | None = None
    phase: str | None = None
    study_type: str | None = None

    @property
    def valid(self) -> bool:
        return self.returned > 0 and not self.metric_errors


@dataclass(frozen=True)
class ComparisonCoverage:
    completion: float
    duration: float
    enrollment: float

    @property
    def dimensions_at_or_above_80_percent(self) -> int:
        return sum(
            value >= ADVANCED_COVERAGE_MIN
            for value in (self.completion, self.duration, self.enrollment)
        )

    @property
    def mean(self) -> float:
        return (self.completion + self.duration + self.enrollment) / 3.0


def _ratio(value: int | None, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, float(value or 0) / float(total)))


def comparison_coverage(probe: ProbeSummary) -> ComparisonCoverage:
    """Return deterministic comparison completeness for a probe."""
    metrics = probe.aggregate_metrics
    return ComparisonCoverage(
        completion=_ratio(metrics.get("completion_comparable_trial_count"), probe.returned),
        duration=_ratio(metrics.get("duration_comparable_trial_count"), probe.returned),
        enrollment=_ratio(metrics.get("enrollment_comparable_trial_count"), probe.returned),
    )


def is_intermediate_probe(probe: ProbeSummary) -> bool:
    return (
        probe.valid
        and INTERMEDIATE_MIN <= probe.returned <= INTERMEDIATE_MAX
        and len(probe.relationship_types) == 1
    )


def is_advanced_probe(probe: ProbeSummary) -> bool:
    if not is_intermediate_probe(probe):
        return False
    coverage = comparison_coverage(probe)
    return coverage.dimensions_at_or_above_80_percent >= 2


def is_hitl_probe(probe: ProbeSummary) -> bool:
    return probe.valid and probe.returned >= HITL_MIN


def _intermediate_score(probe: ProbeSummary) -> tuple[float, int, int, str]:
    # Prefer a useful 4-6 study comparison set, then richer metadata.
    coverage = comparison_coverage(probe)
    target_distance = abs(4 - probe.returned)
    status_specificity = 1 if probe.overall_statuses else 0
    return (
        -float(target_distance),
        status_specificity,
        int(round(coverage.mean * 1000)),
        probe.seed_nct_id,
    )


def _advanced_score(probe: ProbeSummary) -> tuple[int, int, int, str]:
    coverage = comparison_coverage(probe)
    return (
        coverage.dimensions_at_or_above_80_percent,
        int(round(coverage.mean * 1000)),
        probe.returned,
        probe.seed_nct_id,
    )


def _hitl_score(probe: ProbeSummary) -> tuple[int, int, str]:
    coverage = comparison_coverage(probe)
    return (
        int(round(coverage.mean * 1000)),
        probe.returned,
        probe.seed_nct_id,
    )


def select_best_intermediate(
    probes: Iterable[ProbeSummary],
    *,
    excluded_seed_ids: set[str] | None = None,
) -> ProbeSummary | None:
    excluded = excluded_seed_ids or set()
    candidates = [
        probe
        for probe in probes
        if probe.seed_nct_id not in excluded and is_intermediate_probe(probe)
    ]
    return max(candidates, key=_intermediate_score, default=None)


def select_best_advanced(
    probes: Iterable[ProbeSummary],
    *,
    excluded_seed_ids: set[str] | None = None,
) -> ProbeSummary | None:
    excluded = excluded_seed_ids or set()
    candidates = [
        probe
        for probe in probes
        if probe.seed_nct_id not in excluded and is_advanced_probe(probe)
    ]
    return max(candidates, key=_advanced_score, default=None)


def select_best_hitl(
    probes: Iterable[ProbeSummary],
    *,
    excluded_seed_ids: set[str] | None = None,
) -> ProbeSummary | None:
    excluded = excluded_seed_ids or set()
    candidates = [
        probe
        for probe in probes
        if probe.seed_nct_id not in excluded and is_hitl_probe(probe)
    ]
    return max(candidates, key=_hitl_score, default=None)


def probe_to_dict(probe: ProbeSummary) -> dict[str, Any]:
    coverage = comparison_coverage(probe)
    return {
        "scenario": probe.scenario,
        "seed_nct_id": probe.seed_nct_id,
        "title": probe.title,
        "overall_status": probe.overall_status,
        "phase": probe.phase,
        "study_type": probe.study_type,
        "relationship_types": list(probe.relationship_types),
        "overall_statuses": list(probe.overall_statuses),
        "returned": probe.returned,
        "aggregate_metrics": dict(probe.aggregate_metrics),
        "metric_errors": list(probe.metric_errors),
        "comparison_coverage": {
            "completion": round(coverage.completion, 3),
            "duration": round(coverage.duration, 3),
            "enrollment": round(coverage.enrollment, 3),
            "dimensions_at_or_above_80_percent": (
                coverage.dimensions_at_or_above_80_percent
            ),
        },
    }
