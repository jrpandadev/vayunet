from services.satellite import get_sentinel5p_features, calculate_satellite_anomaly

# Test live query for Delhi
result = get_sentinel5p_features(28.6139, 77.2090, "2024-01-01")
print("=== Satellite Signal ===")
print(result)

# Test satellite anomaly calculation
score = calculate_satellite_anomaly(current_no2=result["no2_index"])
print(f"\nSatellite Anomaly Score: {score}")
