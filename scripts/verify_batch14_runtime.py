"""Batch 14 runtime smoke checks for canonical retrieval and hub bounds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from trialiq.chains.cypher_qa import CATALOG_RELATED_TRIAL_COUNT_CAP
from trialiq.services.graph_query_service import (
    query_related_trials,
    query_shared_entities_between_trials,
    query_trials_by_condition,
    query_trials_by_intervention,
    query_trials_by_sponsor,
)
from trialiq.services.models import GraphQueryStatus
from trialiq.services.trial_catalog_service import get_trial_catalog

ANCHOR_NCT_ID = "NCT03416088"
CONDITION_RELATED_NCT_ID = "NCT04214743"


def _check(name: str, passed: bool, detail: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def run_smoke(*, full_load: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    catalog = get_trial_catalog(ANCHOR_NCT_ID, limit=5, offset=0)
    catalog_item = next(
        (item for item in catalog.trials if item.nct_id == ANCHOR_NCT_ID), None
    )
    checks.append(
        _check(
            "catalog_anchor",
            catalog_item is not None
            and catalog_item.related_trial_count <= CATALOG_RELATED_TRIAL_COUNT_CAP,
            {
                "total_count": catalog.total_count,
                "related_trial_count": (
                    catalog_item.related_trial_count if catalog_item else None
                ),
                "related_trial_count_capped": (
                    catalog_item.related_trial_count_capped if catalog_item else None
                ),
            },
        )
    )

    condition = query_trials_by_condition("retinal microcirculation disorder", limit=10)
    condition_ids = [item.nct_id for item in condition.matches]
    checks.append(
        _check(
            "canonical_condition_search",
            ANCHOR_NCT_ID in condition_ids and CONDITION_RELATED_NCT_ID in condition_ids,
            {"status": condition.status.value, "nct_ids": condition_ids},
        )
    )

    intervention = query_trials_by_intervention("beverage consumption", limit=10)
    intervention_ids = [item.nct_id for item in intervention.matches]
    checks.append(
        _check(
            "canonical_intervention_search",
            ANCHOR_NCT_ID in intervention_ids and "NCT04731987" in intervention_ids,
            {"status": intervention.status.value, "nct_ids": intervention_ids},
        )
    )

    sponsor = query_trials_by_sponsor("jiannan huang", limit=10)
    sponsor_ids = [item.nct_id for item in sponsor.matches]
    checks.append(
        _check(
            "canonical_sponsor_search",
            ANCHOR_NCT_ID in sponsor_ids and "NCT07764198" in sponsor_ids,
            {"status": sponsor.status.value, "nct_ids": sponsor_ids},
        )
    )

    shared = query_shared_entities_between_trials(
        ANCHOR_NCT_ID, CONDITION_RELATED_NCT_ID, limit_per_type=10
    )
    checks.append(
        _check(
            "canonical_shared_entity_comparison",
            shared.status == GraphQueryStatus.SUCCESS
            and any(item.entity_type == "condition" for item in shared.shared_entities),
            {
                "status": shared.status.value,
                "shared_entities": [
                    {
                        "entity_type": item.entity_type,
                        "normalized_name": item.normalized_name,
                    }
                    for item in shared.shared_entities
                ],
            },
        )
    )

    related = query_related_trials(
        ANCHOR_NCT_ID,
        max_hops=1,
        per_hop_limit=10,
        limit=10,
    )
    checks.append(
        _check(
            "hub_aware_related_traversal",
            related.status in {GraphQueryStatus.SUCCESS, GraphQueryStatus.NOT_FOUND}
            and len(related.matches) <= 10,
            {
                "status": related.status.value,
                "returned": len(related.matches),
                "nct_ids": [item.nct_id for item in related.matches],
            },
        )
    )

    if full_load:
        placebo = query_trials_by_intervention("placebo", limit=1)
        placebo_seed = placebo.matches[0].nct_id if placebo.matches else None
        bounded = (
            query_related_trials(
                placebo_seed,
                max_hops=1,
                per_hop_limit=20,
                limit=20,
                relationship_types=["HAS_INTERVENTION"],
            )
            if placebo_seed
            else None
        )
        checks.append(
            _check(
                "high_fanout_placebo_probe",
                placebo_seed is not None
                and bounded is not None
                and bounded.status in {GraphQueryStatus.SUCCESS, GraphQueryStatus.NOT_FOUND}
                and len(bounded.matches) <= 20,
                {
                    "seed_nct_id": placebo_seed,
                    "search_status": placebo.status.value,
                    "related_status": bounded.status.value if bounded else None,
                    "returned": len(bounded.matches) if bounded else None,
                },
            )
        )

    return {
        "batch": 14,
        "mode": "full_runtime_smoke" if full_load else "runtime_smoke",
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "bounds": {
            "catalog_related_trial_count_cap": CATALOG_RELATED_TRIAL_COUNT_CAP,
            "related_trial_limit_checked": 20 if full_load else 10,
        },
        "constraints_preserved": {
            "mcp_graph_transport": True,
            "no_runtime_direct_fallback_added": True,
            "fixed_allowlisted_cypher": True,
            "llm_orchestration_modified": False,
            "frontend_layout_modified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-load", action="store_true")
    parser.add_argument("--output", default="data/profiles/batch14_runtime_smoke.json")
    args = parser.parse_args()
    try:
        report = run_smoke(full_load=args.full_load)
    except Exception as exc:
        report = {
            "batch": 14,
            "mode": "full_runtime_smoke" if args.full_load else "runtime_smoke",
            "passed": False,
            "errors": [f"{exc.__class__.__name__}: {exc}"],
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
