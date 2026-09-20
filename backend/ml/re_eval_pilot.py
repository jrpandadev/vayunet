import json
import os
import glob
from backend.ml.grounding_validator import GroundingValidator

RESULTS_DIR = "backend/reports/investigation/gemini_pilot"
BUNDLE_DIR = "backend/data/processed/evidence_bundles"

def main():
    print("| Output | Previous grounding | New grounding | Failures | Causal Passed |")
    print("| ------ | ------------------ | ------------- | -------- | ------------- |")

    # We just want to find all JSON files in RESULTS_DIR that have successful models
    # Wait, some are 503 UNAVAILABLE. They won't have reports.
    for result_path in sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json"))):
        with open(result_path, "r") as f:
            data = json.load(f)

        if data.get("provenance", {}).get("status") == "API_ERROR":
            continue

        event_id = data.get("investigation_report", {}).get("event_id")
        if not event_id:
            continue
        bundle_path = os.path.join(BUNDLE_DIR, f"{event_id}.json")
        if not os.path.exists(bundle_path):
            continue

        with open(bundle_path, "r") as f:
            bundle_data = json.load(f)

        report_data = data.get("investigation_report", {})

        # In GroundingValidator, errors contains both causal and grounding errors
        # Let's extract them
        is_valid, errors = GroundingValidator.validate(report_data, bundle_data)

        causal_errors = [e for e in errors if "Causal Overreach" in e]
        grounding_errors = [e for e in errors if "Causal Overreach" not in e]

        causal_passed = len(causal_errors) == 0
        grounding_passed = len(grounding_errors) == 0

        new_grounding = "PASS" if grounding_passed else "FAIL"
        causal_str = "PASS" if causal_passed else "FAIL"
        failures_str = "; ".join(grounding_errors) if grounding_errors else "None"

        basename = os.path.basename(result_path)
        print(f"| {basename} | FAIL | {new_grounding} | {failures_str} | {causal_str} |")

if __name__ == '__main__':
    main()
