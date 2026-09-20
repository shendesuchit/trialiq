
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import trialiq.etl.aact_extract as extract


TEST_NCT_IDS = ["NCT00000001", "NCT00000002"]

TABLES = extract.EXTRACT_TABLES


def build_artifact(
    *,
    nct_ids: list[str] | None = None,
    scope_limit: int | None = None,
    rows_by_table: dict[str, list[dict]] | None = None,
) -> dict:
    """Build a deterministic extracted artifact for reconciliation tests."""

    resolved_nct_ids = (
        TEST_NCT_IDS
        if nct_ids is None
        else nct_ids
    )

    resolved_scope_limit = (
        len(resolved_nct_ids)
        if scope_limit is None
        else scope_limit
    )

    resolved_rows = (
        {
            table: [
                {"nct_id": nct_id}
                for nct_id in resolved_nct_ids
            ]
            for table in TABLES
        }
        if rows_by_table is None
        else rows_by_table
    )

    return {
        "metadata": {
            "source_database": "aact",
            "source_schema": "ctgov",
            "scope_type": "deterministic_nct_id_order",
            "scope_limit": resolved_scope_limit,
            "nct_ids": resolved_nct_ids,
            "tables": list(TABLES),
        },
        "tables": resolved_rows,
    }


def write_artifact(
    tmp_path: Path,
    artifact: dict,
) -> Path:
    """Write an artifact to a temporary JSON file."""

    artifact_path = tmp_path / "artifact.json"

    artifact_path.write_text(
        json.dumps(artifact),
        encoding="utf-8",
    )

    return artifact_path


def build_connection_mock(
    *,
    source_scope: set[str],
    source_counts: dict[str, int],
) -> tuple[MagicMock, MagicMock]:
    """
    Build a mocked psycopg connection and cursor.

    Reconciliation performs:
    1. One fetchall() for the PostgreSQL trial scope.
    2. One fetchone() per approved extraction table.
    """

    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value.__enter__.return_value = cursor

    cursor.fetchall.return_value = [
        {"nct_id": nct_id}
        for nct_id in sorted(source_scope)
    ]

    cursor.fetchone.side_effect = [
        {"row_count": source_counts[table]}
        for table in TABLES
    ]

    return connection, cursor


def run_reconciliation(
    *,
    tmp_path: Path,
    artifact: dict,
    source_scope: set[str],
    source_counts: dict[str, int],
    schema: str = "ctgov",
) -> dict:
    """Run reconciliation with mocked PostgreSQL access."""

    artifact_path = write_artifact(
        tmp_path,
        artifact,
    )

    connection, _cursor = build_connection_mock(
        source_scope=source_scope,
        source_counts=source_counts,
    )

    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection

    with (
        patch.object(
            extract,
            "get_settings",
        ) as get_settings,
        patch.object(
            extract.psycopg,
            "connect",
            return_value=connection_context,
        ),
    ):
        get_settings.return_value.postgres_schema = schema
        get_settings.return_value.postgres_database = "aact"
        get_settings.return_value.postgres_host = "localhost"
        get_settings.return_value.postgres_port = 5432
        get_settings.return_value.postgres_username = "postgres"
        get_settings.return_value.postgres_password = "postgres"

        return extract.reconcile_aact_artifact(
            artifact_path,
        )


def expected_source_counts(
    *,
    nct_ids: list[str] | None = None,
) -> dict[str, int]:
    """Return expected row counts for each approved table."""

    count = (
        len(TEST_NCT_IDS)
        if nct_ids is None
        else len(nct_ids)
    )

    return {
        table: count
        for table in TABLES
    }


def test_reconciliation_passes_for_matching_artifact(
    tmp_path: Path,
) -> None:
    artifact = build_artifact()

    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=artifact,
        source_scope=set(TEST_NCT_IDS),
        source_counts=expected_source_counts(),
    )

    assert report["passed"] is True
    assert report["scope"] == {
        "expected_trial_count": 2,
        "declared_limit": 2,
    }
    assert report["errors"] == []

    for table in TABLES:
        assert report["tables"][table]["passed"] is True
        assert report["tables"][table]["source_count"] == 2
        assert report["tables"][table]["extracted_count"] == 2
        assert report["tables"][table]["unexpected_nct_ids"] == []


def test_reconciliation_rejects_expected_limit_mismatch(
    tmp_path: Path,
) -> None:
    artifact = build_artifact(
        scope_limit=2,
    )

    artifact_path = write_artifact(
        tmp_path,
        artifact,
    )

    with patch.object(
        extract,
        "get_settings",
    ) as get_settings:
        get_settings.return_value.postgres_schema = "ctgov"

        report = extract.reconcile_aact_artifact(
            artifact_path,
            expected_limit=100,
        )

    assert report["passed"] is False
    assert "Scope limit mismatch" in report["errors"][0]


def test_reconciliation_rejects_unique_nct_count_mismatch(
    tmp_path: Path,
) -> None:
    artifact = build_artifact(
        nct_ids=TEST_NCT_IDS,
        scope_limit=100,
    )

    artifact_path = write_artifact(
        tmp_path,
        artifact,
    )

    with patch.object(
        extract,
        "get_settings",
    ) as get_settings:
        get_settings.return_value.postgres_schema = "ctgov"

        report = extract.reconcile_aact_artifact(
            artifact_path,
        )

    assert report["passed"] is False
    assert (
        "Unique NCT ID count does not match "
        "the declared scope limit"
    ) in report["errors"][0]


