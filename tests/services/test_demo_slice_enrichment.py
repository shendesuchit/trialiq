from datetime import date

import pytest

from trialiq.services.demo_slice_enrichment import (
    DEMO_SLICE_NCT_IDS,
    TRIAL_SOURCE_FIELDS,
    enrich_demo_slice_trial_data,
    inspect_demo_slice_trial_data,
)


def _source_rows():
    return [
        {
            "nct_id": nct_id,
            "brief_title": f"Title {index}",
            "overall_status": "COMPLETED" if index < 3 else "RECRUITING",
            "start_date": date(2020, 1, index + 1),
            "completion_date": date(2020, 6, index + 1),
            "enrollment": 100 + index,
        }
        for index, nct_id in enumerate(DEMO_SLICE_NCT_IDS)
    ]


class Reader:
    def __init__(self, rows=None):
        self.rows = _source_rows() if rows is None else rows
        self.calls = 0

    def get_trials(self, nct_ids):
        self.calls += 1
        assert nct_ids == DEMO_SLICE_NCT_IDS
        return self.rows


class Store:
    def __init__(self, rows=None):
        self.rows = rows or {
            row["nct_id"]: [{"nct_id": row["nct_id"]}]
            for row in _source_rows()
        }
        self.applied = []

    def read_trials(self, nct_ids):
        assert nct_ids == DEMO_SLICE_NCT_IDS
        return self.rows

    def apply_trials(self, rows):
        self.applied = rows
        self.rows = {row["nct_id"]: [dict(row)] for row in rows}
        return rows


def test_inspection_normalizes_source_dates_and_reports_missing_graph_values():
    report = inspect_demo_slice_trial_data(source_reader=Reader(), graph_store=Store())

    assert report["ready_to_apply"] is True
    assert report["synchronized"] is False
    assert report["source_fields"] == list(TRIAL_SOURCE_FIELDS)
    first = report["trials"][0]
    assert first["source"]["start_date"] == "2020-01-01"
    assert first["source"]["completion_date"] == "2020-06-01"
    assert first["source"]["enrollment"] == 100
    assert first["status"] == "NEEDS_ENRICHMENT"


def test_enrichment_updates_only_the_allowlisted_demo_trials_and_verifies_result():
    reader = Reader()
    store = Store()

    result = enrich_demo_slice_trial_data(source_reader=reader, graph_store=store)

    assert result["updated_trial_count"] == 4
    assert result["before"]["synchronized"] is False
    assert result["after"]["synchronized"] is True
    assert [row["nct_id"] for row in store.applied] == list(DEMO_SLICE_NCT_IDS)
    assert set(store.applied[0]) == {"nct_id", *TRIAL_SOURCE_FIELDS}
    assert reader.calls == 1


def test_enrichment_rejects_missing_source_rows_before_writing():
    reader = Reader(rows=_source_rows()[:-1])
    store = Store()

    with pytest.raises(ValueError, match="source rows are missing"):
        enrich_demo_slice_trial_data(source_reader=reader, graph_store=store)

    assert store.applied == []


def test_enrichment_rejects_duplicate_source_rows_before_writing():
    rows = _source_rows()
    reader = Reader(rows=[*rows, dict(rows[0])])
    store = Store()

    with pytest.raises(ValueError, match="Duplicate source row"):
        enrich_demo_slice_trial_data(source_reader=reader, graph_store=store)

    assert store.applied == []


