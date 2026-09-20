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
