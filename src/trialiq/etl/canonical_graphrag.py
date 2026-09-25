"""Source-backed canonical GraphRAG loader for TrialIQ.

Batch 13 introduces a direct AACT -> Neo4j ingestion path for the graph entities
used by the investigator workflow.  It deliberately keeps Cypher fixed and
allowlisted, canonicalizes only exact source-backed names, deduplicates repeated
source rows at the Trial/entity edge, and reconciles every load scope.

The existing artifact ETL remains available for earlier milestones.  This module
is the scalable path for the broader Trial/Condition/Intervention/Sponsor graph.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import json
import uuid

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from trialiq.config.settings import get_settings
from trialiq.graph.connection import Neo4jConnection


CANONICAL_LOADER_VERSION = "batch13-canonical-v1"
DEFAULT_VERIFICATION_LIMIT = 5_000
DEFAULT_BATCH_SIZE = 1_000
MAX_BATCH_SIZE = 10_000

TRIAL_FIELDS = (
    "nct_id",
    "brief_title",
    "official_title",
    "overall_status",
    "phase",
    "study_type",
    "start_date",
    "completion_date",
    "primary_completion_date",
    "enrollment",
    "enrollment_type",
    "number_of_arms",
    "number_of_groups",
    "why_stopped",
    "source",
)

CORE_ENTITY_SPECS: dict[str, dict[str, str]] = {
    "conditions": {
        "label": "Condition",
        "relationship": "HAS_CONDITION",
        "legacy_prefix": "conditions:",
    },
    "interventions": {
        "label": "Intervention",
        "relationship": "HAS_INTERVENTION",
        "legacy_prefix": "interventions:",
    },
    "sponsors": {
        "label": "Sponsor",
        "relationship": "SPONSORED_BY",
        "legacy_prefix": "sponsors:",
    },
}

CANONICAL_SCHEMA_STATEMENTS = (
    """
    CREATE CONSTRAINT trial_nct_id_unique IF NOT EXISTS
    FOR (t:Trial)
    REQUIRE t.nct_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT condition_canonical_key_unique IF NOT EXISTS
    FOR (c:Condition)
    REQUIRE c.canonical_key IS UNIQUE
    """,
    """
    CREATE CONSTRAINT intervention_canonical_key_unique IF NOT EXISTS
    FOR (i:Intervention)
    REQUIRE i.canonical_key IS UNIQUE
    """,
    """
    CREATE CONSTRAINT sponsor_canonical_key_unique IF NOT EXISTS
    FOR (s:Sponsor)
    REQUIRE s.canonical_key IS UNIQUE
    """,
    """
    CREATE INDEX trial_canonical_load_run_index IF NOT EXISTS
    FOR (t:Trial)
    ON (t.canonical_load_run_id)
    """,
    """
    CREATE INDEX condition_normalized_name_index IF NOT EXISTS
    FOR (c:Condition)
    ON (c.normalized_name)
    """,
    """
    CREATE INDEX intervention_normalized_name_index IF NOT EXISTS
    FOR (i:Intervention)
    ON (i.normalized_name)
    """,
    """
    CREATE INDEX sponsor_normalized_name_index IF NOT EXISTS
    FOR (s:Sponsor)
    ON (s.normalized_name)
    """,
    """
    CREATE INDEX condition_loaded_trial_count_index IF NOT EXISTS
    FOR (c:Condition)
    ON (c.loaded_trial_count)
    """,
    """
    CREATE INDEX intervention_loaded_trial_count_index IF NOT EXISTS
    FOR (i:Intervention)
    ON (i.loaded_trial_count)
    """,
    """
    CREATE INDEX sponsor_loaded_trial_count_index IF NOT EXISTS
    FOR (s:Sponsor)
    ON (s.loaded_trial_count)
    """,
    """
    CREATE TEXT INDEX trial_nct_id_search_text_index IF NOT EXISTS
    FOR (t:Trial)
    ON (t.nct_id_search)
    """,
    """
    CREATE TEXT INDEX trial_brief_title_search_text_index IF NOT EXISTS
    FOR (t:Trial)
    ON (t.brief_title_search)
    """,
    """
    CREATE TEXT INDEX trial_official_title_search_text_index IF NOT EXISTS
    FOR (t:Trial)
    ON (t.official_title_search)
    """,
)


def normalize_name(value: str) -> str:
    """Return the conservative name normalization used for canonical identity."""
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("Canonical entity name cannot be blank.")
    return normalized


def canonical_entity_key(
    table: str,
    name: str,
    *,
    intervention_type: str | None = None,
) -> str:
    """Build the Batch-13 exact source-backed canonical key."""
    if table not in CORE_ENTITY_SPECS:
        raise ValueError(f"Unsupported canonical entity table: {table}")
    normalized_name = normalize_name(name)
    if table == "interventions":
        normalized_type = (intervention_type or "").strip().lower()
        return f"{normalized_name}|{normalized_type}"
    return normalized_name


def _postgres_connection_string() -> str:
    settings = get_settings()
    return (
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_database} "
        f"user={settings.postgres_username} "
        f"password={settings.postgres_password}"
    )


def _jsonable_scalar(value: Any) -> Any:
    """Convert source scalars into stable Neo4j property values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _clean_list(values: Iterable[Any] | None) -> list[Any]:
    if not values:
        return []
    return [
        converted
        for value in values
        if value is not None and (converted := _jsonable_scalar(value)) is not None
    ]


