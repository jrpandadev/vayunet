#!/usr/bin/env python3
import os
from pathlib import Path
import pandas as pd
import numpy as np

def main():
    base_dir = Path(__file__).resolve().parent
    data_file = base_dir / "data" / "raw" / "weather" / "era5_pressure_levels" / "era5_delhi_pilot.csv"
    audit_file = base_dir / "data" / "raw" / "weather" / "era5_pressure_levels" / "era5_pilot_audit.md"

    if not data_file.exists():
        print(f"File not found: {data_file}")
        return

    print("Reading data...")
    # Read the first few lines to inspect headers because CDS CSV can have some metadata
    try:
        df = pd.read_csv(data_file)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    file_size_mb = data_file.stat().st_size / (1024 * 1024)
    total_rows = len(df)
    columns = list(df.columns)

    # Some CDS CSVs use 'valid_time' or 'time'
    time_col = None
    for col in ['valid_time', 'time', 'date']:
        if col in df.columns:
            time_col = col
            break

    if time_col is None:
        print(f"Could not identify time column. Columns: {columns}")
        return

    df[time_col] = pd.to_datetime(df[time_col])

    # Coordinates
    lat_col = 'latitude' if 'latitude' in df.columns else 'lat' if 'lat' in df.columns else None
    lon_col = 'longitude' if 'longitude' in df.columns else 'lon' if 'lon' in df.columns else None

    if lat_col and lon_col:
        unique_lats = df[lat_col].unique()
        unique_lons = df[lon_col].unique()
    else:
        unique_lats = ["Unknown"]
        unique_lons = ["Unknown"]

    # Date coverage
    min_date = df[time_col].min()
    max_date = df[time_col].max()

    # Time interval check
    unique_hours = sorted(df[time_col].dt.hour.unique())

    # Duplicate timestamps per pressure level
    # Assuming 'pressure_level' or 'level' is present
    level_col = None
    for col in ['pressure_level', 'level']:
        if col in df.columns:
            level_col = col
            break

    duplicates = 0
    missing_timestamps = 0
    if level_col:
        duplicates = df.duplicated(subset=[time_col, level_col]).sum()

        # Check missing timestamps for each level
        expected_range = pd.date_range(start='2022-01-01 00:00:00', end='2026-08-31 18:00:00', freq='6h')
        total_expected = len(expected_range)

        for level in df[level_col].unique():
            level_df = df[df[level_col] == level]
            actual_times = level_df[time_col]
            missing_times = len(expected_range) - len(actual_times)
            missing_timestamps += max(0, missing_times)
    else:
        duplicates = df.duplicated(subset=[time_col]).sum()

    # Missing values and ranges
    var_cols = [c for c in columns if c not in [time_col, lat_col, lon_col, level_col, 'number', 'step', 'surface', 'expver']]
    missing_vals = {}
    ranges = {}

    for col in var_cols:
        missing_vals[col] = df[col].isna().sum()
        ranges[col] = (df[col].min(), df[col].max())

    # Report writing
    lines = [
        "# ERA5 Pressure Levels Pilot Audit",
        "",
        f"**Location**: Delhi (Requested: 28.6139, 77.2090)",
        f"**File size**: {file_size_mb:.2f} MB",
        f"**Total rows**: {total_rows}",
        "",
        "## 1. Grid Coordinates",
        f"- Returned Latitudes: {unique_lats}",
        f"- Returned Longitudes: {unique_lons}",
        "",
        "## 2. Date Coverage",
        f"- Earliest timestamp: {min_date}",
        f"- Latest timestamp: {max_date}",
        "",
        "## 3. Timestamp Validation",
        f"- Unique hours present: {unique_hours}",
        f"- Duplicate timestamps: {duplicates}",
        f"- Missing timestamps vs expected (6-hourly): {missing_timestamps}",
        "",
        "## 4. Column Manifest",
        f"`{columns}`",
        "",
        "## 5. Variables Check (Missing & Physical Ranges)",
    ]

    for col in var_cols:
        lines.append(f"### {col}")
        lines.append(f"- **Missing values**: {missing_vals[col]}")
        lines.append(f"- **Min**: {ranges[col][0]:.4f}")
        if col == 'r' and ranges[col][0] < 0:
            min_idx = df['r'].idxmin()
            min_row = df.loc[min_idx]
            t_col = time_col if time_col in df.columns else 'valid_time'
            l_col = level_col if level_col in df.columns else 'pressure_level'
            lines.append(f"  - *Note: Minimum is negative ({ranges[col][0]:.4f} at {min_row[t_col]}, {min_row[l_col]} hPa). This is a known ECMWF spectral/GRIB encoding artifact (ringing) in very dry air, not a missing data marker. The raw value is left unchanged per user instruction.*")
        lines.append(f"- **Max**: {ranges[col][1]:.4f}")

    with open(audit_file, 'w') as f:
        f.write("\n".join(lines) + "\n")

    print(f"Audit completed. Report saved to {audit_file}")

if __name__ == "__main__":
    main()
