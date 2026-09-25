from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import pytest

from trialiq.etl.canonical_graphrag import (
    CANONICAL_LOADER_VERSION,
    CANONICAL_SCHEMA_STATEMENTS,
    _clean_list,
    _deduplicate_entity_nodes,
    _prepare_trial_row,
    _upsert_entity_batch,
    apply_canonical_schema,
    canonical_entity_key,
    normalize_name,
)


def test_normalize_name_matches_profile_contract():
    assert normalize_name("  Breast Cancer  ") == "breast cancer"


def test_normalize_name_rejects_blank():
    with pytest.raises(ValueError, match="cannot be blank"):
        normalize_name("   ")


def test_condition_and_sponsor_keys_use_normalized_name():
    assert canonical_entity_key("conditions", " Breast Cancer ") == "breast cancer"
    assert canonical_entity_key("sponsors", " Pfizer ") == "pfizer"


def test_intervention_key_keeps_intervention_type_in_identity():
    assert (
        canonical_entity_key(
            "interventions",
            " Placebo ",
            intervention_type="DRUG",
        )
        == "placebo|drug"
    )
    assert (
        canonical_entity_key(
            "interventions",
            " Placebo ",
            intervention_type="OTHER",
        )
        == "placebo|other"
    )


def test_unknown_entity_table_is_rejected():
    with pytest.raises(ValueError, match="Unsupported canonical entity table"):
        canonical_entity_key("facilities", "Example")


def test_clean_list_removes_nulls_and_serializes_dates():
    assert _clean_list([1, None, date(2026, 9, 25)]) == [1, "2026-09-25"]


def test_prepare_trial_row_preserves_runtime_fields_and_provenance():
    settings = Mock(postgres_database="aact_full", postgres_schema="ctgov")
    with patch(
        "trialiq.etl.canonical_graphrag.get_settings",
        return_value=settings,
    ):
        row = _prepare_trial_row(
            {
                "nct_id": "NCT00000001",
                "brief_title": "Example",
                "overall_status": "COMPLETED",
                "start_date": date(2020, 1, 2),
                "enrollment": 10,
            },
            run_id="run-1",
        )

    assert row["nct_id"] == "NCT00000001"
    properties = row["properties"]
    assert properties["source_key"] == "trial:NCT00000001"
    assert properties["start_date"] == "2020-01-02"
    assert properties["canonical_loader_version"] == CANONICAL_LOADER_VERSION
    assert properties["canonical_load_run_id"] == "run-1"


def test_deduplicate_entity_nodes_uses_one_key_and_stable_display_name():
    rows = [
        {
            "canonical_key": "breast cancer",
            "entity_properties": {
                "canonical_key": "breast cancer",
                "normalized_name": "breast cancer",
                "name": "Breast cancer",
            },
        },
        {
            "canonical_key": "breast cancer",
            "entity_properties": {
                "canonical_key": "breast cancer",
                "normalized_name": "breast cancer",
                "name": "Breast Cancer",
            },
        },
    ]

    nodes = _deduplicate_entity_nodes(rows)

    assert len(nodes) == 1
    assert nodes[0]["canonical_key"] == "breast cancer"
    assert nodes[0]["properties"]["name"] == "Breast Cancer"


def test_schema_contains_all_three_canonical_uniqueness_constraints():
    joined = "\n".join(CANONICAL_SCHEMA_STATEMENTS)
    assert "condition_canonical_key_unique" in joined
    assert "intervention_canonical_key_unique" in joined
    assert "sponsor_canonical_key_unique" in joined
    assert "REQUIRE c.canonical_key IS UNIQUE" in joined
    assert "REQUIRE i.canonical_key IS UNIQUE" in joined
    assert "REQUIRE s.canonical_key IS UNIQUE" in joined


def test_apply_canonical_schema_uses_only_fixed_statements():
    connection = Mock()

    apply_canonical_schema(connection)

    assert connection.execute_write.call_count == len(CANONICAL_SCHEMA_STATEMENTS)
    for call, statement in zip(
        connection.execute_write.call_args_list,
        CANONICAL_SCHEMA_STATEMENTS,
        strict=True,
    ):
        assert call.args == (statement.strip(),)


