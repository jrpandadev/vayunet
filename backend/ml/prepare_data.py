from pathlib import Path
import re

import numpy as np
import pandas as pd


# ============================================================
# VAYUNET — DELHI FORECASTING DATA PREPARATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw" / "delhi"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "delhi_forecasting.csv"


# ------------------------------------------------------------
# Columns
# ------------------------------------------------------------

POLLUTION_COLUMNS = [
    "PM2.5",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "SO2",
    "CO",
    "Ozone",
]

WEATHER_COLUMNS = [
    "AT",
    "RH",
    "WS",
    "WD",
    "SR",
    "BP",
]

# VWS is 100% missing according to validation.
DROP_COLUMNS = [
    "VWS",
    "RF",
    "TOT-RF",
]

TARGET_COLUMN = "PM2.5"

FORECAST_HORIZONS = [6, 24, 72]

LAG_HOURS = [1, 3, 6, 12, 24, 48, 72]

ROLLING_WINDOWS = [6, 24]


# ============================================================
# Helper functions
# ============================================================

def detect_station(filename: str) -> str:
    """
    Extract station name from filenames such as:

    raw_data_hourly_ito,_delhi.csv
    raw_data_hourly_anand_vihar,_delhi.csv
    """

    name = Path(filename).stem.lower()

    prefix = "raw_data_hourly_"

    if name.startswith(prefix):
        name = name[len(prefix):]

    # Everything before ,_delhi is the station name.
    if ",_delhi" in name:
        name = name.split(",_delhi")[0]

    # Clean station name.
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strip unit suffixes from CPCB column headers.

    Raw CPCB files use headers such as:
      "PM2.5 (µg/m³)"  →  "PM2.5"
      "AT (°C)"        →  "AT"
      "WS (m/s)"       →  "WS"

    We keep only the token before the first space/parenthesis.
    The Timestamp column is left unchanged.
    """

    new_columns = []

    for col in df.columns:
        col_stripped = col.strip()
        # Timestamp must stay exactly "Timestamp"
        if col_stripped.lower() == "timestamp":
            new_columns.append("Timestamp")
        else:
            # Take the part before the first space or "("
            base = col_stripped.split("(")[0].split(" ")[0].strip()
            new_columns.append(base)

    df.columns = new_columns
    return df


def load_one_file(file_path: Path) -> pd.DataFrame:
    """
    Load one CPCB CSV and normalize its basic structure.
    """

    print(f"Loading: {file_path.name}")

    df = pd.read_csv(file_path)

    # Strip unit suffixes from column headers first.
    df = normalize_column_names(df)

    # Clean column names.
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Find timestamp column.
    timestamp_column = None

    for column in df.columns:
        if column.lower() == "timestamp":
            timestamp_column = column
            break

    if timestamp_column is None:
        raise ValueError(
            f"No Timestamp column found in {file_path.name}"
        )

    # Rename timestamp consistently.
    if timestamp_column != "Timestamp":
        df = df.rename(
            columns={timestamp_column: "Timestamp"}
        )

    # Parse timestamps.
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )

    # Remove invalid timestamps.
    invalid = df["Timestamp"].isna().sum()

    if invalid > 0:
        print(
            f"  Warning: removing {invalid} invalid timestamps"
        )

        df = df.dropna(subset=["Timestamp"])

    # Add station.
    df["station_id"] = detect_station(file_path.name)

    # Sort.
    df = df.sort_values("Timestamp")

    # Remove duplicate timestamps within this file.
    duplicates = df["Timestamp"].duplicated().sum()

    if duplicates > 0:
        print(
            f"  Warning: removing {duplicates} duplicate timestamps"
        )

        df = df.drop_duplicates(
            subset=["Timestamp"],
            keep="first"
        )

    return df


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert measurement columns to numeric.

    CPCB files may contain values such as NA.
    Those become NaN.
    """

    columns_to_convert = (
        POLLUTION_COLUMNS
        + WEATHER_COLUMNS
    )

    for column in columns_to_convert:

        if column in df.columns:

            df[column] = (
                df[column]
                .replace(
                    [
                        "NA",
                        "N/A",
                        "na",
                        "n/a",
                        "null",
                        "NULL",
                        "",
                        " "
                    ],
                    np.nan
                )
            )

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calendar/time features.
    """

    timestamp = df["Timestamp"]

    df["hour"] = timestamp.dt.hour

    df["day_of_week"] = timestamp.dt.dayofweek

    df["day_of_year"] = timestamp.dt.dayofyear

    df["month"] = timestamp.dt.month

    df["is_weekend"] = (
        timestamp.dt.dayofweek >= 5
    ).astype(int)

    return df


def add_wind_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wind direction from degrees into circular features.

    0° and 360° should represent approximately
    the same direction.
    """

    if "WD" not in df.columns:
        return df

    radians = np.deg2rad(df["WD"])

    df["WD_sin"] = np.sin(radians)

    df["WD_cos"] = np.cos(radians)

    return df


