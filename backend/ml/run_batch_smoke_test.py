import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from google import genai
from google.genai import types
from schemas.investigator_output_schema import PollutionEventInvestigationReport
from pollution_investigator import INVESTIGATOR_SYSTEM_PROMPT, calculate_data_completeness

def remove_additional_properties(schema_dict):
    if isinstance(schema_dict, dict):
        schema_dict.pop("additionalProperties", None)
        for key, value in schema_dict.items():
            remove_additional_properties(value)
    elif isinstance(schema_dict, list):
        for item in schema_dict:
            remove_additional_properties(item)
    return schema_dict

def main():
    print("Starting Batch Smoke Test check...")
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("GEMINI_API_KEY_2")
    if not api_key:
        print("Error: GEMINI_API_KEY_2 not found.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    model_name = "gemini-3.6-flash"

    # Check Batch API availability by trying to upload a dummy file or listing batches
    print("Checking if Batch API is accessible with the current key...")
    try:
        # Just listing batch jobs should tell us if we have access or if it's disabled for Free Tier
        jobs = list(client.batches.list())
        print("Successfully accessed Batch API endpoints.")
    except Exception as e:
        print(f"Batch API check failed: {e}")
        print("This confirms Batch API is not available on the current API key/tier.")
        sys.exit(1)

    print("Batch API is accessible. Preparing smoke test of 20 bundles...")
    # Gather 20 bundles deterministically
    bundle_dir = Path(backend_root) / "data" / "processed" / "evidence_bundles"
    all_bundle_ids = [f.name for f in bundle_dir.glob("*.json")]
    all_bundle_ids.sort()
    test_bundles = all_bundle_ids[:20]

    # We will write the batch requests to a JSONL file
    batch_input_path = Path("backend/reports/investigation/gemini_batch_smoke_test/batch_input.jsonl")
    batch_input_path.parent.mkdir(parents=True, exist_ok=True)

    raw_schema = PollutionEventInvestigationReport.model_json_schema()
    clean_schema = remove_additional_properties(raw_schema)

    requests = []
    for idx, b_id in enumerate(test_bundles):
        bundle_path = bundle_dir / b_id
        with open(bundle_path, "r") as f:
            bundle = json.load(f)

        score, missing = calculate_data_completeness(bundle)
        prompt = f"""EVIDENCE BUNDLE:
{json.dumps(bundle)}

DATA COMPLETENESS SCORE: {score:.2f}
MISSING FIELDS: {', '.join(missing) if missing else 'None'}

Generate the investigation report based strictly on the evidence provided above."""

        requests.append({
            "request_id": b_id,
            "message": {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        })

    with open(batch_input_path, "w") as f:
        for r in requests:
            f.write(json.dumps(r) + "\n")

    print(f"Generated {len(requests)} batch requests.")

    print("Uploading file for batch processing...")
    try:
        # Upload the file
        uploaded_file = client.files.upload(file=str(batch_input_path), config={'mime_type': 'application/jsonl'})
        print(f"File uploaded successfully: {uploaded_file.name}")

        print("Submitting batch job...")
        job = client.batches.create(
            model=model_name,
            src=uploaded_file.name
        )
        print(f"Batch job submitted successfully! Job ID: {job.name}")

    except Exception as e:
        print(f"Failed to submit batch job: {e}")

if __name__ == "__main__":
    main()
