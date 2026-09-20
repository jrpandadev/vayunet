from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# Configuration
# ============================================================

FORECAST_FILE = Path(
    "data/processed/delhi_forecasting.csv"
)

SATELLITE_FILE = Path(
    "data/raw/satellite/delhi_s5p_no2.csv"
)

OUTPUT_FILE = Path(
    "data/processed/fusion/delhi_forecasting_satellite.csv"
)

AUDIT_FILE = Path(
    "reports/satellite/satellite_fusion_audit.csv"
)

MAX_SATELLITE_AGE_HOURS = 72.0


# ============================================================
# Load data
# ============================================================

print("=" * 70)
print("BUILDING LEAKAGE-SAFE SATELLITE FUSION DATASET")
print("=" * 70)

print("\nLoading forecasting dataset...")
forecast = pd.read_csv(FORECAST_FILE)

print(f"Forecast rows: {len(forecast):,}")

print("\nLoading Sentinel-5P dataset...")
satellite = pd.read_csv(SATELLITE_FILE)

print(f"Satellite rows: {len(satellite):,}")


# ============================================================
# Validate schemas
# ============================================================

required_forecast = {
    "Timestamp",
    "station_id",
}

required_satellite = {
    "station_id",
    "timestamp",
    "tropospheric_no2",
}

missing_forecast = (
    required_forecast - set(forecast.columns)
)

missing_satellite = (
    required_satellite - set(satellite.columns)
)

if missing_forecast:
    raise ValueError(
        f"Forecast dataset missing columns: "
        f"{sorted(missing_forecast)}"
    )

if missing_satellite:
    raise ValueError(
        f"Satellite dataset missing columns: "
        f"{sorted(missing_satellite)}"
    )


# ============================================================
# Parse timestamps
# ============================================================

forecast["Timestamp"] = pd.to_datetime(
    forecast["Timestamp"],
    errors="coerce",
)

satellite["timestamp"] = pd.to_datetime(
    satellite["timestamp"],
    errors="coerce",
    utc=True,
)

if forecast["Timestamp"].isna().any():
    raise ValueError(
        "Forecast dataset contains invalid timestamps."
    )

if satellite["timestamp"].isna().any():
    raise ValueError(
        "Satellite dataset contains invalid timestamps."
    )


# Forecast timestamps are naive local IST timestamps.
# Localize explicitly rather than assuming UTC.
forecast["forecast_timestamp_utc"] = (
    forecast["Timestamp"]
    .dt.tz_localize("Asia/Kolkata")
    .dt.tz_convert("UTC")
)


# ============================================================
# Normalize station IDs
# ============================================================

forecast["station_id"] = (
    forecast["station_id"]
    .astype(str)
    .str.strip()
)

satellite["station_id"] = (
    satellite["station_id"]
    .astype(str)
    .str.strip()
)


# ============================================================
# Validate satellite observations
# ============================================================

satellite["tropospheric_no2"] = pd.to_numeric(
    satellite["tropospheric_no2"],
    errors="coerce",
)

if satellite["tropospheric_no2"].isna().any():
    raise ValueError(
        "Satellite dataset contains missing/invalid NO2 values."
    )

duplicate_satellite = satellite.duplicated(
    subset=["station_id", "timestamp"]
).sum()

if duplicate_satellite:
    raise ValueError(
        f"Satellite dataset contains "
        f"{duplicate_satellite:,} duplicate "
        f"(station_id, timestamp) rows."
    )


# ============================================================
# Sort for as-of merge
# ============================================================

forecast = forecast.sort_values(
    "forecast_timestamp_utc"
).reset_index(drop=True)

satellite = satellite.sort_values(
    "timestamp"
).reset_index(drop=True)


# ============================================================
# Leakage-safe as-of merge
# ============================================================

print("\nPerforming causal satellite alignment...")

merged = pd.merge_asof(
    forecast,
    satellite[
        [
            "station_id",
            "timestamp",
            "tropospheric_no2",
        ]
    ],
    left_on="forecast_timestamp_utc",
    right_on="timestamp",
    by="station_id",
    direction="backward",
    allow_exact_matches=True,
)


# ============================================================
# Rename satellite fields
# ============================================================

merged = merged.rename(
    columns={
        "timestamp": "satellite_timestamp_utc",
        "tropospheric_no2": "satellite_no2_latest",
    }
)


# ============================================================
# Calculate satellite age
# ============================================================

merged["satellite_no2_age_hours"] = (
    (
        merged["forecast_timestamp_utc"]
        - merged["satellite_timestamp_utc"]
    )
    .dt.total_seconds()
    / 3600.0
)


# ============================================================
# Leakage checks BEFORE freshness filtering
# ============================================================

future_match_mask = (
    merged["satellite_timestamp_utc"].notna()
    &
    (
        merged["satellite_timestamp_utc"]
        > merged["forecast_timestamp_utc"]
    )
)

future_matches = int(future_match_mask.sum())

print(
    f"Future satellite matches: {future_matches:,}"
)

if future_matches != 0:
    raise RuntimeError(
        "LEAKAGE DETECTED: satellite observation "
        "occurs after forecast origin."
    )


# ============================================================
# Validate age
# ============================================================

negative_age = (
    merged["satellite_no2_age_hours"].notna()
    &
    (
        merged["satellite_no2_age_hours"] < 0
    )
)

if negative_age.any():
    raise RuntimeError(
        "LEAKAGE DETECTED: negative satellite age."
    )


# ============================================================
# Freshness filter
# ============================================================

too_old = (
    merged["satellite_no2_age_hours"].notna()
    &
    (
        merged["satellite_no2_age_hours"]
        > MAX_SATELLITE_AGE_HOURS
    )
)

