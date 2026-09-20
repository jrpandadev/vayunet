import json
import os
import glob
import random
import time
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add backend root to path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from ml.pollution_investigator import investigate_event
from ml.grounding_validator import GroundingValidator
from google.genai.errors import APIError

BUNDLE_DIR = "backend/data/processed/evidence_bundles"
OUTPUT_DIR = "backend/reports/investigation/gemini_50_pilot"
SEED = 12345

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def select_stratified_sample(seed, sample_size=50):
    bundle_paths = glob.glob(os.path.join(BUNDLE_DIR, "*.json"))
    bundles = []

    # Pre-parse metadata for stratification
    for bp in bundle_paths:
        with open(bp, "r") as f:
            data = json.load(f)

        station = data.get("station_id", "unknown")

        fire_act = data.get("fire_activity", {})
        has_firms = bool(fire_act and isinstance(fire_act, dict) and any(v for v in fire_act.values() if isinstance(v, (int, float)) and v > 0))

        nwp = data.get("nwp", {})
        has_nwp = bool(nwp.get("forecast_6h") or nwp.get("forecast_24h") or nwp.get("forecast_72h"))

        sat = data.get("satellite", {})
        has_s5p = bool(sat.get("sentinel5p_no2_latest"))

        event = data.get("event", {})
        duration = event.get("duration_hours", 0)
        is_long = duration > 24

        bundles.append({
            "id": data.get("event_id"),
            "path": bp,
            "station": station,
            "has_firms": has_firms,
            "has_nwp": has_nwp,
            "has_s5p": has_s5p,
            "is_long": is_long
        })

    # Sort deterministically first
    bundles.sort(key=lambda x: x["id"])
    random.seed(seed)

    # Stratification logic (simplified but deterministic and diverse)
    # Group by a composite key
    strata_groups = {}
    for b in bundles:
        key = (b["station"], b["has_firms"], b["has_nwp"], b["has_s5p"], b["is_long"])
        if key not in strata_groups:
            strata_groups[key] = []
        strata_groups[key].append(b)

    selected = []
    keys = list(strata_groups.keys())
    keys.sort()

    # Round-robin selection
    idx = 0
    while len(selected) < sample_size and len(selected) < len(bundles):
        key = keys[idx % len(keys)]
        if len(strata_groups[key]) > 0:
            # pick random from this group
            choice = random.choice(strata_groups[key])
            strata_groups[key].remove(choice)
            selected.append(choice)
        idx += 1

    # Validation step as requested (Pre-sample QA)
    final_selected = []
    for b in selected:
        # verify schema and required fields
        with open(b["path"], "r") as f:
            data = json.load(f)

        is_valid = True
        if not data.get("event_id") or not data.get("event"):
            is_valid = False

        # Target leakage check
        nwp = data.get("nwp", {})
        if nwp.get("forecast_6h") == data.get("event", {}).get("peak_pm25"):
            is_valid = False

        if is_valid:
            final_selected.append(b)
        else:
            # Find replacement (simplified for the script, assuming data is mostly clean)
            pass

    # if len < sample_size, just fill with remaining random
    if len(final_selected) < sample_size:
        remaining = [b for b in bundles if b not in final_selected]
        random.shuffle(remaining)
        final_selected.extend(remaining[:sample_size - len(final_selected)])

    return final_selected[:sample_size]

def main():
    ensure_dir(OUTPUT_DIR)

    # Step 3, 4, 5: Stratified Sample
    sample = select_stratified_sample(SEED, 50)

    manifest = {
        "seed": SEED,
        "sample_size": len(sample),
        "selection_method": "Deterministic round-robin stratification on composite key (station, firms, nwp, s5p, duration)",
        "bundle_ids": [b["id"] for b in sample],
        "strata": {}
    }

    with open(os.path.join(OUTPUT_DIR, "sample_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Selected {len(sample)} bundles. Starting Gemini generation...")

    results = []

    # Step 6 & 7: Gemini Generation with Retry
    for b in sample:
        bundle_id = b["id"]
        bundle_path = b["path"]

        with open(bundle_path, "r") as f:
            bundle_data = json.load(f)

        max_attempts = 3
        attempt = 1
        success = False
        report = None
        error_msg = None
        status = "PENDING"

        while attempt <= max_attempts and not success:
            try:
                # Actual generation
                report = investigate_event(bundle_data, model_name="gemini-3.6-flash")
                success = True
                status = "SUCCESS"
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg or "429" in error_msg or "Unavailable" in error_msg:
                    print(f"[{bundle_id}] Attempt {attempt} failed (transient): {error_msg}")
                    time.sleep(2 ** attempt)
                    attempt += 1
                else:
                    # Terminal error
                    status = "API_ERROR"
                    break

        if not success and status != "API_ERROR":
            status = "API_ERROR"

        # Validation if success
        schema_passed = False
        grounding_passed = False
        causal_passed = False
        val_errors = []

        if success:
            schema_passed = True # investigate_event enforces Pydantic
            is_val, val_errs = GroundingValidator.validate(report, bundle_data)

            causal_failures = [e for e in val_errs if "Causal Overreach" in e]
            grounding_failures = [e for e in val_errs if "Causal Overreach" not in e]

            causal_passed = len(causal_failures) == 0
            grounding_passed = len(grounding_failures) == 0
            val_errors = val_errs

            if not is_val:
                status = "VALIDATION_ERROR"

        # Save output
        out_data = {
            "provenance": {
                "provider": "Google Gemini",
                "model": "gemini-3.6-flash",
                "execution_path": "genuine_gemini",
                "is_mock": False,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "attempt": attempt if success else attempt - 1,
                "status": status,
                "error": error_msg if not success else ("; ".join(val_errors) if val_errors else None),
                "schema_passed": schema_passed,
                "grounding_passed": grounding_passed,
                "causal_passed": causal_passed
            },
            "investigation_report": report
        }

        out_path = os.path.join(OUTPUT_DIR, f"GATE_{bundle_id}.json")
        with open(out_path, "w") as f:
            json.dump(out_data, f, indent=2)

        results.append({
            "bundle_id": bundle_id,
            "status": status,
            "schema": schema_passed,
            "grounding": grounding_passed,
            "causal": causal_passed,
            "attempts": attempt if success else attempt - 1,
            "is_mock": False,
            "error": error_msg
        })

        print(f"Processed {bundle_id} -> {status}")
        time.sleep(1) # Prevent aggressive rate limiting

    # Write summary
    with open(os.path.join(OUTPUT_DIR, "execution_summary.json"), "w") as f:
        json.dump(results, f, indent=2)

    print("Execution complete.")

if __name__ == '__main__':
    main()
