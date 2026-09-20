import sys
import json
from pathlib import Path
from typing import Dict, Any

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

BUNDLE_DIR = Path(backend_root) / "data/processed/evidence_bundles"

def run_preflight():
    if not BUNDLE_DIR.exists():
        print(f"FAIL: Directory {BUNDLE_DIR} does not exist.")
        sys.exit(1)

    bundles = list(BUNDLE_DIR.glob("*.json"))
    total_bundles = len(bundles)
    print(f"Total bundles found: {total_bundles}")

    if total_bundles != 6462:
        print(f"FAIL: Expected 6462 bundles, found {total_bundles}.")
        sys.exit(1)

    malformed = []
    missing_event_id = []
    leakage_violations = []

    for b in bundles:
        try:
            with open(b, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "event_id" not in data or not data["event_id"]:
                missing_event_id.append(b.name)

            nwp = data.get("nwp", {})
            if nwp.get("forecast_6h") is not None or \
               nwp.get("forecast_24h") is not None or \
               nwp.get("forecast_72h") is not None:
                leakage_violations.append(b.name)

        except json.JSONDecodeError:
            malformed.append(b.name)
        except Exception as e:
            malformed.append(f"{b.name} ({e})")

    if malformed:
        print(f"FAIL: {len(malformed)} bundles are malformed (e.g. invalid JSON).")

    if missing_event_id:
        print(f"FAIL: {len(missing_event_id)} bundles are missing 'event_id'.")

    if leakage_violations:
        print(f"FAIL: {len(leakage_violations)} bundles contain non-null NWP forecasts (Leakage!).")

    if malformed or missing_event_id or leakage_violations:
        print("\nPreflight Audit FAILED.")
        sys.exit(1)

    print("\nPreflight Audit PASSED.")
    print("- All 6,462 bundles are readable.")
    print("- 'event_id' present in all bundles.")
    print("- Zero NWP target leakage confirmed.")

if __name__ == "__main__":
    run_preflight()
