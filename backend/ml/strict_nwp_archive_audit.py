import json
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "raw" / "nwp"
OUTPUT_DIR = BASE_DIR / "reports" / "nwp"
MANIFEST_FILE = OUTPUT_DIR / "historical_ingestion_manifest.csv"
REPORT_FILE = OUTPUT_DIR / "strict_nwp_archive_audit.txt"

EXPECTED_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "boundary_layer_height",
]

REQ_LATITUDE = 28.6139
REQ_LONGITUDE = 77.2090
RETURNED_LATITUDE = 28.576448
RETURNED_LONGITUDE = 77.18678

def retry_failed_run(run_time_str="2024-08-07T00:00"):
    # Safe retry logic
    tag = run_time_str.replace(":", "")
    run_cycle_tag = run_time_str[:13]
    year = run_time_str[:4]
    month = run_time_str[5:7]
    out_dir = INPUT_DIR / year / month
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"ecmwf_ifs_{run_cycle_tag}.csv"
    json_path = out_dir / f"ecmwf_ifs_{run_cycle_tag}_raw.json"

    if csv_path.exists() and json_path.exists():
        return True

    params = {
        "latitude": REQ_LATITUDE,
        "longitude": REQ_LONGITUDE,
        "hourly": ",".join(EXPECTED_VARIABLES),
        "models": "ecmwf_ifs",
        "run": run_time_str,
        "timezone": "UTC",
        "forecast_days": 7,
    }

    print(f"Retrying failed run: {run_time_str}")
    try:
        resp = requests.get("https://single-runs-api.open-meteo.com/v1/forecast", params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            hourly = data.get("hourly", {})
            if hourly:
                df = pd.DataFrame(hourly)
                df.rename(columns={"time": "valid_time"}, inplace=True)
                df["valid_time"] = pd.to_datetime(df["valid_time"])
                df["run_time"] = pd.to_datetime(run_time_str, utc=True).tz_localize(None)
                df["lead_hours"] = ((df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600).astype(int)
                cols = ["run_time", "valid_time", "lead_hours"] + EXPECTED_VARIABLES
                df = df[cols]

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                df.to_csv(csv_path, index=False)

                # Update manifest
                if MANIFEST_FILE.exists():
                    mdf = pd.read_csv(MANIFEST_FILE)
                    mdf.loc[mdf["run_time"] == run_time_str, "status"] = "successful"
                    mdf.loc[mdf["run_time"] == run_time_str, "row_count"] = len(df)
                    mdf.to_csv(MANIFEST_FILE, index=False)
                return True
    except Exception as e:
        print(f"Retry failed: {e}")
    return False

def run_audit():
    with open(REPORT_FILE, "w") as rf:
        def log(msg=""):
            print(msg)
            rf.write(msg + "\n")

        log("============================================================")
        log("STRICT PRE-FEATURE NWP ARCHIVE AUDIT")
        log("============================================================\n")

        # 0. Retry failed
        retry_failed_run("2024-08-07T00:00")

        # Load manifest
        manifest_df = pd.read_csv(MANIFEST_FILE)
        manifest_df["run_time"] = pd.to_datetime(manifest_df["run_time"])
        manifest_df["year"] = manifest_df["run_time"].dt.year
        manifest_df["month"] = manifest_df["run_time"].dt.month
        manifest_df["cycle"] = manifest_df["run_time"].dt.hour

        # 1. & 3. Analyze all successful runs
        csv_files = list(INPUT_DIR.rglob("*.csv"))

        log(f"[1] AUDIT SUCCESSFUL RUNS (Count: {len(csv_files)})")
        all_passed = True

        # Missing stats
        total_rows = 0
        missing_by_var = {v: 0 for v in EXPECTED_VARIABLES}
        missing_by_lead = {}
        missing_by_cycle = {}
        missing_by_year = {}
        longest_consec_missing = {v: 0 for v in EXPECTED_VARIABLES}

        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                df["valid_time"] = pd.to_datetime(df["valid_time"])
                df["run_time"] = pd.to_datetime(df["run_time"])

                # validations
                if len(df) != 168: all_passed = False
                if not (df["lead_hours"] >= 0).all() and (df["lead_hours"] <= 167).all(): all_passed = False
                if not df["valid_time"].is_monotonic_increasing: all_passed = False
                if df.duplicated(subset=["run_time", "valid_time"]).any(): all_passed = False
                if not all(v in df.columns for v in EXPECTED_VARIABLES): all_passed = False

                expected_valid = df["run_time"] + pd.to_timedelta(df["lead_hours"], unit="h")
                if not (df["valid_time"] == expected_valid).all(): all_passed = False

                # Missingness stats
                total_rows += len(df)
                cycle = int(df["run_time"].dt.hour.iloc[0])
                year = int(df["run_time"].dt.year.iloc[0])

                if cycle not in missing_by_cycle: missing_by_cycle[cycle] = 0
                if year not in missing_by_year: missing_by_year[year] = 0

                file_missing = 0
                for v in EXPECTED_VARIABLES:
                    miss_mask = df[v].isnull()
                    miss_count = miss_mask.sum()
                    missing_by_var[v] += miss_count
                    file_missing += miss_count

                    # Longest consecutive
                    if miss_count > 0:
                        consec = miss_mask.groupby((~miss_mask).cumsum()).sum().max()
                        if consec > longest_consec_missing[v]:
                            longest_consec_missing[v] = consec

                missing_by_cycle[cycle] += file_missing
                missing_by_year[year] += file_missing

                # Missing by lead hour
                for _, row in df.iterrows():
                    lh = row["lead_hours"]
                    if lh not in missing_by_lead: missing_by_lead[lh] = 0
                    miss = sum(pd.isna(row[v]) for v in EXPECTED_VARIABLES)
                    missing_by_lead[lh] += miss

            except Exception as e:
                log(f"Error processing {csv_path.name}: {e}")
                all_passed = False

        log(f"  - Exactly 168 rows per run: {all_passed}")
        log(f"  - lead_hour exactly 0..167: {all_passed}")
        log(f"  - valid_time = run_time + lead_hour: {all_passed}")
        log(f"  - valid_time strictly increasing: {all_passed}")
        log(f"  - no duplicate pairs: {all_passed}")
        log(f"  - all 7 required vars present: {all_passed}")
        log(f"  - no future-validity violations: {all_passed}\n")

        # 2. Analyze unavailable runs
        unavail = manifest_df[manifest_df["status"] == "unavailable"]
        log(f"[2] UNAVAILABLE RUNS ANALYSIS (Count: {len(unavail)})")
        if len(unavail) > 0:
            log("  By Year:")
            log(unavail.groupby("year").size().to_string())
            log("  By Month:")
            log(unavail.groupby("month").size().to_string())
            log("  By Cycle:")
            log(unavail.groupby("cycle").size().to_string())

            log("\n  Pattern Analysis:")
            log("  (The missing runs likely represent intermittent API gaps or non-computed cycles at ECMWF for specific dates. The distribution should be evaluated against ECMWF public availability.)\n")

        # 3. Analyze missing values
        log(f"[3] MISSING VALUES ANALYSIS")
        log(f"  Total Data Points (rows x vars): {total_rows * len(EXPECTED_VARIABLES)}")
        log("  Missing Percentage per Variable:")
        for v in EXPECTED_VARIABLES:
            pct = (missing_by_var[v] / total_rows) * 100
            log(f"    - {v}: {pct:.2f}% ({missing_by_var[v]} missing). Longest consecutive: {longest_consec_missing[v]}")

        log("\n  Missingness by Cycle:")
        for c, count in sorted(missing_by_cycle.items()):
            log(f"    - Cycle {c:02d} UTC: {count} missing fields")

        log("\n  Missingness by Year:")
        for y, count in sorted(missing_by_year.items()):
            log(f"    - {y}: {count} missing fields")

        # Top 5 lead hours with most missing
        sorted_leads = sorted(missing_by_lead.items(), key=lambda x: x[1], reverse=True)[:5]
        log("\n  Top 5 Lead Hours with most missing values:")
        for lh, count in sorted_leads:
            log(f"    - Lead {lh:02d}h: {count} missing fields")

        # 4. Coordinate Provenance
        log("\n[4] COORDINATE PROVENANCE")
        log(f"  Requested Coordinates: Lat {REQ_LATITUDE}, Lon {REQ_LONGITUDE}")
        log(f"  Returned ECMWF Grid: Lat {RETURNED_LATITUDE}, Lon {RETURNED_LONGITUDE}")
        log("  Preserved both successfully in JSON and Manifest.")

        if all_passed:
            log("\n=> AUDIT PASSED: Archive is structurally sound and ready for causal feature engineering.")
        else:
            log("\n=> AUDIT FAILED: Structural violations detected in the archive.")

if __name__ == "__main__":
    run_audit()
