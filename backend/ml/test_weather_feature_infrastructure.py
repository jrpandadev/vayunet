"""
Test Suite for Horizon-Specific Weather Feature Infrastructure.

Validates:
1. Exact feature counts (6h: 47, 24h: 44, 72h: 42).
2. Exact feature naming and ordering matching models/horizon_features.json.
3. Numerical match against data/processed/delhi_forecasting_weather.csv.
4. Boundary layer height (PBL) NaN preservation (no imputation).
5. Baseline calculation invariance across horizons and standalone baseline.
6. Multi-station, multi-timestamp verification across diverse seasons.
"""

import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.feature_builder import FeatureBuilder, build_features, build_all_horizon_features
DATA_PATH = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
METADATA_PATH = BASE_DIR / "models" / "horizon_features.json"


def test_metadata_alignment():
    print("\n--- Test 1: Metadata Alignment & Counts ---")
    with open(METADATA_PATH) as f:
        meta = json.load(f)

    builder = FeatureBuilder()

    expected_counts = {"6h": 47, "24h": 44, "72h": 42}
    for h, expected_cnt in expected_counts.items():
        cols = builder.get_feature_cols(h)
        assert len(cols) == expected_cnt, f"Count mismatch for {h}: {len(cols)} != {expected_cnt}"
        assert cols == meta["horizon_features"][h], f"Order mismatch for {h} against metadata JSON"
        assert cols[:42] == meta["baseline_features"], f"Baseline mismatch in first 42 features for {h}"
        print(f"  [OK] Horizon {h}: exactly {expected_cnt} features, order matches metadata.")

    baseline_cols = builder.get_feature_cols(None)
    assert len(baseline_cols) == 42
    assert baseline_cols == meta["baseline_features"]
    print("  [OK] Standalone baseline: exactly 42 features.")


def test_station_timestamp_combinations():
    print("\n--- Test 2: Multi-Station & Multi-Timestamp Numerical Parity ---")
    builder = FeatureBuilder()
    raw_df = pd.read_csv(DATA_PATH)
    if "timestamp" in raw_df.columns:
        raw_df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    raw_df["Timestamp"] = pd.to_datetime(raw_df["Timestamp"])

    # Select representative station and timestamp combinations
    test_cases = [
        # (station, timestamp description / query)
        ("anand vihar", "2022-01-15 08:00:00"),  # Winter morning peak
        ("r k puram", "2023-06-20 14:00:00"),    # Summer afternoon
        ("jahangirpuri", "2024-08-10 18:00:00"), # Monsoon evening
        ("wazirpur", "2025-11-05 22:00:00"),     # Post-monsoon smog
        ("ito", "2026-03-01 10:00:00"),          # Spring morning
    ]

    for station, ts_str in test_cases:
        ts = pd.to_datetime(ts_str)
        mask = (raw_df["station_id"] == station) & (raw_df["Timestamp"] == ts)
        assert mask.any(), f"Test point not found: {station} at {ts}"
        source_row = raw_df[mask].iloc[0]

        # Generate all horizons at once
        all_feats = builder.build_all_horizon_features(station, ts)

        # 1. Check 6h
        df_6h = all_feats["6h"]
        assert df_6h.shape == (1, 47)
        # Check weather features
        for w_col in ["shortwave_radiation", "dew_point_2m", "wind_gusts_10m", "relative_humidity_2m", "boundary_layer_height"]:
            exp_val = source_row[w_col]
            got_val = df_6h[w_col].iloc[0]
            if pd.isna(exp_val):
                assert pd.isna(got_val), f"Expected NaN for {w_col} on {station} at {ts}, got {got_val}"
            else:
                assert abs(got_val - float(exp_val)) < 1e-5, f"Mismatch for {w_col}: got {got_val}, expected {exp_val}"

        # 2. Check 24h
        df_24h = all_feats["24h"]
        assert df_24h.shape == (1, 44)
        for w_col in ["temperature_2m", "dew_point_2m"]:
            exp_val = source_row[w_col]
            got_val = df_24h[w_col].iloc[0]
            if pd.isna(exp_val):
                assert pd.isna(got_val), f"Expected NaN for {w_col} on {station} at {ts}, got {got_val}"
            else:
                assert abs(got_val - float(exp_val)) < 1e-5, f"Mismatch for {w_col}: got {got_val}, expected {exp_val}"

        # 3. Check 72h
        df_72h = all_feats["72h"]
        assert df_72h.shape == (1, 42)
        # Check that no weather columns exist in 72h
        for w_col in ["temperature_2m", "shortwave_radiation", "boundary_layer_height"]:
            assert w_col not in df_72h.columns

        print(f"  [OK] Station: {station:15s} | Timestamp: {ts_str} | Verified 6h (47), 24h (44), 72h (42)")


def test_missing_pbl_nan_preservation():
    print("\n--- Test 3: Missing PBL NaN Preservation (No Imputation) ---")
    builder = FeatureBuilder()
    raw_df = builder.df

    # Pick 5 distinct stations at timestamps where boundary_layer_height is NaN
    nan_pbl = raw_df[raw_df["boundary_layer_height"].isna()]
    assert len(nan_pbl) > 0, "No missing PBL records found!"

    # Sample across different stations
    sampled_nan_rows = nan_pbl.groupby("station_id").first().reset_index()
    print(f"  Testing {len(sampled_nan_rows)} stations with missing PBL timestamps:")

    for _, row in sampled_nan_rows.iterrows():
        station = row["station_id"]
        ts = row["Timestamp"]
        df_6h = builder.build_features(station, ts, horizon="6h")
        pbl_val = df_6h["boundary_layer_height"].iloc[0]
        assert np.isnan(pbl_val), f"PBL was imputed for {station} at {ts}! Got: {pbl_val}"
        print(f"    * Station: {station:15s} | Timestamp: {ts} | PBL value = NaN (Strictly Preserved)")


def test_baseline_calculation_invariance():
    print("\n--- Test 4: Baseline Calculation Invariance ---")
    builder = FeatureBuilder()
    raw_df = builder.df
    sample = raw_df.dropna(subset=["PM2.5"]).sample(n=10, random_state=123)

    for _, row in sample.iterrows():
        station = row["station_id"]
        ts = row["Timestamp"]

        df_base = builder.build_features(station, ts, horizon=None)
        df_6h = builder.build_features(station, ts, horizon="6h")
        df_24h = builder.build_features(station, ts, horizon="24h")
        df_72h = builder.build_features(station, ts, horizon="72h")

        # The first 42 columns of df_6h, df_24h, df_72h must match df_base exactly
        for col in builder.baseline_feature_cols:
            b = df_base[col].iloc[0]
            h6 = df_6h[col].iloc[0]
            h24 = df_24h[col].iloc[0]
            h72 = df_72h[col].iloc[0]

            if pd.isna(b):
                assert pd.isna(h6) and pd.isna(h24) and pd.isna(h72)
            else:
                assert b == h6 == h24 == h72

    print("  [OK] Baseline feature calculations are completely identical across all horizons.")


if __name__ == "__main__":
    print("======================================================================")
    print("RUNNING FEATURE INFRASTRUCTURE VALIDATION SUITE")
    print("======================================================================")
    test_metadata_alignment()
    test_station_timestamp_combinations()
    test_missing_pbl_nan_preservation()
    test_baseline_calculation_invariance()
    print("\n======================================================================")
    print("ALL TESTS PASSED WITH 100% COMPLIANCE")
    print("======================================================================")
