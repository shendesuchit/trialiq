from trialiq.services.models import (
    AnswerStatus,
    EvidenceGroundedAnswer,
    EvidenceSource,
    GraphQueryResponse,
    ConditionSearchResponse,
)

def _format_value(
    value: object,
    fallback: str = "Not available",
) -> str:
    if value is None or value == "":
        return fallback

    return str(value)


def _format_entity_names(
    entities: list[dict] | None,
    name_key: str = "name",
) -> str:
    if not entities:
        return "Not available"

    names = [
        str(entity[name_key])
        for entity in entities
        if isinstance(entity, dict) and entity.get(name_key)
    ]

    return ", ".join(names) if names else "Not available"


def _add_missing_field_limitation(
    limitations: list[str],
    value: object,
    field_name: str,
) -> None:
    if value is None or value == "":
        limitations.append(f"{field_name} was not available.")

def extract_evidence_sources(
    evidence: dict,
) -> list[EvidenceSource]:
    source_collections = [
        "trial",
        "conditions",
        "interventions",
        "sponsors",
        "facilities",
        "designs",
        "eligibilities",
    ]

    unique_sources: dict[str, EvidenceSource] = {}

    for collection_name in source_collections:
        records = evidence.get(collection_name)

        if isinstance(records, dict):
            records = [records]

        if not isinstance(records, list):
            continue

        for record in records:
            if not isinstance(record, dict):
                continue

            source_table = record.get("source_table")
            source_key = record.get("source_key")
            source_id = record.get("source_id")

            if not any(
                value is not None
                for value in (source_table, source_key, source_id)
            ):
                continue

            deduplication_key = (
                str(source_key)
                if source_key is not None
                else f"{source_table}|{source_id}"
            )

            if deduplication_key not in unique_sources:
                unique_sources[deduplication_key] = EvidenceSource(
                    source_table=source_table,
                    source_key=source_key,
                    source_id=source_id,
                )

    return list(unique_sources.values())

def format_trial_overview(
    graph_response: GraphQueryResponse,
    question: str,
) -> EvidenceGroundedAnswer:
    limitations: list[str] = []

    # Change Start: Enforce validated evidence before formatting

    if (
        graph_response.status.value != "SUCCESS"
        or not graph_response.validation.valid
    ):
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer=(
                "A trial overview could not be generated because "
                "validated graph evidence is unavailable."
            ),
            graph_response=graph_response,
            limitations=[
                "Graph evidence was not validated successfully."
            ],
        )

    # Change End

    evidence = graph_response.evidence

    if not evidence or not evidence.get("trial"):
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer="No trial evidence was available for this request.",
            graph_response=graph_response,
            limitations=[
                "Trial metadata was not present in the response."
            ],
        )

    trial = evidence["trial"]
    sources = extract_evidence_sources(evidence)
    conditions = evidence.get("conditions", [])
    interventions = evidence.get("interventions", [])
    sponsors = evidence.get("sponsors", [])
    designs = evidence.get("designs", [])

    design = designs[0] if designs else {}

    answer_lines = [
        f"Trial ID: {_format_value(trial.get('nct_id'))}",
        f"Brief title: {_format_value(trial.get('brief_title'))}",
        f"Overall status: {_format_value(trial.get('overall_status'))}",
        f"Study type: {_format_value(trial.get('study_type'))}",
        f"Phase: {_format_value(trial.get('phase'))}",
        f"Enrollment: {_format_value(trial.get('enrollment'))}",
        f"Start date: {_format_value(trial.get('start_date'))}",
        f"Completion date: {_format_value(trial.get('completion_date'))}",
        f"Why stopped: {_format_value(trial.get('why_stopped'))}",
        (
            "Study design: "
            f"Allocation={_format_value(design.get('allocation'))}; "
            f"Masking={_format_value(design.get('masking'))}; "
            f"Intervention model="
            f"{_format_value(design.get('intervention_model'))}; "
            f"Observational model="
            f"{_format_value(design.get('observational_model'))}; "
            f"Time perspective="
            f"{_format_value(design.get('time_perspective'))}"
        ),
        f"Conditions: {_format_entity_names(conditions)}",
        f"Interventions: {_format_entity_names(interventions)}",
        f"Sponsors: {_format_entity_names(sponsors)}",
    ]

    _add_missing_field_limitation(
        limitations,
        trial.get("brief_title"),
        "Brief title",
    )

    _add_missing_field_limitation(
        limitations,
        trial.get("overall_status"),
        "Overall status",
    )

    _add_missing_field_limitation(
        limitations,
        trial.get("study_type"),
        "Study type",
    )

    _add_missing_field_limitation(
        limitations,
        trial.get("phase"),
        "Phase",
    )

    _add_missing_field_limitation(
        limitations,
        trial.get("enrollment"),
        "Enrollment",
    )

    _add_missing_field_limitation(
        limitations,
        trial.get("start_date"),
        "Start date",
    )

    _add_missing_field_limitation(
        limitations,
        trial.get("completion_date"),
        "Completion date",
    )

    if not design:
        limitations.append("Study design was not available.")

    answer = "\n".join(answer_lines)

    return EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=question,
        answer=answer,
        graph_response=graph_response,
        limitations=limitations,
        sources=sources,
    )