def _prepare_trial_row(row: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    nct_id = str(row["nct_id"])
    properties = {
        field: _jsonable_scalar(row.get(field))
        for field in TRIAL_FIELDS
        if row.get(field) is not None
    }
    properties.update(
        {
            "nct_id": nct_id,
            "nct_id_search": nct_id.casefold(),
            "source_key": f"trial:{nct_id}",
            "source_table": "studies",
            "source_database": get_settings().postgres_database,
            "source_schema": get_settings().postgres_schema,
            "canonical_loader_version": CANONICAL_LOADER_VERSION,
            "canonical_load_run_id": run_id,
        }
    )
    if properties.get("brief_title") is not None:
        properties["brief_title_search"] = str(properties["brief_title"]).casefold()
    if properties.get("official_title") is not None:
        properties["official_title_search"] = str(properties["official_title"]).casefold()
    return {"nct_id": nct_id, "properties": properties}


def _fetch_trial_batch(
    cursor: Any,
    *,
    schema: str,
    after_nct_id: str | None,
    batch_size: int,
) -> list[dict[str, Any]]:
    field_sql = sql.SQL(", ").join(sql.Identifier(field) for field in TRIAL_FIELDS)
    if after_nct_id is None:
        query = sql.SQL(
            "SELECT {fields} FROM {schema}.studies "
            "ORDER BY nct_id LIMIT %s"
        ).format(fields=field_sql, schema=sql.Identifier(schema))
        cursor.execute(query, (batch_size,))
    else:
        query = sql.SQL(
            "SELECT {fields} FROM {schema}.studies "
            "WHERE nct_id > %s ORDER BY nct_id LIMIT %s"
        ).format(fields=field_sql, schema=sql.Identifier(schema))
        cursor.execute(query, (after_nct_id, batch_size))
    return [dict(row) for row in cursor.fetchall()]


def _entity_aggregate_query(schema: str, table: str) -> sql.Composed:
    if table not in CORE_ENTITY_SPECS:
        raise ValueError(f"Unsupported canonical entity table: {table}")

    source = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(table))
    if table == "conditions":
        return sql.SQL(
            "SELECT nct_id, lower(trim(name)) AS canonical_key, "
            "lower(trim(name)) AS normalized_name, min(name) AS display_name, "
            "min(id) AS source_id, array_agg(id ORDER BY id) AS source_ids, "
            "count(*) AS source_row_count, "
            "array_agg(DISTINCT name ORDER BY name) AS source_names "
            "FROM {source} "
            "WHERE nct_id = ANY(%s) AND name IS NOT NULL AND btrim(name) <> '' "
            "GROUP BY nct_id, lower(trim(name)) "
            "ORDER BY canonical_key, nct_id"
        ).format(source=source)

    if table == "interventions":
        return sql.SQL(
            "SELECT nct_id, "
            "lower(trim(name)) || '|' || lower(trim(coalesce(intervention_type, ''))) "
            "AS canonical_key, "
            "lower(trim(name)) AS normalized_name, min(name) AS display_name, "
            "min(intervention_type) AS intervention_type, "
            "min(id) AS source_id, array_agg(id ORDER BY id) AS source_ids, "
            "count(*) AS source_row_count, "
            "array_agg(DISTINCT name ORDER BY name) AS source_names "
            "FROM {source} "
            "WHERE nct_id = ANY(%s) AND name IS NOT NULL AND btrim(name) <> '' "
            "GROUP BY nct_id, lower(trim(name)), lower(trim(coalesce(intervention_type, ''))) "
            "ORDER BY canonical_key, nct_id"
        ).format(source=source)

    return sql.SQL(
        "SELECT nct_id, lower(trim(name)) AS canonical_key, "
        "lower(trim(name)) AS normalized_name, min(name) AS display_name, "
        "min(id) AS source_id, array_agg(id ORDER BY id) AS source_ids, "
        "count(*) AS source_row_count, "
        "array_agg(DISTINCT name ORDER BY name) AS source_names, "
        "array_agg(DISTINCT agency_class ORDER BY agency_class) "
        "FILTER (WHERE agency_class IS NOT NULL) AS agency_classes, "
        "array_agg(DISTINCT lead_or_collaborator ORDER BY lead_or_collaborator) "
        "FILTER (WHERE lead_or_collaborator IS NOT NULL) AS sponsor_roles "
        "FROM {source} "
        "WHERE nct_id = ANY(%s) AND name IS NOT NULL AND btrim(name) <> '' "
        "GROUP BY nct_id, lower(trim(name)) "
        "ORDER BY canonical_key, nct_id"
    ).format(source=source)


