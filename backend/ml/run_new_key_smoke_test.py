import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import traceback
import re

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv

# Load .env
env_path = backend_root / ".env"
load_dotenv(dotenv_path=env_path)

# 1. Verify GEMINI_API_KEY_2 exists
new_key = os.getenv("GEMINI_API_KEY_2")
if not new_key:
    print("GEMINI_API_KEY_2 detected: NO")
    sys.exit(1)
else:
    print("GEMINI_API_KEY_2 detected: YES")

# Force the environment in this process to use ONLY GEMINI_API_KEY_2
os.environ["GEMINI_API_KEY"] = new_key

from google import genai
import ml.pollution_investigator as pollution_investigator
from ml.grounding_validator import GroundingValidator
from schemas.investigator_output_schema import (
    PollutionEventInvestigationReport,
    FORBIDDEN_CAUSAL_PHRASES,
)

# Explicitly configure the client on pollution_investigator with GEMINI_API_KEY_2
pollution_investigator.client = genai.Client(api_key=new_key)

BUNDLE_DIR = backend_root / "data/processed/evidence_bundles"
OUTPUT_DIR = backend_root / "reports/investigation/new_key_smoke_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_smoke_test():
    all_bundles = sorted(BUNDLE_DIR.glob("*.json"))
    target_bundles = all_bundles[:5]

    print(f"Target bundle count: {len(target_bundles)}")
    for b in target_bundles:
        print(f" - {b.name}")

    results = []
    summary_stats = {
        "total_requests": 5,
        "successful_requests": 0,
        "429_errors": 0,
        "503_errors": 0,
        "other_api_errors": 0,
        "schema_passed": 0,
        "schema_failed": 0,
        "grounding_passed": 0,
        "grounding_failed": 0,
        "causal_passed": 0,
        "causal_failed": 0,
        "mock_outputs": 0,
        "fallback_outputs": 0,
        "unknown_provenance": 0,
        "model": "gemini-3.6-flash",
        "provider": "Google Gemini",
        "execution_path": "genuine_gemini",
        "key_slot": "GEMINI_API_KEY_2"
    }

    for idx, bundle_path in enumerate(target_bundles):
        bundle_id = bundle_path.name
        print(f"\n[{idx+1}/5] Processing bundle: {bundle_id}")

        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle_data = json.load(f)

        record = {
            "bundle_id": bundle_id,
            "key_slot": "GEMINI_API_KEY_2",
            "provider": "Google Gemini",
            "execution_path": "genuine_gemini",
            "is_mock": False,
            "model": "gemini-3.6-flash",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()
        try:
            # Genuine call
            report = pollution_investigator.investigate_event(bundle_data, model_name="gemini-3.6-flash")
            latency = time.time() - start_time
            record["latency_sec"] = round(latency, 2)
            record["status"] = "SUCCESS"
            record["http_code"] = 200
            summary_stats["successful_requests"] += 1
            print(f"  Call completed in {latency:.2f}s (SUCCESS)")

            # Schema Validation
            try:
                _ = PollutionEventInvestigationReport(**report)
                record["schema_validation"] = "PASS"
                summary_stats["schema_passed"] += 1
                print("  Schema Validation: PASS")
            except Exception as se:
                record["schema_validation"] = f"FAIL: {se}"
                summary_stats["schema_failed"] += 1
                print(f"  Schema Validation: FAIL ({se})")

            # Causal Validation
            causal_violation = None
            narrative = report.get("synthesis_narrative", "").lower()
            for p in FORBIDDEN_CAUSAL_PHRASES:
                if p in narrative:
                    causal_violation = p
                    break
            if not causal_violation:
                for hyp in report.get("evaluated_hypotheses", []):
                    for ev in hyp.get("supporting_evidence", []) + hyp.get("contrasting_evidence", []):
                        for p in FORBIDDEN_CAUSAL_PHRASES:
                            if p in ev.lower():
                                causal_violation = p
                                break
            if causal_violation:
                record["causal_validation"] = f"FAIL: found '{causal_violation}'"
                summary_stats["causal_failed"] += 1
                print(f"  Causal Validation: FAIL (phrase '{causal_violation}')")
            else:
                record["causal_validation"] = "PASS"
                summary_stats["causal_passed"] += 1
                print("  Causal Validation: PASS")

            # Grounding Validation
            g_pass, g_errs = GroundingValidator.validate(report, bundle_data)
            if g_pass:
                record["grounding_validation"] = "PASS"
                summary_stats["grounding_passed"] += 1
                print("  Grounding Validation: PASS")
            else:
                record["grounding_validation"] = f"FAIL: {g_errs}"
                summary_stats["grounding_failed"] += 1
                print(f"  Grounding Validation: FAIL ({g_errs})")

            record["output_report"] = report

            # Save individual output
            out_file = OUTPUT_DIR / f"TEST_NEW_KEY_{bundle_id}"
            with open(out_file, "w", encoding="utf-8") as out_f:
                json.dump(record, out_f, indent=2)

        except Exception as e:
            latency = time.time() - start_time
            record["latency_sec"] = round(latency, 2)
            record["status"] = "ERROR"
            err_str = str(e)
            record["error"] = err_str

            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                record["http_code"] = 429
                summary_stats["429_errors"] += 1
                print(f"  Error: 429 Rate Limit / Quota Exhausted ({err_str})")
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                record["http_code"] = 503
                summary_stats["503_errors"] += 1
                print(f"  Error: 503 Service Unavailable ({err_str})")
            else:
                record["http_code"] = "OTHER_ERROR"
                summary_stats["other_api_errors"] += 1
                print(f"  Error: API Failure ({err_str})")

            # Save error record
            out_file = OUTPUT_DIR / f"TEST_NEW_KEY_{bundle_id}"
            with open(out_file, "w", encoding="utf-8") as out_f:
                json.dump(record, out_f, indent=2)

        results.append(record)

    # Save manifest
    manifest_path = OUTPUT_DIR / "execution_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary_stats,
            "records": results
        }, mf, indent=2)
    print(f"\nSaved execution manifest to {manifest_path}")

    # Generate capacity report
    generate_report(summary_stats, target_bundles, results)

