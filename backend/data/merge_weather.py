import os
import pandas as pd

def merge_weather():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cpcb_path = os.path.join(base_dir, "data", "processed", "delhi_forecasting.csv")
    weather_path = os.path.join(base_dir, "data", "raw", "weather", "delhi_weather_2022_2026.csv")
    output_path = os.path.join(base_dir, "data", "processed", "delhi_forecasting_weather.csv")
    report_path = os.path.join(base_dir, "reports", "weather_merge_report.txt")

    print("Loading datasets...")
    df_cpcb = pd.read_csv(cpcb_path)
    df_weather = pd.read_csv(weather_path)

    # Standardize timestamp column name
    if 'Timestamp' in df_cpcb.columns:
        df_cpcb.rename(columns={'Timestamp': 'timestamp'}, inplace=True)
    if 'Timestamp' in df_weather.columns:
        df_weather.rename(columns={'Timestamp': 'timestamp'}, inplace=True)

    # Store original column list for validation (after standardizing timestamp to 'timestamp')
    original_cpcb_cols = list(df_cpcb.columns)

    # Parse timestamps as naive
    df_cpcb['timestamp'] = pd.to_datetime(df_cpcb['timestamp']).dt.tz_localize(None)
    df_weather['timestamp'] = pd.to_datetime(df_weather['timestamp']).dt.tz_localize(None)

    input_cpcb_rows = len(df_cpcb)
    input_stations = df_cpcb['station_id'].nunique() if 'station_id' in df_cpcb.columns else 0

    print("Merging data...")
    # Left join CPCB with weather
    df_merged = pd.merge(df_cpcb, df_weather, on='timestamp', how='left')

    output_rows = len(df_merged)
    output_stations = df_merged['station_id'].nunique() if 'station_id' in df_merged.columns else 0
    duplicate_rows = df_merged.duplicated(subset=['station_id', 'timestamp']).sum() if 'station_id' in df_merged.columns else 0
    
    weather_cols = [c for c in df_weather.columns if c != 'timestamp']
    # Check for unmatched weather (where merged weather cols are completely null)
    # Since weather should match fully, we can check a known weather column like 'temperature_2m'
    unmatched_timestamps = df_merged['temperature_2m'].isna().sum()

    # Calculate missingness for PBL specifically
    pbl_missing = df_merged['boundary_layer_height'].isna().sum()
    pbl_missing_pct = (pbl_missing / output_rows) * 100 if output_rows > 0 else 0

    # Verify no existing CPCB columns were modified
    existing_cols_modified = 0
    for col in original_cpcb_cols:
        if col != 'timestamp':
            if not df_merged[col].equals(df_cpcb[col]):
                existing_cols_modified += 1

    validation_passed = (
        input_cpcb_rows == output_rows
        and input_stations == output_stations
        and duplicate_rows == 0
        and existing_cols_modified == 0
        # If there are a few unmatched timestamps, we report them. The prompt says "Count how many CPCB rows have no matching weather timestamp." 
        # The prompt wants us to verify all expected checks.
    )

    validation_status = "PASSED" if validation_passed else "FAILED"

    print("Saving merged dataset...")
    df_merged.to_csv(output_path, index=False)

    report = f"""WEATHER MERGE VALIDATION
------------------------
Input CPCB rows: {input_cpcb_rows}
Output rows: {output_rows}
Input stations: {input_stations}
Output stations: {output_stations}
Duplicate station/timestamp rows: {duplicate_rows}
Unmatched weather timestamps: {unmatched_timestamps}
Weather columns added: {len(weather_cols)}
PBL missing: {pbl_missing}
Existing CPCB columns modified: {existing_cols_modified}
Validation status: {validation_status}
"""

    print(report)

    # Also save report
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    merge_weather()
