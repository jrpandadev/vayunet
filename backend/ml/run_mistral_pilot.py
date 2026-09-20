import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import traceback
from pydantic import ValidationError

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from ml.mistral_investigator import investigate_event_mistral
from ml.grounding_validator import GroundingValidator
from schemas.investigator_output_schema import PollutionEventInvestigationReport

BUNDLE_DIR = Path(backend_root) / "data/processed/evidence_bundles"
PILOT_DIR = Path(backend_root) / "reports/investigation/mistral_10_pilot"
PILOT_DIR.mkdir(parents=True, exist_ok=True)

def run_pilot():
    print("Starting Genuine Mistral Pilot Run...")

    # 1. Deterministic selection of 10 bundles
    all_bundles = sorted(BUNDLE_DIR.glob("*.json"))
    pilot_bundles = all_bundles[:10]

    print(f"Selected 10 bundles out of {len(all_bundles)}")
    for b in pilot_bundles:
        print(f" - {b.name}")

    for idx, bundle_path in enumerate(pilot_bundles):
        bundle_name = bundle_path.name
        print(f"\nProcessing {idx+1}/10: {bundle_name}")

        try:
            with open(bundle_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)

            # 2. Call genuine Mistral investigator
            report_dict, input_tokens, output_tokens, duration, attempt = investigate_event_mistral(bundle)
            print(f"  Mistral API call completed in {duration:.2f} seconds. (Attempts: {attempt})")

            # 3. Validations (Schema + Grounding)
            schema_passed = False
            grounding_passed = False
            validation_errors = []

            try:
                # Schema validation (already happens inside investigate_event, but just to be sure)
                _ = PollutionEventInvestigationReport(**report_dict)
                schema_passed = True
                print("  Schema Validation: PASS")
            except Exception as e:
                schema_passed = False
                validation_errors.append(f"Schema: {e}")
                print(f"  Schema Validation Error: {e}")

            try:
                # Grounding and Causal validation
                is_valid, errs = GroundingValidator.validate(report_dict, bundle)
                if not is_valid:
                    grounding_passed = False
                    validation_errors.append(f"Grounding: {errs}")
                    print(f"  Grounding failed: {errs}")
                else:
                    grounding_passed = True
                    print("  Grounding Validation: PASS")
            except Exception as e:
                grounding_passed = False
                validation_errors.append(f"Grounding exception: {e}")
                print(f"  Grounding Validation Error: {e}")

            status = "SUCCESS" if (schema_passed and grounding_passed) else "VALIDATION_FAILED"
            error_msg = "; ".join(validation_errors) if validation_errors else None

        except Exception as e:
            err_str = str(e)
            print(f"  API or Generation Error: {err_str}")
            status = "API_ERROR"
            error_msg = err_str
            report_dict = {}
            schema_passed = False
            grounding_passed = False
            input_tokens = 0
            output_tokens = 0
            attempt = 1
            duration = 0

        # 4. Save with provenance wrapper
        if status in ["SUCCESS", "VALIDATION_FAILED"] and report_dict:
            wrapper = {
                "provenance": {
                    "provider": "Mistral",
                    "model": "mistral-large-latest",
                    "execution_path": "genuine_mistral",
                    "is_mock": False,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "attempt": attempt,
                    "status": status,
                    "error": error_msg,
                    "schema_passed": schema_passed,
                    "grounding_passed": grounding_passed,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_seconds": duration
                },
                "investigation_report": report_dict
            }

            out_path = PILOT_DIR / f"PILOT_MISTRAL_{bundle_name}"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(wrapper, f, indent=2)
            print(f"  Saved result to {out_path.name} with status {status}")
        else:
            # We save API errors as well for the audit
            wrapper = {
                "provenance": {
                    "provider": "Mistral",
                    "model": "mistral-large-latest",
                    "execution_path": "genuine_mistral",
                    "is_mock": False,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "attempt": attempt,
                    "status": status,
                    "error": error_msg,
                    "schema_passed": False,
                    "grounding_passed": False,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_seconds": duration
                }
            }
            out_path = PILOT_DIR / f"PILOT_MISTRAL_{bundle_name}"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(wrapper, f, indent=2)
            print(f"  Saved API error record to {out_path.name}")

if __name__ == "__main__":
    run_pilot()
