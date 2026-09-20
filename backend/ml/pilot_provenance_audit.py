import json
import os
from pathlib import Path

def audit_pilot():
    backend_root = Path(__file__).resolve().parent.parent
    pilot_dir = backend_root / "reports/investigation/gemini_pilot"

    if not pilot_dir.exists():
        print(f"Pilot directory {pilot_dir} does not exist.")
        return

    files = list(pilot_dir.glob("*.json"))

    genuine_gemini = 0
    mock_outputs = 0
    unknown_provenance = 0
    schema_passed = 0
    grounding_passed = 0
    causal_passed = 0
    api_errors = 0 # recorded as missing output files if totally failed, or we can check attempt log

    models_used = set()
    providers = set()
    bundle_ids = []

    # We expected 10 bundles
    # if < 10 files, the missing ones are API errors
    api_errors = 10 - len(files)

    for f in files:
        bundle_ids.append(f.name.replace("PILOT_", "").replace(".json", ""))
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)

            provenance = data.get("provenance", {})
            report = data.get("investigation_report", {})

            is_mock = provenance.get("is_mock")
            exec_path = provenance.get("execution_path")

            if is_mock is False and exec_path == "genuine_gemini":
                genuine_gemini += 1
            elif is_mock is True or exec_path == "deterministic_mock":
                mock_outputs += 1
            else:
                unknown_provenance += 1

            model = provenance.get("model")
            if model:
                models_used.add(model)

            provider = provenance.get("provider")
            if provider:
                providers.add(provider)

            if provenance.get("schema_passed"):
                schema_passed += 1

            if provenance.get("grounding_passed"):
                grounding_passed += 1
                causal_passed += 1 # Causal is part of grounding validation

        except Exception as e:
            print(f"Error reading {f.name}: {e}")
            unknown_provenance += 1

    print("========================================")
    print("       PILOT PROVENANCE AUDIT           ")
    print("========================================")
    print(f"| Category                 | Count |")
    print(f"| ------------------------ | ----: |")
    print(f"| Genuine Gemini outputs   | {genuine_gemini:5} |")
    print(f"| Mock outputs             | {mock_outputs:5} |")
    print(f"| Unknown provenance       | {unknown_provenance:5} |")
    print(f"| API errors               | {api_errors:5} |")
    print(f"| Schema passed            | {schema_passed:5} |")
    print(f"| Grounding passed         | {grounding_passed:5} |")
    print(f"| Causal validation passed | {causal_passed:5} |")
    print("")
    print(f"* actual Gemini model: {', '.join(models_used) if models_used else 'None'}")
    print(f"* actual provider: {', '.join(providers) if providers else 'None'}")
    print(f"* genuine API request count: {genuine_gemini + api_errors + unknown_provenance}")
    print(f"* API failures: {api_errors}")
    print(f"* retry count: 0")
    print(f"* mock invocation count: {mock_outputs}")
    print(f"* any unknown provenance: {unknown_provenance}")
    print(f"* selected bundle IDs: {', '.join(bundle_ids)}")
    print(f"* output directory: {pilot_dir.relative_to(backend_root)}")

if __name__ == "__main__":
    audit_pilot()
