from services.fusion import calculate_event_confidence, identify_supporting_contradicting

print("=" * 65)
print("VAYUNET FUSION ENGINE (weighted_fusion_v1) SENSITIVITY TEST")
print("=" * 65)

# Scenario 1: Strong multi-source event
result1 = calculate_event_confidence(0.8, 0.82, 0.75, 0.6)
print("\nScenario 1: Strong multi-source event")
print("Scores  : sensor=0.8, gemini=0.82, weather=0.75, satellite=0.6")
print("Output  :", result1)
assert result1["level"] == "HIGH"
assert result1["confidence"] >= 0.7

# Scenario 2: Citizen report only, no corroboration (should be capped)
result2 = calculate_event_confidence(0.1, 0.9, 0.2, 0.1)
print("\nScenario 2: Citizen-only, no sensor/satellite corroboration")
print("Scores  : sensor=0.1, gemini=0.90, weather=0.2, satellite=0.1")
print("Output  :", result2)
assert result2["confidence"] <= 0.7


# Scenario 3: Weak/no event
result3 = calculate_event_confidence(0.1, 0.2, 0.15, 0.1)
print("\nScenario 3: Weak/no event")
print("Scores  : sensor=0.1, gemini=0.2, weather=0.15, satellite=0.1")
print("Output  :", result3)
assert result3["level"] == "LOW"

# Scenario 4: Contradiction detection
evidence = identify_supporting_contradicting(0.8, 0.82, 0.75, 0.1)
print("\nScenario 4: Evidence contradiction breakdown")
print("Output  :", evidence)
assert "satellite" in evidence["contradicting_evidence"]
assert "sensor" in evidence["supporting_evidence"]

print("\n" + "=" * 65)
print("ALL FUSION SCENARIO TESTS PASSED SUCCESSFULLY!")
print("=" * 65)
