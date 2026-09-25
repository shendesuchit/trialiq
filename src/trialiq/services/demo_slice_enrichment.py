"""Source-backed enrichment for the bounded NCT03416088 GraphRAG demo slice.

The canonical shared-entity demo topology is intentionally small and explicit.
This module refreshes the scalar Trial attributes used by deterministic timeline
and enrollment comparisons directly from the canonical AACT PostgreSQL source.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from trialiq.config.settings import get_settings
from trialiq.graph.connection import Neo4jConnection


DEMO_SLICE_SEED_NCT_ID = "NCT03416088"
DEMO_SLICE_NCT_IDS = (
    "NCT03416088",
    "NCT04214743",
    "NCT04731987",
    "NCT07764198",
)
TRIAL_SOURCE_FIELDS = (
    "brief_title",
    "overall_status",
    "start_date",
    "completion_date",
    "enrollment",
)


class DemoTrialSourceReader(Protocol):
    def get_trials(self, nct_ids: tuple[str, ...]) -> list[dict[str, Any]]: ...


class DemoTrialGraphStore(Protocol):
    def read_trials(self, nct_ids: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]: ...

    def apply_trials(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


class PostgresDemoTrialSourceReader:
    """Read only the allowlisted Trial fields needed by the demo slice."""

    def get_trials(self, nct_ids: tuple[str, ...]) -> list[dict[str, Any]]:
        settings = get_settings()
        if settings.postgres_schema != "ctgov":
            raise ValueError("Demo-slice enrichment is restricted to the ctgov schema.")

        connection_string = (
            f"host={settings.postgres_host} port={settings.postgres_port} "
            f"dbname={settings.postgres_database} user={settings.postgres_username} "
            f"password={settings.postgres_password}"
        )
        schema = sql.Identifier(settings.postgres_schema)
        query = sql.SQL(
            "SELECT nct_id, brief_title, overall_status, start_date, completion_date, enrollment "
            "FROM {}.studies WHERE nct_id = ANY(%s) ORDER BY nct_id"
        ).format(schema)

        with psycopg.connect(connection_string, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (list(nct_ids),))
                return [dict(row) for row in cursor.fetchall()]


class Neo4jDemoTrialGraphStore:
    """Read and atomically update the four explicit demo Trial nodes."""

    _READ_QUERY = """
    UNWIND $nct_ids AS requested_nct_id
    OPTIONAL MATCH (trial:Trial {nct_id: requested_nct_id})
    WITH requested_nct_id, collect(trial) AS nodes
    RETURN
        requested_nct_id AS nct_id,
        [node IN nodes | {
            nct_id: node.nct_id,
            brief_title: node.brief_title,
            overall_status: node.overall_status,
            start_date: node.start_date,
            completion_date: node.completion_date,
            enrollment: node.enrollment
        }] AS trials
    ORDER BY nct_id
    """

    _CARDINALITY_QUERY = """
    UNWIND $nct_ids AS requested_nct_id
    OPTIONAL MATCH (trial:Trial {nct_id: requested_nct_id})
    RETURN requested_nct_id AS nct_id, count(trial) AS node_count
    ORDER BY nct_id
    """

    _UPDATE_QUERY = """
    UNWIND $rows AS row
    MATCH (trial:Trial {nct_id: row.nct_id})
    SET trial.brief_title = row.brief_title,
        trial.overall_status = row.overall_status,
        trial.start_date = row.start_date,
        trial.completion_date = row.completion_date,
        trial.enrollment = row.enrollment
    RETURN
        trial.nct_id AS nct_id,
        trial.brief_title AS brief_title,
        trial.overall_status AS overall_status,
        trial.start_date AS start_date,
        trial.completion_date AS completion_date,
        trial.enrollment AS enrollment
    ORDER BY nct_id
    """

    def read_trials(self, nct_ids: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
        connection = Neo4jConnection()
        try:
            records = connection.execute_read(self._READ_QUERY, {"nct_ids": list(nct_ids)})
        finally:
            connection.close()

        return {
            str(record["nct_id"]): [dict(item) for item in (record.get("trials") or [])]
            for record in records
        }

    def apply_trials(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nct_ids = tuple(str(row["nct_id"]) for row in rows)
        connection = Neo4jConnection()
        try:
            with connection.transaction() as transaction:
                cardinality = transaction.run(
                    self._CARDINALITY_QUERY,
                    {"nct_ids": list(nct_ids)},
                ).data()
                invalid = {
                    str(record["nct_id"]): int(record.get("node_count") or 0)
                    for record in cardinality
                    if int(record.get("node_count") or 0) != 1
                }
                if invalid:
                    details = ", ".join(
                        f"{nct_id}={count}" for nct_id, count in sorted(invalid.items())
                    )
                    raise ValueError(
                        "Demo-slice enrichment requires exactly one Trial node per NCT ID; "
                        f"invalid counts: {details}."
                    )
                return transaction.run(self._UPDATE_QUERY, {"rows": rows}).data()
        finally:
            connection.close()


def _normalize_source_value(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field in {"start_date", "completion_date"}:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value).strip() or None
    if field == "enrollment":
        if isinstance(value, bool):
            raise ValueError("Boolean enrollment values are not accepted.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid enrollment value: {value!r}") from exc
    return str(value).strip() if value is not None else None


def _normalize_source_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = set(DEMO_SLICE_NCT_IDS)
    normalized: dict[str, dict[str, Any]] = {}

    for row in rows:
        raw_nct_id = row.get("nct_id")
        nct_id = str(raw_nct_id or "").strip().upper()
        if nct_id not in expected:
            raise ValueError(f"Unexpected source NCT ID in demo enrichment: {nct_id or '<empty>'}.")
        if nct_id in normalized:
            raise ValueError(f"Duplicate source row for demo trial {nct_id}.")
        normalized[nct_id] = {
            "nct_id": nct_id,
            **{
                field: _normalize_source_value(field, row.get(field))
                for field in TRIAL_SOURCE_FIELDS
            },
        }

    missing = sorted(expected - set(normalized))
    if missing:
        raise ValueError(
            "Canonical AACT source rows are missing for demo trials: " + ", ".join(missing)
        )

    return [normalized[nct_id] for nct_id in DEMO_SLICE_NCT_IDS]


def _comparison_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _build_report(
    source_rows: list[dict[str, Any]],
    graph_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    trials: list[dict[str, Any]] = []
    ready_to_apply = True
    synchronized = True

    source_by_id = {row["nct_id"]: row for row in source_rows}
    for nct_id in DEMO_SLICE_NCT_IDS:
        source = source_by_id[nct_id]
        candidates = graph_rows.get(nct_id, [])
        node_count = len(candidates)
        graph = candidates[0] if node_count == 1 else None
        if node_count != 1:
            ready_to_apply = False
            synchronized = False
            differences = list(TRIAL_SOURCE_FIELDS)
            status = "MISSING_GRAPH_NODE" if node_count == 0 else "DUPLICATE_GRAPH_NODES"
        else:
            differences = [
                field
                for field in TRIAL_SOURCE_FIELDS
                if _comparison_value(graph.get(field)) != source.get(field)
            ]
            if differences:
                synchronized = False
                status = "NEEDS_ENRICHMENT"
            else:
                status = "SYNCHRONIZED"

        trials.append(
            {
                "nct_id": nct_id,
                "status": status,
                "graph_node_count": node_count,
                "differences": differences,
                "source": source,
                "graph": graph,
            }
        )

    return {
        "demo_slice": DEMO_SLICE_SEED_NCT_ID,
        "nct_ids": list(DEMO_SLICE_NCT_IDS),
        "source_fields": list(TRIAL_SOURCE_FIELDS),
        "ready_to_apply": ready_to_apply,
        "synchronized": synchronized,
        "trials": trials,
    }


def inspect_demo_slice_trial_data(
    *,
    source_reader: DemoTrialSourceReader | None = None,
    graph_store: DemoTrialGraphStore | None = None,
) -> dict[str, Any]:
    """Inspect source/graph differences without changing Neo4j."""
    reader = source_reader or PostgresDemoTrialSourceReader()
    store = graph_store or Neo4jDemoTrialGraphStore()
    source_rows = _normalize_source_rows(reader.get_trials(DEMO_SLICE_NCT_IDS))
    graph_rows = store.read_trials(DEMO_SLICE_NCT_IDS)
    return _build_report(source_rows, graph_rows)


def enrich_demo_slice_trial_data(
    *,
    source_reader: DemoTrialSourceReader | None = None,
    graph_store: DemoTrialGraphStore | None = None,
) -> dict[str, Any]:
    """Refresh the demo Trial scalars from AACT and verify the resulting graph state."""
    reader = source_reader or PostgresDemoTrialSourceReader()
    store = graph_store or Neo4jDemoTrialGraphStore()
    source_rows = _normalize_source_rows(reader.get_trials(DEMO_SLICE_NCT_IDS))
    before = _build_report(source_rows, store.read_trials(DEMO_SLICE_NCT_IDS))

    if not before["ready_to_apply"]:
        invalid = [
            f"{item['nct_id']} ({item['graph_node_count']} nodes)"
            for item in before["trials"]
            if item["graph_node_count"] != 1
        ]
        raise ValueError(
            "Demo-slice Trial-node cardinality check failed: " + ", ".join(invalid)
        )

    updated = store.apply_trials(source_rows)
    after = _build_report(source_rows, store.read_trials(DEMO_SLICE_NCT_IDS))
    if not after["synchronized"]:
        remaining = [
            f"{item['nct_id']}:{','.join(item['differences']) or item['status']}"
            for item in after["trials"]
            if item["status"] != "SYNCHRONIZED"
        ]
        raise RuntimeError(
            "Demo-slice enrichment completed but source/graph verification still differs: "
            + "; ".join(remaining)
        )

    return {
        "demo_slice": DEMO_SLICE_SEED_NCT_ID,
        "updated_trial_count": len(updated),
        "before": before,
        "after": after,
    }
