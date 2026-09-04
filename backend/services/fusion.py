from typing import Literal, Dict, Any

def calculate_event_confidence(
    sensor_anomaly_score: float,
    gemini_evidence_score: float,
    weather_persistence_score: float,
    satellite_signal_score: float
) -> Dict[str, Any]:
    """
    weighted_fusion_v1 — locked formula from architecture doc (§10 & BUILD_RULES.md).
    0.35 * sensor + 0.30 * gemini + 0.20 * weather + 0.15 * satellite
    """
    confidence = (
        0.35 * sensor_anomaly_score
        + 0.30 * gemini_evidence_score
        + 0.20 * weather_persistence_score
        + 0.15 * satellite_signal_score
    )
    confidence = round(min(confidence, 1.0), 3)
    
    # Anti-abuse rule: citizen evidence alone cannot exceed 0.7
    citizen_only = (
        sensor_anomaly_score < 0.2 
        and satellite_signal_score < 0.2
    )
    if citizen_only and confidence > 0.7:
        confidence = 0.65  # cap it
    
    if confidence < 0.4:
        level = "LOW"
    elif confidence < 0.7:
        level = "MODERATE"
    else:
        level = "HIGH"
    
    return {
        "confidence": confidence,
        "level": level,
        "method": "weighted_fusion_v1"
    }


def identify_supporting_contradicting(
    sensor_anomaly_score: float,
    gemini_evidence_score: float,
    weather_persistence_score: float,
    satellite_signal_score: float,
    threshold: float = 0.3
) -> Dict[str, Any]:
    """
    Basic contradiction detection — flags which sources support 
    vs fail to support the event.
    """
    scores = {
        "sensor": sensor_anomaly_score,
        "citizen": gemini_evidence_score,
        "weather": weather_persistence_score,
        "satellite": satellite_signal_score
    }
    
    supporting = [k for k, v in scores.items() if v >= threshold]
    contradicting = [k for k, v in scores.items() if v < threshold]
    
    return {
        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting
    }
