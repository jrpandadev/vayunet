import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "nwp" / "2025" / "09"

API_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs"
LATITUDE = 28.6139
LONGITUDE = 77.2090
TIMEZONE = "UTC"
FORECAST_DAYS = 7  # 168 hours, well above the required 72 hours

VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "boundary_layer_height",
]

CYCLES = ["00", "06", "12", "18"]
START_DATE = datetime(2025, 9, 1)
END_DATE = datetime(2025, 9, 30)

REQUEST_DELAY_SEC = 0.25

# Retry configuration
MAX_RETRIES = 4
BACKOFF_TIMES = [5, 15, 30, 60]  # Exponential backoff in seconds
REQUEST_TIMEOUT = 30  # Reasonable timeout

def generate_run_timestamps():
    """Generates the 120 expected run timestamps for September 2025."""
    runs = []
    curr = START_DATE
    while curr <= END_DATE:
        for cycle in CYCLES:
            dt_str = f"{curr.strftime('%Y-%m-%d')}T{cycle}:00"
            runs.append(dt_str)
        curr += timedelta(days=1)
    return runs


def validate_dataframe(df, run_time_str):
    """
    Validates that:
    1. valid_time is strictly monotonically increasing.
    2. lead_hours == (valid_time - run_time) in hours exactly.
    """
    if not df["valid_time"].is_monotonic_increasing:
        raise ValueError("valid_time is not monotonically increasing.")

    expected_lead = (df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600
    if not (expected_lead.astype(int) == df["lead_hours"]).all():
        raise ValueError("lead_hours does not match (valid_time - run_time) exactly.")


def download_run(run_time_str, overwrite=False):
    """
    Downloads a single NWP model run and saves raw JSON and processed CSV.
    Returns: status ('successful', 'unavailable', 'failed', 'skipped_existing'), dataframe or None, message
    """
    tag = run_time_str.replace(":", "")
    run_cycle_tag = run_time_str[:13]
    csv_path = OUTPUT_DIR / f"ecmwf_ifs_{run_cycle_tag}.csv"
    json_path = OUTPUT_DIR / f"ecmwf_ifs_{run_cycle_tag}_raw.json"

    # Check if already downloaded
    if not overwrite and csv_path.exists() and json_path.exists():
        try:
            df = pd.read_csv(csv_path)
            df["valid_time"] = pd.to_datetime(df["valid_time"])
            df["run_time"] = pd.to_datetime(df["run_time"])
            validate_dataframe(df, run_time_str)
            return "skipped_existing", df, f"Loaded existing {csv_path.name}"
        except Exception as e:
            print(f"[{run_time_str}] Existing file invalid ({e}), re-downloading...")

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": ",".join(VARIABLES),
        "models": MODEL,
        "run": run_time_str,
        "timezone": TIMEZONE,
        "forecast_days": FORECAST_DAYS,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    hourly = data.get("hourly", {})
                    if not hourly:
                        return "failed", None, "Response 200 OK but hourly field is missing or empty."

                    df = pd.DataFrame(hourly)
                    df.rename(columns={"time": "valid_time"}, inplace=True)
                    df["valid_time"] = pd.to_datetime(df["valid_time"])
                    df["run_time"] = pd.to_datetime(run_time_str, utc=True).tz_localize(None)
                    df["lead_hours"] = ((df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600).astype(int)

                    # Reorder columns
                    cols = ["run_time", "valid_time", "lead_hours"] + [
                        c for c in df.columns if c not in ["run_time", "valid_time", "lead_hours"]
                    ]
                    df = df[cols]

                    # Validation
                    validate_dataframe(df, run_time_str)

                    # Save raw JSON
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

                    # Save CSV
                    df.to_csv(csv_path, index=False)

                    return "successful", df, f"Saved {len(df)} rows to {csv_path.name}"
                except Exception as e:
                    return "failed", None, f"Processing/validation error: {e}"

            elif resp.status_code == 400:
                err_msg = resp.text
                if "not available" in err_msg.lower():
                    return "unavailable", None, f"HTTP 400: {err_msg.strip()}"
                else:
                    return "failed", None, f"HTTP 400: {err_msg.strip()}"

            elif resp.status_code >= 500:
                # Transient server error, we will retry
                err_msg = f"HTTP {resp.status_code}: {resp.text.strip()}"
            else:
                return "failed", None, f"HTTP {resp.status_code}: {resp.text.strip()}"

        except requests.RequestException as e:
            err_msg = f"Network error: {e}"

        # If we got here, it's a transient error or 5xx, we should retry if we have attempts left
        if attempt < MAX_RETRIES:
            sleep_time = BACKOFF_TIMES[attempt]
            print(f"[{run_time_str}] Attempt {attempt+1}/{MAX_RETRIES+1} failed: {err_msg}. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
        else:
            return "failed", None, f"Failed after {MAX_RETRIES+1} attempts. Last error: {err_msg}"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    runs = generate_run_timestamps()
    total_requested = len(runs)

    print("=" * 70)
    print("ECMWF IFS SEPTEMBER 2025 INGESTION (WITH RETRY)")
    print("=" * 70)
    print(f"Total runs requested: {total_requested} (4 cycles/day x 30 days)")
    print(f"Output directory:     {OUTPUT_DIR}")
    print(f"Variables:            {', '.join(VARIABLES)}")
    print("=" * 70)

    successful_runs = []
    unavailable_runs = []
    failed_runs = []
    skipped_count = 0
    all_dfs = []

    for idx, run_ts in enumerate(runs, 1):
        status, df, msg = download_run(run_ts)
        print(f"[{idx:03d}/{total_requested}] {run_ts} -> {status.upper()}: {msg}")

        if status == "skipped_existing":
            successful_runs.append(run_ts)
            skipped_count += 1
            if df is not None:
                all_dfs.append(df)
        elif status == "successful":
            successful_runs.append(run_ts)
            if df is not None:
                all_dfs.append(df)
            time.sleep(REQUEST_DELAY_SEC) # Delay only after actual API requests
        elif status == "unavailable":
            unavailable_runs.append((run_ts, msg))
            time.sleep(REQUEST_DELAY_SEC)
        else:
            failed_runs.append((run_ts, msg))
            time.sleep(REQUEST_DELAY_SEC)

    # Ingestion Report
    print("\n" + "=" * 70)
    print("FINAL INGESTION REPORT: ECMWF IFS (SEPTEMBER 2025)")
    print("=" * 70)
    print(f"1. originally requested runs = {total_requested}")
    print(f"2. successful runs now       = {len(successful_runs)}")
    print(f"3. remaining failed runs     = {len(failed_runs)}")
    print(f"4. unavailable runs          = {len(unavailable_runs)}")

    if unavailable_runs:
        print(f"\nUnavailable runs summary ({len(unavailable_runs)}):")
        for r, m in unavailable_runs[:10]:
            print(f"  - {r}: {m}")
        if len(unavailable_runs) > 10:
            print(f"  ... and {len(unavailable_runs) - 10} more.")

    if failed_runs:
        print(f"\nFailed runs summary ({len(failed_runs)}):")
        for r, m in failed_runs:
            print(f"  - {r}: {m}")

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        print(f"5. total CSV rows            = {len(combined)}")
        print(f"6. number of unique run_time = {combined['run_time'].nunique()}")
        print("\n" + "-" * 50)
        print("AGGREGATE DATA SUMMARY")
        print("-" * 50)
        print(f"Minimum run_time:      {combined['run_time'].min()}")
        print(f"Maximum run_time:      {combined['run_time'].max()}")
        print(f"Minimum valid_time:    {combined['valid_time'].min()}")
        print(f"Maximum valid_time:    {combined['valid_time'].max()}")
        print(f"Maximum lead_hours:    {combined['lead_hours'].max()}")

        print("\nChecking lead horizons presence:")
        for lh in [6, 24, 72]:
            has_lh = (combined["lead_hours"] == lh).any()
            count_lh = (combined["lead_hours"] == lh).sum()
            print(f"  - Lead {lh:2d}h exists: {has_lh} (present in {count_lh} runs)")

        print("\nMissing values per variable across all successful runs:")
        for var in VARIABLES:
            missing_cnt = combined[var].isnull().sum() if var in combined.columns else "N/A"
            print(f"  - {var:25s}: {missing_cnt}")
    else:
        print(f"5. total CSV rows            = 0")
        print(f"6. number of unique run_time = 0")
        print("\nNo successful runs to aggregate.")

    print("=" * 70)


if __name__ == "__main__":
    main()
