"""Structured synthesis evidence catalog and deterministic grounding checks."""

from __future__ import annotations

import json
from typing import Any

from .models import RetrievalResult, StructuredFinding, StructuredSynthesis


_SYNTHESIS_SYSTEM_PROMPT = """You are TrialIQ's grounded synthesis stage.
Return only the requested structured object. Use only the supplied evidence catalog.
Do not add medical advice, efficacy conclusions, safety conclusions, or outside knowledge.
Each key finding must cite one or more exact evidence IDs from the catalog.
Do not calculate date, duration, enrollment, or other numeric differences yourself. Only state a
numeric comparison when that comparison is explicitly supplied in the evidence catalog.
When citing a metric evidence ID, reproduce that metric's display text verbatim inside the finding.
Do not invent evidence IDs. When deterministic comparison metrics are available for related trials,
prioritize at least one concise quantitative key finding that uses those supplied metric evidence IDs.
Keep the headline and summary concise. Do not output Markdown.
"""


def _record_id(kind: str, index: int, record: dict[str, Any]) -> str:
    source_key = record.get("source_key")
    if source_key:
        return f"source:{kind}:{source_key}"
    canonical_key = record.get("canonical_key")
    if canonical_key:
        return f"entity:{kind}:{canonical_key}"
    nct_id = record.get("nct_id")
    if kind == "trial" and nct_id:
        return f"trial:{nct_id}"
    return f"evidence:{kind}:{index}"


def build_evidence_catalog(retrieval: RetrievalResult) -> list[dict[str, Any]]:
    """Create stable per-response evidence IDs for synthesis citations."""
    catalog: dict[str, dict[str, Any]] = {}

    def add(evidence_id: str, kind: str, data: Any) -> None:
        catalog.setdefault(
            evidence_id,
            {"evidence_id": evidence_id, "kind": kind, "data": data},
        )

    if retrieval.graph_response is not None:
        evidence = retrieval.graph_response.evidence or {}
        for collection, records in evidence.items():
            if isinstance(records, dict):
                records = [records]
            if not isinstance(records, list):
                continue
            for index, record in enumerate(records):
                if isinstance(record, dict):
                    kind = "trial" if collection == "trial" else collection.rstrip("s")
                    add(_record_id(kind, index, record), kind, record)

    if retrieval.condition_search_response is not None:
        response = retrieval.condition_search_response
        add(
            "condition:query",
            "query_scope",
            {
                "condition": response.condition,
                "limit": response.limit,
                "match_count": len(response.matches),
            },
        )
        for match_index, match in enumerate(response.matches):
            add(f"trial:{match.nct_id}", "trial", match.trial)
            for index, entity in enumerate(match.matched_conditions):
                add(
                    _record_id("condition", match_index * 1000 + index, entity),
                    "condition",
                    entity,
                )

    if retrieval.entity_search_response is not None:
        response = retrieval.entity_search_response
        entity_type = response.entity_type
        add(
            f"{entity_type}:query",
            "query_scope",
            {
                "entity_type": entity_type,
                "query": response.query,
                "limit": response.limit,
                "match_count": len(response.matches),
            },
        )
        for match_index, match in enumerate(response.matches):
            add(f"trial:{match.nct_id}", "trial", match.trial)
            for index, entity in enumerate(match.matched_entities):
                add(
                    _record_id(entity_type, match_index * 1000 + index, entity),
                    entity_type,
                    entity,
                )

    if retrieval.shared_entity_response is not None:
        response = retrieval.shared_entity_response
        add(
            "comparison:trials",
            "comparison",
            {
                "nct_id_a": response.nct_id_a,
                "nct_id_b": response.nct_id_b,
                "shared_entity_count": len(response.shared_entities),
            },
        )
        for index, match in enumerate(response.shared_entities):
            add(
                f"shared:{index}",
                "shared_entity",
                match.model_dump(mode="json"),
            )

    if retrieval.related_trial_response is not None:
        response = retrieval.related_trial_response
        add(
            "related:query",
            "query_scope",
            {
                "seed_nct_id": response.seed_nct_id,
                "max_hops": response.max_hops,
                "relationship_types": response.relationship_types,
                "overall_statuses": response.overall_statuses,
                "match_count": len(response.matches),
            },
        )
        if response.anchor_trial:
            add(f"trial:{response.seed_nct_id}", "anchor_trial", response.anchor_trial)
        aggregate_displays = {
            "related_trial_count": f"Related trials returned: {response.metrics.related_trial_count}",
            "unique_shared_entity_count": f"Unique shared entities: {response.metrics.unique_shared_entity_count}",
            "evidence_path_count": f"Evidence paths: {response.metrics.evidence_path_count}",
            "condition_linked_trial_count": f"Condition-linked trials: {response.metrics.condition_linked_trial_count}",
            "intervention_linked_trial_count": f"Intervention-linked trials: {response.metrics.intervention_linked_trial_count}",
            "sponsor_linked_trial_count": f"Sponsor-linked trials: {response.metrics.sponsor_linked_trial_count}",
            "multi_factor_trial_count": f"Trials sharing multiple factors: {response.metrics.multi_factor_trial_count}",
            "completion_comparable_trial_count": f"Trials with completion comparisons: {response.metrics.completion_comparable_trial_count}",
            "duration_comparable_trial_count": f"Trials with duration comparisons: {response.metrics.duration_comparable_trial_count}",
            "enrollment_comparable_trial_count": f"Trials with enrollment comparisons: {response.metrics.enrollment_comparable_trial_count}",
        }
        for metric_name, display in aggregate_displays.items():
            add(
                f"metric:related:{metric_name}",
                "metric",
                {
                    "metric": metric_name,
                    "value": getattr(response.metrics, metric_name),
                    "unit": "count",
                    "display": display,
                },
            )
        for match in response.matches:
            add(f"trial:{match.nct_id}", "trial", match.trial)
            for index, path in enumerate(match.connected_via):
                add(
                    f"path:{match.nct_id}:{index}",
                    "connection_path",
                    path.model_dump(mode="json"),
                )
                if path.entity_id:
                    add(path.entity_id, "canonical_entity", path.entity)
            if match.metrics is not None:
                metric_displays = {
                    "shared_condition_count": f"Shared conditions: {match.metrics.shared_condition_count}",
                    "shared_intervention_count": f"Shared interventions: {match.metrics.shared_intervention_count}",
                    "shared_sponsor_count": f"Shared sponsors: {match.metrics.shared_sponsor_count}",
                    "total_shared_entity_count": f"Total shared entities: {match.metrics.total_shared_entity_count}",
                    "evidence_path_count": f"Evidence paths: {match.metrics.evidence_path_count}",
                    "start_date_difference_days": match.metrics.start_date_comparison,
                    "completion_date_difference_days": match.metrics.completion_date_comparison,
                    "duration_difference_days": match.metrics.duration_comparison,
                    "enrollment_difference": match.metrics.enrollment_comparison,
                }
                units = {
                    "start_date_difference_days": "days",
                    "completion_date_difference_days": "days",
                    "duration_difference_days": "days",
                    "enrollment_difference": "participants",
                }
                for metric_name, display in metric_displays.items():
                    value = getattr(match.metrics, metric_name)
                    if value is None or not display:
                        continue
                    add(
                        f"metric:{match.nct_id}:{metric_name}",
                        "metric",
                        {
                            "trial_nct_id": match.nct_id,
                            "metric": metric_name,
                            "value": value,
                            "unit": units.get(metric_name, "count"),
                            "display": display,
                        },
                    )

    return list(catalog.values())


