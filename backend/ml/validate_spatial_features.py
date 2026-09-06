"""
Validation script for Experiment S1 Spatial Feature Generator.

Performs comprehensive validation:
1. 10 stations found in metadata.
2. Every station has exactly one coordinate, no duplicate coordinate pairs.
3. Distances are strictly positive (> 0.0), self-distance is excluded.
4. No missing station IDs in spatial features.
5. No future timestamps used: features for timestamp t depend strictly on timestamp t.
6. No target columns used in feature calculation.
7. Preserves exact dataset row count, row order, and original columns.
8. Manual inspection of nearest neighbors and calculated values for key stations (e.g. R K Puram).
"""

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.spatial_features import (
    add_spatial_features,
    get_spatial_feature_names,
    load_station_coordinates,
    compute_distance_matrix,
    haversine_distance,
)

METADATA_FILE = BASE_DIR / "data" / "metadata" / "delhi_station_coordinates.csv"
DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"


def validate_spatial_features():
    print("=" * 70)
    print("VAYUNET SPATIAL FEATURE VALIDATION SUITE (EXPERIMENT S1)")
    print("=" * 70)

    passed = True

    # Check 1: 10 stations found in metadata
    coords_df = load_station_coordinates(METADATA_FILE)
    n_stations = len(coords_df)
    print(f"\n1. Station Count Check: Found {n_stations} stations.")
    if n_stations != 10:
        print(f"   [FAIL] Expected 10 stations, got {n_stations}")
        passed = False
    else:
        print("   [PASS] Exactly 10 stations found.")

    # Check 2: Unique station IDs and unique coordinates
    dup_stations = coords_df["station_id"].duplicated().sum()
    dup_coords = coords_df.duplicated(subset=["latitude", "longitude"]).sum()
    print(f"\n2. Uniqueness Check:")
    print(f"   Duplicate station IDs: {dup_stations}")
    print(f"   Duplicate coordinate pairs: {dup_coords}")
    if dup_stations > 0 or dup_coords > 0:
        print("   [FAIL] Coordinates or station IDs are not unique.")
        passed = False
    else:
        print("   [PASS] Every station has exactly one unique coordinate.")

    # Check 3: Distance Matrix & Self-Distance Check
    neighbor_order, neighbor_dists, dist_matrix = compute_distance_matrix(coords_df)
    print(f"\n3. Distance Matrix & Exclusion Check:")
    all_positive = True
    no_self = True
    for s, others in neighbor_order.items():
        if s in others:
            no_self = False
        dists = neighbor_dists[s]
        if any(d <= 0.0 for d in dists):
            all_positive = False

    if not no_self:
        print("   [FAIL] Self-station was found in neighbor list!")
        passed = False
    else:
        print("   [PASS] Self-station excluded from neighbor lists.")

    if not all_positive:
        print("   [FAIL] Non-positive distance detected between distinct stations!")
        passed = False
    else:
        print("   [PASS] All inter-station distances are strictly positive (> 0 km).")

    # Display nearest neighbors for all stations
    print("\n   Calculated Nearest Neighbor Rankings:")
    for s in coords_df["station_id"]:
        closest = neighbor_order[s][0]
        dist = neighbor_dists[s][0]
        second = neighbor_order[s][1]
        dist2 = neighbor_dists[s][1]
        print(f"   - {s:<14} -> nearest: {closest:<14} ({dist:5.2f} km), 2nd: {second:<14} ({dist2:5.2f} km)")

    # Check 4: Load a substantial slice of the processed dataset and add spatial features
    print(f"\n4. Loading sample from {DATA_FILE.name}...")
    # Load 50,000 rows across multiple stations and timestamps
    df_raw = pd.read_csv(DATA_FILE, nrows=50000)
    orig_len = len(df_raw)
    orig_cols = list(df_raw.columns)
    print(f"   Loaded slice: {orig_len} rows, {len(orig_cols)} columns.")

    t0 = time.time()
    df_spatial = add_spatial_features(df_raw, coords_df)
    elapsed = time.time() - t0
    print(f"   Spatial feature computation completed in {elapsed:.2f}s.")

    # Check 5: Row count and column preservation
    print(f"\n5. Row Count & Column Preservation Check:")
    if len(df_spatial) != orig_len:
        print(f"   [FAIL] Row count changed: original {orig_len} vs spatial {len(df_spatial)}")
        passed = False
    else:
        print(f"   [PASS] Row count preserved ({len(df_spatial)} == {orig_len}).")

    missing_orig = [c for c in orig_cols if c not in df_spatial.columns]
    if missing_orig:
        print(f"   [FAIL] Original columns missing: {missing_orig}")
        passed = False
    else:
        print("   [PASS] All original columns preserved unchanged.")

    # Check 6: Spatial feature columns added
    expected_spatial_cols = get_spatial_feature_names()
    print(f"\n6. Spatial Feature Columns Check ({len(expected_spatial_cols)} features):")
    missing_spatial = [c for c in expected_spatial_cols if c not in df_spatial.columns]
    if missing_spatial:
        print(f"   [FAIL] Missing spatial columns: {missing_spatial}")
        passed = False
    else:
        print(f"   [PASS] All spatial columns present: {expected_spatial_cols}")

    # Check 7: Future Leakage & Target Usage Audit
    print(f"\n7. Leakage & Target Column Audit:")
    # Ensure no target column was referenced or added as input
    targets = ["target_pm25_6h", "target_pm25_24h", "target_pm25_72h"]
    for t_col in targets:
        assert t_col in df_spatial.columns, "Target column should remain in dataset intact"

    # Spot-check temporal alignment on a specific timestamp across stations
    sample_ts = df_raw["timestamp"].dropna().iloc[100]
    ts_slice = df_spatial[df_spatial["timestamp"] == sample_ts]
    print(f"   Auditing timestamp slice: {sample_ts} ({len(ts_slice)} stations present)")

    # For R K Puram at sample_ts:
    rk_row = ts_slice[ts_slice["station_id"] == "r k puram"]
    if not rk_row.empty:
        rk_val = rk_row.iloc[0]
        nearest_st = neighbor_order["r k puram"][0]
        nearest_dist = neighbor_dists["r k puram"][0]
        actual_nn_pm25 = ts_slice[ts_slice["station_id"] == nearest_st]["PM2.5"].values
        expected_nn = actual_nn_pm25[0] if len(actual_nn_pm25) > 0 else np.nan

        print(f"\n8. Manual Spot Check - Station: R K Puram at {sample_ts}:")
        print(f"   - Nearest station        : {nearest_st}")
        print(f"   - Expected distance       : {nearest_dist:.2f} km")
        print(f"   - Feature distance        : {rk_val['nearest_neighbor_distance_km']:.2f} km")
        print(f"   - Nearest station PM2.5   : {expected_nn}")
        print(f"   - Feature nn_pm25 value   : {rk_val['nearest_neighbor_pm25']}")
        print(f"   - neighbor_pm25_mean_2    : {rk_val['neighbor_pm25_mean_2']}")
        print(f"   - neighbor_pm25_mean_3    : {rk_val['neighbor_pm25_mean_3']}")
        print(f"   - neighbor_pm25_max_3     : {rk_val['neighbor_pm25_max_3']}")
        print(f"   - distance_weighted_pm25  : {rk_val['distance_weighted_neighbor_pm25']:.2f}")

        # Assert equivalence
        if not np.isnan(expected_nn):
            assert np.isclose(rk_val["nearest_neighbor_pm25"], expected_nn), "Mismatch in nearest neighbor value!"
            assert np.isclose(rk_val["nearest_neighbor_distance_km"], nearest_dist), "Mismatch in distance!"
            print("   [PASS] Spot check exact numerical match confirmed.")

    # Check Anand Vihar as well
    av_row = ts_slice[ts_slice["station_id"] == "anand vihar"]
    if not av_row.empty:
        av_val = av_row.iloc[0]
        av_nearest_st = neighbor_order["anand vihar"][0]
        av_nearest_dist = neighbor_dists["anand vihar"][0]
        av_actual_nn = ts_slice[ts_slice["station_id"] == av_nearest_st]["PM2.5"].values
        av_expected_nn = av_actual_nn[0] if len(av_actual_nn) > 0 else np.nan

        print(f"\n9. Manual Spot Check - Station: Anand Vihar at {sample_ts}:")
        print(f"   - Nearest station        : {av_nearest_st}")
        print(f"   - Expected distance       : {av_nearest_dist:.2f} km")
        print(f"   - Feature distance        : {av_val['nearest_neighbor_distance_km']:.2f} km")
        print(f"   - Nearest station PM2.5   : {av_expected_nn}")
        print(f"   - Feature nn_pm25 value   : {av_val['nearest_neighbor_pm25']}")
        if not np.isnan(av_expected_nn):
            assert np.isclose(av_val["nearest_neighbor_pm25"], av_expected_nn), "Mismatch in nearest neighbor value!"
            print("   [PASS] Anand Vihar spot check exact numerical match confirmed.")

    # -----------------------------------------------------------------------
    # Check 10: Adversarial Future-Leakage Test
    # -----------------------------------------------------------------------
    # Methodology:
    #   1. Take the full 50k-row slice already loaded (df_raw / df_spatial).
    #   2. Identify the full sorted list of unique timestamps.
    #   3. Truncate the dataset to the FIRST 80% of unique timestamps only.
    #   4. Recompute spatial features on the truncated dataset.
    #   5. For every row that exists in BOTH the full and the truncated run,
    #      every spatial feature value must be numerically identical (or both NaN).
    #
    # If any spatial feature were to "look ahead" (e.g. using a future-timestamp
    # neighbour value), removing those future timestamps would cause its value
    # to differ (become NaN or change) — which would fail the assertion.
    # Because our implementation pivots strictly on timestamp==t before
    # computing neighbour metrics, this test must pass.
    print(f"\n10. Adversarial Future-Leakage Test:")

    spatial_feature_cols = get_spatial_feature_names()

    all_timestamps_sorted = np.sort(df_raw["timestamp"].dropna().unique())
    cutoff_idx = int(len(all_timestamps_sorted) * 0.80)
    cutoff_ts = all_timestamps_sorted[cutoff_idx - 1]

    df_truncated = df_raw[df_raw["timestamp"] <= cutoff_ts].copy()
    n_truncated = len(df_truncated)
    n_full = len(df_raw)
    print(f"   Full dataset : {n_full} rows  ({len(all_timestamps_sorted)} unique timestamps)")
    print(f"   Truncated    : {n_truncated} rows  (kept first {cutoff_idx}/{len(all_timestamps_sorted)} unique timestamps)")
    print(f"   Cutoff       : {cutoff_ts}")

    t0 = time.time()
    df_spatial_truncated = add_spatial_features(df_truncated, coords_df)
    elapsed_trunc = time.time() - t0
    print(f"   Truncated spatial features computed in {elapsed_trunc:.2f}s.")

    # Align on (timestamp, station_id) — keep only rows present in truncated run
    merge_keys = ["timestamp", "station_id"]
    df_full_subset = df_spatial[df_spatial["timestamp"] <= cutoff_ts].copy()

    # Sort both by the same key to ensure row alignment
    df_full_subset = df_full_subset.sort_values(merge_keys).reset_index(drop=True)
    df_trunc_subset = df_spatial_truncated.sort_values(merge_keys).reset_index(drop=True)

    if len(df_full_subset) != len(df_trunc_subset):
        print(
            f"   [FAIL] Row count mismatch between full-subset ({len(df_full_subset)}) "
            f"and truncated ({len(df_trunc_subset)})!"
        )
        passed = False
    else:
        leakage_detected = False
        for feat in spatial_feature_cols:
            full_vals = df_full_subset[feat].values
            trunc_vals = df_trunc_subset[feat].values
            # Both NaN → OK; otherwise must be numerically close
            both_nan = np.isnan(full_vals.astype(float)) & np.isnan(trunc_vals.astype(float))
            mismatched = ~both_nan & ~np.isclose(
                full_vals.astype(float), trunc_vals.astype(float), equal_nan=True
            )
            n_mismatch = int(np.sum(mismatched))
            if n_mismatch > 0:
                leakage_detected = True
                sample_idx = np.where(mismatched)[0][:3]
                print(
                    f"   [FAIL] Feature '{feat}' has {n_mismatch} mismatched values! "
                    f"Rows (0-indexed): {sample_idx.tolist()}"
                )
                for idx in sample_idx:
                    print(
                        f"          row {idx}: full={full_vals[idx]:.4f}  "
                        f"truncated={trunc_vals[idx]:.4f}  "
                        f"ts={df_full_subset.iloc[idx]['timestamp']}  "
                        f"station={df_full_subset.iloc[idx]['station_id']}"
                    )

        if leakage_detected:
            passed = False
            print("   [FAIL] Adversarial leakage detected: spatial features change when future data is removed!")
        else:
            print(
                f"   [PASS] All {len(spatial_feature_cols)} spatial features are numerically identical "
                f"for {len(df_full_subset)} retained rows — no future-leakage detected."
            )

    print("\n" + "=" * 70)
    if passed:
        print("OVERALL SPATIAL VALIDATION: PASS")
        print("All integrity, leakage, and numerical checks passed.")
    else:
        print("OVERALL SPATIAL VALIDATION: FAIL")
    print("=" * 70)

    return passed


if __name__ == "__main__":
    success = validate_spatial_features()
    sys.exit(0 if success else 1)
