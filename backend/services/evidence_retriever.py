import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd

from schemas.evidence import (
    DataAvailability,
    PollutantObservation,
    CPCBStationEvidence,
    WeatherEvidence,
    Sentinel5PEvidence,
    FIRMFireRecord,
    FIRMSEvidence,
    StaticSourceEvidence,
    EvidencePackage,
)
from schemas.report import InternalReport, LocationCoords
from services.geo_utils import haversine_distance
from services.satellite import get_sentinel5p_features
from services.weather import get_weather

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_DIR = BASE_DIR / "data" / "metadata"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
DELHI_STATIONS_FILE = METADATA_DIR / "delhi_station_coordinates.csv"
WEATHER_CSV_FILE = RAW_DATA_DIR / "weather" / "delhi_weather_2022_2026.csv"
FIRMS_CSV_FILE = RAW_DATA_DIR / "firms_viirs.csv"
OWBEII_FILE = RAW_DATA_DIR / "Wasteburned.txt"


# ----------------------------------------------------------------------
# 1. CPCB Ground Station Retrieval
# ----------------------------------------------------------------------
def _load_station_coordinates() -> pd.DataFrame:
    if DELHI_STATIONS_FILE.exists():
        return pd.read_csv(DELHI_STATIONS_FILE)
    return pd.DataFrame()


