from pathlib import Path
import pandas as pd
import numpy as np


INPUT_FILE = Path("data/raw/satellite/delhi_s5p_no2.csv")
REPORT_FILE = Path("reports/satellite/s5p_no2_quality_audit.csv")


df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("SENTINEL-5P NO2 DATA QUALITY AUDIT")
print("=" * 70)

# ------------------------------------------------------------
# Basic structure
# ------------------------------------------------------------

print(f"\nRows: {len(df):,}")
print(f"Columns: {len(df.columns)}")

required = {
    "station_id",
    "timestamp",
    "latitude",
    "longitude",
    "tropospheric_no2",
}

missing_columns = required - set(df.columns)

if missing_columns:
    raise ValueError(
        f"Missing required columns: {sorted(missing_columns)}"
    )

# ------------------------------------------------------------
# Timestamp parsing
# ------------------------------------------------------------

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce",
    utc=True,
)

df["tropospheric_no2"] = pd.to_numeric(
    df["tropospheric_no2"],
    errors="coerce",
)

print("\nTimestamp parsing:")
print(f"  Invalid timestamps: {df['timestamp'].isna().sum():,}")

# ------------------------------------------------------------
# Station coverage
# ------------------------------------------------------------

station_counts = (
    df.groupby("station_id")
      .size()
      .sort_values()
)

print("\nStation observation counts:")
print(station_counts.to_string())

print(
    f"\nUnique stations: "
    f"{df['station_id'].nunique()}"
)

# ------------------------------------------------------------
# Date range
# ------------------------------------------------------------

print("\nTemporal coverage:")
print(f"  First observation: {df['timestamp'].min()}")
print(f"  Last observation:  {df['timestamp'].max()}")

# ------------------------------------------------------------
# Missingness
# ------------------------------------------------------------

missing_no2 = df["tropospheric_no2"].isna().sum()

print("\nNO2 missingness:")
print(f"  Missing: {missing_no2:,}")
print(
    f"  Missing %: "
    f"{100 * missing_no2 / len(df):.4f}%"
)

# ------------------------------------------------------------
# Duplicate observations
# ------------------------------------------------------------

duplicate_station_timestamp = df.duplicated(
    subset=["station_id", "timestamp"]
).sum()

print("\nDuplicates:")
print(
    f"  Duplicate station/timestamp rows: "
    f"{duplicate_station_timestamp:,}"
)

# ------------------------------------------------------------
# Numeric validity
# ------------------------------------------------------------

no2 = df["tropospheric_no2"].dropna()

print("\nNO2 distribution:")
print(f"  Minimum: {no2.min():.6e}")
print(f"  1st percentile: {no2.quantile(0.01):.6e}")
print(f"  Median: {no2.median():.6e}")
print(f"  Mean: {no2.mean():.6e}")
print(f"  99th percentile: {no2.quantile(0.99):.6e}")
print(f"  Maximum: {no2.max():.6e}")

print("\nFinite-value checks:")
print(f"  +Inf: {np.isposinf(no2).sum():,}")
print(f"  -Inf: {np.isneginf(no2).sum():,}")

# ------------------------------------------------------------
# Observations per station per year
# ------------------------------------------------------------

df["year"] = df["timestamp"].dt.year

year_station = (
    df.groupby(["station_id", "year"])
      .size()
      .unstack(fill_value=0)
)

print("\nObservations by station/year:")
print(year_station.to_string())

# ------------------------------------------------------------
# Temporal gap analysis
# ------------------------------------------------------------

print("\nTemporal gap analysis:")

gap_records = []

for station_id, group in df.groupby("station_id"):

    timestamps = (
        group["timestamp"]
        .dropna()
        .sort_values()
        .drop_duplicates()
    )

    deltas = timestamps.diff().dropna()

    if deltas.empty:
        continue

    gap_records.append(
        {
            "station_id": station_id,
            "observations": len(timestamps),
            "median_gap_hours": (
                deltas.dt.total_seconds().median() / 3600
            ),
            "mean_gap_hours": (
                deltas.dt.total_seconds().mean() / 3600
            ),
            "max_gap_hours": (
                deltas.dt.total_seconds().max() / 3600
            ),
            "gaps_gt_7_days": (
                deltas > pd.Timedelta(days=7)
            ).sum(),
        }
    )

gap_df = pd.DataFrame(gap_records)

print(gap_df.to_string(index=False))

# ------------------------------------------------------------
# Coordinate consistency
# ------------------------------------------------------------

coordinate_counts = (
    df.groupby("station_id")
      .agg(
          latitude_nunique=("latitude", "nunique"),
          longitude_nunique=("longitude", "nunique"),
      )
)

print("\nCoordinate consistency:")
print(coordinate_counts.to_string())

# ------------------------------------------------------------
# Summary report
# ------------------------------------------------------------

summary = pd.DataFrame(
    [
        {
            "metric": "rows",
            "value": len(df),
        },
        {
            "metric": "unique_stations",
            "value": df["station_id"].nunique(),
        },
        {
            "metric": "invalid_timestamps",
            "value": df["timestamp"].isna().sum(),
        },
        {
            "metric": "missing_no2",
            "value": missing_no2,
        },
        {
            "metric": "duplicate_station_timestamp",
            "value": duplicate_station_timestamp,
        },
        {
            "metric": "first_timestamp",
            "value": str(df["timestamp"].min()),
        },
        {
            "metric": "last_timestamp",
            "value": str(df["timestamp"].max()),
        },
        {
            "metric": "no2_min",
            "value": no2.min(),
        },
        {
            "metric": "no2_median",
            "value": no2.median(),
        },
        {
            "metric": "no2_max",
            "value": no2.max(),
        },
    ]
)

REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

summary.to_csv(
    REPORT_FILE,
    index=False,
)

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print(f"Summary report: {REPORT_FILE}")
