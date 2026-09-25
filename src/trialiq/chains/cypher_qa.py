
# Change Start
"""Deterministic Neo4j graph queries for TrialIQ."""

from typing import Any

from trialiq.graph.connection import Neo4jConnection


RELATIONSHIP_TYPES = (
    "HAS_CONDITION",
    "HAS_INTERVENTION",
    "SPONSORED_BY",
    "HAS_FACILITY",
    "HAS_DESIGN",
    "HAS_ELIGIBILITY",
)

CORE_RELATED_RELATIONSHIP_TYPES = (
    "HAS_CONDITION",
    "HAS_INTERVENTION",
    "SPONSORED_BY",
)
CATALOG_RELATED_TRIAL_COUNT_CAP = 200
RELATED_ENTITY_LIMIT_PER_TYPE = 5
RELATED_TARGET_LIMIT_PER_ENTITY = 50

_RELATED_ENTITY_TYPES = {
    "HAS_CONDITION": ("Condition", "HAS_CONDITION"),
    "HAS_INTERVENTION": ("Intervention", "HAS_INTERVENTION"),
    "SPONSORED_BY": ("Sponsor", "SPONSORED_BY"),
}


def _serialize_node(node: Any) -> dict | None:
    """Convert a Neo4j node into a serializable dictionary."""

    if node is None:
        return None

    return dict(node)


def _serialize_nodes(nodes: list[Any]) -> list[dict]:
    """Convert Neo4j nodes into serializable dictionaries."""

    return [
        serialized
        for node in nodes
        if (serialized := _serialize_node(node)) is not None
    ]


