"""Bounded trial catalog used by the investigator UI."""

from trialiq.chains.cypher_qa import list_trial_catalog
from trialiq.services.models import (
    TrialCatalogItem,
    TrialCatalogResponse,
    TrialQuestionSuggestion,
)


def _suggested_questions(
    nct_id: str,
    *,
    has_graph_neighbors: bool,
) -> list[TrialQuestionSuggestion]:
    if has_graph_neighbors:
        return [
            TrialQuestionSuggestion(
                kind="related_trials",
                label="Find related trials",
                question=(
                    f"Find trials related to {nct_id}. For each related trial, "
                    "explain the shared condition, intervention, or sponsor that "
                    "connects it to the seed trial, and cite the available source "
                    "evidence. Do not infer relationships that are not supported "
                    "by the retrieved evidence."
                ),
            ),
            TrialQuestionSuggestion(
                kind="connections",
                label="Explain connections",
                question=(
                    f"Find trials connected to {nct_id} through shared conditions, "
                    "interventions, or sponsors. Explain each supported connection "
                    "in plain English and cite the available evidence."
                ),
            ),
            TrialQuestionSuggestion(
                kind="graph_evidence",
                label="Show graph evidence",
                question=(
                    f"Find one-hop related trials for {nct_id} and explain the "
                    "shared graph evidence for each relationship. Do not infer "
                    "unsupported connections."
                ),
            ),
        ]

    return [
        TrialQuestionSuggestion(
            kind="overview",
            label="Summarize this trial",
            question=(
                f"Give me an evidence-grounded overview of {nct_id} using only "
                "the available trial metadata."
            ),
        ),
        TrialQuestionSuggestion(
            kind="metadata",
            label="Show available metadata",
            question=(
                f"Give me an overview of {nct_id} and summarize its available "
                "condition, intervention, sponsor, status, and enrollment metadata."
            ),
        ),
        TrialQuestionSuggestion(
            kind="source_evidence",
            label="Show source evidence",
            question=(
                f"Give me an overview of {nct_id} and cite the available source "
                "evidence. Do not infer information that is not present in the "
                "retrieved records."
            ),
        ),
    ]


def get_trial_catalog(
    query: str = "",
    *,
    limit: int = 50,
    offset: int = 0,
) -> TrialCatalogResponse:
    """Return loaded trials and deterministic questions appropriate to each trial."""
    normalized_query = query.strip()
    raw = list_trial_catalog(
        normalized_query,
        limit=limit,
        offset=offset,
    )

    trials = []
    for item in raw["trials"]:
        related_trial_count = int(item.get("related_trial_count") or 0)
        related_trial_count_capped = bool(item.get("related_trial_count_capped"))
        has_graph_neighbors = related_trial_count > 0
        nct_id = str(item["nct_id"])
        trials.append(
            TrialCatalogItem(
                nct_id=nct_id,
                brief_title=item.get("brief_title"),
                official_title=item.get("official_title"),
                overall_status=item.get("overall_status"),
                related_trial_count=related_trial_count,
                related_trial_count_capped=related_trial_count_capped,
                has_graph_neighbors=has_graph_neighbors,
                relationship_types=list(item.get("relationship_types") or []),
                suggested_questions=_suggested_questions(
                    nct_id,
                    has_graph_neighbors=has_graph_neighbors,
                ),
            )
        )

    total_count = int(raw.get("total_count") or 0)
    return TrialCatalogResponse(
        query=normalized_query,
        limit=limit,
        offset=offset,
        total_count=total_count,
        has_more=offset + len(trials) < total_count,
        trials=trials,
    )
