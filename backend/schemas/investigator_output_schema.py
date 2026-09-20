"""
Strict Pydantic V2 Models and JSON Schema for VayuNet Pollution Event Investigator.

Enforces:
1. Strict schema validation (no extra properties allowed).
2. Non-causal terminology compliance (prohibits definitive causal claims).
3. Standardized Source Hypothesis Taxonomy.
4. Auditable evidence citations (every hypothesis must cite quantitative metrics).
"""

from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class SeverityLevel(str, Enum):
    SEVERE_EVENT = "SEVERE_EVENT"
    POLLUTION_EVENT = "POLLUTION_EVENT"


class VentilationStatus(str, Enum):
    POOR = "POOR"
    MODERATE = "MODERATE"
    FAVORABLE = "FAVORABLE"
    UNKNOWN = "UNKNOWN"


class InversionRisk(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class WindTransportRegime(str, Enum):
    STAGNANT = "STAGNANT"
    LOCAL_CIRCULATION = "LOCAL_CIRCULATION"
    REGIONAL_ADVECTION = "REGIONAL_ADVECTION"
    UNKNOWN = "UNKNOWN"


class SourceHypothesisType(str, Enum):
    BIOMASS_BURNING_REGIONAL = "BIOMASS_BURNING_REGIONAL"
    LOCAL_WASTE_BURNING = "LOCAL_WASTE_BURNING"
    METEOROLOGICAL_STAGNATION_INVERSION = "METEOROLOGICAL_STAGNATION_INVERSION"
    URBAN_TRAFFIC_INDUSTRIAL = "URBAN_TRAFFIC_INDUSTRIAL"
    DUST_OR_COARSE_PARTICULATE = "DUST_OR_COARSE_PARTICULATE"
    SECONDARY_AEROSOL_FORMATION = "SECONDARY_AEROSOL_FORMATION"
    UNCLASSIFIED_MULTIFACTOR = "UNCLASSIFIED_MULTIFACTOR"


class SupportLevel(str, Enum):
    STRONG_SUPPORT = "STRONG_SUPPORT"
    MODERATE_SUPPORT = "MODERATE_SUPPORT"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTED = "CONTRADICTED"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PublicHealthRiskLevel(str, Enum):
    MODERATE = "MODERATE"
    POOR = "POOR"
    VERY_POOR = "VERY_POOR"
    SEVERE = "SEVERE"
    EMERGENCY = "EMERGENCY"


FORBIDDEN_CAUSAL_PHRASES = [
    "definitely caused",
    "proven cause",
    "the sole cause",
    "is the cause of",
    "was caused solely",
    "unquestionably caused",
    "directly caused",
]


class EventSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time: str = Field(..., description="ISO 8601 timestamp of event start")
    end_time: str = Field(..., description="ISO 8601 timestamp of event end")
    duration_hours: int = Field(..., ge=1, description="Event duration in continuous hours")
    severity: SeverityLevel = Field(..., description="Classification: POLLUTION_EVENT or SEVERE_EVENT")
    peak_pm25: float = Field(..., ge=0.0, description="Peak PM2.5 in µg/m³ recorded during event")
    mean_pm25: float = Field(..., ge=0.0, description="Mean PM2.5 in µg/m³ across observed hours")
    min_pm25: float = Field(..., ge=0.0, description="Minimum PM2.5 in µg/m³ across observed hours")
    onset_growth: float = Field(..., description="1-hour PM2.5 delta (µg/m³/h) at onset")


class MeteorologicalAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ventilation_status: VentilationStatus = Field(
        ..., description="Atmospheric dispersion capability: POOR, MODERATE, FAVORABLE, or UNKNOWN"
    )
    inversion_risk: InversionRisk = Field(
        ..., description="Risk of thermal trapping based on PBLH and diurnal cycle"
    )
    wind_transport_regime: WindTransportRegime = Field(
        ..., description="STAGNANT (<1.5 m/s), LOCAL_CIRCULATION, or REGIONAL_ADVECTION"
    )
    evidence_notes: str = Field(
        ..., min_length=10, description="Specific meteorological metrics cited (wind speed, pblh, humidity)"
    )


class HypothesisEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis: SourceHypothesisType = Field(..., description="Taxonomy source hypothesis being evaluated")
    support_level: SupportLevel = Field(..., description="Categorical degree of empirical support")
    confidence: ConfidenceLevel = Field(..., description="Confidence in assessment based on data completeness")
    supporting_evidence: List[str] = Field(
        ..., min_length=1, description="List of quantitative observations supporting this hypothesis"
    )
    contrasting_evidence: List[str] = Field(
        default_factory=list, description="List of observations conflicting with or weakening this hypothesis"
    )
    causal_disclaimer: str = Field(
        default="Statistical association based on observational proximity; direct causality cannot be established.",
        description="Mandatory non-causal disclaimer statement"
    )

    @field_validator("supporting_evidence", "contrasting_evidence")
    @classmethod
    def check_non_causal_language(cls, evidence_list: List[str]) -> List[str]:
        for item in evidence_list:
            lower = item.lower()
            for phrase in FORBIDDEN_CAUSAL_PHRASES:
                if phrase in lower:
                    raise ValueError(
                        f"Non-causal violation: phrase '{phrase}' found in evidence '{item}'. "
                        "Must use non-causal terminology such as 'associated with', 'correlated with', or 'consistent with'."
                    )
        return evidence_list


class DataQualityAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_indicators: List[str] = Field(
        default_factory=list, description="Variables absent in evidence bundle (e.g. 'PBLH', 'Sentinel-5P NO2')"
    )
    instrument_artifacts_detected: List[str] = Field(
        default_factory=list, description="Known sensor limits detected (e.g. 'CPCB 998 µg/m³ saturation ceiling')"
    )
    data_completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Proportion of expected observational modalities available"
    )


