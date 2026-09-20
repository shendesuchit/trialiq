from trialiq.services.answer_service import answer_trial_overview_by_nct_id

result = answer_trial_overview_by_nct_id("NCT00000102")

print("Model fields:")
for name, field in result.__class__.model_fields.items():
    print(f"- {name}: {field.annotation}")

print("\nResult:")
print(result.model_dump_json(indent=2))
