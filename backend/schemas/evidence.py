from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from schemas.report import LocationCoords


class DataAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    STALE = "STALE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PollutantObservation(BaseModel):
    """Specific pollutant reading from a ground sensor station."""
    pollutant: str = Field(..., description="Chemical or particle symbol (e.g. PM2.5, PM10, NO2, CO)")
    value: float = Field(..., description="Measured concentration value")
    unit: str = Field(..., description="Unit of measurement (e.g. µg/m³, mg/m³)")
    observation_time: str = Field(..., description="ISO 8601 observation timestamp")


class CPCBStationEvidence(BaseModel):
    """Ground-level sensor evidence retrieved from nearest CPCB/DPCC/IMD station."""
    status: DataAvailability
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    observation_time: Optional[str] = None
    pollutants: Dict[str, PollutantObservation] = Field(default_factory=dict)
    provenance: str = "CPCB_Ground_Sensor_Network"


class WeatherEvidence(BaseModel):
    """Meteorological observations retrieved around report location and time."""
    status: DataAvailability
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    surface_pressure_hpa: Optional[float] = None
    boundary_layer_height_m: Optional[float] = None
    observation_time: Optional[str] = None
    provenance: str = "Open_Meteo_ERA5"


class Sentinel5PEvidence(BaseModel):
    """Satellite atmospheric observations retrieved from Sentinel-5P / Copernicus."""
    status: DataAvailability
    no2_column_number_density: Optional[float] = Field(
        None, description="Tropospheric NO2 column density (µmol/m² or scaled 1e-6 mol/m²)"
    )
    absorbing_aerosol_index: Optional[float] = Field(
        None, description="UV absorbing aerosol index (unitless index)"
    )
    observation_time: Optional[str] = None
    age_hours: Optional[float] = Field(
        None, description="Temporal age in hours of satellite pass relative to report timestamp"
    )
    provenance: str = "Copernicus_Sentinel_5P_OFFL"


class FIRMFireRecord(BaseModel):
    """Individual active fire detection record from VIIRS / FIRMS."""
    latitude: float
    longitude: float
    distance_km: float
    frp: float = Field(..., description="Fire Radiative Power in MW")
    confidence: Optional[str] = None
    detection_time: str


class FIRMSEvidence(BaseModel):
    """Active fire detection evidence within spatial and temporal proximity."""
    status: DataAvailability
    detection_count: int = Field(default=0, ge=0)
    nearest_fire_distance_km: Optional[float] = None
    max_frp: Optional[float] = None
    fires: List[FIRMFireRecord] = Field(default_factory=list)
    search_radius_km: float = 50.0
    temporal_window_hours: float = 72.0
    provenance: str = "NASA_FIRMS_VIIRS"


class StaticSourceEvidence(BaseModel):
    """Static environmental or emissions context (e.g. OWBEII open waste burning inventory)."""
    status: DataAvailability
    source_type: str = "OWBEII_open_waste_burning"
    nearest_grid_lat: Optional[float] = None
    nearest_grid_lon: Optional[float] = None
    distance_km: Optional[float] = None
    annual_emission_val: Optional[float] = None
    unit: str = "kg yr-1"
    provenance: str = "OWBEII_Emissions_Inventory"


class EvidencePackage(BaseModel):
    """
    Standardized Evidence Package aggregating all deterministic environmental
    observations retrieved for a citizen report.
    Does NOT contain AI verification, LLM reasoning, or confidence verdicts.
    """
    report_id: str
    location: LocationCoords
    timestamp: str
    cpcb: CPCBStationEvidence
    weather: WeatherEvidence
    satellite: Sentinel5PEvidence
    firms: FIRMSEvidence
    static_sources: List[StaticSourceEvidence] = Field(default_factory=list)
    conflicting_signals_noted: List[str] = Field(default_factory=list)
    retrieved_at: str
