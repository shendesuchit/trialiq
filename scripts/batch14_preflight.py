"""Read-only Batch 14 full-load readiness preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from trialiq.config.settings import get_settings
from trialiq.etl.canonical_graphrag import CORE_ENTITY_SPECS
from trialiq.graph.connection import Neo4jConnection

REQUIRED_CONSTRAINTS = {
    "trial_nct_id_unique",
    "condition_canonical_key_unique",
    "intervention_canonical_key_unique",
    "sponsor_canonical_key_unique",
}


def _postgres_connection_string() -> str:
    settings = get_settings()
    return (
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_database} "
        f"user={settings.postgres_username} "
        f"password={settings.postgres_password}"
    )


def run_preflight() -> dict[str, Any]:
    settings = get_settings()
    errors: list[str] = []
    if settings.postgres_schema != "ctgov":
        errors.append("PostgreSQL schema must be ctgov for the canonical full load.")

    source_counts: dict[str, int] = {}
    with psycopg.connect(_postgres_connection_string(), row_factory=dict_row) as source:
        source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        with source.cursor() as cursor:
            for table in ("studies", *CORE_ENTITY_SPECS.keys()):
                cursor.execute(
                    sql.SQL("SELECT count(*) AS row_count FROM {}.{}").format(
                        sql.Identifier(settings.postgres_schema), sql.Identifier(table)
                    )
                )
                row = cursor.fetchone() or {}
                source_counts[table] = int(row.get("row_count") or 0)

    if source_counts.get("studies", 0) <= 0:
        errors.append("AACT studies table is empty.")
    for table in CORE_ENTITY_SPECS:
        if source_counts.get(table, 0) <= 0:
            errors.append(f"AACT {table} table is empty.")

    graph = Neo4jConnection()
    try:
        graph.verify_connectivity()
        constraint_records = graph.execute_read(
            "SHOW CONSTRAINTS YIELD name RETURN name ORDER BY name"
        )
        constraints = {
            str(record["name"])
            for record in constraint_records
            if record.get("name")
        }
        missing_constraints = sorted(REQUIRED_CONSTRAINTS - constraints)
        if missing_constraints:
            errors.append(
                "Missing required Neo4j constraints: " + ", ".join(missing_constraints)
            )

        graph_counts_records = graph.execute_read(
            """
            MATCH (trial:Trial)
            RETURN count(trial) AS trial_nodes,
                   count(CASE WHEN trial.canonical_load_run_id IS NOT NULL THEN 1 END)
                       AS canonical_loaded_trials
            """
        )
        graph_counts = graph_counts_records[0] if graph_counts_records else {}
    finally:
        graph.close()

    return {
        "batch": 14,
        "mode": "full_load_preflight",
        "passed": not errors,
        "source": {
            "database": settings.postgres_database,
            "schema": settings.postgres_schema,
            "row_counts": source_counts,
        },
        "graph": {
            "required_constraints": sorted(REQUIRED_CONSTRAINTS),
            "missing_constraints": missing_constraints,
            "trial_nodes": int(graph_counts.get("trial_nodes") or 0),
            "canonical_loaded_trials": int(
                graph_counts.get("canonical_loaded_trials") or 0
            ),
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/profiles/batch14_preflight.json")
    args = parser.parse_args()
    try:
        report = run_preflight()
    except Exception as exc:
        report = {
            "batch": 14,
            "mode": "full_load_preflight",
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
