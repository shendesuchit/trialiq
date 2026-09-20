
from typing import Any


ENTITY_COLLECTIONS = (
    "conditions",
    "interventions",
    "sponsors",
    "facilities",
    "designs",
    "eligibilities",
)


def validate_trial_evidence(
    evidence: dict[str, Any],
    requested_nct_id: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    normalized_requested_nct_id = (requested_nct_id or "").strip().upper()

    def normalized_nct_id(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        return value.strip().upper()

    if not normalized_requested_nct_id:
        errors.append("Requested NCT ID is empty.")

    if not isinstance(evidence, dict):
        return {
            "valid": False,
            "errors": ["Evidence must be a dictionary."],
            "warnings": [],
        }

    if evidence.get("found") is not True:
        errors.append("Requested trial was not found.")

    returned_nct_id = evidence.get("nct_id")

    if normalized_nct_id(returned_nct_id) != normalized_requested_nct_id:
        errors.append(
            "Evidence NCT ID does not match the requested NCT ID."
        )


    # Change Start
    trial = evidence.get("trial")

    if evidence.get("found") is True:
        if not isinstance(trial, dict):
            errors.append("Trial evidence is missing or is not a dictionary.")
        else:
            if normalized_nct_id(trial.get("nct_id")) != normalized_requested_nct_id:
                errors.append(
                    "Trial record NCT ID does not match the requested NCT ID."
                )

            if not trial.get("source_key"):
                warnings.append("Trial record has no source_key.")

    # Change End

    for collection_name in ENTITY_COLLECTIONS:
        if collection_name not in evidence:
            errors.append(
                f"Missing evidence collection: {collection_name}."
            )
            continue

        records = evidence[collection_name]

        if not isinstance(records, list):
            errors.append(
                f"Evidence collection '{collection_name}' must be a list."
            )
            continue

        for index, record in enumerate(records):
            location = f"{collection_name}[{index}]"

            if not isinstance(record, dict):
                errors.append(f"{location} must be a dictionary.")
                continue

            if normalized_nct_id(record.get("nct_id")) != normalized_requested_nct_id:
                errors.append(
                    f"{location} has an inconsistent nct_id."
                )

            if not record.get("source_key"):
                warnings.append(
                    f"{location} has no source_key."
                )

            if not record.get("source_table"):
                warnings.append(
                    f"{location} has no source_table."
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }