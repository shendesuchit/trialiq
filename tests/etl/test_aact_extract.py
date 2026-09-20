
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from trialiq.etl.aact_extract import (
    EXTRACT_TABLES,
    _build_postgres_connection_string,
    _entity_query,
    _scope_query,
    extract_aact_dataset,
)


def test_scope_query_is_deterministic():
    query = _scope_query("ctgov")

    assert "SELECT nct_id" in query
    assert "FROM ctgov.studies" in query
    assert "ORDER BY nct_id" in query
    assert "LIMIT %s" in query


@pytest.mark.parametrize("table", EXTRACT_TABLES)
def test_entity_query_uses_approved_table(table):
    query = _entity_query("ctgov", table)

    assert f"FROM ctgov.{table}" in query
    assert "WHERE nct_id = ANY(%s)" in query

    if table == "studies":
        assert "ORDER BY nct_id" in query
    else:
        assert "ORDER BY nct_id, id" in query


def test_connection_string_uses_settings():
    settings = MagicMock(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_database="aact",
        postgres_username="postgres",
        postgres_password="secret",
    )

    with patch(
        "trialiq.etl.aact_extract.get_settings",
        return_value=settings,
    ):
        connection_string = _build_postgres_connection_string()

    assert "host=localhost" in connection_string
    assert "port=5432" in connection_string
    assert "dbname=aact" in connection_string
    assert "user=postgres" in connection_string
    assert "password=secret" in connection_string


@pytest.mark.parametrize("invalid_limit", [0, -1, -100])
def test_extraction_rejects_non_positive_limit(invalid_limit, tmp_path):
    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        extract_aact_dataset(
            limit=invalid_limit,
            output_path=tmp_path / "output.json",
        )


def test_extraction_rejects_non_ctgov_schema(tmp_path):
    settings = MagicMock(postgres_schema="other_schema")

    with patch(
        "trialiq.etl.aact_extract.get_settings",
        return_value=settings,
    ):
        with pytest.raises(
            ValueError,
            match="restricted to the ctgov schema",
        ):
            extract_aact_dataset(
                limit=1,
                output_path=tmp_path / "output.json",
            )


def test_extraction_rejects_scope_count_mismatch(tmp_path):
    settings = MagicMock(
        postgres_schema="ctgov",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_database="aact",
        postgres_username="postgres",
        postgres_password="secret",
    )

    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"nct_id": "NCT00000001"},
    ]

    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    connect_context = MagicMock()
    connect_context.__enter__.return_value = connection

    with (
        patch(
            "trialiq.etl.aact_extract.get_settings",
            return_value=settings,
        ),
        patch(
            "trialiq.etl.aact_extract.psycopg.connect",
            return_value=connect_context,
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="Expected 2 trials, but selected 1",
        ):
            extract_aact_dataset(
                limit=2,
                output_path=tmp_path / "output.json",
            )


def test_extraction_writes_expected_artifact(tmp_path):
    settings = MagicMock(
        postgres_schema="ctgov",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_database="aact",
        postgres_username="postgres",
        postgres_password="secret",
    )

    scope_rows = [
        {"nct_id": "NCT00000001"},
        {"nct_id": "NCT00000002"},
    ]

    cursor = MagicMock()
    cursor.fetchall.side_effect = [
        scope_rows,
        [{"nct_id": "NCT00000001"}],
        [],
        [],
        [],
        [],
        [],
        [],
    ]

    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    connect_context = MagicMock()
    connect_context.__enter__.return_value = connection

    output_path = tmp_path / "extracted.json"

    with (
        patch(
            "trialiq.etl.aact_extract.get_settings",
            return_value=settings,
        ),
        patch(
            "trialiq.etl.aact_extract.psycopg.connect",
            return_value=connect_context,
        ),
    ):
        result = extract_aact_dataset(
            limit=2,
            output_path=output_path,
        )

    assert result == Path(output_path)
    assert output_path.is_file()

    import json

    with output_path.open("r", encoding="utf-8") as file:
        artifact = json.load(file)

    assert artifact["metadata"]["source_schema"] == "ctgov"
    assert artifact["metadata"]["scope_limit"] == 2
    assert artifact["metadata"]["nct_ids"] == [
        "NCT00000001",
        "NCT00000002",
    ]
    assert artifact["metadata"]["tables"] == list(EXTRACT_TABLES)
    assert set(artifact["tables"]) == set(EXTRACT_TABLES)