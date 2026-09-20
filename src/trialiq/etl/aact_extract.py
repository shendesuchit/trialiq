
# AACT Extraction Pipeline

# Change Start
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from trialiq.config.settings import get_settings
from collections.abc import Iterable


EXTRACT_TABLES = (
    "studies",
    "conditions",
    "interventions",
    "sponsors",
    "facilities",
    "designs",
    "eligibilities",
)


def _scope_query(schema: str) -> str:
    """Return the deterministic trial-scope query."""
    return f"""
        SELECT nct_id
        FROM {schema}.studies
        ORDER BY nct_id
        LIMIT %s
    """


def _entity_query(schema: str, table: str) -> str:
    """Return a query for one approved entity table."""

    if table == "studies":
        order_by = "nct_id"
    else:
        order_by = "nct_id, id"

    return f"""
        SELECT *
        FROM {schema}.{table}
        WHERE nct_id = ANY(%s)
        ORDER BY {order_by}
    """


def extract_aact_dataset(
    limit: int = 100,
    output_path: str | Path = "data/extracted/aact_100_trials.json",
) -> Path:
    """Extract a deterministic AACT dataset from PostgreSQL."""

    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    settings = get_settings()

    schema = settings.postgres_schema

    if schema != "ctgov":
        raise ValueError(
            "M1 extraction is restricted to the ctgov schema"
        )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    connection_string = (
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_database} "
        f"user={settings.postgres_username} "
        f"password={settings.postgres_password}"
    )

    with psycopg.connect(
        connection_string,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:
            cursor.execute(_scope_query(schema), (limit,))
            scope_rows = cursor.fetchall()

            nct_ids = [
                row["nct_id"]
                for row in scope_rows
            ]

            if len(nct_ids) != limit:
                raise RuntimeError(
                    f"Expected {limit} trials, "
                    f"but selected {len(nct_ids)}"
                )

            extracted_tables: dict[str, list[dict[str, Any]]] = {}

            for table in EXTRACT_TABLES:
                cursor.execute(
                    _entity_query(schema, table),
                    (nct_ids,),
                )

                extracted_tables[table] = cursor.fetchall()

    dataset = {
        "metadata": {
            "source_database": settings.postgres_database,
            "source_schema": schema,
            "scope_type": "deterministic_nct_id_order",
            "scope_limit": limit,
            "extracted_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "nct_ids": nct_ids,
            "tables": list(EXTRACT_TABLES),
        },
        "tables": extracted_tables,
    }

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            dataset,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return output_file


# Change End

# Change Start
def _load_extracted_artifact(
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Load an extracted AACT JSON artifact."""
    artifact_file = Path(artifact_path)

    if not artifact_file.is_file():
        raise FileNotFoundError(
            f"Artifact not found: {artifact_file}"
        )

    with artifact_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def _build_postgres_connection_string() -> str:
    """Build the PostgreSQL connection string from settings."""
    settings = get_settings()

    return (
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_database} "
        f"user={settings.postgres_username} "
        f"password={settings.postgres_password}"
    )


def _validate_nct_membership(
    rows: Iterable[dict[str, Any]],
    expected_nct_ids: set[str],
) -> list[str]:
    """Return NCT IDs that are outside the expected trial scope."""
    unexpected_nct_ids = {
        row["nct_id"]
        for row in rows
        if row.get("nct_id") not in expected_nct_ids
    }

    return sorted(unexpected_nct_ids)


def reconcile_aact_artifact(
    artifact_path: str | Path,
    expected_limit: int | None = None,
) -> dict[str, Any]:
    """Reconcile an extracted AACT artifact against PostgreSQL."""

    artifact = _load_extracted_artifact(artifact_path)
    metadata = artifact.get("metadata", {})
    extracted_tables = artifact.get("tables", {})

    expected_nct_ids = set(metadata.get("nct_ids", []))
    actual_limit = metadata.get("scope_limit")

    if expected_limit is not None:
        if actual_limit != expected_limit:
            return {
                "passed": False,
                "errors": [
                    (
                        "Scope limit mismatch: "
                        f"expected {expected_limit}, "
                        f"found {actual_limit}"
                    )
                ],
            }

    if len(expected_nct_ids) != actual_limit:
        return {
            "passed": False,
            "errors": [
                (
                    "Unique NCT ID count does not match "
                    "the declared scope limit"
                )
            ],
        }

    settings = get_settings()
    schema = settings.postgres_schema

    if schema != "ctgov":
        raise ValueError(
            "M1 reconciliation is restricted to the ctgov schema"
        )

    report: dict[str, Any] = {
        "passed": True,
        "scope": {
            "expected_trial_count": len(expected_nct_ids),
            "declared_limit": actual_limit,
        },
        "tables": {},
        "errors": [],
    }

    with psycopg.connect(
        _build_postgres_connection_string(),
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:
            cursor.execute(
                _scope_query(schema),
                (actual_limit,),
            )

            source_scope = {
                row["nct_id"]
                for row in cursor.fetchall()
            }

            if source_scope != expected_nct_ids:
                report["passed"] = False
                report["errors"].append(
                    "Artifact trial scope does not match PostgreSQL"
                )

            for table in EXTRACT_TABLES:
                extracted_rows = extracted_tables.get(table, [])

                unexpected_nct_ids = _validate_nct_membership(
                    extracted_rows,
                    expected_nct_ids,
                )

                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS row_count
                    FROM {schema}.{table}
                    WHERE nct_id = ANY(%s)
                    """,
                    (list(expected_nct_ids),),
                )

                source_count = cursor.fetchone()["row_count"]
                extracted_count = len(extracted_rows)

                table_passed = (
                    source_count == extracted_count
                    and not unexpected_nct_ids
                )

                report["tables"][table] = {
                    "source_count": source_count,
                    "extracted_count": extracted_count,
                    "unexpected_nct_ids": unexpected_nct_ids,
                    "passed": table_passed,
                }

                if not table_passed:
                    report["passed"] = False
                    report["errors"].append(
                        f"Reconciliation failed for table: {table}"
                    )

    return report
# Change End