import requests
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "nwp"
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "nwp"
RESULTS_DIR = BASE_DIR / "ml" / "results" / "nwp"
REPORTS_DIR = BASE_DIR / "reports" / "nwp"

def create_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def fetch_pilot():
    url = "https://single-runs-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m", # We will test BLH separately if needed, but it usually is in ECMWF as 'boundary_layer_height'
        "models": "ecmwf_ifs",
        "run": "2025-09-01T00:00",
        "timezone": "UTC",
        "forecast_days": 7
    }

    # Try adding boundary_layer_height
    params_test = params.copy()
    params_test["hourly"] += ",boundary_layer_height"

    print(f"Querying Open-Meteo for run: {params['run']}...")
    resp = requests.get(url, params=params_test)

    if resp.status_code != 200:
        print(f"Failed with boundary_layer_height: {resp.status_code} {resp.text}")
        print("Falling back without boundary_layer_height...")
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            print(f"Failed again: {resp.status_code} {resp.text}")
            return

    data = resp.json()

    # Save raw json for verification
    raw_json_path = RAW_DIR / "ecmwf_ifs_pilot_2025-09-01T00_raw.json"
    with open(raw_json_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved raw JSON to {raw_json_path}")

    hourly = data.get("hourly", {})
    if not hourly:
        print("No hourly data in response!")
        return

    df = pd.DataFrame(hourly)
    df.rename(columns={"time": "valid_time"}, inplace=True)
    df["valid_time"] = pd.to_datetime(df["valid_time"])
    df["run_time"] = pd.to_datetime(params["run"], utc=True).tz_localize(None) # Match timezone naive or aware as needed

    # Calculate lead hours
    df["lead_hours"] = (df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600
    df["lead_hours"] = df["lead_hours"].astype(int)

    # Reorder columns
    cols = ["run_time", "valid_time", "lead_hours"] + [c for c in df.columns if c not in ["run_time", "valid_time", "lead_hours"]]
    df = df[cols]

    out_csv = RAW_DIR / "ecmwf_ifs_pilot_2025-09-01T00.csv"
    df.to_csv(out_csv, index=False)

    print("\n" + "="*50)
    print("PILOT DATASET SUMMARY")
    print("="*50)
    print(f"Total rows: {len(df)}")
    print(f"Run time: {df['run_time'].iloc[0]}")
    print(f"Min valid time: {df['valid_time'].min()}")
    print(f"Max valid time: {df['valid_time'].max()}")
    print(f"Max lead hours: {df['lead_hours'].max()}")

    print("\nAvailable variables:")
    vars_present = [c for c in df.columns if c not in ["run_time", "valid_time", "lead_hours"]]
    for v in vars_present:
        print(f" - {v}")

    print("\nMissing values:")
    print(df[vars_present].isnull().sum())

    print("\nChecking required lead horizons:")
    for lh in [6, 24, 72]:
        exists = not df[df["lead_hours"] == lh].empty
        print(f" - Lead {lh}h exists: {exists}")

    print(f"\nSaved CSV to: {out_csv}")

if __name__ == "__main__":
    create_dirs()
    fetch_pilot()
