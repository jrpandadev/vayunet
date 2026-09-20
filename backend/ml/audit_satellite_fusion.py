from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(
    "data/processed/fusion/delhi_forecasting_satellite.csv"
)


print("=" * 70)
print("SATELLITE FUSION DATASET AUDIT")
print("=" * 70)


# ============================================================
# Load
# ============================================================

df = pd.read_csv(INPUT_FILE)

print(f"\nRows: {len(df):,}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# Required columns
# ============================================================

required = {
    "Timestamp",
    "station_id",
    "satellite_no2_latest",
    "satellite_no2_age_hours",
}

missing = required - set(df.columns)

if missing:
    raise ValueError(
        f"Missing required columns: {sorted(missing)}"
    )


# ============================================================
# Timestamp parsing
# ============================================================

df["Timestamp"] = pd.to_datetime(
    df["Timestamp"],
    errors="coerce",
)

if df["Timestamp"].isna().any():
    raise RuntimeError(
        "Invalid forecast timestamps detected."
    )


# ============================================================
# Duplicate check
# ============================================================

duplicates = df.duplicated(
    subset=["station_id", "Timestamp"]
).sum()

print("\nDuplicate check:")
print(
    f"  Duplicate station/timestamp rows: {duplicates:,}"
)

if duplicates != 0:
    raise RuntimeError(
        "Duplicate station/timestamp rows detected."
    )


# ============================================================
# Satellite fields
# ============================================================

df["satellite_no2_latest"] = pd.to_numeric(
    df["satellite_no2_latest"],
    errors="coerce",
)

df["satellite_no2_age_hours"] = pd.to_numeric(
    df["satellite_no2_age_hours"],
    errors="coerce",
)


available = df["satellite_no2_latest"].notna()

print("\nSatellite availability:")
print(
    f"  Available: {available.sum():,} "
    f"({100 * available.mean():.2f}%)"
)

print(
    f"  Missing: {(~available).sum():,} "
    f"({100 * (~available).mean():.2f}%)"
)


# ============================================================
# Age validation
# ============================================================

ages = df.loc[
    available,
    "satellite_no2_age_hours",
]


negative_age = (ages < 0).sum()

over_72 = (ages > 72).sum()

print("\nSatellite age validation:")
print(f"  Negative ages: {negative_age:,}")
print(f"  Ages >72h: {over_72:,}")

if negative_age != 0:
    raise RuntimeError(
        "Negative satellite ages detected."
    )

if over_72 != 0:
    raise RuntimeError(
        "Satellite observations older than 72h detected."
    )


# ============================================================
# Age distribution
# ============================================================

print("\nSatellite age distribution:")

if len(ages):

    for q in [0.00, 0.25, 0.50, 0.75, 0.90, 0.95, 1.00]:

        print(
            f"  q{int(q * 100):02d}: "
            f"{ages.quantile(q):.2f} h"
        )


# ============================================================
# NO2 distribution
# ============================================================

no2 = df.loc[
    available,
    "satellite_no2_latest"
]

print("\nSatellite NO2 distribution:")

print(
    f"  Min: {no2.min():.6e}"
)

print(
    f"  Q1:  {no2.quantile(0.25):.6e}"
)

print(
    f"  Median: {no2.median():.6e}"
)

print(
    f"  Mean: {no2.mean():.6e}"
)

print(
    f"  Q3:  {no2.quantile(0.75):.6e}"
)

print(
    f"  Max: {no2.max():.6e}"
)

print(
    f"  +Inf: {np.isposinf(no2).sum():,}"
)

print(
    f"  -Inf: {np.isneginf(no2).sum():,}"
)


# ============================================================
# Station coverage
# ============================================================

station_stats = (
    df.groupby("station_id")
      .agg(
          rows=("station_id", "size"),
          satellite_available=(
              "satellite_no2_latest",
              lambda x: x.notna().sum(),
          ),
      )
)

station_stats["availability_pct"] = (
    100
    * station_stats["satellite_available"]
    / station_stats["rows"]
)

print("\nStation coverage:")

print(
    station_stats.to_string()
)


# ============================================================
# Existing feature sanity check
# ============================================================

print("\nForecasting feature sanity check:")

expected_existing = [
    "PM2.5",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "SO2",
    "CO",
    "Ozone",
    "AT",
    "RH",
    "WS",
    "WD",
    "SR",
    "BP",
    "segment_id",
    "hour",
    "day_of_week",
    "day_of_year",
    "month",
    "is_weekend",
    "WD_sin",
    "WD_cos",
    "PM2.5_lag_1h",
    "PM2.5_lag_3h",
    "PM2.5_lag_6h",
    "PM2.5_lag_12h",
    "PM2.5_lag_24h",
    "PM2.5_lag_48h",
    "PM2.5_lag_72h",
    "PM2.5_roll_mean_6h",
    "PM2.5_roll_mean_24h",
    "PM2.5_roll_std_24h",
]

missing_existing = [
    c for c in expected_existing
    if c not in df.columns
]

if missing_existing:
    raise RuntimeError(
        f"Existing feature columns missing: {missing_existing}"
    )

print(
    f"  Required existing features present: "
    f"{len(expected_existing)}/{len(expected_existing)}"
)


# ============================================================
# Split definition
# ============================================================

TRAIN_END = pd.Timestamp(
    "2025-03-15 12:00:00"
)

VALID_END = pd.Timestamp(
    "2025-11-21 22:00:00"
)


df["split"] = np.select(
    [
        df["Timestamp"] < TRAIN_END,
        df["Timestamp"] < VALID_END,
    ],
    [
        "train",
        "validation",
    ],
    default="test",
)


# ============================================================
# Split statistics
# ============================================================

print("\nSplit-level satellite coverage:")

split_stats = (
    df.groupby("split")
      .agg(
          rows=("split", "size"),
          satellite_available=(
              "satellite_no2_latest",
              lambda x: x.notna().sum(),
          ),
      )
)

split_stats["availability_pct"] = (
    100
    * split_stats["satellite_available"]
    / split_stats["rows"]
)

print(
    split_stats.to_string()
)


# ============================================================
# Split NO2 distribution
# ============================================================

print("\nSplit-level NO2 statistics:")

for split in ["train", "validation", "test"]:

    values = df.loc[
        (df["split"] == split)
        & available,
        "satellite_no2_latest",
    ]

    print(f"\n{split.upper()}")

    if values.empty:
        print("  No satellite observations.")
        continue

    print(
        f"  Count: {len(values):,}"
    )

    print(
        f"  Median: {values.median():.6e}"
    )

    print(
        f"  Mean: {values.mean():.6e}"
    )

    print(
        f"  Q1: {values.quantile(0.25):.6e}"
    )

    print(
        f"  Q3: {values.quantile(0.75):.6e}"
    )


# ============================================================
# Final
# ============================================================

print("\n" + "=" * 70)
print("SATELLITE FUSION AUDIT COMPLETE")
print("=" * 70)