def test_enrichment_rejects_missing_or_duplicate_graph_nodes_before_writing():
    rows = {
        row["nct_id"]: [{"nct_id": row["nct_id"]}]
        for row in _source_rows()
    }
    rows[DEMO_SLICE_NCT_IDS[1]] = []
    rows[DEMO_SLICE_NCT_IDS[2]] = [
        {"nct_id": DEMO_SLICE_NCT_IDS[2]},
        {"nct_id": DEMO_SLICE_NCT_IDS[2]},
    ]
    store = Store(rows=rows)

    report = inspect_demo_slice_trial_data(source_reader=Reader(), graph_store=store)
    assert report["ready_to_apply"] is False
    assert report["trials"][1]["status"] == "MISSING_GRAPH_NODE"
    assert report["trials"][2]["status"] == "DUPLICATE_GRAPH_NODES"

    with pytest.raises(ValueError, match="cardinality check failed"):
        enrich_demo_slice_trial_data(source_reader=Reader(), graph_store=store)

    assert store.applied == []


def test_invalid_enrollment_is_rejected_instead_of_guessed():
    rows = _source_rows()
    rows[0]["enrollment"] = "not-a-number"

    with pytest.raises(ValueError, match="Invalid enrollment value"):
        inspect_demo_slice_trial_data(source_reader=Reader(rows), graph_store=Store())


def test_neo4j_store_checks_cardinality_before_fixed_field_update():
    from unittest.mock import MagicMock, Mock, patch

    from trialiq.services.demo_slice_enrichment import Neo4jDemoTrialGraphStore

    connection = Mock()
    transaction = Mock()
    connection.transaction.return_value = MagicMock()
    connection.transaction.return_value.__enter__.return_value = transaction
    cardinality_result = Mock()
    cardinality_result.data.return_value = [
        {"nct_id": nct_id, "node_count": 1} for nct_id in DEMO_SLICE_NCT_IDS
    ]
    update_result = Mock()
    update_result.data.return_value = [
        {"nct_id": nct_id} for nct_id in DEMO_SLICE_NCT_IDS
    ]
    transaction.run.side_effect = [cardinality_result, update_result]
    rows = [
        {
            "nct_id": nct_id,
            "brief_title": "Title",
            "overall_status": "COMPLETED",
            "start_date": "2020-01-01",
            "completion_date": "2020-06-01",
            "enrollment": 100,
        }
        for nct_id in DEMO_SLICE_NCT_IDS
    ]

    with patch(
        "trialiq.services.demo_slice_enrichment.Neo4jConnection",
        return_value=connection,
    ):
        result = Neo4jDemoTrialGraphStore().apply_trials(rows)

    assert len(result) == 4
    assert transaction.run.call_count == 2
    update_query, update_parameters = transaction.run.call_args_list[1].args
    assert "trial.start_date = row.start_date" in update_query
    assert "trial.completion_date = row.completion_date" in update_query
    assert "trial.enrollment = row.enrollment" in update_query
    assert update_parameters == {"rows": rows}
    connection.close.assert_called_once()


def test_neo4j_store_refuses_ambiguous_nodes_inside_write_transaction():
    from unittest.mock import MagicMock, Mock, patch

    from trialiq.services.demo_slice_enrichment import Neo4jDemoTrialGraphStore

    connection = Mock()
    transaction = Mock()
    connection.transaction.return_value = MagicMock()
    connection.transaction.return_value.__enter__.return_value = transaction
    cardinality_result = Mock()
    cardinality_result.data.return_value = [
        {"nct_id": nct_id, "node_count": 2 if index == 1 else 1}
        for index, nct_id in enumerate(DEMO_SLICE_NCT_IDS)
    ]
    transaction.run.return_value = cardinality_result
    rows = [
        {
            "nct_id": nct_id,
            "brief_title": "Title",
            "overall_status": "COMPLETED",
            "start_date": "2020-01-01",
            "completion_date": "2020-06-01",
            "enrollment": 100,
        }
        for nct_id in DEMO_SLICE_NCT_IDS
    ]

    with patch(
        "trialiq.services.demo_slice_enrichment.Neo4jConnection",
        return_value=connection,
    ):
        with pytest.raises(ValueError, match="exactly one Trial node"):
            Neo4jDemoTrialGraphStore().apply_trials(rows)

    assert transaction.run.call_count == 1
    connection.close.assert_called_once()
