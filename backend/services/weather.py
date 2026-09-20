# backend/services/weather.py
import requests

def get_weather(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m,"
            "wind_direction_10m"
        )
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def calculate_weather_persistence(weather_data: dict) -> float:
    """
    Higher score = worse dispersion = pollution more likely to persist.
    Low wind speed + high humidity = high persistence.
    """
    wind_speed = weather_data["current"]["wind_speed_10m"]
    humidity = weather_data["current"]["relative_humidity_2m"]

    # Simple heuristic: low wind is the dominant factor
    wind_score = max(0.0, min((10.0 - wind_speed) / 10.0, 1.0))  # wind < 10km/h scores higher
    humidity_score = humidity / 100.0

    persistence_score = (0.7 * wind_score) + (0.3 * humidity_score)
    return round(persistence_score, 3)

def diagnose_inversion_proxy(weather_data: dict) -> dict:
    """
    Returns a structured proxy diagnostic for meteorological stability/inversion risk
    using surface temperature and wind speed.
    """
    try:
        curr = weather_data.get("current", {})
        wind_speed = curr.get("wind_speed_10m", 10.0)
        temp = curr.get("temperature_2m", 25.0)

        # Simple heuristic: low wind (< 2 km/h) and low temp (< 15 C) implies high inversion risk
        if wind_speed < 2.0 and temp < 15.0:
            risk = "HIGH"
        elif wind_speed < 5.0 and temp < 20.0:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "status": "AVAILABLE",
            "inversion_risk": risk,
            "wind_speed_kmh": wind_speed,
            "temperature_c": temp,
            "is_proxy": True,
            "reason": "Derived from surface heuristics (WRF-Chem PBLH explicitly disabled for demo)"
        }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "reason": f"Failed to diagnose inversion proxy: {str(e)}"
        }