merged.loc[
    too_old,
    [
        "satellite_no2_latest",
        "satellite_no2_age_hours",
    ],
] = np.nan


# ============================================================
# Remove helper columns
# ============================================================

merged = merged.drop(
    columns=[
        "forecast_timestamp_utc",
    ]
)


# ============================================================
# Final ordering
# ============================================================

merged = merged.sort_values(
    ["station_id", "Timestamp"]
).reset_index(drop=True)


# ============================================================
# Integrity checks
# ============================================================

print("\nRunning integrity checks...")

if len(merged) != len(forecast):
    raise RuntimeError(
        "Row count changed during satellite fusion."
    )

original_columns = set(forecast.columns) - {
    "forecast_timestamp_utc"
}

for column in original_columns:

    if column not in merged.columns:
        raise RuntimeError(
            f"Original forecast column disappeared: {column}"
        )


# Check CPCB/forecast values were not modified.

for column in [
    "PM2.5",
    "PM10",
    "NO2",
    "NOx",
    "AT",
    "RH",
    "WS",
    "WD",
]:
    if column in forecast.columns:

        original = forecast.sort_values(
            ["station_id", "Timestamp"]
        )[column].reset_index(drop=True)

        result = merged.sort_values(
            ["station_id", "Timestamp"]
        )[column].reset_index(drop=True)

        if not original.equals(result):
            raise RuntimeError(
                f"Existing forecast column changed: {column}"
            )


# ============================================================
# Fusion statistics
# ============================================================

total_rows = len(merged)

available = merged[
    "satellite_no2_latest"
].notna()

available_rows = int(available.sum())

missing_rows = total_rows - available_rows

availability_pct = (
    100.0 * available_rows / total_rows
)

missing_pct = (
    100.0 * missing_rows / total_rows
)

print("\nSatellite availability:")
print(
    f"  Available: {available_rows:,} "
    f"({availability_pct:.2f}%)"
)
print(
    f"  Missing:   {missing_rows:,} "
    f"({missing_pct:.2f}%)"
)


# ============================================================
# Age statistics
# ============================================================

ages = merged.loc[
    available,
    "satellite_no2_age_hours",
]

print("\nSatellite age statistics:")

if len(ages):

    print(
        f"  Minimum: {ages.min():.2f} h"
    )

    print(
        f"  Median: {ages.median():.2f} h"
    )

    print(
        f"  Mean: {ages.mean():.2f} h"
    )

    print(
        f"  90th percentile: "
        f"{ages.quantile(0.90):.2f} h"
    )

    print(
        f"  Maximum: {ages.max():.2f} h"
    )


# ============================================================
# Station availability
# ============================================================

station_stats = (
    merged.groupby("station_id")
    .agg(
        total_rows=("station_id", "size"),
        satellite_available=(
            "satellite_no2_latest",
            lambda x: x.notna().sum(),
        ),
    )
)

station_stats["availability_pct"] = (
    100
    * station_stats["satellite_available"]
    / station_stats["total_rows"]
)

print("\nStation-level satellite availability:")

print(
    station_stats.to_string()
)


# ============================================================
# Train / validation / test availability
# ============================================================

# These boundaries reproduce the existing chronological split.

TRAIN_END = pd.Timestamp(
    "2025-03-15 12:00:00"
)

VALID_END = pd.Timestamp(
    "2025-11-21 22:00:00"
)


def split_name(timestamp):
    if timestamp < TRAIN_END:
        return "train"

    if timestamp < VALID_END:
        return "validation"

    return "test"


merged["split"] = merged[
    "Timestamp"
].apply(split_name)


split_stats = (
    merged.groupby("split")
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

print("\nSplit-level satellite availability:")

print(
    split_stats.to_string()
)


# ============================================================
# Final leakage assertion
# ============================================================

valid_age = merged[
    "satellite_no2_age_hours"
].dropna()

if not valid_age.empty:

    if (valid_age < 0).any():
        raise RuntimeError(
            "Final dataset contains negative satellite ages."
        )

    if (
        valid_age > MAX_SATELLITE_AGE_HOURS
    ).any():
        raise RuntimeError(
            "Final dataset contains satellite "
            "observations older than freshness limit."
        )


# ============================================================
# Save dataset
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

merged.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ============================================================
# Save audit
# ============================================================

audit_rows = [
    {
        "metric": "forecast_rows",
        "value": total_rows,
    },
    {
        "metric": "satellite_available_rows",
        "value": available_rows,
    },
    {
        "metric": "satellite_missing_rows",
        "value": missing_rows,
    },
    {
        "metric": "satellite_availability_pct",
        "value": availability_pct,
    },
    {
        "metric": "satellite_missing_pct",
        "value": missing_pct,
    },
    {
        "metric": "future_match_violations",
        "value": future_matches,
    },
    {
        "metric": "max_allowed_satellite_age_hours",
        "value": MAX_SATELLITE_AGE_HOURS,
    },
]

audit = pd.DataFrame(audit_rows)

AUDIT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

audit.to_csv(
    AUDIT_FILE,
    index=False,
)


# ============================================================
# Complete
# ============================================================

print("\n" + "=" * 70)
print("SATELLITE FUSION COMPLETE")
print("=" * 70)

print(f"Output: {OUTPUT_FILE}")
print(f"Audit:  {AUDIT_FILE}")
print(f"Rows:   {len(merged):,}")

print("\nNew satellite features:")
print("  satellite_no2_latest")
print("  satellite_no2_age_hours")

print("\nLeakage status: PASS")
print("=" * 70)