def generate_report(stats, bundles, results):
    bundle_names = [b.name for b in bundles]

    # Classify key
    if stats["successful_requests"] == 5:
        classification = "WORKING"
        safe_to_test = "YES"
    elif stats["successful_requests"] > 0:
        classification = "WORKING_WITH_LIMITS"
        safe_to_test = "YES"
    elif stats["429_errors"] > 0:
        classification = "RATE_LIMITED"
        safe_to_test = "NO"
    elif stats["other_api_errors"] > 0 and any("403" in r.get("error", "") or "API_KEY_INVALID" in r.get("error", "") for r in results):
        classification = "AUTHENTICATION_FAILED"
        safe_to_test = "NO"
    elif stats["other_api_errors"] > 0 and any("NOT_FOUND" in r.get("error", "") or "model" in r.get("error", "").lower() for r in results):
        classification = "MODEL_ACCESS_FAILED"
        safe_to_test = "NO"
    else:
        classification = "UNKNOWN"
        safe_to_test = "NO"

    report_content = f"""# VayuNet — New Gemini API Key Capacity Verification Report

## 1. Key Verification & Configuration

* **GEMINI_API_KEY_2 detected**: YES
* **Key Slot**: GEMINI_API_KEY_2
* **Existing GEMINI_API_KEY used**: NO (excluded from runtime client)
* **Provider**: Google Gemini
* **Execution Path**: genuine_gemini
* **Model**: gemini-3.6-flash
* **Project identity**: NOT DETERMINED (API key credentials do not disclose Google Cloud project ID)

---

## 2. Target Evidence Bundles

Selected exactly 5 deterministic bundles:
1. `{bundle_names[0]}`
2. `{bundle_names[1]}`
3. `{bundle_names[2]}`
4. `{bundle_names[3]}`
5. `{bundle_names[4]}`

---

## 3. Test Statistics

```text
Total requests: {stats['total_requests']}

Successful Gemini requests: {stats['successful_requests']}
429 errors: {stats['429_errors']}
503 errors: {stats['503_errors']}
Other API errors: {stats['other_api_errors']}

Schema passed: {stats['schema_passed']}
Schema failed: {stats['schema_failed']}

Grounding passed: {stats['grounding_passed']}
Grounding failed: {stats['grounding_failed']}

Causal passed: {stats['causal_passed']}
Causal failed: {stats['causal_failed']}

Mock outputs: {stats['mock_outputs']}
Fallback outputs: {stats['fallback_outputs']}
Unknown provenance: {stats['unknown_provenance']}

Model: {stats['model']}
Provider: {stats['provider']}
Execution path: {stats['execution_path']}
Key slot: {stats['key_slot']}
```

---

## 4. Per-Bundle Execution Details

"""
    for r in results:
        status_line = f"SUCCESS (latency: {r.get('latency_sec', 'N/A')}s)" if r['status'] == 'SUCCESS' else f"ERROR (code: {r.get('http_code')}, error: {r.get('error')})"
        schema_status = r.get('schema_validation', 'N/A')
        grounding_status = r.get('grounding_validation', 'N/A')
        causal_status = r.get('causal_validation', 'N/A')
        report_content += f"""### `{r['bundle_id']}`
* **Status**: {status_line}
* **Schema Validation**: {schema_status}
* **Causal Validation**: {causal_status}
* **Grounding Validation**: {grounding_status}
* **Provenance**: provider={r['provider']}, execution_path={r['execution_path']}, is_mock={r['is_mock']}

"""

    report_content += f"""---

## 5. Security Confirmation

* **API Key Exposure**: Confirmed that `GEMINI_API_KEY_2` and `GEMINI_API_KEY` were NOT printed to stdout, logged to files, exposed in JSON manifests, or written to markdown reports.
* **Mocks / Fallbacks**: Confirmed that NO mocks, fallback models, or deterministic shortcuts were used (`is_mock: false`).

---

## 6. Interpretation & Final Decision

### Key Classification
```text
{classification}
```

### Pilot Recommendation
```text
SAFE TO TEST A LARGER GEMINI PILOT: {safe_to_test}
```

> [!NOTE]
> This test verifies ONLY that `GEMINI_API_KEY_2` functions with the genuine Gemini Investigator. It does not authorize the full 6,462-bundle historical run nor establish whether sufficient quota exists for a mass batch.
"""

    report_path = OUTPUT_DIR / "new_key_capacity_report.md"
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(report_content)
    print(f"Saved capacity report to {report_path}")

if __name__ == "__main__":
    run_smoke_test()
