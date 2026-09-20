import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import glob

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "raw" / "nwp" / "2025" / "09"
OUTPUT_DIR = BASE_DIR / "reports" / "nwp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_VARIABLES = [
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

def generate_expected_runs():
    runs = []
    curr = START_DATE
    while curr <= END_DATE:
        for cycle in CYCLES:
            dt_str = f"{curr.strftime('%Y-%m-%d')}T{cycle}:00:00"
            runs.append(pd.to_datetime(dt_str))
        curr += timedelta(days=1)
    return set(runs)

def run_audit():
    expected_runs = generate_expected_runs()

    csv_files = list(INPUT_DIR.glob("*.csv"))
    json_files = {f.stem.replace("_raw", ""): f for f in INPUT_DIR.glob("*_raw.json")}

    audit_results = []

    metadata_lat = set()
    metadata_lon = set()
    run_times_found = []

    # Track cross-run integrity
    cross_run_issues = []
    global_pairs = set()
    duplicate_runs = set()

    print("=" * 60)
    print("NWP AUDIT: SEPTEMBER 2025 ECMWF IFS")
    print("=" * 60)

    for csv_path in csv_files:
        run_tag = csv_path.stem
        json_path = json_files.get(run_tag)

        file_audit = {
            "file": csv_path.name,
            "1_unique_run_time": "FAIL",
            "2_exact_168_rows": "FAIL",
            "3_valid_time_increasing": "FAIL",
            "4_lead_hours_exact": "FAIL",
            "5_lead_hours_0_167": "FAIL",
            "6_no_duplicate_pairs": "FAIL",
            "7_valid_time_after_run": "FAIL",
            "8_required_vars_exist": "FAIL",
        }

        try:
            df = pd.read_csv(csv_path)
            df["valid_time"] = pd.to_datetime(df["valid_time"])
            df["run_time"] = pd.to_datetime(df["run_time"])

            # 1. Exactly one unique run_time
            unique_rt = df["run_time"].unique()
            if len(unique_rt) == 1:
                file_audit["1_unique_run_time"] = "PASS"
                run_ts = pd.to_datetime(unique_rt[0])
                if run_ts in run_times_found:
                    duplicate_runs.add(run_ts)
                run_times_found.append(run_ts)
            else:
                run_ts = None

            # 2. Exactly 168 hourly rows
            if len(df) == 168:
                file_audit["2_exact_168_rows"] = "PASS"

            # 3. valid_time is strictly increasing
            if df["valid_time"].is_monotonic_increasing:
                file_audit["3_valid_time_increasing"] = "PASS"

            # 4. lead_hours equals exactly (valid_time - run_time) / 1 hour
            expected_lead = (df["valid_time"] - df["run_time"]).dt.total_seconds() / 3600
            if (expected_lead.astype(int) == df["lead_hours"]).all():
                file_audit["4_lead_hours_exact"] = "PASS"

            # 5. Lead hours cover 0 through 167
            if set(df["lead_hours"].unique()) == set(range(168)):
                file_audit["5_lead_hours_0_167"] = "PASS"

            # 6. No duplicate (run_time, valid_time) pairs
            if not df.duplicated(subset=["run_time", "valid_time"]).any():
                file_audit["6_no_duplicate_pairs"] = "PASS"

            # 7. No valid_time occurs before run_time
            if (df["valid_time"] >= df["run_time"]).all():
                file_audit["7_valid_time_after_run"] = "PASS"

            # 8. Required variables exist
            if all(v in df.columns for v in EXPECTED_VARIABLES):
                file_audit["8_required_vars_exist"] = "PASS"

            # Min/Max, Nulls, Infs
            for v in EXPECTED_VARIABLES:
                if v in df.columns:
                    has_inf = np.isinf(df[v]).any()
                    file_audit[f"{v}_missing"] = df[v].isnull().sum()
                    file_audit[f"{v}_min"] = df[v].min()
                    file_audit[f"{v}_max"] = df[v].max()
                    file_audit[f"{v}_has_inf"] = has_inf

            # Check cross run duplicate
            for _, row in df.iterrows():
                pair = (row["run_time"], row["valid_time"])
                if pair in global_pairs:
                    cross_run_issues.append(f"Duplicate cross-run pair: {pair} in {csv_path.name}")
                global_pairs.add(pair)

            # Metadata extraction
            if json_path and json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    jdata = json.load(f)
                    metadata_lat.add(jdata.get("latitude"))
                    metadata_lon.add(jdata.get("longitude"))

        except Exception as e:
            cross_run_issues.append(f"Error processing {csv_path.name}: {e}")

        audit_results.append(file_audit)

    audit_df = pd.DataFrame(audit_results)
    audit_csv_path = OUTPUT_DIR / "september_2025_nwp_audit.csv"
    audit_df.to_csv(audit_csv_path, index=False)

    # Global Checks
    print("\n[GLOBAL INTEGRITY AUDIT]")
    # 12. Check whether all successful runs use the same latitude/longitude.
    print(f"Same Latitude across all runs: {'PASS' if len(metadata_lat) == 1 else 'FAIL'} {metadata_lat}")
    print(f"Same Longitude across all runs: {'PASS' if len(metadata_lon) == 1 else 'FAIL'} {metadata_lon}")

    # 13. Same model check.
    models_in_filename = set([f.name.split('_2025')[0] for f in csv_files])
    print(f"Same Model prefix across all runs: {'PASS' if len(models_in_filename) == 1 else 'FAIL'} {models_in_filename}")

    # 14. Check run cycles
    cycles_found = set([ts.strftime("%H") for ts in run_times_found])
    print(f"Run cycles represented (Expected 00,06,12,18): {'PASS' if cycles_found == set(CYCLES) else 'FAIL'} {cycles_found}")

    # 15. Identify missing runs
    found_runs_set = set(run_times_found)
    missing_runs = expected_runs - found_runs_set
    print(f"Missing runs ({len(missing_runs)}):")
    for r in sorted(list(missing_runs)):
        print(f"  - {r}")

    if duplicate_runs:
        print(f"Duplicate runs found across files: {duplicate_runs}")

    print("\n[PER-FILE AUDIT SUMMARY]")
    for col in [
        "1_unique_run_time",
        "2_exact_168_rows",
        "3_valid_time_increasing",
        "4_lead_hours_exact",
        "5_lead_hours_0_167",
        "6_no_duplicate_pairs",
        "7_valid_time_after_run",
        "8_required_vars_exist",
    ]:
        if col in audit_df.columns:
            passes = (audit_df[col] == "PASS").sum()
            fails = (audit_df[col] == "FAIL").sum()
            status = "PASS" if fails == 0 else "FAIL"
            print(f"Rule {col.split('_', 1)[0]:2}: {col.split('_', 1)[1]:25} -> {status} (Pass: {passes}, Fail: {fails})")

    print("\n[MISSING / INF / MIN / MAX OVERVIEW]")
    for v in EXPECTED_VARIABLES:
        missing_col = f"{v}_missing"
        if missing_col in audit_df.columns:
            total_missing = audit_df[missing_col].sum()
            min_val = audit_df[f"{v}_min"].min()
            max_val = audit_df[f"{v}_max"].max()
            inf_sum = audit_df[f"{v}_has_inf"].sum()
            print(f"{v:25}: Missing={total_missing}, Inf={inf_sum}, Range=[{min_val}, {max_val}]")

    print("\n[CROSS-RUN ISSUES]")
    if not cross_run_issues:
        print("PASS: No cross-run duplicate pairs or processing errors.")
    else:
        print(f"FAIL: {len(cross_run_issues)} issues found. Printing first 10:")
        for issue in cross_run_issues[:10]:
            print(f"  - {issue}")

    print(f"\nDetailed file-level audit saved to {audit_csv_path}")

if __name__ == "__main__":
    run_audit()
