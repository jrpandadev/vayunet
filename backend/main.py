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
from services.satellite import get_sentinel5p_features, calculate_satellite_anomaly
from services.fusion import calculate_event_confidence, identify_supporting_contradicting

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
    gemini_score = citizen_evidence.get("gemini_output", {}).get("confidence", 0.0)
    
    # Step 2: CPCB ground sensor data & anomaly score
    try:
        df = load_cpcb_data(city.lower())
        latest = get_latest_reading(df)
        sensor_anomaly = calculate_sensor_anomaly(df, latest["pm25"])
        sensor_data = {**latest, "anomaly_score": sensor_anomaly}
    except Exception as e:
        sensor_anomaly = 0.5
        sensor_data = {
            "pm25": 180.0,
            "pm10": 240.0,
            "anomaly_score": sensor_anomaly,
            "source": "CPCB_fallback",
            "station_id": "fallback_station",
            "error": str(e)
        }

    # Step 3: Open-Meteo weather data & persistence score
    try:
        weather_raw = get_weather(lat, lng)
        weather_persistence = calculate_weather_persistence(weather_raw)
        weather_data = {
            "wind_speed_kmh": weather_raw["current"]["wind_speed_10m"],
            "humidity_percent": weather_raw["current"]["relative_humidity_2m"],
            "source": "open_meteo",
            "persistence_score": weather_persistence
        }
    except Exception as e:
        weather_persistence = 0.5
        weather_data = {
            "wind_speed_kmh": 2.0,
            "humidity_percent": 80.0,
            "source": "open_meteo_fallback",
            "persistence_score": weather_persistence,
            "error": str(e)
        }

    # Step 4: Sentinel-5P satellite features & anomaly score
    try:
        satellite_raw = get_sentinel5p_features(lat=lat, lng=lng)
        satellite_anomaly = calculate_satellite_anomaly(current_no2=satellite_raw["no2_index"])
        satellite_data = {**satellite_raw, "anomaly_score": satellite_anomaly}
    except Exception as e:
        satellite_anomaly = 0.5
        satellite_data = {
            "no2_index": 18.2,
            "aerosol_index": 1.3,
            "anomaly_score": satellite_anomaly,
            "source": "Sentinel-5P",
            "freshness": "contextual",
            "error": str(e)
        }

    # Step 5: Core Fusion Engine (weighted_fusion_v1)
    fusion_result = calculate_event_confidence(
        sensor_anomaly_score=sensor_anomaly,
        gemini_evidence_score=gemini_score,
        weather_persistence_score=weather_persistence,
        satellite_signal_score=satellite_anomaly
    )

    # Step 6: Contradiction & Supporting Evidence Analysis
    evidence_breakdown = identify_supporting_contradicting(
        sensor_anomaly_score=sensor_anomaly,
        gemini_evidence_score=gemini_score,
        weather_persistence_score=weather_persistence,
        satellite_signal_score=satellite_anomaly
    )

    return {
        "event_id": event_id,
        "location": {"lat": lat, "lng": lng, "city": city},
        "evidence": {
            "citizen": citizen_evidence,
            "sensor": sensor_data,
            "satellite": satellite_data,
            "weather": weather_data
        },
        "detection": {
            **fusion_result,
            **evidence_breakdown
        },
        "status": "processed",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