def test_upsert_entity_batch_uses_canonical_key_and_deduplicated_edge():
    connection = Mock()
    connection.execute_write.side_effect = [
        [{"loaded": 1}],
        [{"loaded": 1}],
    ]
    rows = [
        {
            "nct_id": "NCT00000001",
            "canonical_key": "breast cancer",
            "entity_properties": {
                "canonical": True,
                "canonical_key": "breast cancer",
                "normalized_name": "breast cancer",
                "name": "Breast Cancer",
            },
            "relationship_properties": {
                "source_table": "conditions",
                "source_id": 1,
                "source_ids": [1, 2],
                "source_row_count": 2,
            },
            "source_row_count": 2,
        }
    ]

    result = _upsert_entity_batch(
        connection,
        table="conditions",
        rows=rows,
    )

    assert result == {"nodes": 1, "relationships": 1, "source_rows": 2}
    assert connection.execute_write.call_count == 2
    node_query = connection.execute_write.call_args_list[0].args[0]
    relationship_query = connection.execute_write.call_args_list[1].args[0]
    assert "MERGE (entity:Condition {canonical_key: row.canonical_key})" in node_query
    assert "MERGE (entity)-[rel:HAS_CONDITION]->(trial)" in relationship_query
    assert "UNWIND $rows" in node_query
    assert "UNWIND $rows" in relationship_query


def test_fetch_entity_rows_builds_condition_compatibility_and_edge_provenance():
    from trialiq.etl.canonical_graphrag import _fetch_entity_rows

    cursor = Mock()
    cursor.fetchall.return_value = [
        {
            "nct_id": "NCT00000001",
            "canonical_key": "breast cancer",
            "normalized_name": "breast cancer",
            "display_name": "Breast Cancer",
            "source_id": 10,
            "source_ids": [10, 11],
            "source_row_count": 2,
            "source_names": ["Breast Cancer", "breast cancer"],
        }
    ]
    settings = Mock(postgres_database="aact_full", postgres_schema="ctgov")
    with patch(
        "trialiq.etl.canonical_graphrag.get_settings",
        return_value=settings,
    ):
        rows = _fetch_entity_rows(
            cursor,
            schema="ctgov",
            table="conditions",
            nct_ids=["NCT00000001"],
            run_id="run-1",
        )

    assert len(rows) == 1
    row = rows[0]
    assert row["entity_properties"]["canonical"] is True
    assert row["entity_properties"]["downcase_name"] == "breast cancer"
    assert row["relationship_properties"]["source_id"] == 10
    assert row["relationship_properties"]["source_ids"] == [10, 11]
    assert row["relationship_properties"]["source_row_count"] == 2
    assert row["relationship_properties"]["source_nct_id"] == "NCT00000001"


def test_fetch_entity_rows_preserves_sponsor_relationship_context():
    from trialiq.etl.canonical_graphrag import _fetch_entity_rows

    cursor = Mock()
    cursor.fetchall.return_value = [
        {
            "nct_id": "NCT00000002",
            "canonical_key": "example sponsor",
            "normalized_name": "example sponsor",
            "display_name": "Example Sponsor",
            "source_id": 20,
            "source_ids": [20],
            "source_row_count": 1,
            "source_names": ["Example Sponsor"],
            "agency_classes": ["INDUSTRY"],
            "sponsor_roles": ["LEAD"],
        }
    ]
    settings = Mock(postgres_database="aact_full", postgres_schema="ctgov")
    with patch(
        "trialiq.etl.canonical_graphrag.get_settings",
        return_value=settings,
    ):
        rows = _fetch_entity_rows(
            cursor,
            schema="ctgov",
            table="sponsors",
            nct_ids=["NCT00000002"],
            run_id="run-1",
        )

    rel = rows[0]["relationship_properties"]
    assert rel["agency_classes"] == ["INDUSTRY"]
    assert rel["sponsor_roles"] == ["LEAD"]


def test_reconciliation_uses_current_run_scope_and_passes_exact_counts():
    from trialiq.etl.canonical_graphrag import _reconcile_run

    connection = Mock()
    connection.execute_read.side_effect = [
        [{"trial_count": 2, "sourced_trials": 2}],
        [{
            "relationship_count": 3,
            "represented_source_rows": 3,
            "provenance_relationship_count": 3,
            "connected_entity_nodes": 2,
        }],
        [{
            "relationship_count": 4,
            "represented_source_rows": 5,
            "provenance_relationship_count": 4,
            "connected_entity_nodes": 3,
        }],
        [{
            "relationship_count": 2,
            "represented_source_rows": 2,
            "provenance_relationship_count": 2,
            "connected_entity_nodes": 1,
        }],
    ]
    expected = {
        "conditions": {"relationships": 3, "source_rows": 3},
        "interventions": {"relationships": 4, "source_rows": 5},
        "sponsors": {"relationships": 2, "source_rows": 2},
    }

    report = _reconcile_run(
        connection,
        run_id="run-1",
        expected_trials=2,
        expected_entities=expected,
    )

    assert report["passed"] is True
    assert report["errors"] == []
    entity_query = connection.execute_read.call_args_list[1].args[0]
    assert "canonical_load_run_id: $run_id" in entity_query
