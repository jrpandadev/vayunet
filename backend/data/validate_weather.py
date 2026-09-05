import os
import pandas as pd
import numpy as np

def validate_weather_data():
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "weather", "delhi_weather_2022_2026.csv")
    print(f"Loading {file_path}...\n")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # 1. Load the CSV
    df = pd.read_csv(file_path)
    
    # 2. Print row count
    row_count = len(df)
    print(f"Row count: {row_count}")
    
    # 3. Print column names
    print(f"Columns: {list(df.columns)}")
    
    # 4. Parse timestamp as datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 5. Verify timestamp timezone/interpretation
    # Open-Meteo returns time in the requested timezone, but it might not be explicitly localized in the CSV.
    # We'll check if it has tzinfo, and if not, note that it's naive but assumed IST.
    has_tz = df['timestamp'].dt.tz is not None
    timezone_status = "Localized" if has_tz else "Naive (Assumed Asia/Kolkata from download param)"
    print(f"Timezone status: {timezone_status}")
    
    # 6. Check duplicate timestamps
    duplicate_timestamps = df['timestamp'].duplicated().sum()
    print(f"Duplicate timestamps: {duplicate_timestamps}")
    
    # 7. Check whether timestamps are exactly 1 hour apart
    # 8. Identify any missing hourly timestamps
    min_ts = df['timestamp'].min()
    max_ts = df['timestamp'].max()
    print(f"Minimum timestamp: {min_ts}")
    print(f"Maximum timestamp: {max_ts}")
    
    expected_range = pd.date_range(start=min_ts, end=max_ts, freq='1h')
    expected_rows = len(expected_range)
    missing_hourly = expected_rows - row_count + duplicate_timestamps
    
    missing_timestamps_count = len(set(expected_range) - set(df['timestamp']))
    print(f"Missing hourly timestamps: {missing_timestamps_count}")
    
    # 9. Already printed min/max timestamp above
    
    # 10. Print missing-value count and percentage for every weather variable
    print("\nMissing values:")
    missing_stats = {}
    weather_cols = [c for c in df.columns if c != 'timestamp']
    total_missing = 0
    other_missing = 0
    pbl_missing = 0
    
    for col in weather_cols:
        missing = df[col].isna().sum()
        total_missing += missing
        pct = (missing / row_count) * 100
        print(f"  {col}: {missing} ({pct:.2f}%)")
        missing_stats[col] = missing
        if col == "boundary_layer_height":
            pbl_missing = missing
        else:
            other_missing += missing
    
    # 11. Check whether numeric variables contain infinite values
    print("\nInfinite values:")
    total_infinite = 0
    for col in weather_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            inf_count = np.isinf(df[col]).sum()
            total_infinite += inf_count
            if inf_count > 0:
                print(f"  {col}: {inf_count}")
    if total_infinite == 0:
        print("  None")
        
    # 12. Print basic min/max values for every numeric variable
    print("\nMin/Max values:")
    for col in weather_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_min = df[col].min()
            col_max = df[col].max()
            print(f"  {col}: min={col_min:.2f}, max={col_max:.2f}")
            
    # 13. Check for obviously impossible values
    print("\nImpossible value checks:")
    impossible_issues = 0
    if 'relative_humidity_2m' in df.columns:
        invalid_rh = ((df['relative_humidity_2m'] < 0) | (df['relative_humidity_2m'] > 100)).sum()
        if invalid_rh > 0:
            print(f"  Warning: {invalid_rh} values in relative_humidity_2m outside 0-100 range.")
            impossible_issues += invalid_rh
    
    if 'cloud_cover' in df.columns:
        invalid_cc = ((df['cloud_cover'] < 0) | (df['cloud_cover'] > 100)).sum()
        if invalid_cc > 0:
            print(f"  Warning: {invalid_cc} values in cloud_cover outside 0-100 range.")
            impossible_issues += invalid_cc
            
    if 'wind_direction_10m' in df.columns:
        invalid_wd = ((df['wind_direction_10m'] < 0) | (df['wind_direction_10m'] > 360)).sum()
        if invalid_wd > 0:
            print(f"  Warning: {invalid_wd} values in wind_direction_10m outside 0-360 range.")
            impossible_issues += invalid_wd
            
    if impossible_issues == 0:
        print("  None detected.")

    # Validation Checks
    expected_cols = [
        'timestamp', 'temperature_2m', 'relative_humidity_2m', 'dew_point_2m',
        'precipitation', 'surface_pressure', 'cloud_cover', 'wind_speed_10m',
        'wind_direction_10m', 'wind_gusts_10m', 'shortwave_radiation', 'boundary_layer_height'
    ]
    cols_match = list(df.columns) == expected_cols
    range_match = (str(min_ts) == "2022-01-01 00:00:00") and (str(max_ts) == "2026-08-31 23:00:00")
    
    is_fully_clean = (
        row_count == 40896
        and range_match
        and duplicate_timestamps == 0
        and missing_timestamps_count == 0
        and total_infinite == 0
        and impossible_issues == 0
        and cols_match
        and total_missing == 0
    )
    
    is_valid_with_pbl = (
        row_count == 40896
        and range_match
        and duplicate_timestamps == 0
        and missing_timestamps_count == 0
        and total_infinite == 0
        and impossible_issues == 0
        and cols_match
        and other_missing == 0
    )

    if is_fully_clean:
        status = "PASSED"
    elif is_valid_with_pbl:
        status = "PASSED WITH EXPECTED PBL MISSINGNESS"
    else:
        status = "FAILED"

    # Validation Summary
    print("\nWEATHER DATA VALIDATION")
    print("-" * 23)
    print(f"Rows: {row_count}")
    print(f"Date range: {min_ts} to {max_ts}")
    print(f"Duplicate timestamps: {duplicate_timestamps}")
    print(f"Missing hourly timestamps: {missing_timestamps_count}")
    print(f"Timestamp representation: naive")
    print(f"Timestamp interpretation: Asia/Kolkata")
    print(f"Infinite values: {total_infinite}")
    print(f"PBL missing: {pbl_missing} ({(pbl_missing / row_count) * 100:.2f}%)")
    print(f"Other missing values: {other_missing}")
    print(f"Validation status: {status}")

if __name__ == "__main__":
    validate_weather_data()
