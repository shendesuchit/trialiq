
 // ============================================
 // TrialIQ - Phase 1 Schema Foundation
 // ============================================

 // Change Start

 // --------------------------------------------
 // 1. Trial identity constraint
 // --------------------------------------------

 CREATE CONSTRAINT trial_nct_id_unique IF NOT EXISTS
 FOR (t:Trial)
 REQUIRE t.nct_id IS UNIQUE;

 // --------------------------------------------
 // 2. Trial indexes
 // --------------------------------------------

 CREATE INDEX trial_status_index IF NOT EXISTS
 FOR (t:Trial)
 ON (t.overall_status);

 CREATE INDEX trial_phase_index IF NOT EXISTS
 FOR (t:Trial)
 ON (t.phase);

 CREATE INDEX trial_study_type_index IF NOT EXISTS
 FOR (t:Trial)
 ON (t.study_type);

 // --------------------------------------------
 // 3. Entity lookup indexes
 // --------------------------------------------

 CREATE INDEX condition_name_index IF NOT EXISTS
 FOR (c:Condition)
 ON (c.name);

 CREATE INDEX intervention_name_index IF NOT EXISTS
 FOR (i:Intervention)
 ON (i.name);

 CREATE INDEX sponsor_name_index IF NOT EXISTS
 FOR (s:Sponsor)
 ON (s.name);

 CREATE INDEX facility_country_index IF NOT EXISTS
 FOR (f:Facility)
 ON (f.country);

 // Investigator is intentionally deferred.
 // It is not part of the approved Phase 1 model.

 // Change End

// ============================================
// Batch 13 - Canonical GraphRAG core identity
// ============================================

// Shared Condition/Intervention/Sponsor nodes are source-backed canonical
// entities. Legacy trial-scoped nodes do not carry canonical_key and therefore
// do not conflict with these uniqueness constraints during scoped migration.

CREATE CONSTRAINT condition_canonical_key_unique IF NOT EXISTS
FOR (c:Condition)
REQUIRE c.canonical_key IS UNIQUE;

CREATE CONSTRAINT intervention_canonical_key_unique IF NOT EXISTS
FOR (i:Intervention)
REQUIRE i.canonical_key IS UNIQUE;

CREATE CONSTRAINT sponsor_canonical_key_unique IF NOT EXISTS
FOR (s:Sponsor)
REQUIRE s.canonical_key IS UNIQUE;

CREATE INDEX condition_normalized_name_index IF NOT EXISTS
FOR (c:Condition)
ON (c.normalized_name);

CREATE INDEX intervention_normalized_name_index IF NOT EXISTS
FOR (i:Intervention)
ON (i.normalized_name);

CREATE INDEX sponsor_normalized_name_index IF NOT EXISTS
FOR (s:Sponsor)
ON (s.normalized_name);

CREATE INDEX trial_canonical_load_run_index IF NOT EXISTS
FOR (t:Trial)
ON (t.canonical_load_run_id);


// ============================================
// Batch 14 - Full-graph retrieval support
// ============================================

CREATE INDEX condition_loaded_trial_count_index IF NOT EXISTS
FOR (c:Condition)
ON (c.loaded_trial_count);

CREATE INDEX intervention_loaded_trial_count_index IF NOT EXISTS
FOR (i:Intervention)
ON (i.loaded_trial_count);

CREATE INDEX sponsor_loaded_trial_count_index IF NOT EXISTS
FOR (s:Sponsor)
ON (s.loaded_trial_count);

CREATE TEXT INDEX trial_nct_id_search_text_index IF NOT EXISTS
FOR (t:Trial)
ON (t.nct_id_search);

CREATE TEXT INDEX trial_brief_title_search_text_index IF NOT EXISTS
FOR (t:Trial)
ON (t.brief_title_search);

CREATE TEXT INDEX trial_official_title_search_text_index IF NOT EXISTS
FOR (t:Trial)
ON (t.official_title_search);
