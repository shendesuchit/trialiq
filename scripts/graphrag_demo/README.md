# NCT03416088 GraphRAG demo slice

This directory keeps the bounded canonical shared-entity demo topology in the repository.

`load_graphrag_demo_slice_NCT03416088.cypher` creates only the four allowlisted Trial nodes,
three canonical shared entities, and six source-provenanced relationships. It deliberately does
not hard-code Trial dates, enrollment, title, or status. After loading the topology, run:

```powershell
.venv\Scripts\python.exe scripts\enrich_graphrag_demo_slice.py --apply
.venv\Scripts\python.exe scripts\enrich_graphrag_demo_slice.py --assert-synchronized
```

The enrichment command reads `brief_title`, `overall_status`, `start_date`, `completion_date`,
and `enrollment` from `ctgov.studies`, updates only the existing four demo Trial nodes, and then
checks the resulting graph values against the same source rows.

`cleanup_graphrag_demo_slice_NCT03416088.cypher` removes only canonical demo relationships and
orphaned canonical demo entities. Trial nodes and the original non-canonical ETL graph are kept.
