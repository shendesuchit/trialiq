// Safe cleanup for the NCT03416088 canonical demo slice.
// Only relationships whose START node is one of the canonical demo entities are deleted.
// Trial nodes and original non-canonical TrialIQ relationships are preserved.

MATCH (entity)-[r]->(trial:Trial)
WHERE entity.canonical = true
  AND entity.trialiq_demo_slice = "NCT03416088"
  AND r.trialiq_demo_slice = "NCT03416088"
DELETE r;

MATCH (entity)
WHERE entity.canonical = true
  AND entity.trialiq_demo_slice = "NCT03416088"
  AND NOT (entity)--()
DELETE entity;

RETURN "NCT03416088 canonical demo slice removed" AS status;