def list_trial_catalog(
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List loaded trials with bounded shared-graph-neighbor metadata.

    Batch 14 caps only the *catalog count probe*, not the graph evidence.  This
    prevents a high-fanout entity such as placebo or a major sponsor from
    forcing the study selector to enumerate tens of thousands of neighbors.
    Counts below the cap are exact; a capped count is explicitly flagged so the
    frontend can render ``200+`` without changing the Batch-12 layout.
    """
    normalized_search = search.strip().casefold()
    relationship_types = list(CORE_RELATED_RELATIONSHIP_TYPES)
    parameters = {
        "search": normalized_search,
        "limit": limit,
        "offset": offset,
        "relationship_types": relationship_types,
        "related_count_cap": CATALOG_RELATED_TRIAL_COUNT_CAP,
        "related_probe_limit": CATALOG_RELATED_TRIAL_COUNT_CAP + 1,
    }
    search_predicate = """
    $search = ""
    OR trial.nct_id_search CONTAINS $search
    OR trial.brief_title_search CONTAINS $search
    OR trial.official_title_search CONTAINS $search
    OR (trial.nct_id_search IS NULL
        AND toLower(coalesce(trial.nct_id, "")) CONTAINS $search)
    OR (trial.brief_title_search IS NULL
        AND toLower(coalesce(trial.brief_title, "")) CONTAINS $search)
    OR (trial.official_title_search IS NULL
        AND toLower(coalesce(trial.official_title, "")) CONTAINS $search)
    """

    count_query = f"""
    MATCH (trial:Trial)
    WHERE {search_predicate}
    RETURN count(trial) AS total_count
    """

    page_query = f"""
    MATCH (trial:Trial)
    WHERE {search_predicate}
    WITH trial
    ORDER BY trial.nct_id
    SKIP $offset
    LIMIT $limit

    CALL (trial) {{
        MATCH (entity)-[source_rel]->(trial)
        WHERE type(source_rel) IN $relationship_types
          AND entity.canonical = true
          AND entity.canonical_key IS NOT NULL
          AND coalesce(entity.loaded_trial_count, 0) > 1
        RETURN collect(DISTINCT type(source_rel)) AS relationship_types
    }}

    CALL (trial) {{
        MATCH (entity)-[source_rel]->(trial)
        WHERE type(source_rel) IN $relationship_types
          AND entity.canonical = true
          AND entity.canonical_key IS NOT NULL
          AND coalesce(entity.loaded_trial_count, 0) > 1
        MATCH (entity)-[target_rel]->(related:Trial)
        WHERE type(target_rel) = type(source_rel)
          AND related.nct_id <> trial.nct_id
        WITH DISTINCT related
        LIMIT $related_probe_limit
        RETURN count(related) AS related_probe_count
    }}

    RETURN
        trial.nct_id AS nct_id,
        trial.brief_title AS brief_title,
        trial.official_title AS official_title,
        trial.overall_status AS overall_status,
        CASE
            WHEN related_probe_count > $related_count_cap THEN $related_count_cap
            ELSE related_probe_count
        END AS related_trial_count,
        related_probe_count > $related_count_cap AS related_trial_count_capped,
        relationship_types
    ORDER BY related_trial_count DESC, nct_id
    """

    connection = Neo4jConnection()
    try:
        count_records = connection.execute_read(count_query, parameters)
        page_records = connection.execute_read(page_query, parameters)
    finally:
        connection.close()

    total_count = (
        int(count_records[0].get("total_count") or 0)
        if count_records
        else 0
    )
    trials = []
    for record in page_records:
        nct_id = record.get("nct_id")
        if not nct_id:
            continue
        relationship_types_value = sorted(
            {
                str(value)
                for value in (record.get("relationship_types") or [])
                if value
            }
        )
        related_trial_count = int(record.get("related_trial_count") or 0)
        trials.append(
            {
                "nct_id": str(nct_id),
                "brief_title": record.get("brief_title"),
                "official_title": record.get("official_title"),
                "overall_status": record.get("overall_status"),
                "related_trial_count": related_trial_count,
                "related_trial_count_capped": bool(
                    record.get("related_trial_count_capped")
                ),
                "relationship_types": relationship_types_value,
            }
        )

    return {
        "search": normalized_search,
        "limit": limit,
        "offset": offset,
        "total_count": total_count,
        "trials": trials,
    }


def get_trial_graph(nct_id: str) -> dict:
    """Retrieve a Trial and its connected entities.

    Relationships are currently stored in the following direction:

        Entity -[RELATIONSHIP]-> Trial
    """

    query = """
    MATCH (trial:Trial {nct_id: $nct_id})

    CALL (trial) {
        OPTIONAL MATCH (condition:Condition)-[rel:HAS_CONDITION]->(trial)
        RETURN collect(
            condition {
                .*,
                nct_id: coalesce(
                    rel.source_nct_id,
                    rel.nct_id,
                    condition.nct_id,
                    trial.nct_id
                ),
                source_nct_id: coalesce(
                    rel.source_nct_id,
                    rel.nct_id,
                    condition.source_nct_id,
                    condition.nct_id,
                    trial.nct_id
                ),
                source_id: coalesce(rel.source_id, condition.source_id),
                source_key: coalesce(rel.source_key, condition.source_key),
                source_table: coalesce(rel.source_table, condition.source_table),
                source_database: coalesce(
                    rel.source_database, condition.source_database
                ),
                source_schema: coalesce(rel.source_schema, condition.source_schema),
                provenance_version: coalesce(
                    rel.provenance_version, condition.provenance_version
                ),
                pipeline_run_id: coalesce(
                    rel.pipeline_run_id, condition.pipeline_run_id
                ),
                extracted_at_utc: coalesce(
                    rel.extracted_at_utc, condition.extracted_at_utc
                ),
                transformed_at_utc: coalesce(
                    rel.transformed_at_utc, condition.transformed_at_utc
                ),
                transformation_version: coalesce(
                    rel.transformation_version, condition.transformation_version
                )
            }
        ) AS conditions
    }

    CALL (trial) {
        OPTIONAL MATCH (intervention:Intervention)-[rel:HAS_INTERVENTION]->(trial)
        RETURN collect(
            intervention {
                .*,
                nct_id: coalesce(
                    rel.source_nct_id,
                    rel.nct_id,
                    intervention.nct_id,
                    trial.nct_id
                ),
                source_nct_id: coalesce(
                    rel.source_nct_id,
                    rel.nct_id,
                    intervention.source_nct_id,
                    intervention.nct_id,
                    trial.nct_id
                ),
                source_id: coalesce(rel.source_id, intervention.source_id),
                source_key: coalesce(rel.source_key, intervention.source_key),
                source_table: coalesce(rel.source_table, intervention.source_table),
                source_database: coalesce(
                    rel.source_database, intervention.source_database
                ),
                source_schema: coalesce(
                    rel.source_schema, intervention.source_schema
                ),
                provenance_version: coalesce(
                    rel.provenance_version, intervention.provenance_version
                ),
                pipeline_run_id: coalesce(
                    rel.pipeline_run_id, intervention.pipeline_run_id
                ),
                extracted_at_utc: coalesce(
                    rel.extracted_at_utc, intervention.extracted_at_utc
                ),
                transformed_at_utc: coalesce(
                    rel.transformed_at_utc, intervention.transformed_at_utc
                ),
                transformation_version: coalesce(
                    rel.transformation_version, intervention.transformation_version
                )
            }
        ) AS interventions
    }

    CALL (trial) {
        OPTIONAL MATCH (sponsor:Sponsor)-[rel:SPONSORED_BY]->(trial)
        RETURN collect(
            sponsor {
                .*,
                nct_id: coalesce(
                    rel.source_nct_id,
                    rel.nct_id,
                    sponsor.nct_id,
                    trial.nct_id
                ),
                source_nct_id: coalesce(
                    rel.source_nct_id,
                    rel.nct_id,
                    sponsor.source_nct_id,
                    sponsor.nct_id,
                    trial.nct_id
                ),
                source_id: coalesce(rel.source_id, sponsor.source_id),
                source_key: coalesce(rel.source_key, sponsor.source_key),
                source_table: coalesce(rel.source_table, sponsor.source_table),
                source_database: coalesce(
                    rel.source_database, sponsor.source_database
                ),
                source_schema: coalesce(rel.source_schema, sponsor.source_schema),
                provenance_version: coalesce(
                    rel.provenance_version, sponsor.provenance_version
                ),
                pipeline_run_id: coalesce(rel.pipeline_run_id, sponsor.pipeline_run_id),
                extracted_at_utc: coalesce(
                    rel.extracted_at_utc, sponsor.extracted_at_utc
                ),
                transformed_at_utc: coalesce(
                    rel.transformed_at_utc, sponsor.transformed_at_utc
                ),
                transformation_version: coalesce(
                    rel.transformation_version, sponsor.transformation_version
                )
            }
        ) AS sponsors
    }

    CALL (trial) {
        OPTIONAL MATCH (facility:Facility)-[:HAS_FACILITY]->(trial)
        RETURN collect(facility) AS facilities
    }

    CALL (trial) {
        OPTIONAL MATCH (design:Design)-[:HAS_DESIGN]->(trial)
        RETURN collect(design) AS designs
    }

    CALL (trial) {
        OPTIONAL MATCH (eligibility:Eligibility)-[:HAS_ELIGIBILITY]->(trial)
        RETURN collect(eligibility) AS eligibilities
    }

    RETURN
        trial,
        conditions,
        interventions,
        sponsors,
        facilities,
        designs,
        eligibilities
    """

    connection = Neo4jConnection()

    try:
        records = connection.execute_read(
            query,
            {"nct_id": nct_id},
        )
    finally:
        connection.close()

    if not records:
        return {
            "found": False,
            "nct_id": nct_id,
            "trial": None,
            "conditions": [],
            "interventions": [],
            "sponsors": [],
            "facilities": [],
            "designs": [],
            "eligibilities": [],
        }

    record = records[0]

    return {
        "found": True,
        "nct_id": nct_id,
        "trial": _serialize_node(record["trial"]),
        "conditions": _serialize_nodes(record["conditions"]),
        "interventions": _serialize_nodes(record["interventions"]),
        "sponsors": _serialize_nodes(record["sponsors"]),
        "facilities": _serialize_nodes(record["facilities"]),
        "designs": _serialize_nodes(record["designs"]),
        "eligibilities": _serialize_nodes(record["eligibilities"]),
    }


def count_trial_relationships(nct_id: str) -> dict:
    """Count all entity relationships connected to a Trial."""

    query = """
    MATCH (trial:Trial {nct_id: $nct_id})

    CALL (trial) {
        OPTIONAL MATCH (condition:Condition)-[:HAS_CONDITION]->(trial)
        RETURN count(condition) AS conditions
    }

    CALL (trial) {
        OPTIONAL MATCH (intervention:Intervention)-[:HAS_INTERVENTION]->(trial)
        RETURN count(intervention) AS interventions
    }

    CALL (trial) {
        OPTIONAL MATCH (sponsor:Sponsor)-[:SPONSORED_BY]->(trial)
        RETURN count(sponsor) AS sponsors
    }

    CALL (trial) {
        OPTIONAL MATCH (facility:Facility)-[:HAS_FACILITY]->(trial)
        RETURN count(facility) AS facilities
    }

    CALL (trial) {
        OPTIONAL MATCH (design:Design)-[:HAS_DESIGN]->(trial)
        RETURN count(design) AS designs
    }

    CALL (trial) {
        OPTIONAL MATCH (eligibility:Eligibility)-[:HAS_ELIGIBILITY]->(trial)
        RETURN count(eligibility) AS eligibilities
    }

    RETURN
        conditions,
        interventions,
        sponsors,
        facilities,
        designs,
        eligibilities
    """

    connection = Neo4jConnection()

    try:
        records = connection.execute_read(
            query,
            {"nct_id": nct_id},
        )
    finally:
        connection.close()

    if not records:
        return {
            "found": False,
            "nct_id": nct_id,
            "counts": {
                "conditions": 0,
                "interventions": 0,
                "sponsors": 0,
                "facilities": 0,
                "designs": 0,
                "eligibilities": 0,
            },
        }

    record = records[0]

    return {
        "found": True,
        "nct_id": nct_id,
        "counts": {
            "conditions": record["conditions"],
            "interventions": record["interventions"],
            "sponsors": record["sponsors"],
            "facilities": record["facilities"],
            "designs": record["designs"],
            "eligibilities": record["eligibilities"],
        },
    }


# Change End

def search_trials_by_condition(condition: str, limit: int = 20) -> dict:
    """Find trials through the canonical normalized condition identity."""
    normalized_condition = condition.strip().casefold()
    query = """
    MATCH (condition:Condition {normalized_name: $condition})-[:HAS_CONDITION]->(trial:Trial)
    WHERE condition.canonical = true
      AND condition.canonical_key IS NOT NULL
    WITH trial, collect(DISTINCT condition) AS matched_conditions
    RETURN trial, matched_conditions
    ORDER BY trial.nct_id
    LIMIT $limit
    """
    connection = Neo4jConnection()
    try:
        records = connection.execute_read(
            query,
            {"condition": normalized_condition, "limit": limit},
        )
    finally:
        connection.close()

    matches = []
    for record in records:
        trial = _serialize_node(record.get("trial"))
        conditions = _serialize_nodes(record.get("matched_conditions") or [])
        if trial and trial.get("nct_id"):
            matches.append(
                {
                    "nct_id": trial["nct_id"],
                    "trial": trial,
                    "matched_conditions": conditions,
                }
            )
    return {"condition": normalized_condition, "matches": matches}

_GRAPH_ENTITY_SEARCH = {
    "intervention": ("Intervention", "HAS_INTERVENTION"),
    "sponsor": ("Sponsor", "SPONSORED_BY"),
}

_SHARED_ENTITY_TYPES = {
    "condition": ("Condition", "HAS_CONDITION"),
    "intervention": ("Intervention", "HAS_INTERVENTION"),
    "sponsor": ("Sponsor", "SPONSORED_BY"),
}


def _search_trials_by_named_entity(
    entity_type: str,
    name: str,
    limit: int = 20,
) -> dict:
    """Run an allowlisted exact-name graph lookup for a supported entity type."""
    label, relationship = _GRAPH_ENTITY_SEARCH[entity_type]
    normalized_name = name.strip().casefold()
    query = f"""
    MATCH (entity:{label} {{normalized_name: $name}})-[:{relationship}]->(trial:Trial)
    WHERE entity.canonical = true
      AND entity.canonical_key IS NOT NULL
    WITH trial, collect(DISTINCT entity) AS matched_entities
    RETURN trial, matched_entities
    ORDER BY trial.nct_id
    LIMIT $limit
    """
    connection = Neo4jConnection()
    try:
        records = connection.execute_read(
            query,
            {"name": normalized_name, "limit": limit},
        )
    finally:
        connection.close()

    matches = []
    for record in records:
        trial = _serialize_node(record.get("trial"))
        entities = _serialize_nodes(record.get("matched_entities") or [])
        if trial and trial.get("nct_id"):
            matches.append(
                {
                    "nct_id": trial["nct_id"],
                    "trial": trial,
                    "matched_entities": entities,
                }
            )
    return {
        "entity_type": entity_type,
        "query": normalized_name,
        "matches": matches,
    }


def search_trials_by_intervention(intervention: str, limit: int = 20) -> dict:
    """Find trials by exact, case-insensitive intervention name."""
    return _search_trials_by_named_entity("intervention", intervention, limit)


def search_trials_by_sponsor(sponsor: str, limit: int = 20) -> dict:
    """Find trials by exact, case-insensitive sponsor name."""
    return _search_trials_by_named_entity("sponsor", sponsor, limit)


def find_shared_trial_entities(
    nct_id_a: str,
    nct_id_b: str,
    limit_per_type: int = 20,
) -> dict:
    """Compare two trials using bounded, allowlisted shared named entities."""
    connection = Neo4jConnection()
    try:
        presence_query = """
        OPTIONAL MATCH (trial_a:Trial {nct_id: $nct_id_a})
        OPTIONAL MATCH (trial_b:Trial {nct_id: $nct_id_b})
        RETURN trial_a.nct_id AS nct_id_a, trial_b.nct_id AS nct_id_b
        """
        presence = connection.execute_read(
            presence_query,
            {"nct_id_a": nct_id_a, "nct_id_b": nct_id_b},
        )
        row = presence[0] if presence else {}
        found_a = row.get("nct_id_a") == nct_id_a
        found_b = row.get("nct_id_b") == nct_id_b
        if not (found_a and found_b):
            return {
                "found_a": found_a,
                "found_b": found_b,
                "nct_id_a": nct_id_a,
                "nct_id_b": nct_id_b,
                "shared_entities": [],
            }

        shared_entities = []
        for entity_type, (label, relationship) in _SHARED_ENTITY_TYPES.items():
            query = f"""
            MATCH (entity_a:{label})-[:{relationship}]->(trial_a:Trial {{nct_id: $nct_id_a}})
            MATCH (entity_b:{label})-[:{relationship}]->(trial_b:Trial {{nct_id: $nct_id_b}})
            WHERE entity_a.canonical = true
              AND entity_b.canonical = true
              AND entity_a.canonical_key IS NOT NULL
              AND entity_a.canonical_key = entity_b.canonical_key
            WITH entity_a.canonical_key AS canonical_key,
                 coalesce(entity_a.normalized_name, toLower(trim(entity_a.name))) AS normalized_name,
                 min(coalesce(entity_a.loaded_trial_count, 2147483647)) AS fanout,
                 collect(DISTINCT entity_a) AS trial_a_entities,
                 collect(DISTINCT entity_b) AS trial_b_entities
            RETURN normalized_name, trial_a_entities, trial_b_entities
            ORDER BY fanout, canonical_key
            LIMIT $limit
            """
            records = connection.execute_read(
                query,
                {
                    "nct_id_a": nct_id_a,
                    "nct_id_b": nct_id_b,
                    "limit": limit_per_type,
                },
            )
            for record in records:
                shared_entities.append(
                    {
                        "entity_type": entity_type,
                        "normalized_name": record["normalized_name"],
                        "trial_a_entities": _serialize_nodes(
                            record.get("trial_a_entities") or []
                        ),
                        "trial_b_entities": _serialize_nodes(
                            record.get("trial_b_entities") or []
                        ),
                    }
                )

        return {
            "found_a": True,
            "found_b": True,
            "nct_id_a": nct_id_a,
            "nct_id_b": nct_id_b,
            "shared_entities": shared_entities,
        }
    finally:
        connection.close()


def _select_frontier_entities(
    connection: Neo4jConnection,
    *,
    frontier: list[str],
    relationship_types: list[str],
    entity_limit_per_type: int,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Select the most specific canonical entities for each frontier trial.

    Specificity is deterministic and source-backed: lower ``loaded_trial_count``
    means fewer loaded trials share the entity. Selection happens before the
    entity -> Trial expansion so broad hubs cannot dominate query work.
    """
    query = """
    MATCH (entity)-[source_rel]->(source:Trial)
    WHERE source.nct_id IN $frontier
      AND type(source_rel) IN $relationship_types
      AND entity.canonical = true
      AND entity.canonical_key IS NOT NULL
      AND coalesce(entity.loaded_trial_count, 0) > 1
    WITH source, type(source_rel) AS relationship_type, entity,
         coalesce(entity.loaded_trial_count, 2147483647) AS fanout
    ORDER BY source.nct_id, relationship_type, fanout, entity.canonical_key
    WITH source, relationship_type,
         collect({
             canonical_key: entity.canonical_key,
             entity: properties(entity),
             fanout: fanout
         })[0..$entity_limit_per_type] AS selected_entities
    UNWIND selected_entities AS selected
    RETURN source.nct_id AS source_nct_id,
           relationship_type,
           selected.canonical_key AS canonical_key,
           selected.entity AS entity,
           selected.fanout AS fanout
    ORDER BY source_nct_id, relationship_type, fanout, canonical_key
    """
    records = connection.execute_read(
        query,
        {
            "frontier": frontier,
            "relationship_types": relationship_types,
            "entity_limit_per_type": entity_limit_per_type,
        },
    )
    selected: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        relationship_type = str(record["relationship_type"])
        canonical_key = str(record["canonical_key"])
        per_type = selected.setdefault(relationship_type, {})
        item = per_type.setdefault(
            canonical_key,
            {
                "canonical_key": canonical_key,
                "entity": dict(record.get("entity") or {}),
                "fanout": int(record.get("fanout") or 2147483647),
                "source_nct_ids": set(),
            },
        )
        item["source_nct_ids"].add(str(record["source_nct_id"]))
    return selected


def _fetch_related_candidates_for_entities(
    connection: Neo4jConnection,
    *,
    relationship_type: str,
    selected_entities: dict[str, dict[str, Any]],
    visited: set[str],
    overall_statuses: list[str],
    target_limit_per_entity: int,
) -> list[dict[str, Any]]:
    """Expand a bounded set of allowlisted canonical entities to Trial candidates."""
    if not selected_entities:
        return []
    label, relationship = _RELATED_ENTITY_TYPES[relationship_type]
    rows = [
        {"canonical_key": key}
        for key in sorted(
            selected_entities,
            key=lambda key: (
                int(selected_entities[key]["fanout"]),
                key,
            ),
        )
    ]
    query = f"""
    UNWIND $entities AS selected
    MATCH (entity:{label} {{canonical_key: selected.canonical_key}})
    CALL (entity) {{
        MATCH (entity)-[:{relationship}]->(related:Trial)
        WHERE NOT related.nct_id IN $visited
          AND ($overall_statuses = [] OR related.overall_status IN $overall_statuses)
        RETURN related
        ORDER BY related.nct_id
        LIMIT $target_limit_per_entity
    }}
    RETURN selected.canonical_key AS canonical_key, related
    ORDER BY canonical_key, related.nct_id
    """
    return connection.execute_read(
        query,
        {
            "entities": rows,
            "visited": sorted(visited),
            "overall_statuses": overall_statuses,
            "target_limit_per_entity": target_limit_per_entity,
        },
    )


def find_related_trials_bounded(
    seed_nct_id: str,
    max_hops: int = 2,
    per_hop_limit: int = 20,
    limit: int = 50,
    *,
    relationship_types: list[str] | None = None,
    overall_statuses: list[str] | None = None,
) -> dict:
    """Discover related trials using hub-aware bounded canonical traversal.

    One traversal hop remains ``Trial <- Entity -> Trial``. Batch 14 adds a
    deterministic fan-out guard before expansion: for each frontier Trial and
    relationship type, only the most specific canonical entities are expanded.
    Each selected entity then contributes only a bounded set of Trial candidates.
    The final per-hop result is ranked by specificity, evidence multiplicity,
    total fan-out, and NCT ID. The relationship allowlist remains hard-coded.
    """
    allowed_relationship_types = set(CORE_RELATED_RELATIONSHIP_TYPES)
    resolved_relationship_types = list(dict.fromkeys(
        relationship_types or sorted(allowed_relationship_types)
    ))
    if not resolved_relationship_types or any(
        item not in allowed_relationship_types for item in resolved_relationship_types
    ):
        raise ValueError("Related-trial relationship types must be allowlisted.")
    resolved_statuses = list(dict.fromkeys(overall_statuses or []))
    connection = Neo4jConnection()
    try:
        presence = connection.execute_read(
            "MATCH (trial:Trial {nct_id: $nct_id}) RETURN trial",
            {"nct_id": seed_nct_id},
        )
        if not presence:
            return {
                "found": False,
                "seed_nct_id": seed_nct_id,
                "anchor_trial": None,
                "matches": [],
            }
        anchor_trial = _serialize_node(presence[0].get("trial")) or {
            "nct_id": seed_nct_id
        }

        frontier = [seed_nct_id]
        visited = {seed_nct_id}
        matches: list[dict[str, Any]] = []
        for hop in range(1, max_hops + 1):
            if not frontier or len(matches) >= limit:
                break

            selected = _select_frontier_entities(
                connection,
                frontier=frontier,
                relationship_types=resolved_relationship_types,
                entity_limit_per_type=RELATED_ENTITY_LIMIT_PER_TYPE,
            )
            candidate_map: dict[str, dict[str, Any]] = {}
            for relationship_type in resolved_relationship_types:
                per_type = selected.get(relationship_type, {})
                records = _fetch_related_candidates_for_entities(
                    connection,
                    relationship_type=relationship_type,
                    selected_entities=per_type,
                    visited=visited,
                    overall_statuses=resolved_statuses,
                    target_limit_per_entity=RELATED_TARGET_LIMIT_PER_ENTITY,
                )
                for record in records:
                    trial = _serialize_node(record.get("related"))
                    if not trial or not trial.get("nct_id"):
                        continue
                    nct_id = str(trial["nct_id"])
                    if nct_id in visited:
                        continue
                    canonical_key = str(record["canonical_key"])
                    selected_item = per_type.get(canonical_key)
                    if selected_item is None:
                        continue
                    candidate = candidate_map.setdefault(
                        nct_id,
                        {
                            "nct_id": nct_id,
                            "trial": trial,
                            "paths": {},
                            "entity_fanouts": {},
                        },
                    )
                    entity_id = f"{relationship_type}:{canonical_key}"
                    candidate["entity_fanouts"][entity_id] = int(
                        selected_item["fanout"]
                    )
                    for source_nct_id in sorted(selected_item["source_nct_ids"]):
                        if source_nct_id == nct_id:
                            continue
                        path_key = (source_nct_id, relationship_type, canonical_key)
                        candidate["paths"][path_key] = {
                            "source_nct_id": source_nct_id,
                            "relationship_type": relationship_type,
                            "entity": dict(selected_item["entity"]),
                        }

            ranked_candidates = []
            for candidate in candidate_map.values():
                fanouts = list(candidate["entity_fanouts"].values()) or [2147483647]
                ranked_candidates.append(
                    (
                        min(fanouts),
                        -len(candidate["entity_fanouts"]),
                        sum(fanouts),
                        candidate["nct_id"],
                        candidate,
                    )
                )
            ranked_candidates.sort(key=lambda item: item[:4])
            remaining = min(per_hop_limit, limit - len(matches))
            next_frontier: list[str] = []
            for _, _, _, _, candidate in ranked_candidates[:remaining]:
                nct_id = candidate["nct_id"]
                if nct_id in visited:
                    continue
                visited.add(nct_id)
                next_frontier.append(nct_id)
                matches.append(
                    {
                        "nct_id": nct_id,
                        "trial": candidate["trial"],
                        "discovery_hop": hop,
                        "connected_via": [
                            candidate["paths"][key]
                            for key in sorted(candidate["paths"])
                        ],
                    }
                )
            frontier = next_frontier

        return {
            "found": True,
            "seed_nct_id": seed_nct_id,
            "anchor_trial": anchor_trial,
            "matches": matches,
        }
    finally:
        connection.close()