def test_reconciliation_detects_postgres_scope_mismatch(
    tmp_path: Path,
) -> None:
    artifact = build_artifact()

    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=artifact,
        source_scope={"NCT00000001", "NCT00000003"},
        source_counts=expected_source_counts(),
    )

    assert report["passed"] is False
    assert (
        "Artifact trial scope does not match PostgreSQL"
        in report["errors"]
    )


def test_reconciliation_detects_missing_extracted_rows(
    tmp_path: Path,
) -> None:
    rows_by_table = {
        table: [
            {"nct_id": nct_id}
            for nct_id in TEST_NCT_IDS
        ]
        for table in TABLES
    }

    rows_by_table["conditions"] = [
        {"nct_id": TEST_NCT_IDS[0]},
    ]

    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=build_artifact(
            rows_by_table=rows_by_table,
        ),
        source_scope=set(TEST_NCT_IDS),
        source_counts=expected_source_counts(),
    )

    assert report["passed"] is False
    assert report["tables"]["conditions"]["passed"] is False
    assert report["tables"]["conditions"]["source_count"] == 2
    assert report["tables"]["conditions"]["extracted_count"] == 1
    assert "Reconciliation failed for table: conditions" in (
        report["errors"]
    )


def test_reconciliation_detects_extra_extracted_rows(
    tmp_path: Path,
) -> None:
    rows_by_table = {
        table: [
            {"nct_id": nct_id}
            for nct_id in TEST_NCT_IDS
        ]
        for table in TABLES
    }

    rows_by_table["interventions"].append(
        {"nct_id": TEST_NCT_IDS[0]},
    )

    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=build_artifact(
            rows_by_table=rows_by_table,
        ),
        source_scope=set(TEST_NCT_IDS),
        source_counts=expected_source_counts(),
    )

    assert report["passed"] is False
    assert report["tables"]["interventions"]["passed"] is False
    assert report["tables"]["interventions"]["source_count"] == 2
    assert report["tables"]["interventions"]["extracted_count"] == 3


def test_reconciliation_detects_unexpected_nct_id(
    tmp_path: Path,
) -> None:
    rows_by_table = {
        table: [
            {"nct_id": nct_id}
            for nct_id in TEST_NCT_IDS
        ]
        for table in TABLES
    }

    rows_by_table["sponsors"].append(
        {"nct_id": "NCT99999999"},
    )

    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=build_artifact(
            rows_by_table=rows_by_table,
        ),
        source_scope=set(TEST_NCT_IDS),
        source_counts={
            **expected_source_counts(),
            "sponsors": 3,
        },
    )

    sponsors_report = report["tables"]["sponsors"]

    assert report["passed"] is False
    assert sponsors_report["passed"] is False
    assert sponsors_report["unexpected_nct_ids"] == [
        "NCT99999999",
    ]


def test_reconciliation_detects_missing_table_rows(
    tmp_path: Path,
) -> None:
    rows_by_table = {
        table: [
            {"nct_id": nct_id}
            for nct_id in TEST_NCT_IDS
        ]
        for table in TABLES
    }

    del rows_by_table["eligibilities"]

    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=build_artifact(
            rows_by_table=rows_by_table,
        ),
        source_scope=set(TEST_NCT_IDS),
        source_counts=expected_source_counts(),
    )

    assert report["passed"] is False
    assert report["tables"]["eligibilities"]["source_count"] == 2
    assert report["tables"]["eligibilities"]["extracted_count"] == 0
    assert report["tables"]["eligibilities"]["passed"] is False


def test_reconciliation_rejects_non_ctgov_schema(
    tmp_path: Path,
) -> None:
    artifact_path = write_artifact(
        tmp_path,
        build_artifact(),
    )

    with patch.object(
        extract,
        "get_settings",
    ) as get_settings:
        get_settings.return_value.postgres_schema = "public"

        with pytest.raises(
            ValueError,
            match="M1 reconciliation is restricted to the ctgov schema",
        ):
            extract.reconcile_aact_artifact(
                artifact_path,
            )


@pytest.mark.parametrize(
    "metadata_change",
    [
        {"nct_ids": []},
        {"nct_ids": ["NCT00000001"]},
        {"nct_ids": ["NCT00000001", "NCT00000001"]},
    ],
)
def test_reconciliation_rejects_invalid_scope_metadata(
    tmp_path: Path,
    metadata_change: dict,
) -> None:
    artifact = build_artifact()

    artifact["metadata"].update(metadata_change)

    artifact_path = write_artifact(
        tmp_path,
        artifact,
    )

    with patch.object(
        extract,
        "get_settings",
    ) as get_settings:
        get_settings.return_value.postgres_schema = "ctgov"

        report = extract.reconcile_aact_artifact(
            artifact_path,
        )

    assert report["passed"] is False
    assert report["errors"]


def test_reconciliation_returns_expected_result_structure(
    tmp_path: Path,
) -> None:
    report = run_reconciliation(
        tmp_path=tmp_path,
        artifact=build_artifact(),
        source_scope=set(TEST_NCT_IDS),
        source_counts=expected_source_counts(),
    )

    assert set(report) == {
        "passed",
        "scope",
        "tables",
        "errors",
    }

    assert set(report["scope"]) == {
        "expected_trial_count",
        "declared_limit",
    }

    assert set(report["tables"]) == set(TABLES)

    for table in TABLES:
        assert set(report["tables"][table]) == {
            "source_count",
            "extracted_count",
            "unexpected_nct_ids",
            "passed",
        }