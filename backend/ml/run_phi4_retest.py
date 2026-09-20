import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from ml.grounding_validator import GroundingValidator
from schemas.investigator_output_schema import (
    PollutionEventInvestigationReport,
    FORBIDDEN_CAUSAL_PHRASES,
)
from ml.pollution_investigator import INVESTIGATOR_SYSTEM_PROMPT, calculate_data_completeness

OLLAMA_API_URL = "http://localhost:11434/api/chat"

def get_clean_schema():
    raw_schema = PollutionEventInvestigationReport.model_json_schema()
    def remove_additional_properties(schema_dict):
        if isinstance(schema_dict, dict):
            schema_dict.pop("additionalProperties", None)
            for key, value in list(schema_dict.items()):
                remove_additional_properties(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_additional_properties(item)
        return schema_dict
    return remove_additional_properties(raw_schema)

def run_phi4_model(bundle: Dict[str, Any]) -> Dict[str, Any]:
    completeness_score, missing_indicators = calculate_data_completeness(bundle)
    bundle_json = json.dumps(bundle, indent=2)

    # Repaired Prompt Contract
    prompt = f"""### AUTHORITATIVE EVIDENCE
{bundle_json}

### METADATA
Data Completeness Score: {completeness_score:.2f}
Missing Fields: {', '.join(missing_indicators) if missing_indicators else 'None'}

### INSTRUCTIONS
- Environmental observations must ONLY be drawn from the AUTHORITATIVE EVIDENCE block.
- Do NOT use values from the METADATA block as environmental evidence in your narrative or hypothesis support.
- If a required environmental value is absent: do not infer it, do not estimate it, do not substitute metadata, and do not fabricate it."""

    payload = {
        "model": "phi4-mini:3.8b",
        "messages": [
            {"role": "system", "content": INVESTIGATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "format": get_clean_schema(),
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    start_time = time.time()
    resp = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
    latency = round(time.time() - start_time, 2)

    if resp.status_code != 200:
        raise Exception(f"Ollama API error {resp.status_code}: {resp.text}")

    result = resp.json()
    message_content = result.get("message", {}).get("content", "")

    if message_content.startswith("```"):
        message_content = message_content.split("```")[1]
        if message_content.startswith("json"):
            message_content = message_content[4:]
    message_content = message_content.strip()

    try:
        report_dict = json.loads(message_content)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse JSON output: {message_content[:200]}...")

    return {
        "report_dict": report_dict,
        "latency": latency,
        "prompt_tokens": result.get("prompt_eval_count", 0),
        "output_tokens": result.get("eval_count", 0)
    }

def main():
    bundle_names = [
        "anand vihar_202201010000.json",
        "anand vihar_202201100000.json",
        "anand vihar_202201100800.json",
        "anand vihar_202201102100.json",
        "anand vihar_202201112100.json",
        "anand vihar_202201121300.json",
        "anand vihar_202201231500.json",
        "anand vihar_202201252000.json",
        "anand vihar_202201261900.json",
        "anand vihar_202201272000.json",
    ]

    bundle_dir = backend_root / "data/processed/evidence_bundles"
    base_out_dir = backend_root / "reports/investigation/ollama_phi4_retest"
    base_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}\nEvaluating Model: phi4-mini:3.8b (Repaired Prompt)\n{'='*50}")

    model_stats = {
        "success": 0,
        "api_failure": 0,
        "schema_pass": 0,
        "grounding_pass": 0,
        "causal_pass": 0,
        "unsupported_claims": [],
        "latencies": []
    }

    for bundle_name in bundle_names:
        bundle_path = bundle_dir / bundle_name
        if not bundle_path.exists():
            print(f"ERROR: Bundle {bundle_name} not found!")
            continue

        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle_data = json.load(f)

        print(f"Processing {bundle_name}...")
        output_file = base_out_dir / f"INVESTIGATION_{bundle_name}"

        record = {
            "bundle_id": bundle_name,
            "provider": "Ollama",
            "execution_path": "local_ollama",
            "is_mock": False,
            "fallback": False,
            "model": "phi4-mini:3.8b",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            result = run_phi4_model(bundle_data)
            record["status"] = "SUCCESS"
            record["latency_sec"] = result["latency"]
            record["prompt_tokens"] = result["prompt_tokens"]
            record["output_tokens"] = result["output_tokens"]

            report_dict = result["report_dict"]
            model_stats["success"] += 1
            model_stats["latencies"].append(result["latency"])

            # 1. Schema
            try:
                _ = PollutionEventInvestigationReport(**report_dict)
                record["schema_validation"] = "PASS"
                model_stats["schema_pass"] += 1
            except Exception as e:
                record["schema_validation"] = f"FAIL: {str(e)}"
                print(f"  Schema FAIL: {e}")

            # 2. Causal Validation
            causal_violation = None
            narrative = report_dict.get("synthesis_narrative", "").lower()
            for p in FORBIDDEN_CAUSAL_PHRASES:
                if p in narrative:
                    causal_violation = p
                    break
            if not causal_violation:
                for hyp in report_dict.get("evaluated_hypotheses", []):
                    for ev in hyp.get("supporting_evidence", []) + hyp.get("contrasting_evidence", []):
                        for p in FORBIDDEN_CAUSAL_PHRASES:
                            if p in ev.lower():
                                causal_violation = p
                                break
            if causal_violation:
                record["causal_validation"] = f"FAIL: found '{causal_violation}'"
                print(f"  Causal FAIL: {causal_violation}")
            else:
                record["causal_validation"] = "PASS"
                model_stats["causal_pass"] += 1

            # 3. Grounding Validation
            g_pass, g_errs = GroundingValidator.validate(report_dict, bundle_data)
            if g_pass:
                record["grounding_validation"] = "PASS"
                model_stats["grounding_pass"] += 1
            else:
                record["grounding_validation"] = f"FAIL: {g_errs}"
                model_stats["unsupported_claims"].extend(g_errs)
                print(f"  Grounding FAIL: {g_errs}")

            record["report"] = report_dict
            print(f"  SUCCESS | {result['latency']}s")

        except Exception as e:
            print(f"  Failed: {str(e)}")
            record["status"] = "API_ERROR"
            record["error"] = str(e)
            model_stats["api_failure"] += 1

        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(record, out_f, indent=2)

    with open(base_out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(model_stats, f, indent=2)

    print("\n\nRetest complete. Please review reports.")

if __name__ == "__main__":
    main()