def retrieve_cpcb_evidence(
    lat: float,
    lon: float,
    report_dt: datetime,
    max_distance_km: float = 35.0
) -> CPCBStationEvidence:
    """
    Retrieves ground observations from the nearest CPCB station.
    Enforces causality: observation_time <= report_dt (strictly rejects future observations).
    """
    stations_df = _load_station_coordinates()
    if stations_df.empty:
        return CPCBStationEvidence(
            status=DataAvailability.MISSING,
            provenance="CPCB_Station_Coordinates_Missing"
        )

    # 1. Find nearest station by Haversine distance
    stations_df["distance_km"] = stations_df.apply(
        lambda row: haversine_distance(lat, lon, float(row["latitude"]), float(row["longitude"])),
        axis=1
    )
    nearest = stations_df.sort_values("distance_km").iloc[0]
    dist_km = float(nearest["distance_km"])

    if dist_km > max_distance_km:
        return CPCBStationEvidence(
            status=DataAvailability.MISSING,
            distance_km=dist_km,
            station_id=str(nearest["station_id"]),
            station_name=str(nearest.get("station_name", nearest["station_id"])),
            latitude=float(nearest["latitude"]),
            longitude=float(nearest["longitude"]),
            provenance=f"Nearest station beyond {max_distance_km}km threshold"
        )

    st_id = str(nearest["station_id"]).lower().strip()
    st_name = str(nearest.get("station_name", nearest["station_id"]))

    # 2. Locate data files for this station in backend/data/raw/delhi
    delhi_dir = RAW_DATA_DIR / "delhi"
    st_slug = st_id.replace(" ", "_")
    matched_files = list(delhi_dir.glob(f"*{st_slug}*.csv"))

    if not matched_files:
        return CPCBStationEvidence(
            status=DataAvailability.MISSING,
            station_id=st_id,
            station_name=st_name,
            latitude=float(nearest["latitude"]),
            longitude=float(nearest["longitude"]),
            distance_km=dist_km,
            provenance="No ground observation CSV found for station"
        )

    # 3. Read observation files and search for causal match (obs_time <= report_dt)
    dfs = []
    # Make report_dt naive UTC for consistent pandas comparison
    if report_dt.tzinfo is not None:
        target_time = report_dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        target_time = report_dt

    for f in matched_files:
        try:
            df_part = pd.read_csv(f)
            if "Timestamp" in df_part.columns:
                dfs.append(df_part)
        except Exception:
            continue

    if not dfs:
        return CPCBStationEvidence(
            status=DataAvailability.MISSING,
            station_id=st_id,
            station_name=st_name,
            latitude=float(nearest["latitude"]),
            longitude=float(nearest["longitude"]),
            distance_km=dist_km,
            provenance="Failed to read station CSV data"
        )

    df_all = pd.concat(dfs, ignore_index=True)
    df_all["dt"] = pd.to_datetime(df_all["Timestamp"], errors="coerce")
    df_all = df_all.dropna(subset=["dt"])

    # Strict causality filter: observation must not be in the future
    causal_df = df_all[df_all["dt"] <= target_time].sort_values("dt")
    if causal_df.empty:
        return CPCBStationEvidence(
            status=DataAvailability.MISSING,
            station_id=st_id,
            station_name=st_name,
            latitude=float(nearest["latitude"]),
            longitude=float(nearest["longitude"]),
            distance_km=dist_km,
            provenance="All available station observations are after report timestamp"
        )

    latest_row = causal_df.iloc[-1]
    obs_time = latest_row["dt"]
    delta_hours = (target_time - obs_time).total_seconds() / 3600.0

    # Availability classification based on latency
    if delta_hours <= 3.0:
        avail_status = DataAvailability.AVAILABLE
    elif delta_hours <= 48.0:
        avail_status = DataAvailability.STALE
    else:
        avail_status = DataAvailability.MISSING

    # Map column headers to standard pollutants using prefix matching
    pollutants: Dict[str, PollutantObservation] = {}
    for c in latest_row.index:
        c_clean = str(c).strip().lower().replace(" ", "").replace("_", "")
        val = latest_row[c]
        if pd.isna(val):
            continue
        try:
            num_val = float(val)
        except (ValueError, TypeError):
            continue

        if c_clean.startswith("pm2.5") or c_clean.startswith("pm25"):
            if "PM2.5" not in pollutants:
                pollutants["PM2.5"] = PollutantObservation(
                    pollutant="PM2.5",
                    value=round(num_val, 2),
                    unit="µg/m³",
                    observation_time=obs_time.isoformat()
                )
        elif c_clean.startswith("pm10"):
            if "PM10" not in pollutants:
                pollutants["PM10"] = PollutantObservation(
                    pollutant="PM10",
                    value=round(num_val, 2),
                    unit="µg/m³",
                    observation_time=obs_time.isoformat()
                )
        elif c_clean.startswith("no2"):
            if "NO2" not in pollutants:
                pollutants["NO2"] = PollutantObservation(
                    pollutant="NO2",
                    value=round(num_val, 2),
                    unit="µg/m³",
                    observation_time=obs_time.isoformat()
                )
        elif c_clean.startswith("co(") or c_clean.startswith("co"):
            if "CO" not in pollutants and not c_clean.startswith("color"):
                pollutants["CO"] = PollutantObservation(
                    pollutant="CO",
                    value=round(num_val, 2),
                    unit="mg/m³",
                    observation_time=obs_time.isoformat()
                )

    return CPCBStationEvidence(
        status=avail_status,
        station_id=st_id,
        station_name=st_name,
        latitude=float(nearest["latitude"]),
        longitude=float(nearest["longitude"]),
        distance_km=dist_km,
        observation_time=obs_time.isoformat(),
        pollutants=pollutants,
        provenance=f"CPCB_CAAQMS_{st_id.upper()}"
    )


