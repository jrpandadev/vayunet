import json
import jsonschema

schema_path = r"c:\Users\jrpan\.gemini\antigravity-ide\scratch\vayunet\backend\schemas\evidence_bundle_input_schema.json"
with open(schema_path) as f:
    schema = json.load(f)

# Base valid bundle
valid_bundle = {
  "event_id": "anand vihar_202201010000",
  "station_id": "anand vihar",
  "event": {
    "start_time": "2022-01-01 00:00:00",
    "end_time": "2022-01-06 08:00:00",
    "duration_hours": 129,
    "severity": "SEVERE_EVENT",
    "peak_pm25": 818.75,
    "mean_pm25": 354.33,
    "min_pm25": 88.67,
    "onset_growth": 304.5
  },
  "pollution_dynamics": {
    "pm25": {"mean": 354.33, "max": 818.75},
    "pm10": {"mean": 550.5, "max": 950.0},
    "no2": {"mean": 87.46, "max": 177.78}
  },
  "meteorology": {
    "temperature": {"mean": 12.7},
    "relative_humidity": {"mean": 77.8},
    "wind_speed": {"mean": 8.57},
    "wind_direction": {"mean_sin": -0.32, "mean_cos": -0.52},
    "pblh": {"mean": 227.9}
  },
  "nwp": {
    "forecast_6h": None,
    "forecast_24h": None,
    "forecast_72h": None,
    "provenance": "Missing (NWP forecasts removed due to future ground-truth leakage)"
  },
  "satellite": {
    "sentinel5p_no2_latest": None,
    "sentinel5p_no2_age_hours": None
  },
  "fire_activity": {
    "firms_detections_72h_50km": 28
  },
  "source_context": {
    "owbeii_waste_burned": 145000000.0
  }
}

print("Running negative tests...")

# 1. Valid bundle with null NWP
try:
    jsonschema.validate(instance=valid_bundle, schema=schema)
    print("PASS: Valid bundle with nwp.forecast_6h = null passes")
except jsonschema.exceptions.ValidationError as e:
    print(f"FAIL: Valid bundle threw error: {e}")

# 2. Add future targets (should fail due to extra=forbid)
invalid_bundle = valid_bundle.copy()
invalid_bundle["target_pm25_6h"] = 150.0
try:
    jsonschema.validate(instance=invalid_bundle, schema=schema)
    print("FAIL: Bundle with target_pm25_6h should have been rejected")
except jsonschema.exceptions.ValidationError:
    print("PASS: Bundle with target_pm25_6h was correctly rejected")

invalid_bundle2 = valid_bundle.copy()
invalid_bundle2["target_pm25_24h"] = 150.0
try:
    jsonschema.validate(instance=invalid_bundle2, schema=schema)
    print("FAIL: Bundle with target_pm25_24h should have been rejected")
except jsonschema.exceptions.ValidationError:
    print("PASS: Bundle with target_pm25_24h was correctly rejected")
