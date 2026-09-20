
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