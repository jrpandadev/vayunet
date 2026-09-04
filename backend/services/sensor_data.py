import pandas as pd
from pathlib import Path

def load_cpcb_data(city: str) -> pd.DataFrame:
    """Load and clean CPCB historical data for a given city."""
    # Check potential path locations (running from backend or repo root)
    possible_paths = [
        Path(f"../data/cpcb_{city}.csv"),
        Path(f"data/cpcb_{city}.csv"),
        Path(f"../data/sample_cpcb_{city}.csv"),
        Path(f"data/sample_cpcb_{city}.csv"),
    ]
    file_path = None
    for p in possible_paths:
        if p.exists():
            file_path = p
            break
            
    if not file_path:
        raise FileNotFoundError(f"No CPCB data file found for city: {city}")
        
    df = pd.read_csv(file_path)
    
    # Standardize column names
    df.columns = [c.strip().lower().replace(" ", "_").replace(".", "_") for c in df.columns]
    
    # Map common date/station variations
    if "date" in df.columns and "timestamp" not in df.columns:
        df["timestamp"] = df["date"]
    if "station" in df.columns and "station_id" not in df.columns:
        df["station_id"] = df["station"]
    
    # Parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    
    # Keep only relevant columns
    keep_cols = ["timestamp", "station_id", "pm2_5", "pm10", "no2", "co"]
    df = df[[c for c in keep_cols if c in df.columns]]
    
    # Sort by time
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df

def get_latest_reading(df: pd.DataFrame, station_id: str = None) -> dict:
    """Get the most recent sensor reading."""
    if station_id:
        df = df[df["station_id"] == station_id]
    latest = df.iloc[-1]
    return {
        "pm25": float(latest["pm2_5"]),
        "pm10": float(latest.get("pm10", 0)),
        "timestamp": latest["timestamp"].isoformat(),
        "station_id": latest.get("station_id", "unknown")
    }

def calculate_sensor_anomaly(df: pd.DataFrame, current_pm25: float) -> float:
    """
    Calculates anomaly score per weighted_fusion_v1 formula.
    z = (current - rolling_mean_24h) / rolling_std_24h
    """
    recent = df.tail(24)  # assuming hourly data, last 24 readings
    mean = recent["pm2_5"].mean()
    std = recent["pm2_5"].std()
    
    if std == 0 or pd.isna(std):
        return 0.0
    
    z = (current_pm25 - mean) / std
    anomaly_score = max(0, min(z / 3, 1))  # clip(z/3, 0, 1)
    return round(anomaly_score, 3)