def _fetch_entity_rows(
    cursor: Any,
    *,
    schema: str,
    table: str,
    nct_ids: list[str],
    run_id: str,
) -> list[dict[str, Any]]:
    cursor.execute(_entity_aggregate_query(schema, table), (nct_ids,))
    settings = get_settings()
    rows: list[dict[str, Any]] = []
    for raw in cursor.fetchall():
        row = dict(raw)
        canonical_key = str(row["canonical_key"])
        normalized_name = str(row["normalized_name"])
        nct_id = str(row["nct_id"])
        source_ids = _clean_list(row.get("source_ids"))
        source_names = [str(value) for value in _clean_list(row.get("source_names"))]
        relationship_properties: dict[str, Any] = {
            "source_key": (
                f"canonical:{CORE_ENTITY_SPECS[table]['relationship']}:"
                f"{canonical_key}:{nct_id}"
            ),
            "source_table": table,
            "source_database": settings.postgres_database,
            "source_schema": settings.postgres_schema,
            "source_nct_id": nct_id,
            "nct_id": nct_id,
            "source_id": int(row["source_id"]),
            "source_ids": source_ids,
            "source_row_count": int(row["source_row_count"]),
            "source_names": source_names,
            "canonical_key": canonical_key,
            "canonical_loader_version": CANONICAL_LOADER_VERSION,
            "canonical_load_run_id": run_id,
        }
        if table == "sponsors":
            relationship_properties["agency_classes"] = [
                str(value) for value in _clean_list(row.get("agency_classes"))
            ]
            relationship_properties["sponsor_roles"] = [
                str(value) for value in _clean_list(row.get("sponsor_roles"))
            ]

        entity_properties: dict[str, Any] = {
            "canonical": True,
            "canonical_key": canonical_key,
            "normalized_name": normalized_name,
            "name": str(row["display_name"]),
            "source_table": table,
            "canonical_loader_version": CANONICAL_LOADER_VERSION,
        }
        if table == "conditions":
            # Backward-compatible property used by the existing exact-condition
            # read path until Batch 14 switches it to normalized_name.
            entity_properties["downcase_name"] = normalized_name
        if table == "interventions" and row.get("intervention_type") is not None:
            entity_properties["intervention_type"] = str(row["intervention_type"])

        rows.append(
            {
                "nct_id": nct_id,
                "canonical_key": canonical_key,
                "entity_properties": entity_properties,
                "relationship_properties": relationship_properties,
                "source_row_count": int(row["source_row_count"]),
            }
        )
    return rows


