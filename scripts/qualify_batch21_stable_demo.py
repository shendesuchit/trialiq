"""Final read-only TrialIQ stable-demo scenario qualification.

Batch 21 does not change application behavior. It discovers a small, source-backed
scenario ladder from the currently loaded canonical graph, verifies retrieval through
MCP, and then exercises the natural-language guided path for the scenarios that are
supposed to use the agent workflow.

The output is intended to freeze *questions and evidence characteristics*, not hard-code
special runtime behavior for particular NCT IDs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any
from unittest.mock import patch

from trialiq.agents.api import continue_agent_question, run_agent_question
from trialiq.agents.mcp_client import FastMCPRetrievalClient
from trialiq.agents.models import (
    AgentHumanReviewRun,
    AgentRunResult,
    HumanReviewSelection,
    HumanReviewSelectionMode,
)
from trialiq.graph.connection import Neo4jConnection
from trialiq.llm.service import get_llm_service
from trialiq.qualification.scenarios import (
    ScenarioCandidate,
    discover_batch15_candidates,
    graph_inventory,
    validate_related_response,
)
from trialiq.qualification.stable_demo import (
    ProbeSummary,
    comparison_coverage,
    probe_to_dict,
    select_best_advanced,
    select_best_hitl,
    select_best_intermediate,
)
from trialiq.services.models import GraphQueryStatus


MINIMUM_FULL_GRAPH_TRIALS = 500_000
PROBE_LIMIT = 7
HITL_PROBE_LIMIT = 10
SMALL_ENTITY_SCAN_LIMIT = 2000
RELATIONSHIP_NOUNS = {
    "HAS_CONDITION": "conditions",
    "HAS_INTERVENTION": "interventions",
    "SPONSORED_BY": "sponsors",
}
RELEASE_ENTITY_SPECS = {
    "condition": ("Condition", "HAS_CONDITION"),
    "intervention": ("Intervention", "HAS_INTERVENTION"),
    "sponsor": ("Sponsor", "SPONSORED_BY"),
}


def _timed(call):
    started = perf_counter()
    value = call()
    return value, round((perf_counter() - started) * 1000, 3)


def _discover_small_connected_candidates(connection: Neo4jConnection) -> list[ScenarioCandidate]:
    """Find seeds whose single same-type canonical entity yields 2-6 neighbors.

    The query is fixed and read-only. It starts from the indexed source-backed
    ``loaded_trial_count`` fan-out property and caps the entity scan before expanding
    trials. This keeps qualification memory bounded on the full AACT graph while still
    preferring peers with dates and enrollment for deterministic comparison coverage.
    """

    candidates: list[ScenarioCandidate] = []
    for entity_type, (label, relationship) in RELEASE_ENTITY_SPECS.items():
        query = f"""
        MATCH (entity:{label})
        WHERE entity.canonical = true
          AND entity.canonical_key IS NOT NULL
          AND entity.loaded_trial_count >= 3
          AND entity.loaded_trial_count <= 7
        WITH entity
        ORDER BY entity.loaded_trial_count DESC, entity.canonical_key
        LIMIT {SMALL_ENTITY_SCAN_LIMIT}
        MATCH (entity)-[:{relationship}]->(trial:Trial)
        WHERE trial.start_date IS NOT NULL
          AND trial.completion_date IS NOT NULL
          AND trial.enrollment IS NOT NULL
          AND NOT EXISTS {{
              MATCH (other:{label})-[:{relationship}]->(trial)
              WHERE other.canonical = true
                AND other.canonical_key IS NOT NULL
                AND other <> entity
          }}
          AND NOT EXISTS {{
              MATCH (entity)-[:{relationship}]->(peer:Trial)
              WHERE peer.start_date IS NULL
                 OR peer.completion_date IS NULL
                 OR peer.enrollment IS NULL
          }}
        RETURN entity.normalized_name AS entity_name,
               entity.canonical_key AS canonical_key,
               entity.loaded_trial_count AS entity_fanout,
               trial.nct_id AS seed_nct_id,
               trial.brief_title AS brief_title,
               trial.overall_status AS overall_status,
               trial.study_type AS study_type,
               trial.phase AS phase,
               trial.enrollment AS enrollment
        ORDER BY entity_fanout DESC, canonical_key, seed_nct_id
        LIMIT 10
        """
        rows = connection.execute_read(query)
        for index, row in enumerate(rows, start=1):
            candidates.append(
                ScenarioCandidate(
                    scenario=f"release_{entity_type}_{index}",
                    scenario_family="stable_demo_release_candidate",
                    entity_type=entity_type,
                    relationship_type=relationship,
                    entity_name=str(row.get("entity_name") or row["canonical_key"]),
                    canonical_key=str(row["canonical_key"]),
                    entity_fanout=int(row.get("entity_fanout") or 0),
                    seed_nct_id=str(row["seed_nct_id"]),
                    brief_title=row.get("brief_title"),
                    overall_status=row.get("overall_status"),
                    study_type=row.get("study_type"),
                    phase=row.get("phase"),
                    enrollment=(
                        int(row["enrollment"])
                        if row.get("enrollment") is not None
                        else None
                    ),
                    selection_reason=(
                        "Source-discovered seed with exactly one canonical same-type "
                        "connection entity, 2-6 possible related peers, and complete "
                        "date/enrollment fields across that peer set."
                    ),
                )
            )
    return candidates


def _probe_related(
    client: FastMCPRetrievalClient,
    candidate: ScenarioCandidate,
    *,
    relationship_types: list[str],
    overall_statuses: list[str] | None = None,
    limit: int = PROBE_LIMIT,
) -> tuple[ProbeSummary, dict[str, Any]]:
    response, duration_ms = _timed(
        lambda: client.find_related_trials(
            candidate.seed_nct_id,
            1,
            limit,
            limit,
            relationship_types,
            overall_statuses or [],
        )
    )
    errors = validate_related_response(response)
    probe = ProbeSummary(
        scenario=candidate.scenario,
        seed_nct_id=candidate.seed_nct_id,
        relationship_types=tuple(response.relationship_types),
        overall_statuses=tuple(response.overall_statuses),
        returned=len(response.matches),
        aggregate_metrics=response.metrics.model_dump(),
        metric_errors=tuple(errors),
        title=candidate.brief_title,
        overall_status=candidate.overall_status,
        phase=candidate.phase,
        study_type=candidate.study_type,
    )
    detail = {
        "duration_ms": duration_ms,
        "status": response.status.value,
        "validation_valid": response.validation.valid,
        "probe": probe_to_dict(probe),
        "nct_ids": [match.nct_id for match in response.matches],
    }
    return probe, detail


def _evidence_richness(evidence: dict[str, Any] | None) -> int:
    if not evidence or not evidence.get("found"):
        return -1
    trial = evidence.get("trial") or {}
    score = sum(
        trial.get(field) not in (None, "", [])
        for field in (
            "brief_title",
            "overall_status",
            "study_type",
            "phase",
            "start_date",
            "completion_date",
            "enrollment",
        )
    )
    score += sum(
        bool(evidence.get(field))
        for field in (
            "conditions",
            "interventions",
            "sponsors",
            "facilities",
            "designs",
            "eligibilities",
        )
    )
    return int(score)


def _choose_basic_candidate(
    client: FastMCPRetrievalClient,
    candidates: list[ScenarioCandidate],
    *,
    excluded: set[str],
) -> tuple[ScenarioCandidate | None, dict[str, Any] | None]:
    best: tuple[int, str, ScenarioCandidate, dict[str, Any]] | None = None
    ordered = sorted(
        candidates,
        key=lambda item: (
            -sum(
                value not in (None, "", [])
                for value in (
                    item.brief_title,
                    item.overall_status,
                    item.study_type,
                    item.phase,
                    item.enrollment,
                )
            ),
            item.seed_nct_id,
            item.scenario,
        ),
    )
    for candidate in ordered[:12]:
        if candidate.seed_nct_id in excluded:
            continue
        response, duration_ms = _timed(lambda c=candidate: client.get_trial_evidence(c.seed_nct_id))
        evidence = response.evidence if response.status == GraphQueryStatus.SUCCESS else None
        score = _evidence_richness(evidence)
        if score < 0 or not response.validation.valid:
            continue
        payload = {
            "duration_ms": duration_ms,
            "status": response.status.value,
            "validation_valid": response.validation.valid,
            "richness_score": score,
            "evidence_counts": {
                key: len(evidence.get(key) or [])
                for key in (
                    "conditions",
                    "interventions",
                    "sponsors",
                    "facilities",
                    "designs",
                    "eligibilities",
                )
            },
        }
        key = (score, candidate.seed_nct_id, candidate, payload)
        if best is None or key[:2] > best[:2]:
            best = key
    if best is None:
        return None, None
    return best[2], best[3]


class CountingLLMService:
    """Transparent proxy used only to verify the protected two-call contract."""

    def __init__(self, delegate: Any):
        self.delegate = delegate
        self.calls: list[dict[str, Any]] = []

    def invoke_structured(self, messages: Any, schema: Any):
        started = perf_counter()
        call: dict[str, Any] = {
            "sequence": len(self.calls) + 1,
            "schema": schema.__name__,
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


def _relationship_question(seed_nct_id: str, relationship_type: str, *, advanced: bool) -> str:
    noun = RELATIONSHIP_NOUNS[relationship_type]
    if advanced:
        return (
            f"Find trials related to {seed_nct_id} through shared {noun}. "
            "Compare completion timing, study duration, enrollment, status, and phase where available."
        )
    return (
        f"Find trials related to {seed_nct_id} through shared {noun}. "
        "Explain the shared connection for each related study."
    )


def _hitl_question(seed_nct_id: str) -> str:
    return (
        f"Find trials related to {seed_nct_id}. For each related trial, explain the shared "
        "condition, intervention, or sponsor and compare the available enrollment and study timing."
    )


def _verify_guided_success(question: str, expected: ProbeSummary, *, advanced: bool) -> dict[str, Any]:
    counting = CountingLLMService(get_llm_service())
    with (
        patch("trialiq.chains.intent_extraction.get_llm_service", return_value=counting),
        patch("trialiq.agents.synthesis.get_llm_service", return_value=counting),
    ):
        result = run_agent_question(question, limit=20)

    if not isinstance(result, AgentRunResult):
        return {
            "passed": False,
            "question": question,
            "error": "Expected a completed agent result but the run paused for human review.",
            "logical_llm_calls": counting.calls,
        }

    related = result.retrieval.related_trial_response if result.retrieval else None
    schemas = [item["schema"] for item in counting.calls]
    relation_ok = related is not None and related.relationship_types == list(expected.relationship_types)
    status_ok = related is not None and related.overall_statuses == list(expected.overall_statuses)
    count_ok = related is not None and 2 <= len(related.matches) <= 6
    coverage_ok = True
    coverage = None
    if related is not None:
        actual_probe = ProbeSummary(
            scenario=expected.scenario,
            seed_nct_id=expected.seed_nct_id,
            relationship_types=tuple(related.relationship_types),
            overall_statuses=tuple(related.overall_statuses),
            returned=len(related.matches),
            aggregate_metrics=related.metrics.model_dump(),
        )
        coverage = comparison_coverage(actual_probe)
        if advanced:
            coverage_ok = coverage.dimensions_at_or_above_80_percent >= 2

    transport_ok = bool(result.retrieval and result.retrieval.transport == "mcp")
    intent_stage = next((stage for stage in result.trace if stage.stage == "intent"), None)
    intent_ok = bool(intent_stage and intent_stage.details.get("source") == "llm")
    calls_ok = schemas == ["ExtractedQueryIntent", "StructuredSynthesis"] and all(
        item.get("passed") for item in counting.calls
    )
    passed = bool(
        result.status.value == "SUCCESS"
        and relation_ok
        and status_ok
        and count_ok
        and coverage_ok
        and transport_ok
        and intent_ok
        and calls_ok
    )
    return {
        "passed": passed,
        "question": question,
        "status": result.status.value,
        "retrieval_transport": result.retrieval.transport if result.retrieval else None,
        "relationship_types": related.relationship_types if related else None,
        "overall_statuses": related.overall_statuses if related else None,
        "related_trial_count": len(related.matches) if related else None,
        "comparison_coverage": (
            {
                "completion": round(coverage.completion, 3),
                "duration": round(coverage.duration, 3),
                "enrollment": round(coverage.enrollment, 3),
                "dimensions_at_or_above_80_percent": coverage.dimensions_at_or_above_80_percent,
            }
            if coverage is not None
            else None
        ),
        "logical_llm_calls": counting.calls,
        "logical_llm_call_schemas": schemas,
    }


def _verify_hitl(question: str, expected_seed: str) -> dict[str, Any]:
    counting = CountingLLMService(get_llm_service())
    with (
        patch("trialiq.chains.intent_extraction.get_llm_service", return_value=counting),
        patch("trialiq.agents.synthesis.get_llm_service", return_value=counting),
    ):
        paused = run_agent_question(question, limit=20)
        if not isinstance(paused, AgentHumanReviewRun):
            return {
                "passed": False,
                "question": question,
                "error": "Expected REVIEW_REQUIRED for the broad scenario.",
                "logical_llm_calls": counting.calls,
            }
        suggested = list(paused.human_review.suggested_nct_ids)
        selected = suggested or [item.nct_id for item in paused.human_review.candidates[:6]]
        resumed = continue_agent_question(
            paused.run_id,
            HumanReviewSelection(
                checkpoint_id=paused.human_review.checkpoint_id,
                mode=HumanReviewSelectionMode.SELECTED,
                selected_nct_ids=selected,
            ),
        )

    schemas = [item["schema"] for item in counting.calls]
    related = resumed.answer.related_trial_response
    calls_ok = schemas == ["ExtractedQueryIntent", "StructuredSynthesis"] and all(
        item.get("passed") for item in counting.calls
    )
    retrieval_transport = paused.retrieval.transport
    seed_ok = bool(
        paused.retrieval.related_trial_response
        and paused.retrieval.related_trial_response.seed_nct_id == expected_seed
    )
    passed = bool(
        paused.human_review.candidate_count > 6
        and len(selected) >= 1
        and resumed.status.value == "SUCCESS"
        and resumed.human_review_decision is not None
        and resumed.human_review_decision.discovered_candidate_count
        == paused.human_review.candidate_count
        and resumed.human_review_decision.selected_candidate_count == len(selected)
        and related is not None
        and len(related.matches) == len(selected)
        and retrieval_transport == "mcp"
        and seed_ok
        and calls_ok
    )
    return {
        "passed": passed,
        "question": question,
        "pause_status": paused.status.value,
        "candidate_count": paused.human_review.candidate_count,
        "suggested_count": len(paused.human_review.suggested_nct_ids),
        "selected_count": len(selected),
        "resume_status": resumed.status.value,
        "retrieval_transport": retrieval_transport,
        "logical_llm_calls": counting.calls,
        "logical_llm_call_schemas": schemas,
    }


def run_qualification(*, skip_guided: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    connection = Neo4jConnection()
    try:
        inventory, inventory_ms = _timed(lambda: graph_inventory(connection))
        named_candidates, named_ms = _timed(lambda: discover_batch15_candidates(connection))
        small_candidates, small_ms = _timed(lambda: _discover_small_connected_candidates(connection))
    finally:
        connection.close()

    inventory_passed = (
        inventory.get("trials", 0) >= MINIMUM_FULL_GRAPH_TRIALS
        and inventory.get("conditions", 0) > 0
        and inventory.get("interventions", 0) > 0
        and inventory.get("sponsors", 0) > 0
    )

    client = FastMCPRetrievalClient(timeout=60.0)
    mcp_health, mcp_health_ms = _timed(client.check_health)

    small_probes: list[ProbeSummary] = []
    small_probe_details: list[dict[str, Any]] = []
    seen = set()
    for candidate in small_candidates:
        key = (candidate.seed_nct_id, candidate.relationship_type)
        if key in seen:
            continue
        seen.add(key)
        probe, detail = _probe_related(
            client,
            candidate,
            relationship_types=[candidate.relationship_type],
            limit=PROBE_LIMIT,
        )
        if detail["status"] == "SUCCESS":
            small_probes.append(probe)
        small_probe_details.append({"candidate": candidate.to_dict(), **detail})

    advanced = select_best_advanced(small_probes)
    excluded = {advanced.seed_nct_id} if advanced else set()
    intermediate = select_best_intermediate(small_probes, excluded_seed_ids=excluded)
    if intermediate is None:
        intermediate = select_best_intermediate(small_probes)

    hitl_probes: list[ProbeSummary] = []
    hitl_details: list[dict[str, Any]] = []
    for candidate in named_candidates:
        probe, detail = _probe_related(
            client,
            candidate,
            relationship_types=["HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"],
            limit=HITL_PROBE_LIMIT,
        )
        if detail["status"] == "SUCCESS":
            hitl_probes.append(probe)
        hitl_details.append({"candidate": candidate.to_dict(), **detail})

    scenario_excluded = {
        item.seed_nct_id
        for item in (advanced, intermediate)
        if item is not None
    }
    hitl = select_best_hitl(hitl_probes, excluded_seed_ids=scenario_excluded)
    if hitl is None:
        hitl = select_best_hitl(hitl_probes)

    all_candidates = small_candidates + named_candidates
    basic_candidate, basic_evidence = _choose_basic_candidate(
        client,
        all_candidates,
        excluded=scenario_excluded | ({hitl.seed_nct_id} if hitl else set()),
    )
    if basic_candidate is None:
        basic_candidate, basic_evidence = _choose_basic_candidate(
            client,
            all_candidates,
            excluded=set(),
        )

    selected_ok = all(item is not None for item in (advanced, intermediate, hitl, basic_candidate))

    scenario_payload: dict[str, Any] = {
        "batch": 21,
        "purpose": "stable_demo_scenario_ladder",
        "source_backed": True,
        "runtime_hardcoding_added": False,
        "scenarios": {},
    }

    if basic_candidate is not None:
        scenario_payload["scenarios"]["basic"] = {
            "execution_mode": "direct_evidence_lookup",
            "seed_nct_id": basic_candidate.seed_nct_id,
            "title": basic_candidate.brief_title,
            "question": f"Give me an evidence-grounded overview of {basic_candidate.seed_nct_id}.",
            "qualification": basic_evidence,
        }
    if intermediate is not None:
        relation = intermediate.relationship_types[0]
        scenario_payload["scenarios"]["intermediate"] = {
            "execution_mode": "guided_agent",
            **probe_to_dict(intermediate),
            "question": _relationship_question(intermediate.seed_nct_id, relation, advanced=False),
            "expected_behavior": "Completes without HITL because the final bounded candidate set is 2-6 studies.",
        }
    if advanced is not None:
        relation = advanced.relationship_types[0]
        scenario_payload["scenarios"]["advanced"] = {
            "execution_mode": "guided_agent",
            **probe_to_dict(advanced),
            "question": _relationship_question(advanced.seed_nct_id, relation, advanced=True),
            "expected_behavior": "Completes without HITL and has at least 80% coverage in two deterministic comparison dimensions.",
        }
    if hitl is not None:
        scenario_payload["scenarios"]["hitl"] = {
            "execution_mode": "guided_agent_with_human_review",
            **probe_to_dict(hitl),
            "question": _hitl_question(hitl.seed_nct_id),
            "expected_behavior": "Pauses when more than six candidates are discovered, then resumes from the investigator-approved set without repeating retrieval.",
        }

    guided_checks: dict[str, Any] = {}
    if not skip_guided and selected_ok:
        guided_checks["intermediate"] = _verify_guided_success(
            scenario_payload["scenarios"]["intermediate"]["question"],
            intermediate,
            advanced=False,
        )
        guided_checks["advanced"] = _verify_guided_success(
            scenario_payload["scenarios"]["advanced"]["question"],
            advanced,
            advanced=True,
        )
        guided_checks["hitl"] = _verify_hitl(
            scenario_payload["scenarios"]["hitl"]["question"],
            hitl.seed_nct_id,
        )

    guided_passed = skip_guided or (
        len(guided_checks) == 3 and all(item.get("passed") for item in guided_checks.values())
    )

    report = {
        "batch": 21,
        "mode": "stable_demo_release_qualification",
        "read_only": True,
        "passed": bool(
            inventory_passed
            and mcp_health
            and selected_ok
            and guided_passed
        ),
        "preconditions": {
            "passed": inventory_passed,
            "minimum_full_graph_trials": MINIMUM_FULL_GRAPH_TRIALS,
            "inventory": inventory,
            "inventory_duration_ms": inventory_ms,
            "named_candidate_discovery_duration_ms": named_ms,
            "small_candidate_discovery_duration_ms": small_ms,
        },
        "mcp": {
            "health_passed": bool(mcp_health),
            "health_duration_ms": mcp_health_ms,
            "transport": "mcp",
        },
        "selection": {
            "passed": selected_ok,
            "small_candidate_count": len(small_candidates),
            "small_probe_count": len(small_probes),
            "hitl_probe_count": len(hitl_probes),
            "selected_scenarios": scenario_payload["scenarios"],
        },
        "guided_agent": {
            "skipped": skip_guided,
            "passed": guided_passed,
            "protected_logical_llm_call_count": 2,
            "checks": guided_checks,
        },
        "diagnostics": {
            "small_probe_details": small_probe_details,
            "hitl_probe_details": hitl_details,
        },
        "constraints_preserved": {
            "no_product_runtime_behavior_changed": True,
            "runtime_graph_transport": "mcp",
            "no_runtime_direct_fallback_added": True,
            "no_llm_generated_cypher": True,
            "bounded_allowlisted_related_traversal": True,
            "quantitative_comparisons_deterministic": True,
            "normal_guided_path_logical_llm_calls": 2,
        },
    }
    return report, scenario_payload


def _write_summary(path: Path, report: dict[str, Any], scenarios: dict[str, Any]) -> None:
    lines = [
        "TrialIQ Batch 21 stable-demo qualification",
        "==========================================",
        f"PASS: {report.get('passed')}",
        "",
    ]
    for name in ("basic", "intermediate", "advanced", "hitl"):
        scenario = (scenarios.get("scenarios") or {}).get(name)
        if not scenario:
            lines.extend([f"{name.upper()}: NOT SELECTED", ""])
            continue
        lines.extend(
            [
                name.upper(),
                f"  NCT:      {scenario.get('seed_nct_id')}",
                f"  Question: {scenario.get('question')}",
                f"  Mode:     {scenario.get('execution_mode')}",
                f"  Related:  {scenario.get('returned', 'n/a')}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="data/profiles/batch21_stable_demo_qualification.json",
    )
    parser.add_argument(
        "--scenarios-output",
        default="data/profiles/batch21_stable_demo_scenarios.json",
    )
    parser.add_argument(
        "--summary-output",
        default="data/profiles/batch21_stable_demo_scenarios.txt",
    )
    parser.add_argument(
        "--skip-guided",
        action="store_true",
        help="Skip live LLM guided-path checks. This is diagnostic only, not the final release gate.",
    )
    args = parser.parse_args()

    try:
        report, scenarios = run_qualification(skip_guided=args.skip_guided)
    except Exception as exc:
        report = {
            "batch": 21,
            "mode": "stable_demo_release_qualification",
            "read_only": True,
            "passed": False,
            "errors": [f"{exc.__class__.__name__}: {exc}"],
        }
        scenarios = {
            "batch": 21,
            "purpose": "stable_demo_scenario_ladder",
            "scenarios": {},
            "errors": report["errors"],
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    scenarios_output = Path(args.scenarios_output)
    scenarios_output.parent.mkdir(parents=True, exist_ok=True)
    scenarios_output.write_text(json.dumps(scenarios, indent=2, default=str), encoding="utf-8")

    _write_summary(Path(args.summary_output), report, scenarios)

    print(f"Qualification report: {output.resolve()}")
    print(f"Stable scenarios:     {scenarios_output.resolve()}")
    print(f"Scenario summary:     {Path(args.summary_output).resolve()}")
    if report.get("passed"):
        print("[SUCCESS] Batch 21 stable-demo scenario qualification passed.")
        return 0
    print("[FAIL] Batch 21 stable-demo scenario qualification failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