# Change End

def format_condition_search(
    search_response: ConditionSearchResponse,
    question: str,
) -> EvidenceGroundedAnswer:
    if search_response.status.value != "SUCCESS" or not search_response.validation.valid:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer="No validated trials were found for the requested condition.",
            condition_search_response=search_response,
            limitations=["Condition search did not return validated matches."],
        )

    lines = [
        f"Condition match: {search_response.condition}",
        f"Trials returned: {len(search_response.matches)}",
    ]
    sources = []
    for match in search_response.matches:
        trial = match.trial
        lines.extend([
            "",
            f"Trial ID: {_format_value(trial.get('nct_id'), match.nct_id)}",
            f"Brief title: {_format_value(trial.get('brief_title'))}",
            f"Overall status: {_format_value(trial.get('overall_status'))}",
            f"Study type: {_format_value(trial.get('study_type'))}",
            f"Phase: {_format_value(trial.get('phase'))}",
            f"Enrollment: {_format_value(trial.get('enrollment'))}",
            f"Matched conditions: {_format_entity_names(match.matched_conditions)}",
        ])
        sources.extend(extract_evidence_sources({
            "trial": trial,
            "conditions": match.matched_conditions,
        }))

    unique = {}
    for source in sources:
        key = (source.source_key, source.source_table, source.source_id)
        unique[key] = source

    return EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=question,
        answer="\n".join(lines),
        condition_search_response=search_response,
        limitations=[
            "Matching uses exact case-insensitive condition-name matching only.",
            "Results are bounded by the requested limit.",
        ],
        sources=list(unique.values()),
    )


def format_entity_search(search_response, question: str) -> EvidenceGroundedAnswer:
    """Format validated intervention/sponsor graph matches without an LLM."""
    if search_response.status.value != "SUCCESS" or not search_response.validation.valid:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer=f"No validated trials were found for the requested {search_response.entity_type}.",
            entity_search_response=search_response,
            limitations=[f"{search_response.entity_type.title()} search did not return validated matches."],
        )

    lines = [
        f"{search_response.entity_type.title()} match: {search_response.query}",
        f"Trials returned: {len(search_response.matches)}",
    ]
    sources = []
    for match in search_response.matches:
        trial = match.trial
        lines.extend([
            "",
            f"Trial ID: {_format_value(trial.get('nct_id'), match.nct_id)}",
            f"Brief title: {_format_value(trial.get('brief_title'))}",
            f"Overall status: {_format_value(trial.get('overall_status'))}",
            f"Matched {search_response.entity_type}s: {_format_entity_names(match.matched_entities)}",
        ])
        sources.extend(extract_evidence_sources({"trial": trial, f"{search_response.entity_type}s": match.matched_entities}))

    unique = {(source.source_key, source.source_table, source.source_id): source for source in sources}
    return EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=question,
        answer="\n".join(lines),
        entity_search_response=search_response,
        limitations=[
            f"Matching uses exact case-insensitive {search_response.entity_type}-name matching only.",
            "Results are bounded by the requested limit.",
        ],
        sources=list(unique.values()),
    )


def format_shared_entity_comparison(response, question: str) -> EvidenceGroundedAnswer:
    """Format a bounded deterministic shared-entity comparison."""
    if response.status.value != "SUCCESS" or not response.validation.valid:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer="Validated shared-entity evidence was unavailable for the requested trials.",
            shared_entity_response=response,
            limitations=["Shared-entity comparison did not return validated evidence."],
        )

    lines = [
        f"Trial comparison: {response.nct_id_a} vs {response.nct_id_b}",
        f"Shared entities returned: {len(response.shared_entities)}",
    ]
    for match in response.shared_entities:
        lines.append(f"{match.entity_type}: {match.normalized_name}")

    if not response.shared_entities:
        lines.append("No shared conditions, interventions, or sponsors were found within the bounded comparison.")

    return EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=question,
        answer="\n".join(lines),
        shared_entity_response=response,
        limitations=["Comparison is limited to conditions, interventions, and sponsors.", "Results per entity type are bounded by the requested limit."],
    )


