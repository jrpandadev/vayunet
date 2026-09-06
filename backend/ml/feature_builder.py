"""
Feature Builder for VayuNet PM2.5 Forecasting Pipeline.

Constructs the exact 42 model input features expected by the trained XGBoost
forecasting models (6h, 24h, 72h) for any given station_id and timestamp.

Features and schema are strictly aligned with models/features.json and
the training pipeline in ml/train_forecast.py.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
PROCESSED_BASELINE_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"
FEATURES_FILE = BASE_DIR / "models" / "features.json"
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"

ALL_STATIONS = [
    "anand vihar",
    "aya nagar",
    "bawana",
    "ito",
    "jahangirpuri",
    "narela",
    "punjabi bagh",
    "r k puram",
    "vivek vihar",
    "wazirpur",
]

LAG_HOURS = [1, 3, 6, 12, 24, 48, 72]

BASE_MEASUREMENT_COLS = [
    "PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "SO2", "CO", "Ozone",
    "AT", "RH", "WS", "WD", "SR", "BP"
]

LOCKED_WEATHER_FEATURES: dict[str, list[str]] = {
    "6h": [
        "shortwave_radiation",
        "dew_point_2m",
        "wind_gusts_10m",
        "relative_humidity_2m",
        "boundary_layer_height",
    ],
    "24h": [
        "temperature_2m",
        "dew_point_2m",
    ],
    "72h": [],
}


class FeatureBuilder:
    """
    Standalone feature constructor for VayuNet.
    Reconstructs exact feature vectors required by the models:
      - 6h : 42 baseline + 5 weather = 47 features
      - 24h: 42 baseline + 2 weather = 44 features
      - 72h: 42 baseline + 0 weather = 42 features
      - baseline (horizon=None): 42 baseline features
    """

    def __init__(
        self,
        data_source: Optional[Union[pd.DataFrame, str, Path]] = None,
        features_path: Optional[Union[str, Path]] = None,
        horizon_metadata_path: Optional[Union[str, Path]] = None,
    ):
        # 1. Load baseline feature schema (42 features)
        f_path = Path(features_path) if features_path else FEATURES_FILE
        if not f_path.exists():
            raise FileNotFoundError(f"Feature metadata file not found at {f_path}")
        with open(f_path, "r") as f:
            self.baseline_feature_cols: list[str] = json.load(f)
        self.feature_cols = self.baseline_feature_cols  # Backwards compatibility

        # 2. Setup horizon-specific feature schemas
        meta_path = Path(horizon_metadata_path) if horizon_metadata_path else HORIZON_METADATA_FILE
        if meta_path.exists():
            with open(meta_path, "r") as f:
                meta = json.load(f)
                self.horizon_features: dict[str, list[str]] = meta.get("horizon_features", {})
                self.locked_weather: dict[str, list[str]] = meta.get("locked_weather_features", LOCKED_WEATHER_FEATURES)
        else:
            self.locked_weather = LOCKED_WEATHER_FEATURES
            self.horizon_features = {
                h: self.baseline_feature_cols + self.locked_weather.get(h, [])
                for h in ["6h", "24h", "72h"]
            }

        # 3. Load historical observations
        if data_source is None:
            if PROCESSED_DATA_FILE.exists():
                data_source = PROCESSED_DATA_FILE
            else:
                data_source = PROCESSED_BASELINE_DATA_FILE
        
        if isinstance(data_source, (str, Path)):
            src_path = Path(data_source)
            if not src_path.exists():
                raise FileNotFoundError(f"Dataset not found at {src_path}")
            df = pd.read_csv(src_path)
        elif isinstance(data_source, pd.DataFrame):
            df = data_source.copy()
        else:
            raise TypeError("data_source must be a DataFrame or file path")

        # Standardize timestamp column name (delhi_forecasting_weather uses 'timestamp')
        if "timestamp" in df.columns and "Timestamp" not in df.columns:
            df = df.rename(columns={"timestamp": "Timestamp"})

        if "Timestamp" not in df.columns or "station_id" not in df.columns:
            raise ValueError("Data source must contain 'Timestamp' (or 'timestamp') and 'station_id' columns")

        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        # Ensure proper sorting by station and timestamp
        df = df.sort_values(by=["station_id", "Timestamp"]).reset_index(drop=True)

        self.df = df
        # Pre-index by (station_id, Timestamp) for O(1) exact lookups
        self.indexed_df = df.set_index(["station_id", "Timestamp"]).sort_index()

    def get_feature_cols(self, horizon: Optional[str] = None) -> list[str]:
        """
        Get expected feature column names for a given horizon.
        If horizon is None, returns the 42 baseline feature column names.
        """
        if horizon is None:
            return list(self.baseline_feature_cols)
        h_key = str(horizon).strip().lower()
        if h_key in ["6", "24", "72"]:
            h_key = f"{h_key}h"
        if h_key not in self.horizon_features:
            raise ValueError(f"Invalid horizon '{horizon}'. Must be one of {list(self.horizon_features.keys())} or None.")
        return list(self.horizon_features[h_key])

    def build_features(
        self,
        station_id: str,
        timestamp: Union[str, pd.Timestamp],
        horizon: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Build model input features for a given station, timestamp, and horizon.

        Args:
            station_id: CPCB station identifier (e.g., 'anand vihar')
            timestamp: Target observation timestamp (string or Timestamp)
            horizon: Target forecast horizon ('6h', '24h', '72h', or None).
                     If None: returns 42 baseline features (for backwards compatibility).
                     If '6h': returns 42 baseline + 5 weather = 47 features.
                     If '24h': returns 42 baseline + 2 weather = 44 features.
                     If '72h': returns 42 baseline + 0 weather = 42 features.

        Returns:
            pd.DataFrame: 1-row DataFrame containing the features in exact model order.
        """
        station = str(station_id).strip().lower()
        ts = pd.to_datetime(timestamp)

        if (station, ts) not in self.indexed_df.index:
            raise KeyError(
                f"Observation not found for station '{station}' at timestamp '{ts}'"
            )

        target_row = self.indexed_df.loc[(station, ts)]
        if isinstance(target_row, pd.DataFrame):
            target_row = target_row.iloc[0]

        segment = target_row.get("segment_id", None)

        features: dict[str, float] = {}

        # 1. Base current pollution and meteorological measurements (UNTOUCHED)
        for col in BASE_MEASUREMENT_COLS:
            val = target_row.get(col, np.nan)
            features[col] = float(val) if pd.notna(val) else np.nan

        # 2. Timestamp / calendar features (UNTOUCHED)
        features["hour"] = float(ts.hour)
        features["day_of_week"] = float(ts.dayofweek)
        features["day_of_year"] = float(ts.dayofyear)
        features["month"] = float(ts.month)
        features["is_weekend"] = float(int(ts.dayofweek >= 5))

        # 3. Circular wind direction features (UNTOUCHED)
        wd_val = target_row.get("WD", np.nan)
        if pd.notna(wd_val):
            rad = np.deg2rad(float(wd_val))
            features["WD_sin"] = float(np.sin(rad))
            features["WD_cos"] = float(np.cos(rad))
        else:
            features["WD_sin"] = np.nan
            features["WD_cos"] = np.nan

        # 4. Exact timestamp-based lag features (UNTOUCHED)
        for h in LAG_HOURS:
            lag_ts = ts - pd.Timedelta(hours=h)
            lag_key = f"PM2.5_lag_{h}h"
            if (station, lag_ts) in self.indexed_df.index:
                lag_row = self.indexed_df.loc[(station, lag_ts)]
                if isinstance(lag_row, pd.DataFrame):
                    lag_row = lag_row.iloc[0]
                
                # Verify segment continuity if segment_id is present
                lag_seg = lag_row.get("segment_id", None)
                if segment is not None and lag_seg is not None and lag_seg != segment:
                    features[lag_key] = np.nan
                else:
                    pm_val = lag_row.get("PM2.5", np.nan)
                    features[lag_key] = float(pm_val) if pd.notna(pm_val) else np.nan
            else:
                features[lag_key] = np.nan

        # 5. Rolling PM2.5 features (UNTOUCHED)
        start_ts = ts - pd.Timedelta(hours=72)
        try:
            station_segment_history = self.df[
                (self.df["station_id"] == station)
                & (self.df["Timestamp"] >= start_ts)
                & (self.df["Timestamp"] <= ts)
            ]
            if segment is not None:
                station_segment_history = station_segment_history[
                    station_segment_history["segment_id"] == segment
                ]

            if not station_segment_history.empty:
                pm25_ts = (
                    station_segment_history.set_index("Timestamp")["PM2.5"]
                    .resample("h")
                    .mean()
                )
                rm6 = pm25_ts.rolling(window=6, min_periods=6).mean()
                rm24 = pm25_ts.rolling(window=24, min_periods=24).mean()
                rs24 = pm25_ts.rolling(window=24, min_periods=24).std(ddof=1)

                val_rm6 = rm6.get(ts, np.nan)
                val_rm24 = rm24.get(ts, np.nan)
                val_rs24 = rs24.get(ts, np.nan)

                features["PM2.5_roll_mean_6h"] = float(val_rm6) if pd.notna(val_rm6) else np.nan
                features["PM2.5_roll_mean_24h"] = float(val_rm24) if pd.notna(val_rm24) else np.nan
                features["PM2.5_roll_std_24h"] = float(val_rs24) if pd.notna(val_rs24) else np.nan
            else:
                features["PM2.5_roll_mean_6h"] = np.nan
                features["PM2.5_roll_mean_24h"] = np.nan
                features["PM2.5_roll_std_24h"] = np.nan
        except Exception:
            features["PM2.5_roll_mean_6h"] = np.nan
            features["PM2.5_roll_mean_24h"] = np.nan
            features["PM2.5_roll_std_24h"] = np.nan

        # 6. One-hot station encoding (UNTOUCHED)
        for s in ALL_STATIONS:
            features[f"station_id_{s}"] = 1.0 if station == s else 0.0

        # 7. Horizon-specific selected weather features
        if horizon is not None:
            h_key = str(horizon).strip().lower()
            if h_key in ["6", "24", "72"]:
                h_key = f"{h_key}h"
            if h_key not in self.horizon_features:
                raise ValueError(
                    f"Invalid horizon '{horizon}'. Must be one of {list(self.horizon_features.keys())} or None."
                )
            
            weather_cols = self.locked_weather.get(h_key, [])
            for w_col in weather_cols:
                w_val = target_row.get(w_col, np.nan)
                # Strict requirement: Missing PBL remains NaN and is NOT imputed
                features[w_col] = float(w_val) if pd.notna(w_val) else np.nan

            expected_cols = self.horizon_features[h_key]
        else:
            expected_cols = self.baseline_feature_cols

        # Build single-row DataFrame and order columns strictly by expected_cols
        res_df = pd.DataFrame([features])
        
        for col in expected_cols:
            if col not in res_df.columns:
                res_df[col] = np.nan

        return res_df[expected_cols].copy()

    def build_all_horizon_features(
        self,
        station_id: str,
        timestamp: Union[str, pd.Timestamp],
    ) -> dict[str, pd.DataFrame]:
        """
        Build feature DataFrames for all horizons ('6h', '24h', '72h')
        for the given station and timestamp.

        Returns:
            dict with keys '6h' (47 features), '24h' (44 features), '72h' (42 features).
        """
        return {
            h: self.build_features(station_id, timestamp, horizon=h)
            for h in ["6h", "24h", "72h"]
        }


