import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Ensure backend root is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from google import genai
from google.genai import types
from schemas.investigator_output_schema import PollutionEventInvestigationReport

# Load environment
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

INVESTIGATOR_SYSTEM_PROMPT = """You are an expert environmental data analyst investigating a severe pollution event.
Your objective is to evaluate strict factual evidence and produce a structured, non-causal analytical synthesis.

CRITICAL RULES:
1. EVIDENCE GROUNDING: The provided Evidence Bundle is your SOLE factual source. Do NOT invent measurements, sources, locations, weather conditions, satellite data, fire counts, or any other facts absent from the bundle. Every numerical value (e.g. pm2.5, wind speed, temperature) must match the bundle EXACTLY. Do not round numbers, approximate them, or invent them.
2. CAUSALITY: Do NOT use definitive causal language (e.g., "caused by", "the sole cause", "proven cause", "proves", "confirms", "established causality", "direct proof"). Use observational associations such as "associated with", "consistent with", or "correlated with". Do not treat fire detections or satellite NO2 as absolute proof of a particular emission source.
3. MISSING DATA (NWP): If a field (like NWP forecasts) is null or missing, acknowledge that it is unavailable. Do NOT attempt to reconstruct it or fabricate forecasts from future observations. Never cite a numerical forecast value if NWP is null.
4. MISSING DATA (SATELLITE/FIRMS): If FIRMS/VIIRS fire detections are null or empty, you MUST NOT mention active fires, FIRMS, VIIRS, or biomass burning detections in the supporting/contrasting evidence.
5. UNCERTAINTY: If the evidence does not establish clear support for a hypothesis, explicitly communicate the uncertainty.
6. SCHEMA: You must return ONLY valid JSON matching the required schema structure. No extra text or markdown blocks outside the JSON."""

def calculate_data_completeness(bundle: Dict[str, Any]) -> tuple:
    """Deterministically calculate data completeness based on expected fields."""
    expected_fields = [
        "pollution_dynamics.pm25.mean",
        "pollution_dynamics.pm10.mean",
        "pollution_dynamics.no2.mean",
        "meteorology.temperature.mean",
        "meteorology.wind_speed.mean",
        "meteorology.pblh.mean",
        "nwp.forecast_6h",
        "satellite.sentinel5p_no2_latest",
        "fire_activity.firms_detections_72h_50km"
    ]

    present = 0
    missing_indicators = []

    def get_nested(d, keys):
        for k in keys:
            if not isinstance(d, dict) or k not in d:
                return None
            d = d[k]
        return d

    for field in expected_fields:
        val = get_nested(bundle, field.split("."))
        if val is not None:
            present += 1
        else:
            missing_indicators.append(field)

    score = present / len(expected_fields) if expected_fields else 0.0
    return score, missing_indicators

def investigate_event(bundle: Dict[str, Any], model_name: str = "gemini-3.6-flash") -> Dict[str, Any]:
    """Runs the Gemini Investigator on a given evidence bundle."""
    global client
    if not client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment.")
        client = genai.Client(api_key=api_key)

    # 1. Deterministic Pre-processing
    completeness_score, missing_indicators = calculate_data_completeness(bundle)

    # 2. Prepare Prompt
    bundle_json = json.dumps(bundle, indent=2)
    prompt = f"""EVIDENCE BUNDLE:
{bundle_json}

DATA COMPLETENESS SCORE: {completeness_score:.2f}
MISSING FIELDS: {', '.join(missing_indicators) if missing_indicators else 'None'}

Generate the investigation report based strictly on the evidence provided above."""

    contents = [INVESTIGATOR_SYSTEM_PROMPT, prompt]

    # 3. Prepare Schema for Gemini (Remove additionalProperties)
    def remove_additional_properties(schema_dict):
        if isinstance(schema_dict, dict):
            schema_dict.pop("additionalProperties", None)
            for key, value in schema_dict.items():
                remove_additional_properties(value)
        elif isinstance(schema_dict, list):
            for item in schema_dict:
                remove_additional_properties(item)
        return schema_dict

    raw_schema = PollutionEventInvestigationReport.model_json_schema()
    clean_schema = remove_additional_properties(raw_schema)

    # 4. Invoke Gemini
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=clean_schema
            )
        )

        text = response.text.strip()

        # Strip markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        raw_json = json.loads(text)

        # 4. Strict Pydantic V2 Validation
        # Enforces schema structure and non-causal validators
        validated_report = PollutionEventInvestigationReport(**raw_json)

        # Optionally inject deterministic data quality audit fields if Gemini missed them
        # (Since Gemini was told the score, we verify it didn't drift)
        if abs(validated_report.data_quality_audit.data_completeness_score - completeness_score) > 0.05:
             validated_report.data_quality_audit.data_completeness_score = completeness_score

        for indicator in missing_indicators:
             if indicator not in validated_report.data_quality_audit.missing_indicators:
                  validated_report.data_quality_audit.missing_indicators.append(indicator)

        # Automatically populate investigation metadata if it hallucinated it
        event_id = bundle.get("event_id", "UNKNOWN")
        validated_report.event_id = event_id
        validated_report.station_id = bundle.get("station_id", "UNKNOWN")

        # Ensure investigation_id has the required format (e.g. INV_...)
        if not validated_report.investigation_id.startswith("INV_"):
             validated_report.investigation_id = f"INV_{event_id}"

        # Add generated_at
        from datetime import datetime, timezone
        validated_report.generated_at = datetime.now(timezone.utc).isoformat()

        return validated_report.model_dump()

    except Exception as e:
        # Wrap error for logging/auditing
        raise RuntimeError(f"Investigation failed: {e}")

if __name__ == "__main__":
    # Test script with dummy bundle
    dummy_bundle = {
        "event_id": "test_event_01",
        "station_id": "anand vihar",
        "event": {
            "start_time": "2023-11-01 00:00:00",
            "end_time": "2023-11-02 00:00:00",
            "duration_hours": 24,
            "severity": "SEVERE_EVENT",
            "peak_pm25": 400.5,
            "mean_pm25": 300.2,
            "min_pm25": 150.0,
            "onset_growth": 50.0
        },
        "pollution_dynamics": {
            "pm25": {"mean": 300.2, "max": 400.5}
        },
        "meteorology": {
            "temperature": {"mean": 15.0},
            "relative_humidity": {"mean": 60.0},
            "wind_speed": {"mean": 1.0},
            "wind_direction": {"mean_sin": 0.5, "mean_cos": 0.5},
            "pblh": {"mean": 300.0}
        },
        "nwp": {
            "forecast_6h": None,
            "forecast_24h": None,
            "forecast_72h": None,
            "provenance": "Missing (NWP forecasts removed due to future ground-truth leakage)"
        },
        "satellite": {},
        "fire_activity": {},
        "source_context": {}
    }
    print("Testing investigator module...")
    try:
        report = investigate_event(dummy_bundle)
        print(json.dumps(report, indent=2))
    except Exception as e:
        print(f"Error: {e}")
