from trialiq.provenance import enrich_transformed_artifact


def test_enrich_transformed_artifact_adds_node_and_relationship_provenance():
    artifact = {
        "metadata": {
            "source_database": "aact_full",
            "source_schema": "ctgov",
            "extracted_at_utc": "2026-01-01T00:00:00+00:00",
        },
        "nodes": [
            {
                "key": "trial:NCT00000102",
                "label": "Trial",
                "properties": {"nct_id": "NCT00000102"},
            },
            {
                "key": "conditions:NCT00000102:1",
                "label": "Condition",
                "properties": {
                    "nct_id": "NCT00000102",
                    "source_table": "conditions",
                    "source_id": 1,
                },
            },
        ],
        "relationships": [
            {
                "type": "HAS_CONDITION",
                "source": "conditions:NCT00000102:1",
                "target": "trial:NCT00000102",
                "properties": {
                    "nct_id": "NCT00000102",
                    "source_table": "conditions",
                    "source_id": 1,
                },
            }
        ],
    }
    result = enrich_transformed_artifact(artifact, run_id="run-1")
    assert result["metadata"]["pipeline_run_id"] == "run-1"
    assert result["nodes"][0]["properties"]["source_table"] == "studies"
    assert result["nodes"][1]["properties"]["pipeline_run_id"] == "run-1"
    assert result["relationships"][0]["properties"]["pipeline_run_id"] == "run-1"
