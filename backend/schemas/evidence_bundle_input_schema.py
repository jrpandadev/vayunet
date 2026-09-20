from pydantic import BaseModel, Field
from typing import Optional

class EventInfo(BaseModel):
    start_time: str
    end_time: str
    duration_hours: Optional[int]
    severity: str
    peak_pm25: Optional[float]
    mean_pm25: Optional[float]
    min_pm25: Optional[float]
    onset_growth: Optional[float]

class Stat(BaseModel):
    mean: Optional[float] = None
    max: Optional[float] = None

class WindDirection(BaseModel):
    mean_sin: Optional[float] = None
    mean_cos: Optional[float] = None

class PollutionDynamics(BaseModel):
    pm25: Stat
    pm10: Stat
    no2: Stat

class Meteorology(BaseModel):
    temperature: Stat
    relative_humidity: Stat
    wind_speed: Stat
    wind_direction: WindDirection
    pblh: Stat

class NWP(BaseModel):
    forecast_6h: Optional[float] = None
    forecast_24h: Optional[float] = None
    forecast_72h: Optional[float] = None
    provenance: Optional[str] = None

class Satellite(BaseModel):
    sentinel5p_no2_latest: Optional[float] = None
    sentinel5p_no2_age_hours: Optional[float] = None

class FireActivity(BaseModel):
    firms_detections_72h_50km: Optional[int] = None

class SourceContext(BaseModel):
    owbeii_waste_burned: Optional[float] = None

class EvidenceBundleInput(BaseModel):
    event_id: str
    station_id: str
    event: EventInfo
    pollution_dynamics: PollutionDynamics
    meteorology: Meteorology
    nwp: NWP
    satellite: Satellite
    fire_activity: FireActivity
    source_context: SourceContext

    class Config:
        extra = "forbid"

if __name__ == "__main__":
    import json
    schema = EvidenceBundleInput.schema()
    with open(r"c:\Users\jrpan\.gemini\antigravity-ide\scratch\vayunet\backend\schemas\evidence_bundle_input_schema.json", "w") as f:
        json.dump(schema, f, indent=2)