# Global module-level cached builder for convenient imports
_default_builder: Optional[FeatureBuilder] = None


def build_features(
    station_id: str,
    timestamp: Union[str, pd.Timestamp],
    horizon: Optional[str] = None,
    builder: Optional[FeatureBuilder] = None,
) -> pd.DataFrame:
    """
    Exposed API function to build model feature DataFrame
    for any station, timestamp, and horizon.

    Args:
        station_id: Name of the station (e.g., 'anand vihar')
        timestamp: Observation timestamp
        horizon: Optional target horizon ('6h', '24h', '72h', or None for baseline)
        builder: Optional pre-initialized FeatureBuilder instance

    Returns:
        pd.DataFrame: 1-row DataFrame with exact columns in model order.
    """
    global _default_builder
    if builder is not None:
        return builder.build_features(station_id, timestamp, horizon=horizon)
    if _default_builder is None:
        _default_builder = FeatureBuilder()
    return _default_builder.build_features(station_id, timestamp, horizon=horizon)


def build_all_horizon_features(
    station_id: str,
    timestamp: Union[str, pd.Timestamp],
    builder: Optional[FeatureBuilder] = None,
) -> dict[str, pd.DataFrame]:
    """
    Build feature DataFrames for all horizons ('6h', '24h', '72h')
    for the given station and timestamp.
    """
    global _default_builder
    if builder is not None:
        return builder.build_all_horizon_features(station_id, timestamp)
    if _default_builder is None:
        _default_builder = FeatureBuilder()
    return _default_builder.build_all_horizon_features(station_id, timestamp)