class PublicHealthExposure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: PublicHealthRiskLevel = Field(..., description="Exposure risk category")
    dominant_health_concern: str = Field(..., min_length=5, description="Primary exposure concern")
    recommended_precautions: List[str] = Field(
        ..., min_length=1, description="Targeted guidance for sensitive populations and general public"
    )


class PollutionEventInvestigationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investigation_id: str = Field(..., description="Unique investigation identifier (e.g. INV_anand_vihar_202201010000)")
    event_id: str = Field(..., description="Target event identifier matching the evidence bundle")
    station_id: str = Field(..., description="Station name (e.g. anand vihar)")
    generated_at: str = Field(..., description="ISO 8601 generation timestamp")
    investigation_version: str = Field("1.0.0", description="Investigator engine schema version")

    event_summary: EventSummary = Field(..., description="Deterministic event boundary metrics")
    meteorological_assessment: MeteorologicalAssessment = Field(..., description="Atmospheric ventilation assessment")
    evaluated_hypotheses: List[HypothesisEvaluation] = Field(
        ..., min_length=1, description="Structured evaluation of source hypotheses from the taxonomy"
    )
    primary_contributing_factors: List[SourceHypothesisType] = Field(
        ..., min_length=1, description="Top hypotheses exhibiting STRONG_SUPPORT or MODERATE_SUPPORT"
    )
    data_quality_audit: DataQualityAudit = Field(..., description="Assessment of missing data and instrument artifacts")
    public_health_exposure: PublicHealthExposure = Field(..., description="Exposure and advisory assessment")
    synthesis_narrative: str = Field(
        ..., min_length=50, description="Non-causal analytical synthesis integrating meteorology, emissions, and dynamics"
    )

    @field_validator("synthesis_narrative")
    @classmethod
    def check_narrative_causality(cls, v: str) -> str:
        lower = v.lower()
        for phrase in FORBIDDEN_CAUSAL_PHRASES:
            if phrase in lower:
                raise ValueError(
                    f"Non-causal violation in synthesis_narrative: forbidden phrase '{phrase}'. "
                    "All conclusions must be framed as observational associations."
                )
        return v


def export_json_schema(output_path: Optional[str] = None) -> dict:
    """Export the Pydantic model to a standard JSON Schema draft-07/2020-12 dictionary."""
    schema = PollutionEventInvestigationReport.model_json_schema()
    if output_path:
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
    return schema


if __name__ == "__main__":
    from pathlib import Path
    out_file = Path(__file__).resolve().parent / "investigator_output_schema.json"
    schema = export_json_schema(str(out_file))
    print(f"Exported strict JSON Schema to {out_file} ({len(schema['properties'])} top-level properties)")