def build_synthesis_messages(
    question: str,
    retrieval: RetrievalResult,
) -> list[tuple[str, str]]:
    catalog = build_evidence_catalog(retrieval)
    payload = {
        "question": question,
        "evidence_catalog": catalog,
    }
    return [
        ("system", _SYNTHESIS_SYSTEM_PROMPT),
        ("human", json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)),
    ]


def _finding_validation_errors(
    finding: StructuredFinding,
    index: int,
    *,
    allowed_ids: set[str],
    metric_displays: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    if not finding.evidence_ids:
        return [f"Finding {index + 1} has no evidence references."]

    unknown = [item for item in finding.evidence_ids if item not in allowed_ids]
    if unknown:
        return [
            f"Finding {index + 1} references unknown evidence IDs: {', '.join(unknown)}."
        ]

    for evidence_id in finding.evidence_ids:
        display = metric_displays.get(evidence_id)
        if display and display.casefold() not in finding.statement.casefold():
            errors.append(
                f"Finding {index + 1} must reproduce the deterministic metric text for {evidence_id}."
            )
    return errors


def filter_grounded_synthesis(
    synthesis: StructuredSynthesis,
    retrieval: RetrievalResult,
) -> tuple[StructuredSynthesis | None, list[str]]:
    """Keep only findings that pass deterministic evidence-ID/metric validation.

    A single malformed LLM finding should not discard other independently grounded
    findings.  The caller can still mark the response as degraded and surface the
    rejected-claim reasons for auditability.
    """
    catalog = build_evidence_catalog(retrieval)
    allowed_ids = {item["evidence_id"] for item in catalog}
    metric_displays = {
        item["evidence_id"]: str(item["data"].get("display"))
        for item in catalog
        if item.get("kind") == "metric"
        and isinstance(item.get("data"), dict)
        and item["data"].get("display")
    }
    valid_findings: list[StructuredFinding] = []
    errors: list[str] = []
    for index, finding in enumerate(synthesis.key_findings):
        finding_errors = _finding_validation_errors(
            finding,
            index,
            allowed_ids=allowed_ids,
            metric_displays=metric_displays,
        )
        if finding_errors:
            errors.extend(finding_errors)
        else:
            valid_findings.append(finding)

    if not valid_findings:
        return None, errors
    return synthesis.model_copy(update={"key_findings": valid_findings}), errors


def build_deterministic_related_synthesis(
    retrieval: RetrievalResult,
) -> StructuredSynthesis | None:
    """Create a concise structured fallback from already-validated related-trial data."""
    response = retrieval.related_trial_response
    if response is None or not response.matches:
        return None

    related_count = response.metrics.related_trial_count or len(response.matches)
    shared_count = response.metrics.unique_shared_entity_count or sum(
        len(match.connected_via) for match in response.matches
    )
    path_count = response.metrics.evidence_path_count or sum(
        len(match.connected_via) for match in response.matches
    )
    status_word = " completed" if response.overall_statuses == ["COMPLETED"] else ""
    headline = (
        f"{related_count}{status_word} related trial"
        f"{'s' if related_count != 1 else ''} connected to {response.seed_nct_id}"
    )

    comparable = any(
        match.metrics is not None
        and any(
            value is not None
            for value in (
                match.metrics.start_date_difference_days,
                match.metrics.completion_date_difference_days,
                match.metrics.duration_difference_days,
                match.metrics.enrollment_difference,
            )
        )
        for match in response.matches
    )
    summary = (
        f"TrialIQ found {related_count} related trial{'s' if related_count != 1 else ''} "
        f"through {shared_count} canonical shared entit{'ies' if shared_count != 1 else 'y'} "
        f"across {path_count} evidence path{'s' if path_count != 1 else ''}."
    )
    if not comparable:
        summary += (
            " Timeline and enrollment comparisons cannot be calculated because the "
            "required values are not present in the loaded graph evidence."
        )

    relationship_labels = {
        "HAS_CONDITION": "Condition",
        "HAS_INTERVENTION": "Intervention",
        "SPONSORED_BY": "Sponsor",
    }
    findings: list[StructuredFinding] = []
    for match in response.matches[:8]:
        labels: list[str] = []
        evidence_ids: list[str] = []
        for index, path in enumerate(match.connected_via):
            label = relationship_labels.get(path.relationship_type, path.relationship_type)
            entity_name = path.entity.get("name") or path.entity.get("normalized_name") or "shared entity"
            labels.append(f"{label} — {entity_name}")
            evidence_ids.append(f"path:{match.nct_id}:{index}")
        if not evidence_ids:
            continue

        statement = f"{match.nct_id} is connected through " + "; ".join(labels) + "."
        if match.metrics is not None:
            quantitative_options = (
                (
                    "completion_date_difference_days",
                    match.metrics.completion_date_difference_days,
                    match.metrics.completion_date_comparison,
                ),
                (
                    "enrollment_difference",
                    match.metrics.enrollment_difference,
                    match.metrics.enrollment_comparison,
                ),
                (
                    "duration_difference_days",
                    match.metrics.duration_difference_days,
                    match.metrics.duration_comparison,
                ),
                (
                    "start_date_difference_days",
                    match.metrics.start_date_difference_days,
                    match.metrics.start_date_comparison,
                ),
            )
            for metric_name, value, display in quantitative_options:
                if value is None or not display:
                    continue
                statement += f" {display}"
                evidence_ids.append(f"metric:{match.nct_id}:{metric_name}")
                break

        findings.append(
            StructuredFinding(
                statement=statement,
                evidence_ids=evidence_ids,
            )
        )

    if not findings:
        return None
    return StructuredSynthesis(
        headline=headline,
        summary=summary,
        key_findings=findings,
    )


def validate_structured_synthesis(
    synthesis: StructuredSynthesis,
    retrieval: RetrievalResult,
) -> list[str]:
    """Validate that every key finding cites evidence present in this retrieval."""
    _filtered, errors = filter_grounded_synthesis(synthesis, retrieval)
    return errors


def render_structured_synthesis(synthesis: StructuredSynthesis) -> str:
    """Render structured content for backward-compatible text consumers."""
    parts = [synthesis.headline, "", synthesis.summary]
    if synthesis.key_findings:
        parts.extend(["", "Key findings:"])
        parts.extend(f"- {finding.statement}" for finding in synthesis.key_findings)
    return "\n".join(parts)
