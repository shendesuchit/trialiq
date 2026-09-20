import json
from pathlib import Path

from trialiq.services.answer_service import answer_trial_overview_by_nct_id


def find_nct_ids(value):
    ids = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"nct_id", "nctid"} and isinstance(item, str):
                if item.upper().startswith("NCT"):
                    ids.append(item)
            else:
                ids.extend(find_nct_ids(item))

    elif isinstance(value, list):
        for item in value:
            ids.extend(find_nct_ids(item))

    return ids


artifact_path = Path("data/extracted/aact_100_trials.json")
data = json.loads(artifact_path.read_text(encoding="utf-8"))

nct_ids = list(dict.fromkeys(find_nct_ids(data)))

if not nct_ids:
    raise AssertionError("No NCT IDs found in extracted artifact")

nct_id = nct_ids[0]
print(f"Testing NCT ID: {nct_id}")

result = answer_trial_overview_by_nct_id(nct_id)

print(f"Status: {result.status}")
print(f"Answer present: {bool(result.answer)}")
print(f"Evidence sources: {len(result.sources)}")

assert result.status.value in {"GROUNDED", "INSUFFICIENT_EVIDENCE", "ERROR"}, f"Unexpected status: {result.status}"

assert result.status != "EXECUTION_ERROR", result

if result.status == "SUCCESS":
    assert result.answer
    assert result.sources
    print("PASS: Evidence-grounded answer returned")

print("PASS: Read-only end-to-end answer validation")