def verify_feature_builder(
    builder: FeatureBuilder,
    num_samples: int = 100,
    tolerance: float = 1e-5,
) -> bool:
    """
    Comprehensive verification routine asserting:
    1. 6h produces exactly 47 features
    2. 24h produces exactly 44 features
    3. 72h produces exactly 42 features
    4. feature names/order exactly match model metadata
    5. numerical values match source data (both baseline and weather)
    6. missing PBL remains NaN and is NOT imputed
    7. baseline feature calculations are completely unchanged
    """
    print("=" * 70)
    print("HORIZON-SPECIFIC FEATURE BUILDER VERIFICATION")
    print("=" * 70)

    # 1. Feature count & metadata order validation
    expected_counts = {"6h": 47, "24h": 44, "72h": 42}
    print("1. Validating feature counts and ordering against metadata:")
    for h, expected_cnt in expected_counts.items():
        cols = builder.get_feature_cols(h)
        cnt = len(cols)
        print(f"   Horizon {h:3s}: {cnt} features (expected {expected_cnt})")
        assert cnt == expected_cnt, f"Feature count mismatch for {h}: got {cnt}, expected {expected_cnt}"
        
        # Verify order matches horizon_features metadata
        meta_cols = builder.horizon_features[h]
        assert cols == meta_cols, f"Feature ordering mismatch for {h}"
        
        # Verify baseline 42 features are the first 42 in identical order
        assert cols[:42] == builder.baseline_feature_cols, f"Baseline feature order altered in {h}"

    cols_none = builder.get_feature_cols(None)
    assert len(cols_none) == 42, f"Baseline count mismatch: got {len(cols_none)}, expected 42"
    assert cols_none == builder.baseline_feature_cols, "Baseline features altered"
    print("   All feature counts and ordering checks: PASSED [OK]\n")

    # 2. Numerical validation across random samples
    print(f"2. Validating numerical equivalence on {num_samples} sample observations:")
    raw_df = builder.df
    candidates = raw_df.dropna(subset=["PM2.5"]).copy()
    if len(candidates) < num_samples:
        num_samples = len(candidates)

    sample_indices = random.sample(range(len(candidates)), num_samples)
    encoded_df = pd.get_dummies(candidates, columns=["station_id"], dtype=int)

    mismatches = 0
    nan_mismatches = 0
    max_diff = 0.0

    for idx in sample_indices:
        orig_row = candidates.iloc[idx]
        enc_row = encoded_df.iloc[idx]
        station = orig_row["station_id"]
        ts = orig_row["Timestamp"]

        # Test all horizons
        for h in ["6h", "24h", "72h"]:
            recon_df = builder.build_features(station, ts, horizon=h)
            recon_vec = recon_df.iloc[0]
            expected_cols = builder.get_feature_cols(h)

            assert len(recon_df.columns) == len(expected_cols)
            assert list(recon_df.columns) == expected_cols

            for col in expected_cols:
                val_recon = recon_vec[col]

                # Stored source value
                if col in enc_row:
                    val_stored = enc_row[col]
                elif col.startswith("station_id_"):
                    val_stored = 0.0
                else:
                    val_stored = np.nan

                is_recon_nan = pd.isna(val_recon)
                is_stored_nan = pd.isna(val_stored)

                if is_recon_nan and is_stored_nan:
                    continue
                elif is_recon_nan != is_stored_nan:
                    nan_mismatches += 1
                    mismatches += 1
                else:
                    diff = abs(float(val_recon) - float(val_stored))
                    if diff > tolerance:
                        mismatches += 1
                        max_diff = max(max_diff, diff)

    print(f"   Tested observations        : {num_samples}")
    print(f"   Feature mismatches         : {mismatches}")
    print(f"   Missing-value mismatches   : {nan_mismatches}")
    print(f"   Maximum numerical diff     : {max_diff:.8f}")
    if mismatches == 0 and nan_mismatches == 0:
        print("   Numerical validation       : PASSED [OK]\n")
    else:
        print("   Numerical validation       : FAILED [X]\n")
        return False

    # 3. Explicit Missing PBL NaN preservation check
    print("3. Validating missing boundary_layer_height (PBL) NaN preservation:")
    pbl_nan_rows = raw_df[raw_df["boundary_layer_height"].isna()]
    print(f"   Total rows with NaN PBL in dataset: {len(pbl_nan_rows)} ({len(pbl_nan_rows)/len(raw_df)*100:.2f}%)")
    
    if not pbl_nan_rows.empty:
        pbl_sample_indices = random.sample(range(len(pbl_nan_rows)), min(20, len(pbl_nan_rows)))
        for p_idx in pbl_sample_indices:
            row = pbl_nan_rows.iloc[p_idx]
            st = row["station_id"]
            t = row["Timestamp"]
            feat_6h = builder.build_features(st, t, horizon="6h")
            pbl_val = feat_6h["boundary_layer_height"].iloc[0]
            assert pd.isna(pbl_val), f"PBL was improperly imputed for {st} at {t}! Got {pbl_val}"
        print("   PBL NaN preservation check: PASSED (NaN verified, not imputed) [OK]\n")

    # 4. Explicit Valid PBL value preservation check
    print("4. Validating valid boundary_layer_height numerical parity:")
    pbl_valid_rows = raw_df[raw_df["boundary_layer_height"].notna()]
    if not pbl_valid_rows.empty:
        pbl_valid_samples = random.sample(range(len(pbl_valid_rows)), min(20, len(pbl_valid_rows)))
        for pv_idx in pbl_valid_samples:
            row = pbl_valid_rows.iloc[pv_idx]
            st = row["station_id"]
            t = row["Timestamp"]
            expected_pbl = float(row["boundary_layer_height"])
            feat_6h = builder.build_features(st, t, horizon="6h")
            pbl_val = float(feat_6h["boundary_layer_height"].iloc[0])
            assert abs(pbl_val - expected_pbl) < 1e-5, f"PBL value mismatch: {pbl_val} vs {expected_pbl}"
        print("   Valid PBL parity check     : PASSED [OK]\n")

    # 5. Baseline identity check: Ensure baseline feature values are identical across all horizons
    print("5. Validating baseline feature values are completely unchanged across horizons:")
    for idx in sample_indices[:20]:
        orig_row = candidates.iloc[idx]
        st = orig_row["station_id"]
        t = orig_row["Timestamp"]

        base_vec = builder.build_features(st, t, horizon=None).iloc[0]
        h6_vec = builder.build_features(st, t, horizon="6h").iloc[0]
        h24_vec = builder.build_features(st, t, horizon="24h").iloc[0]
        h72_vec = builder.build_features(st, t, horizon="72h").iloc[0]

        for col in builder.baseline_feature_cols:
            b_val = base_vec[col]
            h6_val = h6_vec[col]
            h24_val = h24_vec[col]
            h72_val = h72_vec[col]

            for h_name, h_val in [("6h", h6_val), ("24h", h24_val), ("72h", h72_val)]:
                if pd.isna(b_val):
                    assert pd.isna(h_val), f"Baseline NaN mismatch for {col} in {h_name}"
                else:
                    assert abs(float(b_val) - float(h_val)) < 1e-8, f"Baseline value mismatch for {col} in {h_name}"
    print("   Baseline invariance check  : PASSED [OK]\n")

    print("=" * 70)
    print("ALL VERIFICATIONS PASSED SUCCESSFULLY [OK]")
    print("=" * 70)
    return True


