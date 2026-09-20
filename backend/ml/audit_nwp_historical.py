import json
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "raw" / "nwp"
OUTPUT_DIR = BASE_DIR / "reports" / "nwp"

EXPECTED_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "boundary_layer_height",
]

def run_historical_audit():
    csv_files = list(INPUT_DIR.rglob("*.csv"))
    json_files = {f.stem.replace("_raw", ""): f for f in INPUT_DIR.rglob("*_raw.json")}

    metadata_lat = set()
    metadata_lon = set()
    run_times_found = set()

    total_rows = 0
    missing_counts = {v: 0 for v in EXPECTED_VARIABLES}

    print("=" * 60)
    print("NWP AUDIT: ECMWF IFS HISTORICAL")
    print("=" * 60)

    # Read the manifest to get requested/unavailable/failed
    manifest_file = OUTPUT_DIR / "historical_ingestion_manifest.csv"
    if manifest_file.exists():
        manifest_df = pd.read_csv(manifest_file)
        total_requested = len(manifest_df)
        successful = len(manifest_df[manifest_df['status'].isin(['successful', 'skipped_existing'])])
        unavailable = len(manifest_df[manifest_df['status'] == 'unavailable'])
        failed = len(manifest_df[manifest_df['status'] == 'failed'])
        unavailable_runs = manifest_df[manifest_df['status'] == 'unavailable']['run_time'].tolist()
        failed_runs = manifest_df[manifest_df['status'] == 'failed']['run_time'].tolist()
    else:
        total_requested = "Unknown"
        successful = len(csv_files)
        unavailable = "Unknown"
        failed = "Unknown"
        unavailable_runs = []
        failed_runs = []

    for csv_path in csv_files:
        run_tag = csv_path.stem
        json_path = json_files.get(run_tag)

        try:
            # Only quick read for rows and missing
            df = pd.read_csv(csv_path)
            total_rows += len(df)

            unique_rt = df["run_time"].unique()
            if len(unique_rt) == 1:
                run_times_found.add(unique_rt[0])

            for v in EXPECTED_VARIABLES:
                if v in df.columns:
                    missing_counts[v] += df[v].isnull().sum()

            if json_path and json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    jdata = json.load(f)
                    metadata_lat.add(jdata.get("latitude"))
                    metadata_lon.add(jdata.get("longitude"))

        except Exception as e:
            print(f"Error processing {csv_path.name}: {e}")

    print("\n[GLOBAL INTEGRITY AUDIT]")
    print(f"Total requested runs: {total_requested}")
    print(f"Successful runs: {successful}")
    print(f"Unavailable runs: {unavailable}")
    print(f"Failed runs: {failed}")
    print(f"Total CSV rows: {total_rows}")
    print(f"Unique run_times: {len(run_times_found)}")
    print(f"Duplicate pairs: Skipped across all {successful} files to save memory, individual files were checked during ingestion.")

    print("\n[COORDINATE CONSISTENCY]")
    print(f"Requested Latitude: 28.6139")
    print(f"Requested Longitude: 77.2090")
    print(f"Returned Latitudes: {metadata_lat}")
    print(f"Returned Longitudes: {metadata_lon}")

    print("\n[VARIABLE MISSINGNESS]")
    for v, c in missing_counts.items():
        print(f"  - {v:25}: {c} missing values")

    print("\n[REMAINING FAILED/UNAVAILABLE RUNS]")
    if failed_runs:
        print(f"Failed ({len(failed_runs)}): {failed_runs[:5]} ...")
    if unavailable_runs:
        print(f"Unavailable ({len(unavailable_runs)}): {unavailable_runs[:5]} ...")

if __name__ == "__main__":
    run_historical_audit()
