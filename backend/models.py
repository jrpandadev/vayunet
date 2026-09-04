from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class Location(BaseModel):
    lat: float
    lng: float
    city: str


class CitizenGeminiOutput(BaseModel):
    event_type: str
    severity: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str
    needs_human_review: bool


class CitizenEvidence(BaseModel):
    gemini_output: CitizenGeminiOutput
    photo_url: Optional[str] = None
    source: str = "citizen"
    freshness: str = "fresh"


class SensorEvidence(BaseModel):
    pm25: float
    pm10: float
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    source: str = "CPCB"
    station_id: str
    quality: str = "verified"


class SatelliteEvidence(BaseModel):
    no2_index: float
    aerosol_index: float
    source: str = "Sentinel-5P"
    freshness: str = "contextual"


class WeatherEvidence(BaseModel):
    wind_speed_kmh: float
    humidity_percent: float
    source: str = "open_meteo"


class Evidence(BaseModel):
    citizen: CitizenEvidence
    sensor: SensorEvidence
    satellite: SatelliteEvidence
    weather: WeatherEvidence


class Correlation(BaseModel):
    duplicate_of: Optional[str] = None
    supporting_reports_count: int = Field(default=0, ge=0)


class Detection(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    method: str = "weighted_fusion_v1"
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)


class Forecast(BaseModel):
    pm25_6h: float
    pm25_24h: float
    pm25_72h: float
    spike_probability: Literal["LOW", "MEDIUM", "HIGH"]
    forecast_uncertainty: Literal["LOW", "MEDIUM", "HIGH"]


class SourceHypothesis(BaseModel):
    category: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class AuthorityResponse(BaseModel):
    alert_sent: bool = False
    authority_class: str
    status: Literal["pending", "acknowledged", "investigating", "confirmed", "dismissed", "resolved"] = "pending"


class TimelineEntry(BaseModel):
    time: str
    event: str


class VayuNetPollutionEvent(BaseModel):
    """
    Locked VayuNet Pollution Event Schema matching Master Architecture Doc §11
    and /docs/schema.json.
    """
    event_id: str
    location: Location
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    evidence: Evidence
    correlation: Correlation
    detection: Detection
    forecast: Forecast
    risk: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    source_hypothesis: SourceHypothesis
    explanation: str
    response: AuthorityResponse
    outcome: Optional[str] = "unconfirmed"
    timeline: List[TimelineEntry] = Field(default_factory=list)