def _deduplicate_entity_nodes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one deterministic node payload per canonical key in a batch."""
    nodes: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["canonical_key"]
        properties = dict(row["entity_properties"])
        existing = nodes.get(key)
        if existing is None:
            nodes[key] = {"canonical_key": key, "properties": properties}
            continue
        # A canonical node may appear in many trials.  Keep a stable display name
        # across batches and reruns rather than whichever source row is seen last.
        current_name = str(existing["properties"].get("name") or "")
        candidate_name = str(properties.get("name") or "")
        if candidate_name and (not current_name or candidate_name < current_name):
            existing["properties"]["name"] = candidate_name
    return [nodes[key] for key in sorted(nodes)]


def apply_canonical_schema(connection: Neo4jConnection) -> None:
    """Apply the Batch-13 canonical identity constraints and lookup indexes."""
    for statement in CANONICAL_SCHEMA_STATEMENTS:
        connection.execute_write(statement.strip())


def _cleanup_scope(
    connection: Neo4jConnection,
    *,
    nct_ids: list[str],
) -> dict[str, int]:
    """Remove only replaceable core-graph data for the current trial scope."""
    removed: dict[str, int] = {}
    for table, spec in CORE_ENTITY_SPECS.items():
        label = spec["label"]
        relationship = spec["relationship"]
        prefix = spec["legacy_prefix"]

        canonical_result = connection.execute_write(
            f"""
            MATCH (entity:{label})-[rel:{relationship}]->(trial:Trial)
            WHERE trial.nct_id IN $nct_ids
              AND entity.canonical_key IS NOT NULL
            WITH collect(rel) AS relationships
            FOREACH (rel IN relationships | DELETE rel)
            RETURN size(relationships) AS removed
            """,
            {"nct_ids": nct_ids},
        )
        canonical_removed = int(canonical_result[0]["removed"]) if canonical_result else 0

        legacy_result = connection.execute_write(
            f"""
            MATCH (entity:{label})-[rel:{relationship}]->(trial:Trial)
            WHERE trial.nct_id IN $nct_ids
              AND entity.canonical_key IS NULL
              AND entity.source_key STARTS WITH $prefix
            WITH collect(DISTINCT entity) AS entities, collect(rel) AS relationships
            FOREACH (rel IN relationships | DELETE rel)
            FOREACH (entity IN entities | DETACH DELETE entity)
            RETURN size(relationships) AS relationships_removed,
                   size(entities) AS nodes_removed
            """,
            {"nct_ids": nct_ids, "prefix": prefix},
        )
        legacy_relationships = (
            int(legacy_result[0]["relationships_removed"]) if legacy_result else 0
        )
        legacy_nodes = int(legacy_result[0]["nodes_removed"]) if legacy_result else 0
        removed[f"{table}_canonical_relationships"] = canonical_removed
        removed[f"{table}_legacy_relationships"] = legacy_relationships
        removed[f"{table}_legacy_nodes"] = legacy_nodes
    return removed


def _upsert_trials(
    connection: Neo4jConnection,
    rows: list[dict[str, Any]],
) -> int:
    if not rows:
        return 0
    result = connection.execute_write(
        """
        UNWIND $rows AS row
        MERGE (trial:Trial {nct_id: row.nct_id})
        SET trial += row.properties
        RETURN count(trial) AS loaded
        """,
        {"rows": rows},
    )
    return int(result[0]["loaded"]) if result else 0


def _upsert_entity_batch(
    connection: Neo4jConnection,
    *,
    table: str,
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    if not rows:
        return {"nodes": 0, "relationships": 0, "source_rows": 0}
    spec = CORE_ENTITY_SPECS[table]
    label = spec["label"]
    relationship = spec["relationship"]
    node_rows = _deduplicate_entity_nodes(rows)

    node_result = connection.execute_write(
        f"""
        UNWIND $rows AS row
        MERGE (entity:{label} {{canonical_key: row.canonical_key}})
        WITH entity, row, entity.name AS existing_name
        SET entity += row.properties
        SET entity.name = CASE
            WHEN existing_name IS NULL OR row.properties.name < existing_name
            THEN row.properties.name
            ELSE existing_name
        END
        RETURN count(entity) AS loaded
        """,
        {"rows": node_rows},
    )

    relationship_rows = [
        {
            "nct_id": row["nct_id"],
            "canonical_key": row["canonical_key"],
            "properties": row["relationship_properties"],
        }
        for row in rows
    ]
    relationship_result = connection.execute_write(
        f"""
        UNWIND $rows AS row
        MATCH (entity:{label} {{canonical_key: row.canonical_key}})
        MATCH (trial:Trial {{nct_id: row.nct_id}})
        MERGE (entity)-[rel:{relationship}]->(trial)
        SET rel += row.properties
        RETURN count(rel) AS loaded
        """,
        {"rows": relationship_rows},
    )
    return {
        "nodes": int(node_result[0]["loaded"]) if node_result else 0,
        "relationships": (
            int(relationship_result[0]["loaded"]) if relationship_result else 0
        ),
        "source_rows": sum(int(row["source_row_count"]) for row in rows),
    }


def _refresh_loaded_fanout(connection: Neo4jConnection) -> dict[str, int]:
    """Materialize graph-local fan-out for future bounded hub-aware retrieval."""
    refreshed: dict[str, int] = {}
    for table, spec in CORE_ENTITY_SPECS.items():
        label = spec["label"]
        relationship = spec["relationship"]
        result = connection.execute_write(
            f"""
            MATCH (entity:{label})-[rel:{relationship}]->(:Trial)
            WHERE entity.canonical = true
              AND entity.canonical_key IS NOT NULL
            WITH entity, count(rel) AS loaded_trial_count,
                 sum(coalesce(rel.source_row_count, 1)) AS loaded_source_row_count
            SET entity.loaded_trial_count = loaded_trial_count,
                entity.loaded_source_row_count = loaded_source_row_count
            RETURN count(entity) AS refreshed
            """
        )
        refreshed[table] = int(result[0]["refreshed"]) if result else 0
    return refreshed


def _delete_orphaned_canonical_nodes(connection: Neo4jConnection) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for table, spec in CORE_ENTITY_SPECS.items():
        label = spec["label"]
        result = connection.execute_write(
            f"""
            MATCH (entity:{label})
            WHERE entity.canonical = true
              AND entity.canonical_key IS NOT NULL
              AND NOT EXISTS {{ MATCH (entity)--() }}
            WITH collect(entity) AS entities
            FOREACH (entity IN entities | DELETE entity)
            RETURN size(entities) AS deleted
            """
        )
        deleted[table] = int(result[0]["deleted"]) if result else 0
    return deleted


def _reconcile_run(
    connection: Neo4jConnection,
    *,
    run_id: str,
    expected_trials: int,
    expected_entities: dict[str, dict[str, int]],
) -> dict[str, Any]:
    trial_records = connection.execute_read(
        """
        MATCH (trial:Trial)
        WHERE trial.canonical_load_run_id = $run_id
        RETURN count(trial) AS trial_count,
               count(CASE WHEN trial.source_key IS NOT NULL THEN 1 END) AS sourced_trials
        """,
        {"run_id": run_id},
    )
    trial_row = trial_records[0] if trial_records else {}
    actual_trials = int(trial_row.get("trial_count") or 0)
    sourced_trials = int(trial_row.get("sourced_trials") or 0)

    entity_reports: dict[str, Any] = {}
    errors: list[str] = []
    if actual_trials != expected_trials:
        errors.append(
            f"Trial count mismatch: expected {expected_trials}, found {actual_trials}."
        )
    if sourced_trials != expected_trials:
        errors.append(
            f"Trial provenance mismatch: expected {expected_trials}, found {sourced_trials}."
        )

    for table, spec in CORE_ENTITY_SPECS.items():
        label = spec["label"]
        relationship = spec["relationship"]
        records = connection.execute_read(
            f"""
            MATCH (trial:Trial {{canonical_load_run_id: $run_id}})
            MATCH (entity:{label})-[rel:{relationship}]->(trial)
            RETURN count(rel) AS relationship_count,
                   sum(coalesce(rel.source_row_count, 0)) AS represented_source_rows,
                   count(CASE
                       WHEN entity.canonical = true
                        AND entity.canonical_key IS NOT NULL
                        AND rel.source_table = $source_table
                        AND rel.source_id IS NOT NULL
                        AND rel.source_nct_id = trial.nct_id
                       THEN 1
                   END) AS provenance_relationship_count,
                   count(DISTINCT entity) AS connected_entity_nodes
            """,
            {"run_id": run_id, "source_table": table},
        )
        row = records[0] if records else {}
        actual_relationships = int(row.get("relationship_count") or 0)
        actual_source_rows = int(row.get("represented_source_rows") or 0)
        provenance_relationships = int(row.get("provenance_relationship_count") or 0)
        connected_nodes = int(row.get("connected_entity_nodes") or 0)
        expected = expected_entities[table]
        table_errors: list[str] = []
        if actual_relationships != expected["relationships"]:
            table_errors.append(
                f"relationship count expected {expected['relationships']}, "
                f"found {actual_relationships}"
            )
        if actual_source_rows != expected["source_rows"]:
            table_errors.append(
                f"represented source rows expected {expected['source_rows']}, "
                f"found {actual_source_rows}"
            )
        if provenance_relationships != expected["relationships"]:
            table_errors.append(
                f"provenance-bearing relationships expected {expected['relationships']}, "
                f"found {provenance_relationships}"
            )
        if table_errors:
            errors.extend(f"{table}: {message}." for message in table_errors)
        entity_reports[table] = {
            "expected_relationships": expected["relationships"],
            "actual_relationships": actual_relationships,
            "expected_source_rows": expected["source_rows"],
            "actual_represented_source_rows": actual_source_rows,
            "provenance_relationships": provenance_relationships,
            "connected_canonical_nodes": connected_nodes,
            "passed": not table_errors,
        }

    return {
        "passed": not errors,
        "run_id": run_id,
        "trials": {
            "expected": expected_trials,
            "actual": actual_trials,
            "provenance_trials": sourced_trials,
            "passed": actual_trials == expected_trials and sourced_trials == expected_trials,
        },
        "entities": entity_reports,
        "errors": errors,
    }


def _verify_source_samples(nct_ids: list[str]) -> dict[str, Any]:
    """Run existing graph-vs-AACT verification for a small deterministic sample."""
    from trialiq.services.source_verification import (
        VerificationStatus,
        verify_trial_evidence,
    )

    results: list[dict[str, Any]] = []
    for nct_id in nct_ids:
        try:
            response = verify_trial_evidence(nct_id)
            results.append(
                {
                    "nct_id": nct_id,
                    "status": response.status.value,
                    "passed": response.status == VerificationStatus.VERIFIED,
                    "discrepancies": list(response.discrepancies),
                    "validation": response.validation.model_dump(mode="json"),
                }
            )
        except Exception as exc:  # verification should still leave a report
            results.append(
                {
                    "nct_id": nct_id,
                    "status": "ERROR",
                    "passed": False,
                    "discrepancies": [
                        f"Source sample verification failed: {exc.__class__.__name__}: {exc}"
                    ],
                    "validation": {"valid": False, "errors": [str(exc)], "warnings": []},
                }
            )
    return {
        "passed": all(item["passed"] for item in results),
        "sample_count": len(results),
        "samples": results,
    }


def _write_report(report: dict[str, Any], output_path: str | Path | None) -> Path | None:
    if output_path is None:
        return None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_canonical_core_graph(
    *,
    limit: int | None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    output_path: str | Path | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    execution_batch: int = 13,
) -> dict[str, Any]:
    """Load and reconcile a deterministic AACT scope into the canonical core graph.

    ``limit=None`` means the full AACT ``ctgov.studies`` population.  A positive
    limit selects the first N studies by NCT ID and is intended for verification.
    """
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero when provided")
    if not 1 <= batch_size <= MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")

    settings = get_settings()
    if settings.postgres_schema != "ctgov":
        raise ValueError("Canonical GraphRAG loading is restricted to the ctgov schema.")

    run_id = (
        f"{CANONICAL_LOADER_VERSION}:"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}:"
        f"{uuid.uuid4().hex[:8]}"
    )
    started_at = datetime.now(timezone.utc)
    expected_entities = {
        table: {"relationships": 0, "source_rows": 0}
        for table in CORE_ENTITY_SPECS
    }
    load_totals = {
        table: {"nodes_touched": 0, "relationships_loaded": 0, "source_rows": 0}
        for table in CORE_ENTITY_SPECS
    }
    cleanup_totals: dict[str, int] = {}
    expected_trials = 0
    batch_count = 0
    first_nct_id: str | None = None
    last_nct_id: str | None = None
    batch_anchor_nct_ids: list[str] = []

    graph = Neo4jConnection()
    try:
        graph.verify_connectivity()
        apply_canonical_schema(graph)

        with psycopg.connect(
            _postgres_connection_string(),
            row_factory=dict_row,
        ) as source_connection:
            source_connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            with source_connection.cursor() as cursor:
                while limit is None or expected_trials < limit:
                    remaining = None if limit is None else limit - expected_trials
                    requested_batch = batch_size if remaining is None else min(batch_size, remaining)
                    trial_source_rows = _fetch_trial_batch(
                        cursor,
                        schema=settings.postgres_schema,
                        after_nct_id=last_nct_id,
                        batch_size=requested_batch,
                    )
                    if not trial_source_rows:
                        break

                    nct_ids = [str(row["nct_id"]) for row in trial_source_rows]
                    if first_nct_id is None:
                        first_nct_id = nct_ids[0]
                    last_nct_id = nct_ids[-1]
                    batch_anchor_nct_ids.append(nct_ids[0])
                    batch_count += 1

                    cleanup = _cleanup_scope(graph, nct_ids=nct_ids)
                    for key, value in cleanup.items():
                        cleanup_totals[key] = cleanup_totals.get(key, 0) + int(value)

                    trial_rows = [
                        _prepare_trial_row(row, run_id=run_id)
                        for row in trial_source_rows
                    ]
                    loaded_trials = _upsert_trials(graph, trial_rows)
                    if loaded_trials != len(trial_rows):
                        raise RuntimeError(
                            "Trial batch load count mismatch: "
                            f"expected {len(trial_rows)}, loaded {loaded_trials}."
                        )

                    for table in CORE_ENTITY_SPECS:
                        entity_rows = _fetch_entity_rows(
                            cursor,
                            schema=settings.postgres_schema,
                            table=table,
                            nct_ids=nct_ids,
                            run_id=run_id,
                        )
                        result = _upsert_entity_batch(
                            graph,
                            table=table,
                            rows=entity_rows,
                        )
                        expected_entities[table]["relationships"] += len(entity_rows)
                        expected_entities[table]["source_rows"] += sum(
                            int(row["source_row_count"]) for row in entity_rows
                        )
                        load_totals[table]["nodes_touched"] += result["nodes"]
                        load_totals[table]["relationships_loaded"] += result["relationships"]
                        load_totals[table]["source_rows"] += result["source_rows"]

                    expected_trials += len(trial_rows)
                    if progress_callback is not None:
                        progress_callback(
                            {
                                "batch_count": batch_count,
                                "trials_loaded": expected_trials,
                                "last_nct_id": last_nct_id,
                                "limit": limit,
                            }
                        )

        if limit is not None and expected_trials != limit:
            raise RuntimeError(
                f"Requested {limit} verification trials but source returned {expected_trials}."
            )

        orphan_cleanup = _delete_orphaned_canonical_nodes(graph)
        fanout_refresh = _refresh_loaded_fanout(graph)
        reconciliation = _reconcile_run(
            graph,
            run_id=run_id,
            expected_trials=expected_trials,
            expected_entities=expected_entities,
        )

        sample_ids: list[str] = []
        if first_nct_id is not None:
            sample_ids.append(first_nct_id)
        if batch_anchor_nct_ids:
            sample_ids.append(batch_anchor_nct_ids[len(batch_anchor_nct_ids) // 2])
        if last_nct_id is not None:
            sample_ids.append(last_nct_id)
        sample_ids = list(dict.fromkeys(sample_ids))
        source_sample_verification = _verify_source_samples(sample_ids)
        overall_passed = reconciliation["passed"] and source_sample_verification["passed"]
        completed_at = datetime.now(timezone.utc)
        report: dict[str, Any] = {
            "batch": execution_batch,
            "loader_origin_batch": 13,
            "loader_version": CANONICAL_LOADER_VERSION,
            "run_id": run_id,
            "mode": "full" if limit is None else "verification",
            "passed": overall_passed,
            "started_at_utc": started_at.isoformat(),
            "completed_at_utc": completed_at.isoformat(),
            "scope": {
                "requested_limit": limit,
                "trial_count": expected_trials,
                "first_nct_id": first_nct_id,
                "last_nct_id": last_nct_id,
                "batch_size": batch_size,
                "batch_count": batch_count,
            },
            "load": {
                "trials_loaded": expected_trials,
                "entities": load_totals,
                "cleanup": cleanup_totals,
                "orphaned_canonical_nodes_removed": orphan_cleanup,
                "fanout_nodes_refreshed": fanout_refresh,
                "blank_name_policy": "source rows with null/blank names are excluded",
            },
            "reconciliation": reconciliation,
            "source_sample_verification": source_sample_verification,
            "constraints_preserved": {
                "mcp_graph_transport": True,
                "no_direct_runtime_fallback_added": True,
                "fixed_loader_cypher_only": True,
                "frontend_modified": False,
                "llm_orchestration_modified": False,
            },
        }
        written_path = _write_report(report, output_path)
        if written_path is not None:
            report["report_path"] = str(written_path)
        return report
    finally:
        graph.close()
