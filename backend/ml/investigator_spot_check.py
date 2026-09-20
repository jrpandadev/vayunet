import json
from pathlib import Path
import random
import sys
from datetime import datetime

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from ml.grounding_validator import GroundingValidator
from schemas.investigator_output_schema import PollutionEventInvestigationReport

BATCH_DIR = Path(backend_root) / "reports/investigation/batch"
RESULTS_DIR = Path(backend_root) / "reports/investigation/full_results"
MANIFEST_PATH = BATCH_DIR / "manifest.json"

def run_spot_check_and_report():
    if not MANIFEST_PATH.exists():
        print("FAIL: Manifest not found.")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_bundles = len(manifest)
    total_processed = sum(1 for v in manifest.values() if v["status"] != "PENDING")
    successful = sum(1 for v in manifest.values() if v["status"] == "SUCCESS")
    api_errors = sum(1 for v in manifest.values() if v["status"] == "API_ERROR")
    schema_rejections = sum(1 for v in manifest.values() if v["status"] == "SCHEMA_REJECTED")
    grounding_rejections = sum(1 for v in manifest.values() if v["status"] == "GROUNDING_REJECTED")
    final_failures = sum(1 for v in manifest.values() if v["status"] == "FAILED")
    pending = sum(1 for v in manifest.values() if v["status"] == "PENDING")

    total_attempts = sum(v["attempt_count"] for v in manifest.values())
    avg_attempts = total_attempts / total_processed if total_processed > 0 else 0
    success_rate = (successful / total_processed * 100) if total_processed > 0 else 0

    start_times = [datetime.fromisoformat(v["request_timestamp"]) for v in manifest.values() if v.get("request_timestamp")]
    end_times = [datetime.fromisoformat(v["response_timestamp"]) for v in manifest.values() if v.get("response_timestamp")]

    if start_times and end_times:
        duration = max(end_times) - min(start_times)
        duration_str = str(duration)
    else:
        duration_str = "Unknown"

    print("========================================")
    print("       FINAL BATCH REPORT               ")
    print("========================================")
    print(f"1. Total bundles: {total_bundles}")
    print(f"2. SUCCESS count: {successful}")
    print(f"3. API_ERROR count: {api_errors}")
    print(f"4. SCHEMA_REJECTED count: {schema_rejections}")
    print(f"5. GROUNDING_REJECTED count: {grounding_rejections}")
    print(f"6. FAILED count: {final_failures}")
    print(f"7. PENDING count: {pending}")
    print(f"8. Retry statistics: {total_attempts} total attempts ({avg_attempts:.2f} per bundle)")
    print(f"9. Processing duration: {duration_str}")
    print(f"10. Final success rate: {success_rate:.1f}%")
    print(f"12. Output Directory: {RESULTS_DIR}")
    print(f"13. Manifest Path: {MANIFEST_PATH}")
    print("========================================")

    print("\n--- SPOT CHECK ---")
    success_keys = [k for k, v in manifest.items() if v["status"] == "SUCCESS"]

    if not success_keys:
        print("No successful bundles to spot check.")
        return

    random.seed(42)
    sample_size = min(20, len(success_keys))
    sample_keys = random.sample(success_keys, sample_size)

    print(f"Spot checking {sample_size} random successful reports...")

    passed_validation = 0

    for key in sample_keys:
        record = manifest[key]
        report_path = Path(record["output_path"])
        bundle_path = Path(backend_root) / "data/processed/evidence_bundles" / key

        if not report_path.exists():
            print(f"  [ERROR] Report missing for {key}")
            continue

        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle_data = json.load(f)

        try:
            # 1. Schema Check
            report = PollutionEventInvestigationReport(**report_data)

            # 2. Grounding Check
            is_valid, errs = GroundingValidator.validate(report_data, bundle_data)
            if not is_valid:
                print(f"  [FAIL] {key}: Grounding rejected: {errs}")
                continue

            print(f"  [PASS] {key}: Schema valid and grounded.")
            passed_validation += 1
        except Exception as e:
            print(f"  [FAIL] {key}: Schema/Exception: {e}")

    print(f"\n11. Validation statistics: {passed_validation}/{sample_size} passed independent spot check.")

if __name__ == "__main__":
    run_spot_check_and_report()