def main():
    print("Loading FeatureBuilder and historical dataset...")
    builder = FeatureBuilder()
    print(f"Successfully loaded {len(builder.baseline_feature_cols)} baseline features.")
    for h in ["6h", "24h", "72h"]:
        print(f"  - Horizon {h:3s}: {len(builder.get_feature_cols(h))} features")

    # Run verification
    random.seed(42)
    passed = verify_feature_builder(builder, num_samples=100)

    if not passed:
        raise RuntimeError("FeatureBuilder verification failed!")

    print("\n" + "=" * 70)
    print("CLI DEMONSTRATION")
    print("=" * 70)

    # Pick a recent valid observation from the dataset
    demo_row = builder.df.dropna(subset=["PM2.5"]).iloc[-1]
    station = demo_row["station_id"]
    ts = demo_row["Timestamp"]
    curr_pm25 = demo_row["PM2.5"]

    print(f"station_id   : {station}")
    print(f"timestamp    : {ts}")
    print(f"current PM2.5: {curr_pm25}\n")

    for h in ["6h", "24h", "72h"]:
        df_h = build_features(station, ts, horizon=h, builder=builder)
        print(f"--- Horizon {h} (Total Features: {len(df_h.columns)}) ---")
        added_weather = builder.locked_weather[h]
        if added_weather:
            print(f"  Added weather features ({len(added_weather)}):")
            for w in added_weather:
                val = df_h[w].iloc[0]
                val_str = f"{val:.4f}" if pd.notna(val) else "NaN"
                print(f"    * {w:25s} = {val_str}")
        else:
            print("  Added weather features: None (Baseline only)")
        print()

    print("=" * 70)
    print("FEATURE BUILDER READY")
    print("=" * 70)


if __name__ == "__main__":
    main()