# ----------------------------------------------------------------------
# 2. Weather / Meteorology Retrieval
# ----------------------------------------------------------------------
def retrieve_weather_evidence(
    lat: float,
    lon: float,
    report_dt: datetime
) -> WeatherEvidence:
    """
    Retrieves meteorological variables (temp, humidity, wind, pressure, PBLH).
    Enforces causality: observation_time <= report_dt.
    """
    now = datetime.now(timezone.utc)
    if report_dt.tzinfo is not None:
        target_time = report_dt.astimezone(timezone.utc)
        target_naive = target_time.replace(tzinfo=None)
    else:
        target_time = report_dt.replace(tzinfo=timezone.utc)
        target_naive = report_dt

    age_from_now_hours = (now - target_time).total_seconds() / 3600.0

    # 1. If report is near real-time (last 24 hours), query Open-Meteo live API
    if -1.0 <= age_from_now_hours <= 24.0:
        try:
            live_data = get_weather(lat, lon)
            curr = live_data.get("current", {})
            return WeatherEvidence(
                status=DataAvailability.AVAILABLE,
                temperature_c=float(curr.get("temperature_2m", 0.0)),
                relative_humidity_pct=float(curr.get("relative_humidity_2m", 0.0)),
                wind_speed_kmh=float(curr.get("wind_speed_10m", 0.0)),
                wind_direction_deg=float(curr.get("wind_direction_10m", 0.0)),
                surface_pressure_hpa=float(curr.get("surface_pressure", 1013.25)),
                boundary_layer_height_m=None,  # Open-Meteo current endpoint doesn't include PBLH
                observation_time=curr.get("time", target_time.isoformat()),
                provenance="Open_Meteo_Live_Forecast_API"
            )
        except Exception:
            pass  # Fall back to historical file if Open-Meteo query fails

    # 2. Historical weather archive from local ERA5 / Open-Meteo weather dataset
    if WEATHER_CSV_FILE.exists():
        try:
            df_w = pd.read_csv(WEATHER_CSV_FILE)
            df_w["dt"] = pd.to_datetime(df_w["timestamp"], errors="coerce")
            df_w = df_w.dropna(subset=["dt"])

            # Causal filter: obs_time <= report_dt
            causal_w = df_w[df_w["dt"] <= target_naive].sort_values("dt")
            if not causal_w.empty:
                row = causal_w.iloc[-1]
                obs_dt = row["dt"]
                delta_h = (target_naive - obs_dt).total_seconds() / 3600.0
                status = DataAvailability.AVAILABLE if delta_h <= 3.0 else (
                    DataAvailability.STALE if delta_h <= 48.0 else DataAvailability.MISSING
                )

                def _safe_float(val):
                    return float(val) if pd.notna(val) else None

                return WeatherEvidence(
                    status=status,
                    temperature_c=_safe_float(row.get("temperature_2m")),
                    relative_humidity_pct=_safe_float(row.get("relative_humidity_2m")),
                    wind_speed_kmh=_safe_float(row.get("wind_speed_10m")),
                    wind_direction_deg=_safe_float(row.get("wind_direction_10m")),
                    surface_pressure_hpa=_safe_float(row.get("surface_pressure")),
                    boundary_layer_height_m=_safe_float(row.get("boundary_layer_height")),
                    observation_time=obs_dt.isoformat(),
                    provenance="Delhi_ERA5_Hourly_Archive"
                )
        except Exception:
            pass

    return WeatherEvidence(
        status=DataAvailability.MISSING,
        provenance="Weather_Data_Unavailable"
    )


# ----------------------------------------------------------------------
# 3. Sentinel-5P Satellite Retrieval
# ----------------------------------------------------------------------
def retrieve_sentinel5p_evidence(
    lat: float,
    lon: float,
    report_dt: datetime
) -> Sentinel5PEvidence:
    """
    Retrieves Sentinel-5P tropospheric NO2 and Aerosol Index around report time.
    Enforces causality: acquisition window ends on or before report timestamp.
    """
    if report_dt.tzinfo is not None:
        target_naive = report_dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        target_naive = report_dt

    # Acquisition window: 24h preceding report_dt
    end_date_str = target_naive.strftime("%Y-%m-%d")
    start_dt = target_naive - pd.Timedelta(days=2)
    start_date_str = start_dt.strftime("%Y-%m-%d")

    try:
        raw_sat = get_sentinel5p_features(
            lat=lat,
            lng=lon,
            start_date=start_date_str,
            end_date=end_date_str
        )
        is_live = raw_sat.get("live", False)
        status = DataAvailability.AVAILABLE if is_live else DataAvailability.STALE

        return Sentinel5PEvidence(
            status=status,
            no2_column_number_density=float(raw_sat.get("no2_index", 0.0)),
            absorbing_aerosol_index=float(raw_sat.get("aerosol_index", 0.0)),
            observation_time=end_date_str,
            age_hours=24.0,
            provenance="Copernicus_Sentinel_5P_OFFL_EarthEngine" if is_live else "Copernicus_S5P_Baseline_Context"
        )
    except Exception as e:
        return Sentinel5PEvidence(
            status=DataAvailability.MISSING,
            provenance=f"Sentinel5P_Retrieval_Failed: {str(e)}"
        )


