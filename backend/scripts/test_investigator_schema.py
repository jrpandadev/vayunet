import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pydantic import ValidationError
from backend.schemas.investigator_output_schema import (
    PollutionEventInvestigationReport,
    SeverityLevel,
    VentilationStatus,
    InversionRisk,
    WindTransportRegime,
    SourceHypothesisType,
    SupportLevel,
    ConfidenceLevel,
    PublicHealthRiskLevel
)

def create_valid_report_dict():
    return {
        "investigation_id": "INV_anand_vihar_202201010000",
        "event_id": "anand vihar_202201010000",
        "station_id": "anand vihar",
        "generated_at": "2026-09-13T21:00:00Z",
        "investigation_version": "1.0.0",
        "event_summary": {
            "start_time": "2022-01-01 00:00:00",
            "end_time": "2022-01-06 08:00:00",
            "duration_hours": 129,
            "severity": "SEVERE_EVENT",
            "peak_pm25": 818.75,
            "mean_pm25": 354.33,
            "min_pm25": 88.67,
            "onset_growth": 304.5
        },
        "meteorological_assessment": {
            "ventilation_status": "POOR",
            "inversion_risk": "HIGH",
            "wind_transport_regime": "STAGNANT",
            "evidence_notes": "Mean wind speed was calm at 1.2 m/s with estimated nocturnal PBLH dropping below 250m."
        },
        "evaluated_hypotheses": [
            {
                "hypothesis": "METEOROLOGICAL_STAGNATION_INVERSION",
                "support_level": "STRONG_SUPPORT",
                "confidence": "HIGH",
                "supporting_evidence": [
                    "Observed calm wind speed mean of 1.2 m/s",
                    "Boundary layer height averaged 227.9m across the 129h episode",
                    "High relative humidity averaging 77.8% favors particulate accumulation"
                ],
                "contrasting_evidence": [],
                "causal_disclaimer": "Statistical association based on observational proximity; direct causality cannot be established."
            },
            {
                "hypothesis": "BIOMASS_BURNING_REGIONAL",
                "support_level": "WEAK_SUPPORT",
                "confidence": "MEDIUM",
                "supporting_evidence": [
                    "28 FIRMS thermal detections observed within 50km during the 72h onset window"
                ],
                "contrasting_evidence": [
                    "Low regional transport winds suggest primarily localized accumulation rather than distant plume advection"
                ],
                "causal_disclaimer": "Statistical association based on observational proximity; direct causality cannot be established."
            }
        ],
        "primary_contributing_factors": [
            "METEOROLOGICAL_STAGNATION_INVERSION"
        ],
        "data_quality_audit": {
            "missing_indicators": ["Sentinel-5P NO2"],
            "instrument_artifacts_detected": ["CPCB 998 ceiling not triggered; peak was 818.75 µg/m³"],
            "data_completeness_score": 0.85
        },
        "public_health_exposure": {
            "risk_level": "EMERGENCY",
            "dominant_health_concern": "Sustained severe particulate exposure over 5 continuous days",
            "recommended_precautions": [
                "Issue public health emergency advisory",
                "Advise vulnerable groups to remain indoors with air filtration",
                "Halt non-essential outdoor physical activity"
            ]
        },
        "synthesis_narrative": "The 129-hour severe episode at Anand Vihar was characterized by persistent atmospheric stagnation, with mean wind speed of 1.2 m/s and nocturnal boundary layer compression. Evidence is strongly consistent with local pollutant trapping under an inversion layer, accompanied by moderate localized background emissions."
    }

def test_valid_report():
    data = create_valid_report_dict()
    report = PollutionEventInvestigationReport.model_validate(data)
    assert report.event_id == "anand vihar_202201010000"
    assert report.event_summary.duration_hours == 129
    assert len(report.evaluated_hypotheses) == 2
    print("PASS: Valid report validates cleanly.")

def test_forbidden_causal_language():
    data = create_valid_report_dict()
    # Insert forbidden causal phrase
    data["synthesis_narrative"] = "The severe pollution episode was definitely caused by stubble burning in Punjab."
    try:
        PollutionEventInvestigationReport.model_validate(data)
        assert False, "Should have failed due to forbidden causal phrase!"
    except ValidationError as e:
        assert "Non-causal violation" in str(e)
        print("PASS: Causal phrase 'definitely caused' successfully rejected.")

def test_forbidden_extra_fields():
    data = create_valid_report_dict()
    data["unauthorized_extra_field"] = "malicious_injection"
    try:
        PollutionEventInvestigationReport.model_validate(data)
        assert False, "Should have failed due to extra field!"
    except ValidationError as e:
        assert "Extra inputs are not permitted" in str(e)
        print("PASS: Extra fields successfully rejected.")

def test_invalid_enum():
    data = create_valid_report_dict()
    data["meteorological_assessment"]["ventilation_status"] = "SUPER_AWESOME"
    try:
        PollutionEventInvestigationReport.model_validate(data)
        assert False, "Should have failed due to invalid enum!"
    except ValidationError as e:
        assert "Input should be 'POOR', 'MODERATE', 'FAVORABLE' or 'UNKNOWN'" in str(e)
        print("PASS: Invalid enum rejected.")

if __name__ == "__main__":
    test_valid_report()
    test_forbidden_causal_language()
    test_forbidden_extra_fields()
    test_invalid_enum()
    print("ALL 4 SCHEMA TESTS PASSED SUCCESSFULLY!")
