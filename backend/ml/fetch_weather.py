"""
Fetch hourly historical weather for Delhi from Open-Meteo Historical Weather API.

Time Range: 2022-01-01 through 2026-08-31
Timezone: Asia/Kolkata (Matches CPCB local time)
Variables:
    - temperature_2m
    - relative_humidity_2m
    - dew_point_2m
    - precipitation
    - surface_pressure
    - cloud_cover
    - wind_speed_10m
    - wind_direction_10m
    - wind_gusts_10m
    - shortwave_radiation
    - boundary_layer_height

Saves output to: data/raw/weather/delhi_weather_2022_2026.csv
"""

import time
from pathlib import Path
import httpx
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "weather"
OUTPUT_FILE = OUTPUT_DIR / "delhi_weather_2022_2026.csv"

# Central Delhi coordinates
LATITUDE = 28.6139
LONGITUDE = 77.2090
TIMEZONE = "Asia/Kolkata"

VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "boundary_layer_height",
]

# Yearly chunks to avoid network timeouts and large payload errors
CHUNKS = [
    ("2022-01-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", "2025-12-31"),
    ("2026-01-01", "2026-08-31"),
]


def fetch_chunk(start_date: str, end_date: str, client: httpx.Client) -> pd.DataFrame:
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(VARIABLES),
        "timezone": TIMEZONE,
    }

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Fetching {start_date} to {end_date} (attempt {attempt}/{max_retries})...")
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            hourly = data.get("hourly", {})
            if not hourly or "time" not in hourly:
                raise ValueError(f"No hourly data returned in response: {data}")
                
            df = pd.DataFrame(hourly)
            # Rename 'time' to 'Timestamp' for consistency with VayuNet CPCB data
            df = df.rename(columns={"time": "Timestamp"})
            print(f"  Received {len(df):,} rows.")
            return df
        except Exception as exc:
            print(f"  Error fetching {start_date} to {end_date}: {exc}")
            if attempt == max_retries:
                raise
            sleep_time = attempt * 3
            print(f"  Retrying in {sleep_time}s...")
            time.sleep(sleep_time)


def main():
    print("=" * 70)
    print("FETCHING DELHI HISTORICAL WEATHER FROM OPEN-METEO")
    print("=" * 70)
    print(f"Coordinates : Lat {LATITUDE}, Lon {LONGITUDE} (Delhi)")
    print(f"Timezone    : {TIMEZONE}")
    print(f"Period      : 2022-01-01 to 2026-08-31")
    print(f"Variables   : {len(VARIABLES)} meteorological variables")
    print(f"Destination : {OUTPUT_FILE}")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_frames = []
    with httpx.Client(timeout=120.0) as client:
        for start_date, end_date in CHUNKS:
            df_chunk = fetch_chunk(start_date, end_date, client)
            all_frames.append(df_chunk)
            # Polite pause between requests to respect rate limits
            time.sleep(1.0)

    print("\nConcatenating weather chunks...")
    combined_df = pd.concat(all_frames, ignore_index=True)
    
    # Verify continuous timestamps
    combined_df["Timestamp"] = pd.to_datetime(combined_df["Timestamp"])
    combined_df = combined_df.sort_values(by="Timestamp").drop_duplicates(subset=["Timestamp"]).reset_index(drop=True)

    print(f"Total observations fetched: {len(combined_df):,}")
    print(f"Date range: {combined_df['Timestamp'].min()} to {combined_df['Timestamp'].max()}")
    print("\nMissing values summary:")
    for col in combined_df.columns:
        if col != "Timestamp":
            missing_count = combined_df[col].isna().sum()
            pct = (missing_count / len(combined_df)) * 100
            print(f"  {col:25s}: {missing_count:5d} missing ({pct:5.2f}%)")

    # Save to raw weather directory
    combined_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved combined weather dataset successfully to: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
