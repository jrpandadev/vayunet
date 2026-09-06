from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw" / "delhi"


# Columns we care about for the first validation
IMPORTANT_COLUMNS = [
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
    "RF",
    "TOT-RF",
    "SR",
    "BP",
    "VWS",
]


def detect_station(filename: str) -> str:
    """
    Extract station name from the filename.

    Expected pattern is roughly:
    raw_data_hourly_ito,_delhi...
    raw_data_hourly_anand_vihar,_delhi...
    """

    name = Path(filename).stem.lower()

    prefix = "raw_data_hourly_"

    if name.startswith(prefix):
        name = name[len(prefix):]

    # Remove everything after the Delhi marker
    if ",_delhi" in name:
        name = name.split(",_delhi")[0]

    return name.replace("_", " ").strip()


def analyze_file(file_path: Path):
    """Analyze one CSV file."""

    print(f"\nChecking: {file_path.name}")

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"  ERROR reading file: {e}")
        return None

    # -----------------------------------------------------
    # Find timestamp column
    # -----------------------------------------------------

    timestamp_column = None

    for col in df.columns:
        if col.strip().lower() == "timestamp":
            timestamp_column = col
            break

    if timestamp_column is None:
        print("  ERROR: Timestamp column not found.")
        return None

    df[timestamp_column] = pd.to_datetime(
        df[timestamp_column],
        errors="coerce"
    )

    invalid_timestamps = df[timestamp_column].isna().sum()

    df = df.dropna(subset=[timestamp_column])

    df = df.sort_values(timestamp_column)

    # -----------------------------------------------------
    # Basic information
    # -----------------------------------------------------

    station = detect_station(file_path.name)

    start_time = df[timestamp_column].min()
    end_time = df[timestamp_column].max()

    duplicate_count = df[timestamp_column].duplicated().sum()

    # -----------------------------------------------------
    # Missing-value percentages
    # -----------------------------------------------------

    missing_percent = {}

    for column in IMPORTANT_COLUMNS:

        # Match columns that start with the name (handles unit suffixes like " (µg/m³)")
        matched_col = next(
            (c for c in df.columns if c.strip().split(" ")[0].split("(")[0].strip() == column),
            None
        )

        if matched_col:
            missing_percent[column] = (
                df[matched_col]
                .replace(["NA", "N/A", "na", "n/a", "null", ""], pd.NA)
                .isna()
                .mean()
                * 100
            )

    # -----------------------------------------------------
    # Detect hourly gaps
    # -----------------------------------------------------

    timestamps = df[timestamp_column].drop_duplicates().sort_values()

    time_differences = timestamps.diff()

    gaps = time_differences[time_differences > pd.Timedelta(hours=1)]

    gap_count = len(gaps)

    if gap_count > 0:
        longest_gap = gaps.max()

        # Missing hours inside the longest gap
        longest_gap_missing_hours = int(
            longest_gap.total_seconds() / 3600
        ) - 1
    else:
        longest_gap = pd.Timedelta(0)
        longest_gap_missing_hours = 0

    return {
        "file": file_path.name,
        "station": station,
        "rows": len(df),
        "columns": len(df.columns),
        "start": start_time,
        "end": end_time,
        "duplicates": duplicate_count,
        "invalid_timestamps": invalid_timestamps,
        "gap_count": gap_count,
        "longest_gap": str(longest_gap),
        "longest_gap_missing_hours": longest_gap_missing_hours,
        "missing_percent": missing_percent,
    }


def main():

    print("=" * 70)
    print("VAYUNET — DELHI RAW DATA VALIDATION")
    print("=" * 70)

    print(f"\nData directory:")
    print(DATA_DIR)

    if not DATA_DIR.exists():
        print("\nERROR: Delhi data directory does not exist.")
        print(f"Expected: {DATA_DIR}")
        return

    files = sorted(DATA_DIR.glob("*.csv"))

    print(f"\nCSV files found: {len(files)}")

    if len(files) == 0:
        print("\nERROR: No CSV files found.")
        return

    # -----------------------------------------------------
    # Analyze every file
    # -----------------------------------------------------

    results = []

    for file_path in files:

        result = analyze_file(file_path)

        if result is not None:
            results.append(result)

    # -----------------------------------------------------
    # Print summary
    # -----------------------------------------------------

    print("\n")
    print("=" * 70)
    print("FILE SUMMARY")
    print("=" * 70)

    for result in results:

        print(f"\n{result['file']}")
        print(f"  Station:              {result['station']}")
        print(f"  Rows:                 {result['rows']}")
        print(f"  Columns:              {result['columns']}")
        print(f"  Start:                {result['start']}")
        print(f"  End:                  {result['end']}")
        print(f"  Duplicate timestamps: {result['duplicates']}")
        print(f"  Invalid timestamps:   {result['invalid_timestamps']}")
        print(f"  Gap count:            {result['gap_count']}")
        print(f"  Longest gap:          {result['longest_gap']}")
        print(
            f"  Missing hours "
            f"(longest gap):       {result['longest_gap_missing_hours']}"
        )

        print("  Missing percentages:")

        for column, percentage in result["missing_percent"].items():
            print(f"    {column:10s}: {percentage:6.2f}%")

    # -----------------------------------------------------
    # Station summary
    # -----------------------------------------------------

    stations = sorted(
        set(result["station"] for result in results)
    )

    print("\n")
    print("=" * 70)
    print("STATION SUMMARY")
    print("=" * 70)

    print(f"\nUnique stations detected: {len(stations)}")

    for station in stations:
        station_files = [
            r for r in results
            if r["station"] == station
        ]

        print(
            f"  {station:25s} "
            f"{len(station_files)} files"
        )

    # -----------------------------------------------------
    # Final status
    # -----------------------------------------------------

    print("\n")
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
