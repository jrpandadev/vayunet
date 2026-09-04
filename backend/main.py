import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.gemini_evidence import extract_evidence
from services.sensor_data import load_cpcb_data, get_latest_reading, calculate_sensor_anomaly
from services.weather import get_weather, calculate_weather_persistence
from services.satellite import get_sentinel5p_features

app = FastAPI(
    title="VayuNet API",
    description="Federated Environmental Intelligence Platform for Hyper-Local Pollution Detection",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = Path(__file__).resolve().parent / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def health_check():
    return {
        "status": "VayuNet backend running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
def health_check_endpoint():
    return {
        "status": "healthy",
        "service": "VayuNet Ingestion & Event API",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }


@app.post("/api/report")
async def submit_report(
    text: str = Form(..., description="Citizen's voice/text incident description"),
    lat: float = Form(..., description="Latitude coordinate"),
    lng: float = Form(..., description="Longitude coordinate"),
    city: str = Form(..., description="Target city name (e.g. delhi, mumbai, bhubaneswar)"),
    photo: Optional[UploadFile] = File(None, description="Optional photographic evidence")
):
    event_id = str(uuid.uuid4())
    
    # Save photo temporarily if uploaded
    image_path = None
    if photo and photo.filename:
        safe_ext = Path(photo.filename).suffix or ".jpg"
        image_path = str(TEMP_DIR / f"{event_id}{safe_ext}")
        with open(image_path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
    
    # Step 1: Gemini multimodal evidence extraction
    citizen_evidence = extract_evidence(description=text, image_path=image_path)
    
    # Step 2: CPCB ground sensor data & anomaly score
    try:
        df = load_cpcb_data(city.lower())
        latest = get_latest_reading(df)
        anomaly_score = calculate_sensor_anomaly(df, latest["pm25"])
        sensor_data = {**latest, "anomaly_score": anomaly_score}
    except Exception as e:
        sensor_data = {
            "pm25": 180.0,
            "pm10": 240.0,
            "anomaly_score": 0.5,
            "source": "CPCB_fallback",
            "station_id": "fallback_station",
            "error": str(e)
        }

    # Step 3: Open-Meteo weather data & persistence score
    try:
        weather_raw = get_weather(lat, lng)
        persistence_score = calculate_weather_persistence(weather_raw)
        weather_data = {
            "wind_speed_kmh": weather_raw["current"]["wind_speed_10m"],
            "humidity_percent": weather_raw["current"]["relative_humidity_2m"],
            "source": "open_meteo",
            "persistence_score": persistence_score
        }
    except Exception as e:
        persistence_score = 0.5
        weather_data = {
            "wind_speed_kmh": 2.0,
            "humidity_percent": 80.0,
            "source": "open_meteo_fallback",
            "persistence_score": persistence_score,
            "error": str(e)
        }

    # Step 4: Sentinel-5P satellite features
    try:
        satellite_data = get_sentinel5p_features(lat=lat, lng=lng)
    except Exception as e:
        satellite_data = {
            "no2_index": 18.2,
            "aerosol_index": 1.3,
            "source": "Sentinel-5P",
            "freshness": "contextual",
            "error": str(e)
        }

    return {
        "event_id": event_id,
        "location": {"lat": lat, "lng": lng, "city": city},
        "citizen_evidence": citizen_evidence,
        "sensor": sensor_data,
        "weather": weather_data,
        "satellite": satellite_data,
        "status": "processed",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
