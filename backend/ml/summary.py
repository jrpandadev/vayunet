import json
import os

OUTPUT_DIR = "backend/reports/investigation/gemini_50_pilot"

def main():
    with open(os.path.join(OUTPUT_DIR, "execution_summary.json"), "r") as f:
        results = json.load(f)

    status_counts = {}
    schema_passed = 0
    grounding_passed = 0
    causal_passed = 0
    grounding_failed = 0

    for r in results:
        s = r.get("status")
        status_counts[s] = status_counts.get(s, 0) + 1

        if r.get("status") in ["SUCCESS", "VALIDATION_ERROR"]:
            if r.get("schema"): schema_passed += 1
            if r.get("grounding"): grounding_passed += 1
            else: grounding_failed += 1
            if r.get("causal"): causal_passed += 1

    print("Status counts:", status_counts)
    print(f"Schema passed: {schema_passed}")
    print(f"Grounding passed: {grounding_passed}")
    print(f"Grounding failed: {grounding_failed}")
    print(f"Causal passed: {causal_passed}")

if __name__ == '__main__':
    main()
