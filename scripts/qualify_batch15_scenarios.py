"""Qualify realistic TrialIQ scenarios against the full canonical AACT graph.

Batch 15 is deliberately read-only.  It discovers representative scenario seeds
with fixed Cypher, then executes product retrieval through FastMCP.  A small
set of normal natural-language questions is also run through the real agent
workflow while a transparent proxy counts logical structured LLM invocations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
from unittest.mock import patch

from trialiq.agents.api import run_agent_question
from trialiq.agents.mcp_client import FastMCPRetrievalClient
from trialiq.graph.connection import Neo4jConnection
from trialiq.llm.service import get_llm_service
from trialiq.qualification.scenarios import (
    ScenarioCandidate,
    discover_batch15_candidates,
    graph_inventory,
    summarize_related_response,
    validate_related_response,
)
from trialiq.services.models import GraphQueryStatus
from trialiq.services.trial_catalog_service import get_trial_catalog


EXPECTED_SCENARIOS = {
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

MINIMUM_FULL_GRAPH_TRIALS = 500_000
SCENARIO_RELATED_LIMIT = 10
SCENARIO_PER_HOP_LIMIT = 10


def _timed(call: Callable[[], Any]) -> tuple[Any, float]:
    started = perf_counter()
    value = call()
    return value, round((perf_counter() - started) * 1000, 3)


def _mcp_exact_search(
    client: FastMCPRetrievalClient,
    candidate: ScenarioCandidate,
) -> tuple[Any, float]:
    if candidate.entity_type == "condition":
        return _timed(
            lambda: client.search_trials_by_condition(candidate.entity_name, limit=20)
        )
    if candidate.entity_type == "intervention":
        return _timed(
            lambda: client.search_trials_by_intervention(candidate.entity_name, limit=20)
        )
    if candidate.entity_type == "sponsor":
        return _timed(
            lambda: client.search_trials_by_sponsor(candidate.entity_name, limit=20)
        )
    raise ValueError(f"Unsupported Batch-15 entity type: {candidate.entity_type}")


def _summarize_exact_search(response: Any) -> dict[str, Any]:
    matches = list(response.matches)
    payload: dict[str, Any] = {
        "status": response.status.value,
        "returned": len(matches),
        "nct_ids": [item.nct_id for item in matches],
    }
    if hasattr(response, "condition"):
        payload["query"] = response.condition
        payload["matched_canonical_keys"] = sorted(
            {
                str(entity.get("canonical_key"))
                for item in matches
                for entity in item.matched_conditions
                if entity.get("canonical_key")
            }
        )
    else:
        payload["query"] = response.query
        payload["matched_canonical_keys"] = sorted(
            {
                str(entity.get("canonical_key"))
                for item in matches
                for entity in item.matched_entities
                if entity.get("canonical_key")
            }
        )
    return payload


def _qualify_one_mcp_scenario(
    client: FastMCPRetrievalClient,
    candidate: ScenarioCandidate,
) -> dict[str, Any]:
    evidence, evidence_ms = _timed(
        lambda: client.get_trial_evidence(candidate.seed_nct_id)
    )
    exact, search_ms = _mcp_exact_search(client, candidate)
    related, related_ms = _timed(
        lambda: client.find_related_trials(
            candidate.seed_nct_id,
            1,
            SCENARIO_PER_HOP_LIMIT,
            SCENARIO_RELATED_LIMIT,
            [candidate.relationship_type],
            [],
        )
    )
    metric_errors = validate_related_response(related)

    comparison = None
    comparison_ms = None
    comparison_passed = True
    if related.matches:
        first_related = related.matches[0].nct_id
        comparison, comparison_ms = _timed(
            lambda: client.compare_trial_shared_entities(
                candidate.seed_nct_id,
                first_related,
                10,
            )
        )
        comparison_passed = (
            comparison.status == GraphQueryStatus.SUCCESS
            and len(comparison.shared_entities) > 0
        )

    evidence_passed = (
        evidence.status == GraphQueryStatus.SUCCESS
        and evidence.evidence is not None
        and evidence.evidence.get("found") is True
    )
    exact_passed = exact.status.value == "SUCCESS" and len(exact.matches) > 0
    related_passed = (
        related.status == GraphQueryStatus.SUCCESS
        and 0 < len(related.matches) <= SCENARIO_RELATED_LIMIT
        and not metric_errors
    )

    return {
        "scenario": candidate.scenario,
        "passed": bool(
            evidence_passed and exact_passed and related_passed and comparison_passed
        ),
        "candidate": candidate.to_dict(),
        "transport": "mcp",
        "timings_ms": {
            "trial_evidence": evidence_ms,
            "exact_entity_search": search_ms,
            "related_trials": related_ms,
            "shared_entity_comparison": comparison_ms,
        },
        "trial_evidence": {
            "status": evidence.status.value,
            "found": bool(evidence.evidence and evidence.evidence.get("found")),
        },
        "exact_entity_search": _summarize_exact_search(exact),
        "related_trials": summarize_related_response(related),
        "related_metric_consistency_errors": metric_errors,
        "shared_entity_comparison": (
            {
                "status": comparison.status.value,
                "nct_id_a": comparison.nct_id_a,
                "nct_id_b": comparison.nct_id_b,
                "shared_entities": [
                    {
                        "entity_type": item.entity_type,
                        "normalized_name": item.normalized_name,
                    }
                    for item in comparison.shared_entities
                ],
            }
            if comparison is not None
            else None
        ),
    }


class CountingLLMService:
    """Delegate to the configured LLM while counting logical structured calls."""

    def __init__(self, delegate: Any):
        self.delegate = delegate
        self.calls: list[dict[str, Any]] = []

    def invoke_structured(self, messages: Any, schema: Any):
        started = perf_counter()
        call: dict[str, Any] = {
            "schema": schema.__name__,
            "sequence": len(self.calls) + 1,
        }
        self.calls.append(call)
        try:
            value, metadata = self.delegate.invoke_structured(messages, schema)
            call.update(
                {
                    "passed": True,
                    "provider": metadata.provider,
                    "model": metadata.model,
                    "attempted_providers": metadata.attempted_providers,
                    "latency_ms": metadata.latency_ms,
                    "wall_clock_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
            return value, metadata
        except Exception as exc:
            call.update(
                {
                    "passed": False,
                    "error_type": exc.__class__.__name__,
                    "wall_clock_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


def _guided_questions(candidates: dict[str, ScenarioCandidate]) -> list[dict[str, str]]:
    overview = candidates["rare_specific_condition"]
    related = candidates["cardiovascular_condition"]
    condition = candidates["oncology_condition"]
    return [
        {
            "scenario": "guided_overview",
            "question": (
                f"Give me an evidence-grounded overview of {overview.seed_nct_id}."
            ),
        },
        {
            "scenario": "guided_related_trials",
            "question": (
                f"Find trials related to {related.seed_nct_id}. For each related trial, "
                "explain the shared condition, intervention, or sponsor and compare "
                "the available enrollment and study timing."
            ),
        },
        {
            "scenario": "guided_condition_search",
            "question": f"Find trials for the condition {condition.entity_name}.",
        },
    ]


def _run_guided_question(question: str, scenario: str) -> dict[str, Any]:
    counting = CountingLLMService(get_llm_service())
    started = perf_counter()
    with (
        patch(
            "trialiq.chains.intent_extraction.get_llm_service",
            return_value=counting,
        ),
        patch(
            "trialiq.agents.synthesis.get_llm_service",
            return_value=counting,
        ),
    ):
        result = run_agent_question(question, limit=20)
    wall_clock_ms = round((perf_counter() - started) * 1000, 3)

    retrieval_stage = next(
        (stage for stage in result.trace if stage.stage == "retrieval"), None
    )
    intent_stage = next(
        (stage for stage in result.trace if stage.stage == "intent"), None
    )
    schemas = [item["schema"] for item in counting.calls]
    expected_schemas = ["ExtractedQueryIntent", "StructuredSynthesis"]
    exactly_two = schemas == expected_schemas
    intent_source = intent_stage.details.get("source") if intent_stage else None
    transport = retrieval_stage.details.get("transport") if retrieval_stage else None
    calls_succeeded = len(counting.calls) == 2 and all(
        bool(item.get("passed")) for item in counting.calls
    )
    passed = (
        result.status.value == "SUCCESS"
        and exactly_two
        and calls_succeeded
        and intent_source == "llm"
        and transport == "mcp"
    )

    return {
        "scenario": scenario,
        "passed": passed,
        "question": question,
        "status": result.status.value,
        "wall_clock_ms": wall_clock_ms,
        "logical_llm_call_count": len(counting.calls),
        "logical_llm_call_schemas": schemas,
        "exactly_two_logical_llm_calls": exactly_two,
        "logical_llm_calls_succeeded": calls_succeeded,
        "llm_calls": counting.calls,
        "intent_source": intent_source,
        "retrieval_transport": transport,
        "retrieval_tool": (
            retrieval_stage.details.get("tool_name") if retrieval_stage else None
        ),
        "trace": [
            {
                "stage": stage.stage,
                "status": stage.status.value,
                "duration_ms": stage.duration_ms,
                "details": stage.details,
            }
            for stage in result.trace
        ],
        "generation": result.generation.model_dump() if result.generation else None,
        "source_count": len(result.answer.sources),
        "limitation_count": len(result.answer.limitations),
        "related_trial_count": (
            len(result.answer.related_trial_response.matches)
            if result.answer.related_trial_response is not None
            else None
        ),
    }


def _catalog_checks(candidates: list[ScenarioCandidate]) -> list[dict[str, Any]]:
    checks = []
    for candidate in candidates[:5]:
        catalog, duration_ms = _timed(
            lambda c=candidate: get_trial_catalog(c.seed_nct_id, limit=5, offset=0)
        )
        item = next(
            (entry for entry in catalog.trials if entry.nct_id == candidate.seed_nct_id),
            None,
        )
        checks.append(
            {
                "scenario": candidate.scenario,
                "passed": item is not None and catalog.total_count >= 1,
                "query": candidate.seed_nct_id,
                "duration_ms": duration_ms,
                "total_count": catalog.total_count,
                "related_trial_count": item.related_trial_count if item else None,
                "related_trial_count_capped": (
                    item.related_trial_count_capped if item else None
                ),
            }
        )
    return checks


def _demo_candidate_payload(
    candidates: list[ScenarioCandidate],
    scenario_results: list[dict[str, Any]],
) -> dict[str, Any]:
    results = {item["scenario"]: item for item in scenario_results}
    recommendations = []
    for candidate in candidates:
        result = results.get(candidate.scenario, {})
        related = result.get("related_trials") or {}
        recommendations.append(
            {
                **candidate.to_dict(),
                "qualification_passed": bool(result.get("passed")),
                "related_trial_count_returned": int(related.get("returned") or 0),
                "related_nct_ids": [
                    item["nct_id"] for item in (related.get("matches") or [])
                ],
                "aggregate_metrics": related.get("aggregate_metrics"),
            }
        )
    return {
        "batch": 15,
        "purpose": "candidate_pool_for_later_ui_demo_selection",
        "note": (
            "These IDs are discovered from the currently loaded full AACT graph. "
            "They are candidates, not a permanent hard-coded demo set."
        ),
        "candidates": recommendations,
    }


def run_qualification(*, skip_live_llm: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    connection = Neo4jConnection()
    try:
        inventory, inventory_ms = _timed(lambda: graph_inventory(connection))
        candidates, discovery_ms = _timed(
            lambda: discover_batch15_candidates(connection)
        )
    finally:
        connection.close()

    candidate_map = {candidate.scenario: candidate for candidate in candidates}
    missing_scenarios = sorted(EXPECTED_SCENARIOS - set(candidate_map))
    inventory_passed = (
        inventory["trials"] >= MINIMUM_FULL_GRAPH_TRIALS
        and inventory["conditions"] > 0
        and inventory["interventions"] > 0
        and inventory["sponsors"] > 0
        and inventory["condition_relationships"] > 0
        and inventory["intervention_relationships"] > 0
        and inventory["sponsor_relationships"] > 0
    )

    client = FastMCPRetrievalClient(timeout=60.0)
    mcp_health, mcp_health_ms = _timed(client.check_health)
    scenario_results = [
        _qualify_one_mcp_scenario(client, candidate) for candidate in candidates
    ]
    catalog_checks = _catalog_checks(candidates)

    guided_results: list[dict[str, Any]] = []
    if not skip_live_llm and not missing_scenarios:
        for item in _guided_questions(candidate_map):
            guided_results.append(
                _run_guided_question(item["question"], item["scenario"])
            )

    mcp_scenarios_passed = (
        len(scenario_results) == len(EXPECTED_SCENARIOS)
        and all(item["passed"] for item in scenario_results)
    )
    catalog_passed = bool(catalog_checks) and all(
        item["passed"] for item in catalog_checks
    )
    guided_passed = (
        True
        if skip_live_llm
        else len(guided_results) == 3 and all(item["passed"] for item in guided_results)
    )

    report = {
        "batch": 15,
        "mode": "realistic_scenario_qualification",
        "read_only": True,
        "passed": bool(
            inventory_passed
            and not missing_scenarios
            and mcp_health
            and mcp_scenarios_passed
            and catalog_passed
            and guided_passed
        ),
        "preconditions": {
            "passed": inventory_passed and not missing_scenarios,
            "scenario_discovery_transport": "direct_read_only_fixed_cypher",
            "minimum_full_graph_trials": MINIMUM_FULL_GRAPH_TRIALS,
            "inventory": inventory,
            "inventory_duration_ms": inventory_ms,
            "candidate_discovery_duration_ms": discovery_ms,
            "expected_scenarios": sorted(EXPECTED_SCENARIOS),
            "missing_scenarios": missing_scenarios,
        },
        "mcp": {
            "health_passed": bool(mcp_health),
            "health_duration_ms": mcp_health_ms,
            "scenario_count": len(scenario_results),
            "all_scenarios_passed": mcp_scenarios_passed,
            "scenarios": scenario_results,
        },
        "catalog": {
            "passed": catalog_passed,
            "checks": catalog_checks,
        },
        "guided_agent": {
            "skipped": skip_live_llm,
            "passed": guided_passed,
            "expected_logical_llm_calls_per_question": 2,
            "checks": guided_results,
        },
        "constraints_preserved": {
            "runtime_graph_transport": "mcp",
            "no_runtime_direct_fallback_added": True,
            "fixed_allowlisted_cypher_only": True,
            "bounded_related_traversal": True,
            "quantitative_metrics_deterministic": True,
            "frontend_modified": False,
            "llm_orchestration_modified": False,
        },
    }
    candidate_payload = _demo_candidate_payload(candidates, scenario_results)
    return report, candidate_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="data/profiles/batch15_realistic_qualification.json",
    )
    parser.add_argument(
        "--candidates-output",
        default="data/profiles/batch15_demo_candidates.json",
    )
    parser.add_argument(
        "--skip-live-llm",
        action="store_true",
        help=(
            "Skip the three natural-language two-call checks. Intended only for "
            "offline diagnostics; the standard Batch-15 runner does not use this."
        ),
    )
    args = parser.parse_args()

    try:
        report, candidates = run_qualification(skip_live_llm=args.skip_live_llm)
    except Exception as exc:
        report = {
            "batch": 15,
            "mode": "realistic_scenario_qualification",
            "read_only": True,
            "passed": False,
            "errors": [f"{exc.__class__.__name__}: {exc}"],
        }
        candidates = {
            "batch": 15,
            "purpose": "candidate_pool_for_later_ui_demo_selection",
            "candidates": [],
            "errors": report["errors"],
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    candidates_output = Path(args.candidates_output)
    candidates_output.parent.mkdir(parents=True, exist_ok=True)
    candidates_output.write_text(
        json.dumps(candidates, indent=2, default=str), encoding="utf-8"
    )

    print(json.dumps(report, indent=2, default=str))
    print(f"Qualification report: {output.resolve()}")
    print(f"Demo candidate pool:   {candidates_output.resolve()}")
    return 0 if report.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