def identify_continuous_segments(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Identify continuous hourly segments.

    A new segment begins whenever the difference between
    consecutive timestamps is greater than one hour.

    This prevents lag/rolling features from crossing
    the 31-day 2026 outage.
    """

    df = df.sort_values(
        ["station_id", "Timestamp"]
    ).copy()

    time_difference = (
        df.groupby("station_id")["Timestamp"]
        .diff()
    )

    new_segment = (
        time_difference.isna()
        | (time_difference > pd.Timedelta(hours=1))
    )

    df["segment_id"] = (
        new_segment
        .groupby(df["station_id"])
        .cumsum()
    )

    return df


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create PM2.5 lag features using exact timestamp matching.

    For each row at timestamp t, look up the PM2.5 value at
    t - h hours exactly.  If that timestamp is absent from the
    segment (hour was not recorded) or PM2.5 was NaN there,
    the lag is NaN.

    Crucially this never crosses station or segment boundaries.
    """

    lag_cols = {col: pd.Series(np.nan, index=df.index, dtype=float)
                for col in [f"PM2.5_lag_{h}h" for h in LAG_HOURS]}

    for station in df["station_id"].unique():
        station_mask = df["station_id"] == station
        sdf = df[station_mask]

        for seg in sdf["segment_id"].unique():
            seg_mask = station_mask & (df["segment_id"] == seg)
            seg_df = df[seg_mask]

            # Build a Timestamp → PM2.5 lookup for this segment.
            # Keep NaN PM2.5 rows so lookups correctly return NaN.
            pm25_lookup = seg_df.set_index("Timestamp")["PM2.5"]

            for h in LAG_HOURS:
                target_ts = seg_df["Timestamp"] - pd.Timedelta(hours=h)
                values = pm25_lookup.reindex(target_ts.values).values
                lag_cols[f"PM2.5_lag_{h}h"][seg_mask] = values

    for col, series in lag_cols.items():
        df[col] = series

    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create rolling PM2.5 statistics within each continuous segment.

    Resamples the segment to a full hourly DatetimeIndex first so
    that sporadic gaps produce NaN windows rather than silently
    collapsing missing hours into adjacent observations.
    """

    roll_mean_6   = pd.Series(np.nan, index=df.index, dtype=float)
    roll_mean_24  = pd.Series(np.nan, index=df.index, dtype=float)
    roll_std_24   = pd.Series(np.nan, index=df.index, dtype=float)

    for station in df["station_id"].unique():
        station_mask = df["station_id"] == station
        sdf = df[station_mask]

        for seg in sdf["segment_id"].unique():
            seg_mask = station_mask & (df["segment_id"] == seg)
            seg_df = df[seg_mask]

            pm25_ts = seg_df.set_index("Timestamp")["PM2.5"]

            # Resample to hourly so gaps become explicit NaN rows.
            hourly = pm25_ts.resample("h").mean()

            rm6  = hourly.rolling(window=6,  min_periods=6).mean()
            rm24 = hourly.rolling(window=24, min_periods=24).mean()
            rs24 = hourly.rolling(window=24, min_periods=24).std()

            # Map computed values back to the original row timestamps.
            orig_ts = seg_df["Timestamp"]
            roll_mean_6[seg_mask]  = rm6.reindex(orig_ts.values).values
            roll_mean_24[seg_mask] = rm24.reindex(orig_ts.values).values
            roll_std_24[seg_mask]  = rs24.reindex(orig_ts.values).values

    df["PM2.5_roll_mean_6h"]  = roll_mean_6
    df["PM2.5_roll_mean_24h"] = roll_mean_24
    df["PM2.5_roll_std_24h"]  = roll_std_24

    return df


def add_forecast_targets(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Create future PM2.5 targets using exact timestamp matching.

    For each row at timestamp t, look up the PM2.5 value at
    t + h hours exactly.  Missing timestamps or missing PM2.5
    produce NaN.  Cannot cross station or segment boundaries.
    """

    target_cols = {col: pd.Series(np.nan, index=df.index, dtype=float)
                   for col in [f"target_pm25_{h}h" for h in FORECAST_HORIZONS]}

    for station in df["station_id"].unique():
        station_mask = df["station_id"] == station
        sdf = df[station_mask]

        for seg in sdf["segment_id"].unique():
            seg_mask = station_mask & (df["segment_id"] == seg)
            seg_df = df[seg_mask]

            pm25_lookup = seg_df.set_index("Timestamp")["PM2.5"]

            for h in FORECAST_HORIZONS:
                target_ts = seg_df["Timestamp"] + pd.Timedelta(hours=h)
                values = pm25_lookup.reindex(target_ts.values).values
                target_cols[f"target_pm25_{h}h"][seg_mask] = values

    for col, series in target_cols.items():
        df[col] = series

    return df


# ============================================================
# Main preparation pipeline
# ============================================================

def main():

    print("=" * 70)
    print("VAYUNET — PREPARING DELHI FORECASTING DATA")
    print("=" * 70)

    print(f"\nRaw directory:")
    print(RAW_DIR)

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {RAW_DIR}"
        )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Find files
    # --------------------------------------------------------

    files = sorted(
        RAW_DIR.glob("*.csv")
    )

    print(f"\nCSV files found: {len(files)}")

    if not files:
        raise FileNotFoundError(
            "No CSV files found."
        )

    # --------------------------------------------------------
    # Load all files
    # --------------------------------------------------------

    frames = []

    for file_path in files:

        df = load_one_file(file_path)

        frames.append(df)

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    print("\nCombining files...")

    df = pd.concat(
        frames,
        ignore_index=True
    )

    print(
        f"Combined rows: {len(df):,}"
    )

    # --------------------------------------------------------
    # Convert measurements
    # --------------------------------------------------------

    print("\nConverting numeric columns...")

    df = convert_numeric_columns(df)

    # --------------------------------------------------------
    # Remove physically implausible meteorological values
    # --------------------------------------------------------

    # AT > 55°C is not physically plausible for Delhi.
    # Setting to NaN is preferable to clipping, which would
    # inject artificial data into the training set.
    invalid_at = df["AT"] > 55
    print(f"\nInvalid AT values >55 deg C: {invalid_at.sum()} — setting to NaN")
    df.loc[invalid_at, "AT"] = np.nan

    # --------------------------------------------------------
    # Keep relevant columns
    # --------------------------------------------------------

    available_columns = [
        "Timestamp",
        "station_id",
    ]

    for column in (
        POLLUTION_COLUMNS
        + WEATHER_COLUMNS
    ):

        if column in df.columns:
            available_columns.append(column)

    df = df[available_columns].copy()

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    df = df.sort_values(
        ["station_id", "Timestamp"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Identify continuous segments
    # --------------------------------------------------------

    print("\nIdentifying continuous hourly segments...")

    df = identify_continuous_segments(df)

    number_of_segments = (
        df.groupby("station_id")["segment_id"]
        .nunique()
    )

    print("\nSegments by station:")

    for station, count in number_of_segments.items():

        print(
            f"  {station:25s}: {count}"
        )

    # --------------------------------------------------------
    # Time features
    # --------------------------------------------------------

    print("\nCreating time features...")

    df = add_time_features(df)

    # --------------------------------------------------------
    # Wind features
    # --------------------------------------------------------

    print("Creating wind direction features...")

    df = add_wind_features(df)

    # --------------------------------------------------------
    # Lag features
    # --------------------------------------------------------

    print("Creating PM2.5 lag features...")

    df = add_lag_features(df)

    # --------------------------------------------------------
    # Rolling features
    # --------------------------------------------------------

    print("Creating rolling features...")

    df = add_rolling_features(df)

    # --------------------------------------------------------
    # Forecast targets
    # --------------------------------------------------------

    print("Creating 6h / 24h / 72h targets...")

    df = add_forecast_targets(df)

    # --------------------------------------------------------
    # Remove rows without PM2.5
    # --------------------------------------------------------

    before = len(df)

    df = df.dropna(
        subset=["PM2.5"]
    ).copy()

    removed = before - len(df)

    print(
        f"\nRemoved rows without current PM2.5: "
        f"{removed:,}"
    )

    # --------------------------------------------------------
    # Remove helper segment column
    # --------------------------------------------------------

    # Keep segment_id for now.
    # It is useful for debugging and validation.

    # --------------------------------------------------------
    # Final sorting
    # --------------------------------------------------------

    df = df.sort_values(
        ["station_id", "Timestamp"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    print(
        f"\nSaving processed dataset:"
    )

    print(OUTPUT_FILE)

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("PREPARATION COMPLETE")
    print("=" * 70)

    print(
        f"\nFinal rows:    {len(df):,}"
    )

    print(
        f"Final columns: {len(df.columns)}"
    )

    print(
        f"Stations:      {df['station_id'].nunique()}"
    )

    print(
        f"Output:        {OUTPUT_FILE}"
    )

    print("\nTarget availability:")

    for horizon in FORECAST_HORIZONS:

        column = f"target_pm25_{horizon}h"

        available = df[column].notna().sum()

        percentage = (
            available / len(df) * 100
        )

        print(
            f"  {horizon:2d}h: "
            f"{available:,} rows "
            f"({percentage:.2f}%)"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
