import os
import sys
import json
import random
from pathlib import Path

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from ml.pollution_investigator import investigate_event

BUNDLE_DIR = Path(backend_root) / "data/processed/evidence_bundles"
OUTPUT_DIR = Path(backend_root) / "reports/investigation/sample_results"

def run_sample(num_samples: int = 5):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not BUNDLE_DIR.exists():
        print(f"Error: {BUNDLE_DIR} does not exist.")
        return

    all_bundles = list(BUNDLE_DIR.glob("*.json"))
    if not all_bundles:
        print(f"Error: No bundles found in {BUNDLE_DIR}")
        return

    print(f"Found {len(all_bundles)} bundles. Selecting {num_samples} random samples...")

    # Use a fixed seed for reproducibility during this test
    random.seed(42)
    sample_files = random.sample(all_bundles, min(num_samples, len(all_bundles)))

    success_count = 0
    failure_count = 0

    for bundle_path in sample_files:
        print(f"\nProcessing {bundle_path.name}...")
        try:
            with open(bundle_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)

            report = investigate_event(bundle)

            out_path = OUTPUT_DIR / f"INV_{bundle_path.name}"
            with open(out_path, "w", encoding="utf-8") as out_f:
                json.dump(report, out_f, indent=2)

            print(f"  -> Success: Wrote {out_path.name}")
            success_count += 1

        except Exception as e:
            print(f"  -> FAILED: {e}")
            failure_count += 1

    print(f"\nCompleted sample run. Success: {success_count}, Failures: {failure_count}")

if __name__ == "__main__":
    run_sample(5)
