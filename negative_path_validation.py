from trialiq.services.answer_service import answer_trial_overview_by_nct_id
from trialiq.validation.evidence import validate_trial_evidence


def check(label, condition):
    if not condition:
        raise AssertionError(f"FAIL: {label}")
    print(f"PASS: {label}")


# 1. Nonexistent NCT ID
result = answer_trial_overview_by_nct_id("NCT99999999")

check(
    "Nonexistent NCT ID handled without execution error",
    result.status.value != "ERROR",
)

check(
    "Nonexistent NCT ID does not produce a grounded answer",
    result.status.value != "GROUNDED",
)


# 2. Malformed NCT ID
result = answer_trial_overview_by_nct_id("INVALID_ID")

check(
    "Malformed NCT ID handled without execution error",
    result.status.value != "ERROR",
)

check(
    "Malformed NCT ID does not produce a grounded answer",
    result.status.value != "GROUNDED",
)


# 3. Valid trial and evidence validation
result = answer_trial_overview_by_nct_id("NCT00000102")

check(
    "Valid trial returns grounded answer",
    result.status.value == "GROUNDED",
)

check(
    "Valid trial contains sources",
    bool(result.sources),
)

check(
    "Valid graph response is present",
    result.graph_response is not None,
)

check(
    "Valid graph evidence passes validation",
    result.graph_response.validation.valid is True,
)

check(
    "Valid graph evidence has no validation errors",
    not result.graph_response.validation.errors,
)


# 4. Direct evidence-integrity checks
valid_evidence = result.graph_response.evidence

valid_result = validate_trial_evidence(
    valid_evidence,
    "NCT00000102",
)

check(
    "Valid evidence accepted",
    valid_result["valid"] is True,
)


mismatched_result = validate_trial_evidence(
    valid_evidence,
    "NCT99999999",
)

check(
    "Mismatched NCT ID rejected or flagged",
    (
        mismatched_result["valid"] is False
        or bool(mismatched_result["errors"])
        or bool(mismatched_result["warnings"])
    ),
)


print("PASS: Consolidated negative-path and evidence-integrity validation")

