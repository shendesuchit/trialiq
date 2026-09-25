"""Cross-source verification of graph evidence against canonical AACT PostgreSQL rows."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Protocol

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field

from trialiq.config.settings import get_settings
from trialiq.services.graph_query_service import query_trial_by_nct_id
from trialiq.services.models import GraphQueryResponse, GraphQueryStatus, ValidationResult

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CONFLICT = "CONFLICT"
    MISSING_SOURCE = "MISSING_SOURCE"
    NOT_CHECKED = "NOT_CHECKED"


class FieldVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    status: VerificationStatus
    graph_value: Any = None
    source_value: Any = None
    source_table: str | None = None


class TrialVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str
    status: VerificationStatus
    fields: list[FieldVerification] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    validation: ValidationResult


class TrialSourceReader(Protocol):
    def get_trial_snapshot(self, nct_id: str) -> dict[str, Any] | None: ...


class PostgresTrialSourceReader:
    """Read the small allowlisted source projection used for verification."""

    def get_trial_snapshot(self, nct_id: str) -> dict[str, Any] | None:
        settings = get_settings()
        if settings.postgres_schema != "ctgov":
            raise ValueError("Source verification is restricted to the ctgov schema.")

        connection_string = (
            f"host={settings.postgres_host} port={settings.postgres_port} "
            f"dbname={settings.postgres_database} user={settings.postgres_username} "
            f"password={settings.postgres_password}"
        )
        schema = sql.Identifier(settings.postgres_schema)
        with psycopg.connect(connection_string, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "SELECT nct_id, brief_title, overall_status, start_date, completion_date, enrollment "
                        "FROM {}.studies WHERE nct_id = %s"
                    ).format(schema),
                    (nct_id,),
                )
                study = cursor.fetchone()
                if study is None:
                    return None

                snapshot: dict[str, Any] = dict(study)
                for table in ("conditions", "interventions", "sponsors"):
                    cursor.execute(
                        sql.SQL("SELECT name FROM {}.{} WHERE nct_id = %s ORDER BY name").format(
                            schema, sql.Identifier(table)
                        ),
                        (nct_id,),
                    )
                    snapshot[table] = [row["name"] for row in cursor.fetchall() if row.get("name")]
                return snapshot


def _normalized_scalar(value: Any) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split()).casefold()


def _normalized_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names = []
    for item in value:
        raw = item.get("name") if isinstance(item, dict) else item
        normalized = _normalized_scalar(raw)
        if normalized:
            names.append(normalized)
    return sorted(set(names))


def _field(
    name: str,
    graph_value: Any,
    source_value: Any,
    source_table: str,
    *,
    collection: bool = False,
) -> FieldVerification:
    graph_normalized = _normalized_names(graph_value) if collection else _normalized_scalar(graph_value)
    source_normalized = _normalized_names(source_value) if collection else _normalized_scalar(source_value)
    return FieldVerification(
        field=name,
        status=(
            VerificationStatus.VERIFIED
            if graph_normalized == source_normalized
            else VerificationStatus.CONFLICT
        ),
        graph_value=graph_value,
        source_value=source_value,
        source_table=source_table,
    )


def verify_graph_response_against_source(
    graph_response: GraphQueryResponse,
    *,
    source_reader: TrialSourceReader | None = None,
) -> TrialVerificationResponse:
    """Compare high-value graph facts with their canonical AACT source rows."""
    nct_id = graph_response.nct_id.strip().upper()
    if graph_response.status != GraphQueryStatus.SUCCESS or not graph_response.evidence:
        return TrialVerificationResponse(
            nct_id=nct_id,
            status=VerificationStatus.NOT_CHECKED,
            validation=ValidationResult(
                valid=False,
                errors=["Source verification requires successful validated graph evidence."],
            ),
        )

    reader = source_reader or PostgresTrialSourceReader()
    try:
        source = reader.get_trial_snapshot(nct_id)
    except Exception:
        logger.exception("PostgreSQL source verification failed")
        return TrialVerificationResponse(
            nct_id=nct_id,
            status=VerificationStatus.NOT_CHECKED,
            validation=ValidationResult(
                valid=False,
                errors=["Source verification could not be completed because of an internal source error."],
            ),
        )

    if source is None:
        return TrialVerificationResponse(
            nct_id=nct_id,
            status=VerificationStatus.MISSING_SOURCE,
            validation=ValidationResult(
                valid=False,
                errors=[f"Canonical source record was not found for {nct_id}."],
            ),
        )

    evidence = graph_response.evidence
    trial = evidence.get("trial") or {}
    fields = [
        _field("nct_id", trial.get("nct_id"), source.get("nct_id"), "studies"),
        _field("brief_title", trial.get("brief_title"), source.get("brief_title"), "studies"),
        _field("overall_status", trial.get("overall_status"), source.get("overall_status"), "studies"),
        _field("start_date", trial.get("start_date"), source.get("start_date"), "studies"),
        _field("completion_date", trial.get("completion_date"), source.get("completion_date"), "studies"),
        _field("enrollment", trial.get("enrollment"), source.get("enrollment"), "studies"),
        _field("conditions", evidence.get("conditions", []), source.get("conditions", []), "conditions", collection=True),
        _field("interventions", evidence.get("interventions", []), source.get("interventions", []), "interventions", collection=True),
        _field("sponsors", evidence.get("sponsors", []), source.get("sponsors", []), "sponsors", collection=True),
    ]
    conflicts = [item.field for item in fields if item.status == VerificationStatus.CONFLICT]
    return TrialVerificationResponse(
        nct_id=nct_id,
        status=VerificationStatus.CONFLICT if conflicts else VerificationStatus.VERIFIED,
        fields=fields,
        discrepancies=[f"Graph/source mismatch for field: {field}." for field in conflicts],
        validation=ValidationResult(
            valid=not conflicts,
            errors=[],
            warnings=[f"Cross-source discrepancies detected: {', '.join(conflicts)}."] if conflicts else [],
        ),
    )


def verify_trial_evidence(nct_id: str) -> TrialVerificationResponse:
    """Retrieve graph evidence and verify it against canonical PostgreSQL source rows."""
    return verify_graph_response_against_source(query_trial_by_nct_id(nct_id))
