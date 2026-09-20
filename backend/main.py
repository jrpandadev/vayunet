import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routers.reports import router as reports_router
from services.gemini_evidence import extract_evidence
from services.sensor_data import load_cpcb_data, get_latest_reading, calculate_sensor_anomaly
from services.weather import get_weather, calculate_weather_persistence, diagnose_inversion_proxy
from services.satellite import get_sentinel5p_features, calculate_satellite_anomaly
from services.fusion import calculate_event_confidence, identify_supporting_contradicting
from services.evidence_retriever import calculate_potential_regional_plume_influence
from ml.forecast_service import ForecastService
import pandas as pd
from datetime import timezone

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

app.include_router(reports_router)

TEMP_DIR = Path(__file__).resolve().parent / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Initialize ForecastService once
forecast_service = None
try:
    forecast_service = ForecastService()
except Exception as e:
    print(f"Warning: Failed to initialize ForecastService: {e}")


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


import base64
import json
from fastapi import Request, Depends
from services.auth_service import get_current_user, require_authority

@app.post("/api/report")
async def submit_report(
    request: Request,
    text: str = Form(..., description="Citizen's voice/text incident description"),
    lat: float = Form(..., description="Latitude coordinate"),
    lng: float = Form(..., description="Longitude coordinate"),
    city: str = Form(..., description="Target city name (e.g. delhi, mumbai, bhubaneswar)"),
    photo: Optional[UploadFile] = File(None, description="Optional photographic evidence"),
    user: dict = Depends(get_current_user)
):
    event_id = str(uuid.uuid4())
    user_id = user.get("uid", "anonymous")

    # Save photo temporarily if uploaded and upload to Supabase
    image_path = None
    supabase_path = None
    if photo and photo.filename:
        safe_ext = Path(photo.filename).suffix or ".jpg"
        file_name = f"{user_id}/{event_id}{safe_ext}"
        image_path = str(TEMP_DIR / f"{event_id}{safe_ext}")
        file_bytes = await photo.read()

        with open(image_path, "wb") as f:
            f.write(file_bytes)

        # Upload to Supabase
        from services.supabase_service import upload_evidence
        supabase_path = await upload_evidence(file_bytes, file_name, photo.content_type or "image/jpeg")

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
        sensor_anomaly = 0.0
        sensor_data = {
            "pm25": None,
            "pm10": None,
            "anomaly_score": None,
            "source": "CPCB",
            "status": "UNAVAILABLE",
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
        weather_persistence = 0.0
        weather_data = {
            "wind_speed_kmh": None,
            "humidity_percent": None,
            "source": "open_meteo",
            "status": "UNAVAILABLE",
            "persistence_score": None,
            "error": str(e)
        }

    # Step 4: Sentinel-5P satellite features & anomaly score
    try:
        satellite_raw = get_sentinel5p_features(lat=lat, lng=lng)
        satellite_anomaly = calculate_satellite_anomaly(current_no2=satellite_raw["no2_index"])
        satellite_data = {**satellite_raw, "anomaly_score": satellite_anomaly}
    except Exception as e:
        satellite_anomaly = 0.0
        satellite_data = {
            "no2_index": None,
            "aerosol_index": None,
            "anomaly_score": None,
            "source": "Sentinel-5P",
            "status": "UNAVAILABLE",
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

    # Attach supabase_path to citizen_evidence if available
    if supabase_path:
        citizen_evidence["supabase_path"] = supabase_path

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


@app.get("/api/evidence/url")
async def get_evidence_url(
    path: str,
    user: dict = Depends(get_current_user)
):

    from services.supabase_service import get_signed_url
    signed_url = await get_signed_url(path)
    if not signed_url:
        raise HTTPException(status_code=404, detail="File not found or configuration missing")
    return {"url": signed_url}


@app.get("/api/sih_forecast")
def get_sih_forecast(
    lat: float,
    lng: float,
    city: str,
    user: dict = Depends(require_authority)
):
    event_id = f"SIH-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    report_dt = datetime.now(timezone.utc)

    # 1. Weather & Inversion Proxy
    try:
        weather_raw = get_weather(lat, lng)
        inversion = diagnose_inversion_proxy(weather_raw)
        wind_dir = weather_raw.get("current", {}).get("wind_direction_10m", 0.0)
        wind_speed = weather_raw.get("current", {}).get("wind_speed_10m", 0.0)
    except Exception as e:
        inversion = {"status": "UNAVAILABLE", "reason": str(e)}
        wind_dir = 0.0
        wind_speed = 0.0

    # 2. Plume Influence Proxy
    try:
        plume = calculate_potential_regional_plume_influence(lat, lng, wind_dir, report_dt)
    except Exception as e:
        plume = {"status": "UNAVAILABLE", "reason": str(e)}

    # 3. PM2.5 Forecast (72-hour)
    pm25_forecast = {"status": "UNAVAILABLE", "reason": "Model not loaded"}
    if forecast_service:
        try:
            # We construct a dummy feature row with defaults to run the forecast service
            sample_row = pd.DataFrame([{}])
            for col in forecast_service.feature_cols:
                sample_row[col] = 0
            if "temperature_2m" in sample_row.columns:
                try:
                    sample_row["temperature_2m"] = weather_raw.get("current", {}).get("temperature_2m", 25.0)
                except Exception:
                    pass

            result = forecast_service.predict(sample_row)
            pm25_forecast = {
                "status": "AVAILABLE",
                "forecast": result["forecast"],
                "spike_risk": result["spike_risk"]
            }
        except Exception as e:
            pm25_forecast = {"status": "UNAVAILABLE", "reason": str(e)}

    return {
        "event_id": event_id,
        "location": {"lat": lat, "lng": lng, "city": city},
        "forecasts": {
            "pm25": pm25_forecast,
            "pm10": {"status": "UNAVAILABLE", "reason": "No validated forecast model currently connected"},
            "o3": {"status": "UNAVAILABLE", "reason": "No validated forecast model currently connected"},
            "nox": {"status": "UNAVAILABLE", "reason": "No validated forecast model currently connected"}
        },
        "diagnostics": {
            "inversion_proxy": inversion,
            "plume_influence_proxy": plume,
            "wind": {
                "speed_kmh": wind_speed,
                "direction_deg": wind_dir
            }
        },
        "risk_level": pm25_forecast.get("spike_risk", {}).get("level", "UNKNOWN"),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
