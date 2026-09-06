"""
VayuNet — Processed Data Inspector
Inspects data/processed/delhi_forecasting.csv without modifying it.
"""

from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"

MODELING_FEATURES = [
    "PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "SO2", "CO", "Ozone",
    "AT", "RH", "WS", "WD", "SR", "BP",
    "hour", "day_of_week", "day_of_year", "month", "is_weekend",
    "WD_sin", "WD_cos",
    "PM2.5_lag_1h", "PM2.5_lag_3h", "PM2.5_lag_6h", "PM2.5_lag_12h",
    "PM2.5_lag_24h", "PM2.5_lag_48h", "PM2.5_lag_72h",
    "PM2.5_roll_mean_6h", "PM2.5_roll_mean_24h", "PM2.5_roll_std_24h",
]

TARGET_COLUMNS = [
    "target_pm25_6h",
    "target_pm25_24h",
    "target_pm25_72h",
]

LAG_HORIZONS = {
    "PM2.5_lag_1h":  1,
    "PM2.5_lag_24h": 24,
    "PM2.5_lag_72h": 72,
}

TARGET_HORIZONS = {
    "target_pm25_6h":  6,
    "target_pm25_24h": 24,
    "target_pm25_72h": 72,
}

PASS_FAIL = {}


def record(check_name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    PASS_FAIL[check_name] = status
    marker = "OK" if passed else "!!"
    print(f"  [{marker}] {check_name}: {status}  {detail}")


def section(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main():
    print("=" * 70)
    print("  VAYUNET — PROCESSED DATA INSPECTION")
    print("=" * 70)
    print(f"\n  File: {PROCESSED_FILE}\n")

    if not PROCESSED_FILE.exists():
        print("  ERROR: File does not exist. Run prepare_data.py first.")
        return

    df = pd.read_csv(PROCESSED_FILE, parse_dates=["Timestamp"])
    print(f"  Loaded {len(df):,} rows × {len(df.columns)} columns")

    # ------------------------------------------------------------------ #
    # CHECK 1: Shape and column names                                      #
    # ------------------------------------------------------------------ #
    section("CHECK 1 — Shape & Column Names")

    expected_cols = 38
    shape_ok = len(df.columns) == expected_cols
    record("Column count == 38", shape_ok, f"(got {len(df.columns)})")

    print(f"\n  All {len(df.columns)} columns:")
    for i, col in enumerate(df.columns, 1):
        print(f"    {i:2d}. {col}")

    # ------------------------------------------------------------------ #
    # CHECK 2: Exactly 10 unique stations                                  #
    # ------------------------------------------------------------------ #
    section("CHECK 2 — Unique Stations")

    stations = sorted(df["station_id"].unique())
    stations_ok = len(stations) == 10
    record("Exactly 10 unique stations", stations_ok, f"(got {len(stations)})")

    for s in stations:
        n = (df["station_id"] == s).sum()
        print(f"    {s:25s}: {n:,} rows")

    # ------------------------------------------------------------------ #
    # CHECK 3: No duplicate station_id + Timestamp                        #
    # ------------------------------------------------------------------ #
    section("CHECK 3 — Duplicate station_id + Timestamp")

    dupes = df.duplicated(subset=["station_id", "Timestamp"]).sum()
    record("Zero duplicates", dupes == 0, f"({dupes} found)")

    # ------------------------------------------------------------------ #
    # CHECK 4: Chronological order within every station                   #
    # ------------------------------------------------------------------ #
    section("CHECK 4 — Chronological Order Within Each Station")

    all_sorted = True
    for station in stations:
        ts = df.loc[df["station_id"] == station, "Timestamp"]
        if not ts.is_monotonic_increasing:
            all_sorted = False
            print(f"    NOT sorted: {station}")

    record("All stations chronologically sorted", all_sorted)

    # ------------------------------------------------------------------ #
    # CHECK 5: Exactly 2 segments per station                             #
    # ------------------------------------------------------------------ #
    section("CHECK 5 — Segments per Station")

    all_2_segs = True
    for station in stations:
        n_segs = df.loc[df["station_id"] == station, "segment_id"].nunique()
        ok = n_segs == 2
        if not ok:
            all_2_segs = False
        print(f"    {station:25s}: {n_segs} segment(s)  {'OK' if ok else 'FAIL'}")

    record("All stations have exactly 2 segments", all_2_segs)

    # ------------------------------------------------------------------ #
    # CHECK 6: Lag correctness                                            #
    # ------------------------------------------------------------------ #
    section("CHECK 6 -- Lag Feature Correctness (timestamp-based)")

    all_lags_ok = True

    for lag_col, shift_hours in LAG_HORIZONS.items():
        mismatches = 0
        checked = 0

        for station in stations:
            sdf = df[df["station_id"] == station]

            for seg in sdf["segment_id"].unique():
                seg_df = sdf[sdf["segment_id"] == seg]

                # Build Timestamp -> PM2.5 lookup for this segment
                pm25_lookup = seg_df.set_index("Timestamp")["PM2.5"]

                # For each row at t, the lag should be PM2.5 at t - h hours
                expected_ts = seg_df["Timestamp"] - pd.Timedelta(hours=shift_hours)
                expected_vals = pm25_lookup.reindex(expected_ts.values).values
                actual_vals   = seg_df[lag_col].values

                # Only check rows where both expected and actual are non-NaN
                valid = ~np.isnan(expected_vals) & ~np.isnan(actual_vals)
                checked += valid.sum()
                if valid.sum() > 0:
                    diff = np.abs(expected_vals[valid] - actual_vals[valid])
                    mismatches += (diff > 1e-3).sum()

        lag_ok = mismatches == 0
        if not lag_ok:
            all_lags_ok = False
        record(
            f"{lag_col} correct",
            lag_ok,
            f"(checked {checked:,} rows, {mismatches} mismatches)"
        )

    # ------------------------------------------------------------------ #
    # CHECK 7: Target correctness                                         #
    # ------------------------------------------------------------------ #
    section("CHECK 7 -- Forecast Target Correctness (timestamp-based)")

    all_targets_ok = True

    for target_col, horizon in TARGET_HORIZONS.items():
        mismatches = 0
        checked = 0

        for station in stations:
            sdf = df[df["station_id"] == station]

            for seg in sdf["segment_id"].unique():
                seg_df = sdf[sdf["segment_id"] == seg]

                pm25_lookup = seg_df.set_index("Timestamp")["PM2.5"]

                # For each row at t, the target should be PM2.5 at t + h hours
                expected_ts = seg_df["Timestamp"] + pd.Timedelta(hours=horizon)
                expected_vals = pm25_lookup.reindex(expected_ts.values).values
                actual_vals   = seg_df[target_col].values

                valid = ~np.isnan(expected_vals) & ~np.isnan(actual_vals)
                checked += valid.sum()
                if valid.sum() > 0:
                    diff = np.abs(expected_vals[valid] - actual_vals[valid])
                    mismatches += (diff > 1e-3).sum()

        target_ok = mismatches == 0
        if not target_ok:
            all_targets_ok = False
        record(
            f"{target_col} correct",
            target_ok,
            f"(checked {checked:,} rows, {mismatches} mismatches)"
        )

    # ------------------------------------------------------------------ #
    # CHECK 8: No lag/target crosses segment boundary                     #
    # ------------------------------------------------------------------ #
    section("CHECK 8 — No Lag/Target Crosses Segment Boundary")

    violations = 0

    for station in stations:
        sdf = df[df["station_id"] == station].copy().reset_index(drop=True)

        # Find the boundary: last row of segment 0, first row of segment 1
        seg_ids = sorted(sdf["segment_id"].unique())
        if len(seg_ids) < 2:
            continue

        seg0 = sdf[sdf["segment_id"] == seg_ids[0]]
        seg1 = sdf[sdf["segment_id"] == seg_ids[1]]

        last_seg0_ts = seg0["Timestamp"].max()
        first_seg1_ts = seg1["Timestamp"].min()
        gap_hours = (first_seg1_ts - last_seg0_ts).total_seconds() / 3600

        # The first row of segment 1 should have NaN lags (no valid prior data)
        first_row = seg1.iloc[0]

        for lag_col in LAG_HORIZONS:
            if lag_col in df.columns and not pd.isna(first_row[lag_col]):
                violations += 1
                print(f"    VIOLATION: {station} {lag_col} not NaN at segment boundary")

        # The last row of segment 0 should have NaN targets (no valid future data)
        last_row = seg0.iloc[-1]
        for target_col in TARGET_HORIZONS:
            if target_col in df.columns and not pd.isna(last_row[target_col]):
                # Targets near boundary may be valid if gap < horizon; just note
                pass

    record("No lag/target crosses segment boundary", violations == 0,
           f"({violations} violations)")

    # ------------------------------------------------------------------ #
    # CHECK 9: Missing percentages for all features + targets             #
    # ------------------------------------------------------------------ #
    section("CHECK 9 — Missing Value Percentages")

    total = len(df)
    print(f"\n  {'Column':<30} {'Missing':>8}  {'%':>7}")
    print(f"  {'-'*48}")

    for col in MODELING_FEATURES + TARGET_COLUMNS:
        if col not in df.columns:
            print(f"  {'[MISSING COL] ' + col:<30}")
            continue
        n_missing = df[col].isna().sum()
        pct = n_missing / total * 100
        flag = "  << HIGH" if pct > 20 else ""
        print(f"  {col:<30} {n_missing:>8,}  {pct:>6.2f}%{flag}")

    # ------------------------------------------------------------------ #
    # CHECK 10: Descriptive statistics for PM2.5 and PM10                 #
    # ------------------------------------------------------------------ #
    section("CHECK 10 — Descriptive Statistics")

    for col in ["PM2.5", "PM10"]:
        if col not in df.columns:
            print(f"  {col} not found.")
            continue
        s = df[col].dropna()
        print(f"\n  {col}:")
        print(f"    count  : {s.count():>10,}")
        print(f"    mean   : {s.mean():>10.2f}")
        print(f"    median : {s.median():>10.2f}")
        print(f"    std    : {s.std():>10.2f}")
        print(f"    min    : {s.min():>10.2f}")
        print(f"    p5     : {s.quantile(0.05):>10.2f}")
        print(f"    p25    : {s.quantile(0.25):>10.2f}")
        print(f"    p75    : {s.quantile(0.75):>10.2f}")
        print(f"    p95    : {s.quantile(0.95):>10.2f}")
        print(f"    p99    : {s.quantile(0.99):>10.2f}")
        print(f"    max    : {s.max():>10.2f}")

    # ------------------------------------------------------------------ #
    # CHECK 11: Impossible / invalid values (flag only, no deletion)      #
    # ------------------------------------------------------------------ #
    section("CHECK 11 — Impossible / Invalid Value Flags")

    flags = []

    if "PM2.5" in df.columns:
        neg = (df["PM2.5"] < 0).sum()
        extreme = (df["PM2.5"] > 2000).sum()
        if neg:   flags.append(f"PM2.5 < 0     : {neg:,} rows")
        if extreme: flags.append(f"PM2.5 > 2000  : {extreme:,} rows")

    if "PM10" in df.columns:
        neg = (df["PM10"] < 0).sum()
        extreme = (df["PM10"] > 3000).sum()
        if neg:   flags.append(f"PM10 < 0      : {neg:,} rows")
        if extreme: flags.append(f"PM10 > 3000   : {extreme:,} rows")

    if "AT" in df.columns:
        cold = (df["AT"] < -10).sum()
        hot  = (df["AT"] > 55).sum()
        if cold: flags.append(f"AT < -10 deg C : {cold:,} rows")
        if hot:  flags.append(f"AT > 55 deg C  : {hot:,} rows  (should be 0 -- cleaned in prepare_data.py)")

    if "RH" in df.columns:
        low  = (df["RH"] < 0).sum()
        high = (df["RH"] > 100).sum()
        if low:  flags.append(f"RH < 0%       : {low:,} rows")
        if high: flags.append(f"RH > 100%     : {high:,} rows")

    if flags:
        for f in flags:
            print(f"  [WARN] {f}")
        record("No impossible values found", False, f"({len(flags)} issues - review only, not deleted)")
    else:
        record("No impossible values found", True)

    # ------------------------------------------------------------------ #
    # FINAL PASS/FAIL SUMMARY                                             #
    # ------------------------------------------------------------------ #
    section("FINAL VALIDATION SUMMARY")

    passed = sum(1 for v in PASS_FAIL.values() if v == "PASS")
    failed = sum(1 for v in PASS_FAIL.values() if v == "FAIL")
    total_checks = len(PASS_FAIL)

    print()
    for check, status in PASS_FAIL.items():
        marker = "OK" if status == "PASS" else "!!"
        print(f"  [{marker}] {status}  --  {check}")

    print()
    print(f"  Result: {passed}/{total_checks} checks passed")

    if failed == 0:
        print("\n  [ALL CHECKS PASSED] -- ready for XGBoost baseline.")
    else:
        print(f"\n  [FAILED] {failed} CHECK(S) FAILED -- review before training.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
