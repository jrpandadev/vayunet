import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
BASE_OUTPUT_DIR = BASE_DIR / "data" / "raw" / "nwp"
MANIFEST_FILE = BASE_DIR / "reports" / "nwp" / "historical_ingestion_manifest.csv"

API_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs"
REQ_LATITUDE = 28.6139
REQ_LONGITUDE = 77.2090
TIMEZONE = "UTC"
FORECAST_DAYS = 7  # 168 hours

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
START_DATE = datetime(2024, 3, 14)
END_DATE = datetime(2026, 8, 31)

REQUEST_DELAY_SEC = 0.25
MAX_RETRIES = 4
BACKOFF_TIMES = [5, 15, 30, 60]
REQUEST_TIMEOUT = 30

def generate_run_timestamps():
    runs = []
    curr = START_DATE
    while curr <= END_DATE:
        for cycle in CYCLES:
            dt_str = f"{curr.strftime('%Y-%m-%d')}T{cycle}:00"
            runs.append(dt_str)
        curr += timedelta(days=1)
    return runs

def validate_dataframe(df, run_time_str):
    if len(df) != 168:
        raise ValueError(f"Expected 168 rows, got {len(df)}")

    if not df["valid_time"].is_monotonic_increasing:
        raise ValueError("valid_time is not monotonically increasing.")

    expected_lead = (df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600
    if not (expected_lead.astype(int) == df["lead_hours"]).all():
        raise ValueError("lead_hours does not match (valid_time - run_time) exactly.")

    if set(df["lead_hours"].unique()) != set(range(168)):
        raise ValueError("lead_hours does not cover 0 through 167 exactly.")

    if df.duplicated(subset=["run_time", "valid_time"]).any():
        raise ValueError("Duplicate run_time/valid_time pairs found.")

    if not (df["valid_time"] >= df["run_time"]).all():
        raise ValueError("valid_time occurs before run_time.")

    for var in VARIABLES:
        if var not in df.columns:
            raise ValueError(f"Required variable '{var}' missing.")

def download_run(run_time_str, overwrite=False):
    tag = run_time_str.replace(":", "")
    run_cycle_tag = run_time_str[:13]

    # run_time_str format: YYYY-MM-DDT...
    year = run_time_str[:4]
    month = run_time_str[5:7]
    out_dir = BASE_OUTPUT_DIR / year / month
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"ecmwf_ifs_{run_cycle_tag}.csv"
    json_path = out_dir / f"ecmwf_ifs_{run_cycle_tag}_raw.json"

    manifest_record = {
        "run_time": run_time_str,
        "requested_latitude": REQ_LATITUDE,
        "requested_longitude": REQ_LONGITUDE,
        "returned_latitude": None,
        "returned_longitude": None,
        "model": MODEL,
        "status": "pending",
        "row_count": 0,
        "csv_path": str(csv_path.relative_to(BASE_DIR)),
        "json_path": str(json_path.relative_to(BASE_DIR)),
        "failure_reason": None
    }

    if not overwrite and csv_path.exists() and json_path.exists():
        try:
            df = pd.read_csv(csv_path)
            df["valid_time"] = pd.to_datetime(df["valid_time"])
            df["run_time"] = pd.to_datetime(df["run_time"])
            validate_dataframe(df, run_time_str)

            with open(json_path, "r", encoding="utf-8") as f:
                jdata = json.load(f)
                manifest_record["returned_latitude"] = jdata.get("latitude")
                manifest_record["returned_longitude"] = jdata.get("longitude")

            manifest_record["status"] = "skipped_existing"
            manifest_record["row_count"] = len(df)
            return manifest_record, df, f"Loaded existing {csv_path.name}"
        except Exception as e:
            print(f"[{run_time_str}] Existing file invalid ({e}), re-downloading...")

    params = {
        "latitude": REQ_LATITUDE,
        "longitude": REQ_LONGITUDE,
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
                        raise ValueError("Response 200 OK but hourly field is missing or empty.")

                    df = pd.DataFrame(hourly)
                    df.rename(columns={"time": "valid_time"}, inplace=True)
                    df["valid_time"] = pd.to_datetime(df["valid_time"])
                    df["run_time"] = pd.to_datetime(run_time_str, utc=True).tz_localize(None)
                    df["lead_hours"] = ((df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600).astype(int)

                    cols = ["run_time", "valid_time", "lead_hours"] + [
                        c for c in df.columns if c not in ["run_time", "valid_time", "lead_hours"]
                    ]
                    df = df[cols]

                    validate_dataframe(df, run_time_str)

                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

                    df.to_csv(csv_path, index=False)

                    manifest_record["status"] = "successful"
                    manifest_record["row_count"] = len(df)
                    manifest_record["returned_latitude"] = data.get("latitude")
                    manifest_record["returned_longitude"] = data.get("longitude")

                    return manifest_record, df, f"Saved {len(df)} rows to {csv_path.name}"
                except Exception as e:
                    manifest_record["status"] = "failed"
                    manifest_record["failure_reason"] = f"Processing/validation error: {e}"
                    return manifest_record, None, manifest_record["failure_reason"]

            elif resp.status_code == 400:
                err_msg = resp.text
                if "not available" in err_msg.lower():
                    manifest_record["status"] = "unavailable"
                    manifest_record["failure_reason"] = f"HTTP 400: {err_msg.strip()}"
                    return manifest_record, None, manifest_record["failure_reason"]
                else:
                    manifest_record["status"] = "failed"
                    manifest_record["failure_reason"] = f"HTTP 400: {err_msg.strip()}"
                    return manifest_record, None, manifest_record["failure_reason"]

            elif resp.status_code >= 500:
                err_msg = f"HTTP {resp.status_code}: {resp.text.strip()}"
            else:
                manifest_record["status"] = "failed"
                manifest_record["failure_reason"] = f"HTTP {resp.status_code}: {resp.text.strip()}"
                return manifest_record, None, manifest_record["failure_reason"]

        except requests.RequestException as e:
            err_msg = f"Network error: {e}"

        if attempt < MAX_RETRIES:
            sleep_time = BACKOFF_TIMES[attempt]
            print(f"[{run_time_str}] Attempt {attempt+1}/{MAX_RETRIES+1} failed: {err_msg}. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
        else:
            manifest_record["status"] = "failed"
            manifest_record["failure_reason"] = f"Failed after {MAX_RETRIES+1} attempts. Last error: {err_msg}"
            return manifest_record, None, manifest_record["failure_reason"]


def update_manifest(manifest_records):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(manifest_records)
    df.to_csv(MANIFEST_FILE, index=False)
    return MANIFEST_FILE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print expected schedule and directories, do not download.")
    parser.add_argument("--test-batch", type=int, help="Run only a small batch of N runs.", default=0)
    args = parser.parse_args()

    runs = generate_run_timestamps()

    if args.dry_run:
        print("======================================================")
        print("DRY RUN: ECMWF IFS HISTORICAL INGESTION")
        print("======================================================")
        print(f"Expected number of runs: {len(runs)}")
        print(f"Expected dates:          {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
        print(f"Expected cycles:         {CYCLES}")

        expected_dirs = set()
        for r in runs:
            y = r[:4]
            m = r[5:7]
            expected_dirs.add(str(BASE_OUTPUT_DIR / y / m))

        print("\nExpected directory structure (top 5):")
        for d in sorted(list(expected_dirs))[:5]:
            print(f"  - {d}")
        if len(expected_dirs) > 5:
            print(f"  ... and {len(expected_dirs) - 5} more.")

        return

    total_requested = len(runs)

    if args.test_batch > 0:
        step = max(1, total_requested // args.test_batch)
        runs = runs[::step][:args.test_batch]
        total_requested = len(runs)
        print(f"*** RUNNING IN TEST BATCH MODE: {total_requested} runs ***")

    print("=" * 70)
    print("ECMWF IFS HISTORICAL INGESTION")
    print("=" * 70)
    print(f"Total runs requested: {total_requested}")
    print(f"Manifest file:        {MANIFEST_FILE}")
    print("=" * 70)

    existing_manifest = {}
    if MANIFEST_FILE.exists():
        try:
            m_df = pd.read_csv(MANIFEST_FILE)
            for _, row in m_df.iterrows():
                existing_manifest[row['run_time']] = row.to_dict()
        except Exception:
            pass

    manifest_records = []
    successful_count = 0
    unavailable_count = 0
    failed_count = 0

    for idx, run_ts in enumerate(runs, 1):
        record, df, msg = download_run(run_ts)
        print(f"[{idx:04d}/{total_requested}] {run_ts} -> {record['status'].upper()}: {msg}")

        manifest_records.append(record)

        # Incremental save
        if idx % 50 == 0 or idx == total_requested:
            update_manifest(manifest_records)

        if record["status"] in ("successful", "skipped_existing"):
            successful_count += 1
            if record["status"] == "successful":
                time.sleep(REQUEST_DELAY_SEC)
        elif record["status"] == "unavailable":
            unavailable_count += 1
            time.sleep(REQUEST_DELAY_SEC)
        else:
            failed_count += 1
            time.sleep(REQUEST_DELAY_SEC)

    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"Requested:   {total_requested}")
    print(f"Successful:  {successful_count}")
    print(f"Unavailable: {unavailable_count}")
    print(f"Failed:      {failed_count}")

    if args.test_batch > 0:
        print("\nTest batch complete. Verify the logs and manifest before full run.")

if __name__ == "__main__":
    main()