def format_related_trial_search(response, question: str) -> EvidenceGroundedAnswer:
    """Format bounded related-trial traversal with explicit path evidence."""
    if response.status.value != "SUCCESS" or not response.validation.valid or not response.matches:
        return EvidenceGroundedAnswer(
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            question=question,
            answer="No validated related-trial paths were available for the requested seed trial.",
            related_trial_response=response,
            limitations=["Related-trial traversal did not return validated path evidence."],
        )

    metrics = response.metrics
    lines = [
        f"Seed trial: {response.seed_nct_id}",
        f"Related trials returned: {metrics.related_trial_count}",
        f"Unique shared entities: {metrics.unique_shared_entity_count}",
        f"Evidence paths: {metrics.evidence_path_count}",
        f"Condition-linked trials: {metrics.condition_linked_trial_count}",
        f"Intervention-linked trials: {metrics.intervention_linked_trial_count}",
        f"Sponsor-linked trials: {metrics.sponsor_linked_trial_count}",
        f"Trials sharing multiple factors: {metrics.multi_factor_trial_count}",
        f"Trials with completion comparisons: {metrics.completion_comparable_trial_count}",
        f"Trials with enrollment comparisons: {metrics.enrollment_comparable_trial_count}",
        f"Maximum traversal depth: {response.max_hops} hop(s)",
    ]
    if response.relationship_types:
        lines.append(f"Relationship filters: {', '.join(response.relationship_types)}")
    if response.overall_statuses:
        lines.append(f"Status filters: {', '.join(response.overall_statuses)}")

    sources = []
    if response.anchor_trial:
        sources.extend(extract_evidence_sources({"trial": response.anchor_trial}))
    for match in response.matches:
        lines.extend([
            "",
            f"Trial ID: {_format_value(match.trial.get('nct_id'), match.nct_id)}",
            f"Brief title: {_format_value(match.trial.get('brief_title'))}",
            f"Overall status: {_format_value(match.trial.get('overall_status'))}",
            f"Enrollment: {_format_value(match.trial.get('enrollment'))}",
            f"Start date: {_format_value(match.trial.get('start_date'))}",
            f"Completion date: {_format_value(match.trial.get('completion_date'))}",
            f"Discovery hop: {match.discovery_hop}",
        ])
        sources.extend(extract_evidence_sources({"trial": match.trial}))
        for path in match.connected_via:
            entity_name = path.entity.get("name") or path.entity.get("normalized_name") or "Not available"
            stable_id = f" [{path.entity_id}]" if path.entity_id else ""
            lines.append(
                f"Connected from {path.source_nct_id} via {path.relationship_type}: "
                f"{entity_name}{stable_id}"
            )
            sources.extend(extract_evidence_sources({"conditions": [path.entity]}))

        if match.metrics is not None:
            match_metrics = match.metrics
            lines.append(
                "Shared entity counts: "
                f"conditions={match_metrics.shared_condition_count}; "
                f"interventions={match_metrics.shared_intervention_count}; "
                f"sponsors={match_metrics.shared_sponsor_count}; "
                f"total={match_metrics.total_shared_entity_count}; "
                f"evidence paths={match_metrics.evidence_path_count}"
            )
            for comparison in (
                match_metrics.start_date_comparison,
                match_metrics.completion_date_comparison,
                match_metrics.duration_comparison,
                match_metrics.enrollment_comparison,
            ):
                if comparison:
                    lines.append(comparison)

    unique = {(source.source_key, source.source_table, source.source_id): source for source in sources}
    return EvidenceGroundedAnswer(
        status=AnswerStatus.GROUNDED,
        question=question,
        answer="\n".join(lines),
        related_trial_response=response,
        limitations=[
            "Traversal is limited to shared condition, intervention, and sponsor metadata.",
            f"Traversal is bounded to at most {response.max_hops} hop(s).",
            "Results are bounded by per-hop and overall limits.",
        ],
        sources=list(unique.values()),
    )