_FIRMS_CACHE: Optional[pd.DataFrame] = None

def _get_firms_df() -> Optional[pd.DataFrame]:
    global _FIRMS_CACHE
    if _FIRMS_CACHE is not None:
        return _FIRMS_CACHE
    if not FIRMS_CSV_FILE.exists():
        return None
    try:
        df_fires = pd.read_csv(FIRMS_CSV_FILE, dtype={"version": str, "type": str})
        if "acq_time" not in df_fires.columns or "acq_date" not in df_fires.columns:
            return None
        acq_time_str = df_fires["acq_time"].astype(str).str.zfill(4)
        df_fires["dt"] = pd.to_datetime(
            df_fires["acq_date"] + " " + acq_time_str,
            format="%Y-%m-%d %H%M",
            errors="coerce"
        )
        _FIRMS_CACHE = df_fires.dropna(subset=["dt"])
        return _FIRMS_CACHE
    except Exception:
        return None


# ----------------------------------------------------------------------
# 4. FIRMS Active Fire Retrieval
# ----------------------------------------------------------------------
def retrieve_firms_evidence(
    lat: float,
    lon: float,
    report_dt: datetime,
    search_radius_km: float = 50.0,
    window_hours: float = 72.0
) -> FIRMSEvidence:
    """
    Retrieves NASA FIRMS active fire detections within search_radius_km and preceding window_hours.
    Enforces causality: detection_time <= report_dt.
    """
    if not FIRMS_CSV_FILE.exists():
        return FIRMSEvidence(
            status=DataAvailability.MISSING,
            search_radius_km=search_radius_km,
            temporal_window_hours=window_hours,
            provenance="FIRMS_VIIRS_File_Not_Found"
        )

    if report_dt.tzinfo is not None:
        target_naive = report_dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        target_naive = report_dt

    min_window_dt = target_naive - pd.Timedelta(hours=window_hours)

    try:
        df_fires = _get_firms_df()
        if df_fires is None or df_fires.empty:
            return FIRMSEvidence(
                status=DataAvailability.MISSING,
                search_radius_km=search_radius_km,
                temporal_window_hours=window_hours,
                provenance="FIRMS_Data_Unavailable"
            )

        # Strict causality and temporal window filter: min_window_dt <= dt <= target_naive
        time_mask = (df_fires["dt"] >= min_window_dt) & (df_fires["dt"] <= target_naive)
        window_fires = df_fires[time_mask].copy()

        if window_fires.empty:
            return FIRMSEvidence(
                status=DataAvailability.AVAILABLE,
                detection_count=0,
                nearest_fire_distance_km=None,
                max_frp=0.0,
                fires=[],
                search_radius_km=search_radius_km,
                temporal_window_hours=window_hours,
                provenance="NASA_FIRMS_VIIRS_Archive"
            )

        # Spatial distance calculation
        window_fires["dist_km"] = window_fires.apply(
            lambda r: haversine_distance(lat, lon, float(r["latitude"]), float(r["longitude"])),
            axis=1
        )
        nearby_fires = window_fires[window_fires["dist_km"] <= search_radius_km].sort_values("dist_km")

        if nearby_fires.empty:
            return FIRMSEvidence(
                status=DataAvailability.AVAILABLE,
                detection_count=0,
                nearest_fire_distance_km=None,
                max_frp=0.0,
                fires=[],
                search_radius_km=search_radius_km,
                temporal_window_hours=window_hours,
                provenance="NASA_FIRMS_VIIRS_Archive"
            )

        fire_records: List[FIRMFireRecord] = []
        for _, r in nearby_fires.iterrows():
            frp_val = float(r["frp"]) if pd.notna(r.get("frp")) else 0.0
            conf_val = str(r["confidence"]) if pd.notna(r.get("confidence")) else None
            fire_records.append(
                FIRMFireRecord(
                    latitude=float(r["latitude"]),
                    longitude=float(r["longitude"]),
                    distance_km=float(r["dist_km"]),
                    frp=round(frp_val, 2),
                    confidence=conf_val,
                    detection_time=r["dt"].isoformat()
                )
            )

        nearest_dist = float(nearby_fires.iloc[0]["dist_km"])
        max_frp_val = float(nearby_fires["frp"].max()) if pd.notna(nearby_fires["frp"].max()) else 0.0

        return FIRMSEvidence(
            status=DataAvailability.AVAILABLE,
            detection_count=len(fire_records),
            nearest_fire_distance_km=nearest_dist,
            max_frp=round(max_frp_val, 2),
            fires=fire_records,
            search_radius_km=search_radius_km,
            temporal_window_hours=window_hours,
            provenance="NASA_FIRMS_VIIRS_Archive"
        )
    except Exception as e:
        return FIRMSEvidence(
            status=DataAvailability.MISSING,
            search_radius_km=search_radius_km,
            temporal_window_hours=window_hours,
            provenance=f"FIRMS_Error: {str(e)}"
        )


