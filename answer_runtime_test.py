from trialiq.services.answer_service import (
    answer_trial_overview_by_nct_id,
    answer_trial_overview,
)

tests = [
    ("VALID_NCT", lambda: answer_trial_overview_by_nct_id("NCT00000102")),
    ("LOWERCASE_NCT", lambda: answer_trial_overview_by_nct_id("nct00000102")),
    ("NOT_FOUND", lambda: answer_trial_overview_by_nct_id("NCT99999999")),
    ("INVALID_PREFIX", lambda: answer_trial_overview_by_nct_id("ABC00000102")),
    ("INVALID_FORMAT", lambda: answer_trial_overview_by_nct_id("NCTABC")),
    ("EMPTY_NCT", lambda: answer_trial_overview_by_nct_id("")),
    ("MISSING_NCT_QUESTION", lambda: answer_trial_overview("Give me a trial overview.")),
    ("UNSUPPORTED_QUESTION", lambda: answer_trial_overview("Compare two clinical trials.")),
]

for name, test in tests:
    print(f"\n=== {name} ===")
    try:
        result = test()
        print("STATUS:", result.status.value)
        print("ANSWER:", result.answer)
        print("LIMITATIONS:", result.limitations)
        print("SOURCES:", len(result.sources))

        if result.graph_response:
            print("GRAPH_STATUS:", result.graph_response.status.value)
            print("VALIDATION_VALID:", result.graph_response.validation.valid)

    except Exception as exc:
        print("UNEXPECTED_EXCEPTION:", type(exc).__name__, str(exc))
