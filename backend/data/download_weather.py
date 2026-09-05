import os
import requests
import pandas as pd
from datetime import datetime

def download_weather_data():
    """Download historical weather data for Delhi from Open-Meteo."""
    print("Starting Open-Meteo historical weather download...")
    
    # Delhi coordinates
    latitude = 28.6139
    longitude = 77.2090
    
    # Date range matching the pollution dataset
    start_date = "2022-01-01"
    end_date = "2026-08-31"
    
    # Open-Meteo Archive API endpoint
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    # Parameters
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "precipitation",
            "surface_pressure",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "shortwave_radiation"
        ],
        "timezone": "Asia/Kolkata"
    }
    
    # Note: boundary_layer_height might not be freely available in archive, let's see if it works or fails, if it fails, I'll remove it. Wait, the prompt says "These are available from the historical API." I will include it.
    params["hourly"].append("boundary_layer_height")

    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "weather")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "delhi_weather_2022_2026.csv")
    
    print(f"Requesting data for Delhi ({latitude}, {longitude})")
    print(f"Period: {start_date} to {end_date}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Parse the JSON response into a DataFrame
        hourly_data = data["hourly"]
        df = pd.DataFrame(hourly_data)
        
        # Rename the time column to match our conventions if needed, or keep as time
        df.rename(columns={"time": "timestamp"}, inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        print(f"\nSuccessfully downloaded weather data.")
        print(f"Saved to: {output_path}")
        print(f"Total rows: {len(df)}")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print("\nColumns:")
        for col in df.columns:
            print(f"- {col}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Open-Meteo: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response text: {e.response.text}")

if __name__ == "__main__":
    download_weather_data()