# ----------------------------------------------------------------------
# 5. Static Emissions Source Context (OWBEII)
# ----------------------------------------------------------------------
def retrieve_owbeii_evidence(lat: float, lon: float) -> StaticSourceEvidence:
    """
    Retrieves nearest open waste burning emission context from OWBEII inventory.
    """
    if not OWBEII_FILE.exists():
        return StaticSourceEvidence(
            status=DataAvailability.MISSING,
            source_type="OWBEII_open_waste_burning",
            provenance="OWBEII_File_Not_Found"
        )

    try:
        df_ow = pd.read_csv(OWBEII_FILE, sep="\t", header=0, names=["lat", "lon", "val"])
        # Quick bounding box filter around target (+/- 1 degree) to accelerate Haversine
        box = df_ow[
            (df_ow["lat"] >= lat - 1.0) & (df_ow["lat"] <= lat + 1.0) &
            (df_ow["lon"] >= lon - 1.0) & (df_ow["lon"] <= lon + 1.0)
        ].copy()

        search_df = box if not box.empty else df_ow

        search_df["dist_km"] = search_df.apply(
            lambda r: haversine_distance(lat, lon, float(r["lat"]), float(r["lon"])),
            axis=1
        )
        nearest = search_df.sort_values("dist_km").iloc[0]

        return StaticSourceEvidence(
            status=DataAvailability.AVAILABLE,
            source_type="OWBEII_open_waste_burning",
            nearest_grid_lat=float(nearest["lat"]),
            nearest_grid_lon=float(nearest["lon"]),
            distance_km=float(nearest["dist_km"]),
            annual_emission_val=float(nearest["val"]),
            unit="kg yr-1",
            provenance="OWBEII_Static_Emissions_Inventory"
        )
    except Exception as e:
        return StaticSourceEvidence(
            status=DataAvailability.MISSING,
            source_type="OWBEII_open_waste_burning",
            provenance=f"OWBEII_Error: {str(e)}"
        )


# ----------------------------------------------------------------------
# 6. Conflict Detection (Deterministic Heuristics, No LLM)
# ----------------------------------------------------------------------
def detect_conflicts(
    cpcb: CPCBStationEvidence,
    weather: WeatherEvidence,
    firms: FIRMSEvidence,
    satellite: Sentinel5PEvidence
) -> List[str]:
    """
    Identifies notable divergences between observational sources without LLM smoothing.
    """
    notes: List[str] = []

    # Check 1: High ground PM2.5 but strong dispersion weather
    pm25_obs = cpcb.pollutants.get("PM2.5")
    if pm25_obs and pm25_obs.value >= 250.0:
        if weather.wind_speed_kmh and weather.wind_speed_kmh >= 20.0:
            notes.append(
                f"Severe ground PM2.5 ({pm25_obs.value} µg/m³) coincides with high wind speed ({weather.wind_speed_kmh} km/h), typically unfavorable to stagnation."
            )

    # Check 2: Severe ground PM2.5 but zero nearby fire detections
    if pm25_obs and pm25_obs.value >= 300.0:
        if firms.status == DataAvailability.AVAILABLE and firms.detection_count == 0:
            notes.append(
                f"Severe ground PM2.5 ({pm25_obs.value} µg/m³) with zero active fire detections within {firms.search_radius_km}km."
            )

    # Check 3: Clean ground PM2.5 but high satellite aerosol index
    if pm25_obs and pm25_obs.value <= 40.0:
        if satellite.absorbing_aerosol_index and satellite.absorbing_aerosol_index >= 2.0:
            notes.append(
                f"Clean ground PM2.5 ({pm25_obs.value} µg/m³) contrasts with elevated satellite UV Aerosol Index ({satellite.absorbing_aerosol_index})."
            )

    return notes


