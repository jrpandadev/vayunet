from services.sensor_data import load_cpcb_data, get_latest_reading, calculate_sensor_anomaly
from services.weather import get_weather, calculate_weather_persistence

print("=== 1. Sensor Data & Anomaly Score Test ===")
df = load_cpcb_data("delhi")
latest = get_latest_reading(df)
print("Latest sensor reading:", latest)

score_180 = calculate_sensor_anomaly(df, current_pm25=180)
print(f"Anomaly score for PM2.5 = 180: {score_180}")

score_current = calculate_sensor_anomaly(df, current_pm25=latest["pm25"])
print(f"Anomaly score for PM2.5 = {latest['pm25']}: {score_current}")

print("\n=== 2. Weather & Persistence Score Test ===")
delhi_weather = get_weather(lat=28.6139, lon=77.2090)
print("Delhi Current Weather:", {
    "temperature": delhi_weather["current"]["temperature_2m"],
    "humidity": delhi_weather["current"]["relative_humidity_2m"],
    "wind_speed": delhi_weather["current"]["wind_speed_10m"]
})

persistence = calculate_weather_persistence(delhi_weather)
print(f"Weather Persistence Score: {persistence}")
