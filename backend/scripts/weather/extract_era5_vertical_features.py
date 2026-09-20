#!/usr/bin/env python3
"""
VayuNet — ERA5 Vertical Meteorology Feature Extractor
Extracts vertical stability, wind shear, and lapse rates across pressure levels
(925, 850, 700 hPa) from the raw pilot reanalysis file.
Preserves raw data untouched and outputs a clean intermediate representation.
"""

from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_ERA5_CSV = BASE_DIR / "data" / "raw" / "weather" / "era5_pressure_levels" / "era5_delhi_pilot.csv"
OUT_DIR = BASE_DIR / "data" / "processed" / "weather"
OUT_PARQUET = OUT_DIR / "era5_vertical_features.parquet"

def potential_temp(t_kelvin, p_hpa):
    return t_kelvin * (1000.0 / p_hpa) ** 0.286

def extract_vertical_features():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_ERA5_CSV.exists():
        raise FileNotFoundError(f"Raw ERA5 pilot not found at: {RAW_ERA5_CSV}")

    df = pd.read_csv(RAW_ERA5_CSV)
    time_col = "valid_time" if "valid_time" in df.columns else "time"
    df[time_col] = pd.to_datetime(df[time_col])

    # Pivot pressure levels: 925, 850, 700
    pivoted = df.pivot(index=time_col, columns="pressure_level", values=["u", "v", "t", "r", "z", "w"])
    pivoted.columns = [f"{var}_{int(level)}hpa" for var, level in pivoted.columns]
    features_df = pivoted.reset_index().rename(columns={time_col: "timestamp"})

    # 1. Wind speeds
    for p in [925, 850, 700]:
        features_df[f"wind_speed_{p}hpa"] = np.sqrt(features_df[f"u_{p}hpa"]**2 + features_df[f"v_{p}hpa"]**2)

    # 2. Vertical wind shear
    features_df["wind_shear_925_850"] = np.sqrt(
        (features_df["u_850hpa"] - features_df["u_925hpa"])**2 +
        (features_df["v_850hpa"] - features_df["v_925hpa"])**2
    )
    features_df["wind_shear_925_700"] = np.sqrt(
        (features_df["u_700hpa"] - features_df["u_925hpa"])**2 +
        (features_df["v_700hpa"] - features_df["v_925hpa"])**2
    )

    # 3. Stability & Inversion (Potential Temperature)
    theta_925 = potential_temp(features_df["t_925hpa"], 925)
    theta_850 = potential_temp(features_df["t_850hpa"], 850)
    theta_700 = potential_temp(features_df["t_700hpa"], 700)

    features_df["theta_gradient_925_850"] = theta_850 - theta_925
    features_df["theta_gradient_925_700"] = theta_700 - theta_925
    features_df["temperature_inversion_flag"] = (features_df["t_850hpa"] > features_df["t_925hpa"]).astype(int)

    # Sort and save
    features_df = features_df.sort_values("timestamp").reset_index(drop=True)
    features_df.to_parquet(OUT_PARQUET, index=False)
    print(f"Saved {len(features_df):,} vertical feature rows to: {OUT_PARQUET}")
    print(f"Columns: {list(features_df.columns)}")

if __name__ == "__main__":
    extract_vertical_features()
