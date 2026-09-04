from services.fusion import calculate_event_confidence

# Test with Gemini=1.0, Sensor=0.1, Satellite=0.1, Weather=1.0
res = calculate_event_confidence(
    sensor_anomaly_score=0.1,
    gemini_evidence_score=1.0,
    weather_persistence_score=1.0,
    satellite_signal_score=0.1
)
print("Uncapped Score would be 0.535.")
print("If Gemini=1.0 and Weather=1.0 but no Sensor/Satellite corroboration, Output is:", res)
assert res["confidence"] <= 0.70
