"""Narrow deterministic intent fallback for explicitly supported demo patterns."""

from __future__ import annotations

import re

from trialiq.chains.intent_extraction import ExtractedQueryIntent
from trialiq.services.query_intent import QueryIntent


_NCT_PATTERN = re.compile(r"\bNCT\d{8}\b", flags=re.IGNORECASE)


def extract_supported_intent_fallback(question: str) -> ExtractedQueryIntent | None:
    """Recognize only bounded, explicit patterns when all LLM providers are down.

    This deliberately does not attempt general NLP. It supports the concrete
    NCT-based demo/query shapes that TrialIQ can execute deterministically.
    """
    normalized = question.strip()
    lowered = normalized.lower()
    nct_ids = [value.upper() for value in _NCT_PATTERN.findall(normalized)]

    if len(nct_ids) >= 2 and any(
        token in lowered for token in ("compare", "shared", "in common")
    ):
        return ExtractedQueryIntent(
            intent=QueryIntent.SHARED_ENTITIES_BETWEEN_TRIALS,
            nct_id=nct_ids[0],
            nct_id_b=nct_ids[1],
        )

    if len(nct_ids) == 1 and any(
        token in lowered for token in ("related", "connected", "connection")
    ):
        relationship_types: list[str] = []
        if "condition" in lowered:
            relationship_types.append("HAS_CONDITION")
        if any(token in lowered for token in ("intervention", "drug", "device", "procedure")):
            relationship_types.append("HAS_INTERVENTION")
        if "sponsor" in lowered:
            relationship_types.append("SPONSORED_BY")
        if not relationship_types:
            relationship_types = [
                "HAS_CONDITION",
                "HAS_INTERVENTION",
                "SPONSORED_BY",
            ]

        two_hops = bool(
            re.search(r"\b(?:two|2)[ -]?hop", lowered)
            or "within two hops" in lowered
        )
        statuses = ["COMPLETED"] if "completed" in lowered else []
        return ExtractedQueryIntent(
            intent=QueryIntent.RELATED_TRIALS,
            nct_id=nct_ids[0],
            max_hops=2 if two_hops else 1,
            relationship_types=relationship_types,
            overall_statuses=statuses,
        )

    if len(nct_ids) == 1 and any(
        token in lowered
        for token in ("overview", "summary", "summarize", "details", "show me", "tell me")
    ):
        return ExtractedQueryIntent(
            intent=QueryIntent.TRIAL_OVERVIEW,
            nct_id=nct_ids[0],
        )

    return None
