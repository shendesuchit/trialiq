// TrialIQ GraphRAG demo slice — repository-owned safe loader.
// Seed: NCT03416088
// Four Trial nodes, three canonical shared entity nodes, six canonical relationships.
// No existing nodes or relationships are deleted.
//
// Trial scalar attributes are intentionally NOT hard-coded here. After loading this topology,
// run scripts/enrich_graphrag_demo_slice.py --apply so title/status/dates/enrollment come from
// canonical AACT ctgov.studies rows.

// -----------------------------------------------------------------------------
// Shared CONDITION: Retinal Microcirculation Disorder
// NCT03416088 <-> NCT04214743
// -----------------------------------------------------------------------------
MERGE (seed:Trial {nct_id: "NCT03416088"})
MERGE (related:Trial {nct_id: "NCT04214743"})
MERGE (entity:Condition {canonical_key: "retinal microcirculation disorder"})
SET entity.name = "Retinal Microcirculation Disorder",
    entity.normalized_name = "retinal microcirculation disorder",
    entity.canonical = true,
    entity.trialiq_demo_slice = "NCT03416088"
MERGE (entity)-[seed_rel:HAS_CONDITION]->(seed)
SET seed_rel.source_database = "aact_full",
    seed_rel.source_schema = "ctgov",
    seed_rel.source_table = "conditions",
    seed_rel.source_id = 416354331,
    seed_rel.source_key = "conditions:NCT03416088:416354331",
    seed_rel.source_nct_id = "NCT03416088",
    seed_rel.trialiq_demo_slice = "NCT03416088"
MERGE (entity)-[related_rel:HAS_CONDITION]->(related)
SET related_rel.source_database = "aact_full",
    related_rel.source_schema = "ctgov",
    related_rel.source_table = "conditions",
    related_rel.source_id = 415887852,
    related_rel.source_key = "conditions:NCT04214743:415887852",
    related_rel.source_nct_id = "NCT04214743",
    related_rel.trialiq_demo_slice = "NCT03416088";

// -----------------------------------------------------------------------------
// Shared INTERVENTION: Beverage consumption
// NCT03416088 <-> NCT04731987
// -----------------------------------------------------------------------------
MERGE (seed:Trial {nct_id: "NCT03416088"})
MERGE (related:Trial {nct_id: "NCT04731987"})
MERGE (entity:Intervention {canonical_key: "beverage consumption|behavioral"})
SET entity.name = "Beverage consumption",
    entity.normalized_name = "beverage consumption",
    entity.intervention_type = "BEHAVIORAL",
    entity.canonical = true,
    entity.trialiq_demo_slice = "NCT03416088"
MERGE (entity)-[seed_rel:HAS_INTERVENTION]->(seed)
SET seed_rel.source_database = "aact_full",
    seed_rel.source_schema = "ctgov",
    seed_rel.source_table = "interventions",
    seed_rel.source_id = 398765905,
    seed_rel.source_key = "interventions:NCT03416088:398765905",
    seed_rel.source_nct_id = "NCT03416088",
    seed_rel.trialiq_demo_slice = "NCT03416088"
MERGE (entity)-[related_rel:HAS_INTERVENTION]->(related)
SET related_rel.source_database = "aact_full",
    related_rel.source_schema = "ctgov",
    related_rel.source_table = "interventions",
    related_rel.source_id = 398647881,
    related_rel.source_key = "interventions:NCT04731987:398647881",
    related_rel.source_nct_id = "NCT04731987",
    related_rel.trialiq_demo_slice = "NCT03416088";

// -----------------------------------------------------------------------------
// Shared SPONSOR: Jiannan Huang
// NCT03416088 <-> NCT07764198
// -----------------------------------------------------------------------------
MERGE (seed:Trial {nct_id: "NCT03416088"})
MERGE (related:Trial {nct_id: "NCT07764198"})
MERGE (entity:Sponsor {canonical_key: "jiannan huang"})
SET entity.name = "Jiannan Huang",
    entity.normalized_name = "jiannan huang",
    entity.canonical = true,
    entity.trialiq_demo_slice = "NCT03416088"
MERGE (entity)-[seed_rel:SPONSORED_BY]->(seed)
SET seed_rel.source_database = "aact_full",
    seed_rel.source_schema = "ctgov",
    seed_rel.source_table = "sponsors",
    seed_rel.source_id = 387728835,
    seed_rel.source_key = "sponsors:NCT03416088:387728835",
    seed_rel.source_nct_id = "NCT03416088",
    seed_rel.trialiq_demo_slice = "NCT03416088"
MERGE (entity)-[related_rel:SPONSORED_BY]->(related)
SET related_rel.source_database = "aact_full",
    related_rel.source_schema = "ctgov",
    related_rel.source_table = "sponsors",
    related_rel.source_id = 387741929,
    related_rel.source_key = "sponsors:NCT07764198:387741929",
    related_rel.source_nct_id = "NCT07764198",
    related_rel.trialiq_demo_slice = "NCT03416088";

// Exact topology verification: this must return six rows.
MATCH (entity)-[r]->(trial:Trial)
WHERE entity.canonical = true
  AND entity.trialiq_demo_slice = "NCT03416088"
  AND r.trialiq_demo_slice = "NCT03416088"
RETURN
  labels(entity)[0] AS entity_type,
  entity.name AS entity,
  type(r) AS relationship,
  trial.nct_id AS nct_id,
  r.source_table AS source_table,
  r.source_id AS source_id
ORDER BY entity_type, entity, nct_id;
