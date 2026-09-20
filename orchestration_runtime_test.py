from trialiq.services.answer_service import answer_trial_overview

tests = [
    ("VALID_OVERVIEW", "Give me an overview of NCT00000102."),
    ("LOWERCASE_OVERVIEW", "Give me an overview of nct00000102."),
    ("NOT_FOUND", "Give me an overview of NCT99999999."),
    ("MISSING_NCT", "Give me an overview of a clinical trial."),
    ("UNSUPPORTED_COMPARISON", "Compare two clinical trials."),
    ("UNSUPPORTED_EFFICACY", "Which clinical trial is more effective?"),
    ("EMPTY_QUESTION", ""),
]

for name, question in tests:
    print(f"\n=== {name} ===")
    print("QUESTION:", repr(question))

    try:
        result = answer_trial_overview(question)

        print("STATUS:", result.status.value)
        print("ANSWER:", result.answer)
        print("LIMITATIONS:", result.limitations)
        print("SOURCES:", len(result.sources))

        if result.graph_response:
            print("GRAPH_STATUS:", result.graph_response.status.value)
            print("VALIDATION_VALID:", result.graph_response.validation.valid)

    except Exception as exc:
        print("UNEXPECTED_EXCEPTION:", type(exc).__name__, str(exc))
