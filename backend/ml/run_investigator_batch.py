import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import traceback
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from ml.fast_investigator import investigate_event
from ml.grounding_validator import GroundingValidator

BUNDLE_DIR = Path(backend_root) / "data/processed/evidence_bundles"
BATCH_DIR = Path(backend_root) / "reports/investigation/batch"
RESULTS_DIR = Path(backend_root) / "reports/investigation/full_results"
MANIFEST_PATH = BATCH_DIR / "manifest.json"

BATCH_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

class APIError(Exception):
    pass

class SchemaRejectError(Exception):
    pass

class GroundingRejectError(Exception):
    pass

# Tenacity retry logic for API/Transient errors ONLY.
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(APIError),
    reraise=True
)
def process_single_bundle_with_retries(bundle_path: Path):
    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    try:
        report = investigate_event(bundle)
        is_valid, errs = GroundingValidator.validate(report, bundle)
        if not is_valid:
            raise GroundingRejectError(f"Grounding Failed: {errs}")
        return report, bundle
    except ValidationError as e:
        # Schema or grounding validation failed
        raise SchemaRejectError(f"Pydantic Validation Failed: {str(e)}")
    except Exception as e:
        err_str = str(e)
        if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "quota" in err_str.lower():
            raise APIError(err_str)
        # For other unexpected exceptions, we still wrap as API error to attempt retry, or could fail fast.
        # But for this batch we'll assume unknown exceptions are API related unless they are ValidationErrors.
        raise APIError(f"Unexpected error during generation: {err_str}")

def load_manifest():
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_manifest(manifest):
    # Atomic write
    temp_path = MANIFEST_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    temp_path.replace(MANIFEST_PATH)

def run_batch():
    bundles = list(BUNDLE_DIR.glob("*.json"))
    manifest = load_manifest()

    # Initialize un-tracked bundles
    for b in bundles:
        key = b.name
        if key not in manifest:
            manifest[key] = {
                "event_id": key.replace(".json", ""), # Approximate, will update on read
                "filename": key,
                "status": "PENDING",
                "attempt_count": 0,
                "model": "gemini-3.6-flash",
                "request_timestamp": None,
                "response_timestamp": None,
                "failure_reason": None,
                "output_path": None
            }

    # Filter bundles that need processing
    to_process = [
        b for b in bundles
        if manifest[b.name]["status"] in ("PENDING", "API_ERROR", "RETRYING", "PROCESSING")
        and manifest[b.name]["attempt_count"] < 5
    ]

    print(f"Total bundles: {len(bundles)}")
    print(f"To process: {len(to_process)}")

    consecutive_api_errors = 0
    total_processed_this_run = 0
    schema_rejects = sum(1 for m in manifest.values() if m["status"] == "SCHEMA_REJECTED")
    grounding_rejects = sum(1 for m in manifest.values() if m["status"] == "GROUNDING_REJECTED")
    total_attempts = sum(1 for m in manifest.values() if m["status"] != "PENDING")

    pbar = tqdm(total=len(to_process), desc="Investigating")
    manifest_lock = threading.Lock()
    stop_event = threading.Event()

    def process_bundle(b):
        nonlocal consecutive_api_errors, schema_rejects, grounding_rejects, total_processed_this_run, total_attempts

        if stop_event.is_set():
            return

        key = b.name

        with manifest_lock:
            record = manifest[key]
            # Read exact event_id if not set correctly
            if record["event_id"] == key.replace(".json", ""):
                try:
                    with open(b, "r", encoding="utf-8") as f:
                        event_id = json.load(f).get("event_id", key)
                        record["event_id"] = event_id
                except:
                    pass

            record["status"] = "RETRYING" if record["attempt_count"] > 0 else "PROCESSING"
            record["request_timestamp"] = datetime.now(timezone.utc).isoformat()
            record["attempt_count"] += 1

        try:
            report, _ = process_single_bundle_with_retries(b)

            # Success
            out_path = RESULTS_DIR / f"INV_{key}"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            with manifest_lock:
                record["status"] = "SUCCESS"
                record["output_path"] = str(out_path)
                record["response_timestamp"] = datetime.now(timezone.utc).isoformat()
                record["failure_reason"] = None
                consecutive_api_errors = 0 # Reset

        except SchemaRejectError as e:
            with manifest_lock:
                record["status"] = "SCHEMA_REJECTED"
                record["response_timestamp"] = datetime.now(timezone.utc).isoformat()
                record["failure_reason"] = str(e)
                schema_rejects += 1
                consecutive_api_errors = 0

        except GroundingRejectError as e:
            with manifest_lock:
                record["status"] = "GROUNDING_REJECTED"
                record["response_timestamp"] = datetime.now(timezone.utc).isoformat()
                record["failure_reason"] = str(e)
                grounding_rejects += 1
                consecutive_api_errors = 0

        except APIError as e:
            with manifest_lock:
                record["status"] = "API_ERROR"
                record["response_timestamp"] = datetime.now(timezone.utc).isoformat()
                record["failure_reason"] = str(e)
                consecutive_api_errors += 1

        except Exception as e:
            with manifest_lock:
                record["status"] = "FAILED"
                record["response_timestamp"] = datetime.now(timezone.utc).isoformat()
                record["failure_reason"] = f"Unknown: {str(e)}"
                consecutive_api_errors += 1

        with manifest_lock:
            total_processed_this_run += 1
            total_attempts += 1

            if total_processed_this_run % 1000 == 0:
                save_manifest(manifest)


            # Check Stop Conditions
            if consecutive_api_errors >= 20:
                print(f"\n[ABORT] Systemic API failure detected ({consecutive_api_errors} consecutive). Stopping.")
                stop_event.set()

            if total_attempts > 100: # Wait for a reasonable sample size before checking reject rate
                reject_rate = (schema_rejects + grounding_rejects) / total_attempts
                if reject_rate > 0.05:
                    print(f"\n[ABORT] Schema/Grounding rejection rate too high ({reject_rate*100:.1f}%). Stopping.")
                    stop_event.set()

        pbar.update(1)

    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(process_bundle, b) for b in to_process]
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        stop_event.set()
    finally:
        pbar.close()
        with manifest_lock:
            save_manifest(manifest)
        print("\nBatch runner exited.")

if __name__ == "__main__":
    run_batch()
