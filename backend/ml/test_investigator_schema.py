import pytest
import sys
from pathlib import Path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from pydantic import ValidationError
from schemas.investigator_output_schema import (
    PollutionEventInvestigationReport,
    HypothesisEvaluation,
    SourceHypothesisType,
    SupportLevel,
    ConfidenceLevel,
    EventSummary,
    SeverityLevel,
    MeteorologicalAssessment,
    VentilationStatus,
    InversionRisk,
    WindTransportRegime,
    DataQualityAudit,
    PublicHealthExposure,
    PublicHealthRiskLevel
)
from ml.grounding_validator import GroundingValidator

def create_valid_report():
    return PollutionEventInvestigationReport(
        investigation_id="INV_test_01",
        event_id="test_01",
        station_id="anand vihar",
        generated_at="2023-11-01T12:00:00Z",
        event_summary=EventSummary(
            start_time="2023-11-01T00:00:00Z",
            end_time="2023-11-02T00:00:00Z",
            duration_hours=24,
            severity=SeverityLevel.SEVERE_EVENT,
            peak_pm25=400.5,
            mean_pm25=300.2,
            min_pm25=150.0,
            onset_growth=50.0
        ),
        meteorological_assessment=MeteorologicalAssessment(
            ventilation_status=VentilationStatus.POOR,
            inversion_risk=InversionRisk.HIGH,
            wind_transport_regime=WindTransportRegime.STAGNANT,
            evidence_notes="Low wind speed 1m/s and PBLH 300m"
        ),
        evaluated_hypotheses=[
            HypothesisEvaluation(
                hypothesis=SourceHypothesisType.BIOMASS_BURNING_REGIONAL,
                support_level=SupportLevel.WEAK_SUPPORT,
                confidence=ConfidenceLevel.MEDIUM,
                supporting_evidence=["Some fires detected"],
                contrasting_evidence=["Winds are stagnant, not advecting from source"],
            )
        ],
        primary_contributing_factors=[SourceHypothesisType.METEOROLOGICAL_STAGNATION_INVERSION],
        data_quality_audit=DataQualityAudit(
            missing_indicators=["nwp.forecast_6h"],
            data_completeness_score=0.8
        ),
        public_health_exposure=PublicHealthExposure(
            risk_level=PublicHealthRiskLevel.SEVERE,
            dominant_health_concern="PM2.5 exposure",
            recommended_precautions=["Stay indoors"]
        ),
        synthesis_narrative="The event is associated with extremely low ventilation and is consistent with local accumulation."
    )

def test_causal_overclaim():
    report = create_valid_report()

    with pytest.raises(ValidationError) as exc_info:
        report.synthesis_narrative = "The event was caused solely by biomass burning, which was the main reason for the spike."
        PollutionEventInvestigationReport(**report.model_dump())
    assert "Non-causal violation" in str(exc_info.value)

def test_schema_violation():
    raw_dict = create_valid_report().model_dump()
    raw_dict["extra_field"] = "This should be rejected"

    with pytest.raises(ValidationError) as exc_info:
        PollutionEventInvestigationReport(**raw_dict)
    assert "Extra inputs are not permitted" in str(exc_info.value)

def test_grounding_validator():
    report = create_valid_report().model_dump()

    # 1. Valid Grounding
    bundle_data = {
        "event_summary": {"peak_pm25": 400.5, "mean_pm25": 300.2},
        "nwp": {"forecast_6h": 350.0},
        "firms_viirs": [{"frp": 12.0}],
    }
    is_valid, errs = GroundingValidator.validate(report, bundle_data)
    assert is_valid, f"Expected valid, got: {errs}"

    # 2. Missing-NWP Hallucination
    bundle_data_no_nwp = {
        "event_summary": {"peak_pm25": 400.5},
        "nwp": {"forecast_6h": None, "forecast_24h": None, "forecast_72h": None},
    }
    report["synthesis_narrative"] = "The forecast predicted 450.0 pm2.5."
    is_valid, errs = GroundingValidator.validate(report, bundle_data_no_nwp)
    assert not is_valid
    assert any("NWP forecast mentioned numerically" in e for e in errs)

    # 3. Unsupported Source Claim
    bundle_data_no_firms = {
        "event_summary": {"peak_pm25": 400.5},
        "firms_viirs": []
    }
    report["synthesis_narrative"] = "FIRMS detected active fires nearby."
    is_valid, errs = GroundingValidator.validate(report, bundle_data_no_firms)
    assert not is_valid
    assert any("FIRMS/VIIRS active fires mentioned" in e for e in errs)

    # 4. Numerical Hallucination
    bundle_data_numbers = {
        "event_summary": {"peak_pm25": 400.5},
    }
    report["synthesis_narrative"] = "Peak was 999.5"
    is_valid, errs = GroundingValidator.validate(report, bundle_data_numbers)
    assert not is_valid
    assert any("999.5 not found in bundle" in e for e in errs)

    # 5. Causal Overreach (Extended)
    report["synthesis_narrative"] = "This proves that traffic is the reason."
    is_valid, errs = GroundingValidator.validate(report, bundle_data_numbers)
    assert not is_valid
    assert any("proves" in e for e in errs)

if __name__ == "__main__":
    pytest.main([__file__])