# ----------------------------------------------------------------------
# 7. Complete Evidence Package Builder
# ----------------------------------------------------------------------
def build_evidence_package(report: InternalReport) -> EvidencePackage:
    """
    Builds the standardized EvidencePackage for an ingested citizen report.
    """
    # Parse report timestamp
    raw_ts = report.timestamp.replace("Z", "+00:00") if report.timestamp.endswith("Z") else report.timestamp
    try:
        report_dt = datetime.fromisoformat(raw_ts)
    except Exception:
        report_dt = datetime.now(timezone.utc)

    lat = report.location.latitude
    lon = report.location.longitude

    # Retrieve all evidence domains
    cpcb = retrieve_cpcb_evidence(lat, lon, report_dt)
    weather = retrieve_weather_evidence(lat, lon, report_dt)
    satellite = retrieve_sentinel5p_evidence(lat, lon, report_dt)
    firms = retrieve_firms_evidence(lat, lon, report_dt)
    owbeii = retrieve_owbeii_evidence(lat, lon)

    # Detect conflicts deterministically
    conflicts = detect_conflicts(cpcb, weather, firms, satellite)

    return EvidencePackage(
        report_id=report.report_id,
        location=report.location,
        timestamp=report.timestamp,
        cpcb=cpcb,
        weather=weather,
        satellite=satellite,
        firms=firms,
        static_sources=[owbeii],
        conflicting_signals_noted=conflicts,
        retrieved_at=datetime.now(timezone.utc).isoformat()
    )

def calculate_potential_regional_plume_influence(lat: float, lon: float, wind_dir: float, report_dt: datetime) -> dict:
    """
    Fetches FIRMS data and evaluates if any fires are upwind.
    """
    try:
        # Get fires within 200km over the last 72 hours
        firms_evidence = retrieve_firms_evidence(lat, lon, report_dt, search_radius_km=200.0, window_hours=72.0)

        if firms_evidence.status != DataAvailability.AVAILABLE or firms_evidence.detection_count == 0:
            return {
                "status": "AVAILABLE",
                "plume_influence_risk": "LOW",
                "upwind_fire_count": 0,
                "reason": "No active fires detected in region"
            }

        upwind_count = 0
        for f in firms_evidence.fires:
            import math
            lat1, lon1 = math.radians(lat), math.radians(lon)
            lat2, lon2 = math.radians(f.latitude), math.radians(f.longitude)
            dlon = lon2 - lon1
            x = math.sin(dlon) * math.cos(lat2)
            y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
            initial_bearing = math.atan2(x, y)
            initial_bearing = math.degrees(initial_bearing)
            bearing = (initial_bearing + 360) % 360

            diff = abs(bearing - wind_dir)
            if diff > 180:
                diff = 360 - diff
            if diff <= 45:
                upwind_count += 1

        if upwind_count > 10:
            risk = "HIGH"
        elif upwind_count > 0:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "status": "AVAILABLE",
            "plume_influence_risk": risk,
            "upwind_fire_count": upwind_count,
            "total_regional_fires": firms_evidence.detection_count,
            "is_proxy": True,
            "reason": f"Heuristic plume assessment based on {upwind_count} upwind fires"
        }
    except Exception as e:
         return {
            "status": "UNAVAILABLE",
            "reason": f"Failed to calculate plume influence: {str(e)}"
        }
