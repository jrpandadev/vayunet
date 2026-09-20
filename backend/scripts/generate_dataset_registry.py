import os
import json
import sqlite3
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"

registry = []

def record(dataset_name, source, raw_path, processed_path, role, temporal_res, spatial_res,
           date_start, date_end, variables, units, crs, forecast_avail, hist_avail,
           latency_rule, license_name, provenance, quality_status, allowed_prod, allowed_ablation, notes):
    registry.append({
        "dataset": dataset_name,
        "source": source,
        "raw_path": str(raw_path) if raw_path else "UNKNOWN",
        "processed_path": str(processed_path) if processed_path else "UNKNOWN",
        "dataset_role": role,
        "temporal_resolution": temporal_res,
        "spatial_resolution": spatial_res,
        "date_start": str(date_start) if date_start else "UNKNOWN",
        "date_end": str(date_end) if date_end else "UNKNOWN",
        "variables": variables,
        "units": units,
        "coordinate_system": crs,
        "forecast_available": forecast_avail,
        "historical_available": hist_avail,
        "latency_rule": latency_rule,
        "license": license_name,
        "provenance": provenance,
        "quality_status": quality_status,
        "allowed_for_production": allowed_prod,
        "allowed_for_ablation": allowed_ablation,
        "notes": notes
    })

def main():
    print("Inspecting all datasets...")

    # --- 1. CPCB Delhi ---
    cpcb_delhi_dir = data_dir / "raw" / "delhi"
    delhi_files = list(cpcb_delhi_dir.glob("*.csv"))
    delhi_size = sum(f.stat().st_size for f in delhi_files) / (1024**2)
    record(
        dataset_name="CPCB CAAQMS Delhi (10 Core Stations)",
        source="Central Pollution Control Board (CPCB) / DPCC",
        raw_path="backend/data/raw/delhi/",
        processed_path="backend/data/processed/delhi_forecasting.csv",
        role="B. HISTORICAL TRAINING INPUT, F. VALIDATION/REFERENCE",
        temporal_res="1-hour (hourly)",
        spatial_res="Point monitoring stations (10 stations)",
        date_start="2022-01-01 00:00:00",
        date_end="2026-08-31 23:00:00",
        variables="PM2.5, PM10, NO, NO2, NOx, NH3, SO2, CO, Ozone, AT, RH, WS, WD, SR, BP, BTX",
        units="ug/m3 (gases/PM), ppb (NOx), mg/m3 (CO), deg C (AT), % (RH), m/s (WS), deg (WD), mmHg (BP), W/m2 (SR)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Observational ground truth: only historical observations prior to forecast timestamp are accessible.",
        license_name="Open Government Data (OGD) India / CPCB Portal Terms",
        provenance="Acquired from CPCB CAAQMS portal across 10 Delhi DPCC/CPCB monitoring stations.",
        quality_status="VERIFIED_CANONICAL",
        allowed_prod=True,
        allowed_ablation=True,
        notes=f"50 CSV files ({delhi_size:.2f} MB), 10 stations across 2022-2026. Forms the target PM2.5 and baseline pollutant lags."
    )

    # --- 2. CPCB Delhi-NCR ---
    ncr_raw_dir = data_dir / "raw" / "delhi_ncr"
    ncr_proc_parquet = data_dir / "processed" / "delhi_ncr" / "ncr_caaqms_hourly.parquet"
    ncr_files = list(ncr_raw_dir.glob("*.csv"))
    ncr_size = sum(f.stat().st_size for f in ncr_files) / (1024**2)
    record(
        dataset_name="CPCB CAAQMS Delhi-NCR (Regional Grid)",
        source="Central Pollution Control Board (CPCB) / State PCBs (DPCC, HSPCB, UPPCB)",
        raw_path="backend/data/raw/delhi_ncr/",
        processed_path="backend/data/processed/delhi_ncr/ncr_caaqms_hourly.parquet",
        role="B. HISTORICAL TRAINING INPUT, C. POLLUTION/SOURCE INVESTIGATION, E. SPATIAL CONTEXT",
        temporal_res="1-hour (hourly)",
        spatial_res="Regional monitoring network (69 stations across Delhi, Haryana, UP, Rajasthan NCR)",
        date_start="2022-01-01 00:00:00",
        date_end="2026-08-31 23:00:00",
        variables="PM2.5, PM10, NO, NO2, NOx, NH3, SO2, CO, Ozone, meteorology",
        units="Standard CPCB units (ug/m3, mg/m3, ppm/ppb, deg C, %)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Observational ground truth: regional station measurements only available up to T_0. Cannot be used as future inputs.",
        license_name="Open Government Data (OGD) India",
        provenance="Multi-state portal extraction, cleaned and merged into ncr_caaqms_hourly.parquet (135 MB).",
        quality_status="AUDITED_PROCESSED",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"297 CSV files in raw ({ncr_size:.2f} MB). Cleaned parquet contains 69 viable regional stations. High potential for spatial advection ablation."
    )

    # --- 3. Open-Meteo Weather ---
    record(
        dataset_name="Open-Meteo Historical Reanalysis & Weather",
        source="Open-Meteo API (ECMWF ERA5 / ERA5-Land seamless archive)",
        raw_path="backend/data/raw/weather/delhi_weather_2022_2026.csv",
        processed_path="backend/data/processed/delhi_forecasting_weather.csv",
        role="B. HISTORICAL TRAINING INPUT, F. VALIDATION/REFERENCE",
        temporal_res="1-hour (hourly)",
        spatial_res="0.1 x 0.1 degree (~10 km grid)",
        date_start="2022-01-01 00:00:00",
        date_end="2026-08-31 23:00:00",
        variables="temperature_2m, relative_humidity_2m, dew_point_2m, precipitation, surface_pressure, cloud_cover, wind_speed_10m, wind_direction_10m, wind_gusts_10m, shortwave_radiation, boundary_layer_height",
        units="deg C, %, deg C, mm, hPa, %, m/s, deg, m/s, W/m2, m",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Historical archive: observations only available at or before T_0. Future weather at T+H MUST come from NWP forecasts.",
        license_name="Open Data Commons Attribution License (ODC-By) / Copernicus Terms",
        provenance="Acquired from Open-Meteo historical weather API for central Delhi coordinates.",
        quality_status="VERIFIED_CANONICAL",
        allowed_prod=True,
        allowed_ablation=True,
        notes="40,896 hourly timestamps. Serves as historical meteorology baseline in production S0-S6."
    )

    # --- 4. ECMWF IFS NWP Forecasts ---
    record(
        dataset_name="ECMWF IFS Operational NWP Forecasts",
        source="European Centre for Medium-Range Weather Forecasts (ECMWF) IFS",
        raw_path="backend/data/raw/nwp/",
        processed_path="backend/data/processed/fusion/delhi_forecasting_s5_nwp.csv",
        role="A. FORECAST INPUT, B. HISTORICAL TRAINING INPUT",
        temporal_res="00 UTC & 12 UTC cycles, hourly to 6-hourly lead times",
        spatial_res="0.25 x 0.25 degree (~25 km resolution)",
        date_start="2024-03-14 00:00:00",
        date_end="2026-08-31 18:00:00",
        variables="nwp_temperature_2m, nwp_relative_humidity_2m, nwp_precipitation, nwp_surface_pressure, nwp_wind_speed_10m, nwp_wind_direction_10m, nwp_boundary_layer_height (at 6h, 24h, 72h horizons)",
        units="deg C, %, mm, hPa, m/s, deg, m",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=True,
        hist_avail=True,
        latency_rule="Causal NWP rule: only the forecast run initialized and disseminated BEFORE prediction timestamp T_0 is utilized.",
        license_name="ECMWF Open Data License",
        provenance="6,608 raw files (3,304 CSV + 3,304 JSON) ingested and aligned via matched-row protocol into S5 feature set.",
        quality_status="VERIFIED_CANONICAL",
        allowed_prod=True,
        allowed_ablation=True,
        notes="Validated in S5 production models. Coverage begins March 2024; required matched-row masking."
    )

    # --- 5. Sentinel-5P TROPOMI NO2 ---
    record(
        dataset_name="Sentinel-5P TROPOMI Tropospheric NO2",
        source="ESA Copernicus Open Access Hub / Google Earth Engine",
        raw_path="backend/data/raw/satellite/delhi_s5p_no2.csv",
        processed_path="backend/data/processed/fusion/delhi_forecasting_satellite.csv",
        role="A. FORECAST INPUT (with latency), B. HISTORICAL TRAINING INPUT, C. POLLUTION/SOURCE INVESTIGATION",
        temporal_res="Daily overpass (~13:30 local solar time, ascending orbit)",
        spatial_res="3.5 x 5.5 km (post-2019 upgrade)",
        date_start="2022-01-01 07:54:14",
        date_end="2026-08-26 07:37:42",
        variables="tropospheric_no2, satellite_no2_latest, satellite_no2_age_hours",
        units="mol/m2 (column density), hours (age)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Strict acquisition latency: Satellite observation valid only after overpass ingestion (~3-6 hour operational latency). Carried forward with age tracking.",
        license_name="Copernicus Open Access / CC-BY-SA 3.0 IGO",
        provenance="Extracted over 10 Delhi station coordinates, merged into S3/S4 feature table.",
        quality_status="VERIFIED_CANONICAL",
        allowed_prod=True,
        allowed_ablation=True,
        notes="13,139 overpass soundings. In production model with satellite_no2_latest and satellite_no2_age_hours."
    )

    # --- 6. MODIS MCD19A2 V061 MAIAC AOD ---
    maiac_dir = data_dir / "raw" / "satellite" / "modis_maiac"
    maiac_files = list(maiac_dir.glob("*.hdf"))
    maiac_size = sum(f.stat().st_size for f in maiac_files) / (1024**2)
    record(
        dataset_name="MODIS Terra/Aqua MCD19A2 V061 MAIAC AOD",
        source="NASA Earthdata / LP DAAC (MODIS Atmosphere Team)",
        raw_path="backend/data/raw/satellite/modis_maiac/",
        processed_path="backend/data/processed/satellite/delhi_mcd19a2_maiac_station_aod.parquet",
        role="B. HISTORICAL TRAINING INPUT, C. POLLUTION/SOURCE INVESTIGATION, G. RESEARCH/ABLATION ONLY",
        temporal_res="Daily daytime overpasses (Terra ~10:30, Aqua ~13:30 local solar time)",
        spatial_res="1 km grid (Sinusoidal tile h24v06)",
        date_start="2022-01-01",
        date_end="2023-12-31",
        variables="Optical_Depth_047, Optical_Depth_055, AOD_QA, Column_Water_Vapor, Cosine_of_Solar_Zenith_Angle",
        units="Dimensionless (AOD at 0.47um and 0.55um), cm (CWV)",
        crs="Sinusoidal projection (tile h24v06)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Historical satellite observation: available with 12-24h latency. Cannot be used as future observation at forecast time.",
        license_name="NASA Open Data Policy (Public Domain)",
        provenance="1,699 HDF granules downloaded from NASA CMR / LP DAAC covering tile h24v06.",
        quality_status="ACQUIRED_RAW_AUDITED",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"1,699 HDF4 files ({maiac_size:.2f} MB / 17.46 GB). High resolution 1km AOD. Extracted station AOD table generated."
    )

    # --- 7. NASA FIRMS VIIRS/MODIS Fire Data ---
    firms_file = data_dir / "raw" / "firms_viirs.csv"
    firms_size = firms_file.stat().st_size / (1024**2) if firms_file.exists() else 0
    record(
        dataset_name="NASA FIRMS VIIRS Active Fire Detections (Suomi NPP, NOAA-20, NOAA-21)",
        source="NASA LANCE FIRMS (Fire Information for Resource Management System)",
        raw_path="backend/data/raw/firms_viirs.csv",
        processed_path="backend/data/processed/fusion/delhi_forecasting_s7_firms.csv",
        role="A. FORECAST INPUT (with latency), B. HISTORICAL TRAINING INPUT, C. POLLUTION/SOURCE INVESTIGATION",
        temporal_res="Satellite overpasses (twice daily per sensor: ~01:30 & ~13:30 local)",
        spatial_res="375 m pixel resolution (I-Band 375m)",
        date_start="2022-01-01",
        date_end="2026-08-31",
        variables="latitude, longitude, bright_ti4, bright_ti5, frp (fire radiative power), confidence, daynight, acq_date, acq_time",
        units="Kelvin (brightness temp), MW (FRP), % (confidence)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Operational detection latency: NRT fires available within 3 hours; archive fires within 1-3 days. Feature builder uses spatial distance decay and temporal age decay.",
        license_name="NASA Open Data Policy / LANCE FIRMS Terms",
        provenance="Acquired from NASA FIRMS API covering Punjab, Haryana, and NCR (1,329,628 fire detections).",
        quality_status="VERIFIED_AUDITED",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"1,329,628 fire detections ({firms_size:.2f} MB). Processed in S7 ablation; proved critical during Oct-Nov post-monsoon crop residue burning episodes."
    )

    # --- 8. OpenStreetMap Northern Zone ---
    osm_north = data_dir / "raw" / "northern-zone-260910-free.gpkg" / "northern-zone.gpkg"
    osm_north_size = osm_north.stat().st_size / (1024**2) if osm_north.exists() else 0
    record(
        dataset_name="OpenStreetMap Northern Zone (Roads, Landuse, Buildings)",
        source="OpenStreetMap contributors / Geofabrik GmbH",
        raw_path="backend/data/raw/northern-zone-260910-free.gpkg/northern-zone.gpkg",
        processed_path="UNKNOWN (Static feature extractor available)",
        role="E. SPATIAL CONTEXT, C. POLLUTION/SOURCE INVESTIGATION",
        temporal_res="Static snapshot (2026-09-10)",
        spatial_res="Vector geometries (polygons, lines, points: 1-10m fidelity)",
        date_start="2026-09-10",
        date_end="2026-09-10",
        variables="roads (motorway, trunk, primary, secondary), landuse (industrial, commercial, residential), buildings, railways, natural, water",
        units="Categorical / vector lengths and buffer areas (meters / sq meters)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Static spatial context: constant over forecasting horizons. Time-invariant station embedding.",
        license_name="Open Database License (ODbL) 1.0",
        provenance="Downloaded from Geofabrik regional OSM export (Northern Zone India).",
        quality_status="VERIFIED_RAW_GEOPACKAGE",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"GeoPackage ({osm_north_size:.2f} MB) with 10 feature layers (11.2M points, 3.4M roads, 4.4M buildings). Ideal for spatial buffer features."
    )

    # --- 9. OpenStreetMap Central Zone ---
    osm_central = data_dir / "raw" / "central-zone-260910-free.gpkg" / "central-zone.gpkg"
    osm_central_size = osm_central.stat().st_size / (1024**2) if osm_central.exists() else 0
    record(
        dataset_name="OpenStreetMap Central Zone (Roads, Landuse, Buildings)",
        source="OpenStreetMap contributors / Geofabrik GmbH",
        raw_path="backend/data/raw/central-zone-260910-free.gpkg/central-zone.gpkg",
        processed_path="UNKNOWN (Static feature extractor available)",
        role="E. SPATIAL CONTEXT, C. POLLUTION/SOURCE INVESTIGATION",
        temporal_res="Static snapshot (2026-09-10)",
        spatial_res="Vector geometries (polygons, lines, points)",
        date_start="2026-09-10",
        date_end="2026-09-10",
        variables="roads, landuse, buildings, railways, waterways, points of interest",
        units="Vector geometries (meters / sq meters)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Static spatial context: constant over forecasting horizons.",
        license_name="Open Database License (ODbL) 1.0",
        provenance="Downloaded from Geofabrik regional OSM export (Central Zone India).",
        quality_status="VERIFIED_RAW_GEOPACKAGE",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"GeoPackage ({osm_central_size:.2f} MB) with 10 feature layers (14.6M points, 4.1M roads, 8.4M buildings). Covers southern NCR periphery."
    )

    # --- 10. ERA5 Pressure-Level Pilot ---
    era5_pilot = data_dir / "raw" / "weather" / "era5_pressure_levels" / "era5_delhi_pilot.csv"
    era5_pilot_size = era5_pilot.stat().st_size / (1024**2) if era5_pilot.exists() else 0
    record(
        dataset_name="ERA5 Pressure-Level Reanalysis Pilot (Delhi Point)",
        source="Copernicus Climate Data Store (ECMWF ERA5 Reanalysis)",
        raw_path="backend/data/raw/weather/era5_pressure_levels/era5_delhi_pilot.csv",
        processed_path="backend/data/processed/weather/era5_vertical_features.parquet",
        role="G. RESEARCH/ABLATION ONLY, F. VALIDATION/REFERENCE",
        temporal_res="6-hourly (00, 06, 12, 18 UTC)",
        spatial_res="0.25 x 0.25 degree (point 28.5N, 77.25E at 700, 850, 925 hPa)",
        date_start="2022-01-01 00:00:00",
        date_end="2026-08-31 18:00:00",
        variables="u (eastward wind), v (northward wind), t (temp), r (relative humidity), z (geopotential), w (vertical velocity)",
        units="m/s, m/s, K, %, m2/s2, Pa/s",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="REANALYSIS ONLY: Available with 5-day to 3-month latency. Strictly prohibited as operational future forecast input. Valid ONLY for historical vertical physics ablation.",
        license_name="Copernicus Data Information and Access Service Terms",
        provenance="Retrieved via CDS API for Delhi pilot point across 3 pressure levels.",
        quality_status="VERIFIED_PILOT",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"20,448 records ({era5_pilot_size:.2f} MB). Demonstrates vertical wind shear and atmospheric stability profiles."
    )

    # --- 11. Large GRIB Archive (ERA5 Regional Reanalysis) ---
    grib_file = data_dir / "raw" / "2cfd8dfef8800741a21fc57927ee70e1.grib"
    grib_size = grib_file.stat().st_size / (1024**2) if grib_file.exists() else 0
    record(
        dataset_name="ECMWF CDS GRIB Archive (ERA5 Reanalysis Bulk)",
        source="Copernicus Climate Data Store (CDS)",
        raw_path="backend/data/raw/2cfd8dfef8800741a21fc57927ee70e1.grib",
        processed_path="UNKNOWN (GRIB format - extraction pending)",
        role="G. RESEARCH/ABLATION ONLY",
        temporal_res="Hourly to 6-hourly (reanalysis)",
        spatial_res="0.25 x 0.25 degree",
        date_start="UNKNOWN",
        date_end="UNKNOWN",
        variables="Atmospheric pressure level and surface meteorological fields (GRIB edition 1)",
        units="SI meteorological units",
        crs="GRIB Grid (Spherical/Latitude-Longitude)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Reanalysis product: delayed dissemination. Research/reanalysis ablation only.",
        license_name="Copernicus License",
        provenance="Bulk download from CDS portal (request UID: 2cfd8dfef8800741a21fc57927ee70e1).",
        quality_status="RAW_ARCHIVE_UNPROCESSED",
        allowed_prod=False,
        allowed_ablation=False,
        notes=f"Single large GRIB1 file ({grib_size:.2f} MB / 2.88 GB). Requires ecCodes/cfgrib indexing if needed for regional reanalysis."
    )

    # --- 12. GHSL Population Exposure 2025 (100m) ---
    ghsl_file = data_dir / "processed" / "exposure" / "ghsl_population_2025_100m.csv"
    ghsl_size = ghsl_file.stat().st_size / (1024**2) if ghsl_file.exists() else 0
    record(
        dataset_name="Global Human Settlement Layer (GHSL) Population 2025 (100m)",
        source="European Commission Joint Research Centre (JRC) / Google Earth Engine",
        raw_path="JRC/GHSL/P2023A/GHS_POP (via Earth Engine API)",
        processed_path="backend/data/processed/exposure/ghsl_population_2025_100m.csv",
        role="D. EXPOSURE/RISK CONTEXT, E. SPATIAL CONTEXT",
        temporal_res="Static projection (Epoch 2025)",
        spatial_res="100 m grid (aggregated to 5km and 10km geodesic circular station buffers)",
        date_start="2025-01-01",
        date_end="2025-12-31",
        variables="population_5km, population_10km, station_id, station_name, city, state, latitude, longitude",
        units="Estimated human population count (headcount)",
        crs="EPSG:4326 (WGS84)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Static exposure descriptor: available at all prediction timestamps. Static feature for population-weighted AQI and health burden modeling.",
        license_name="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        provenance="Extracted via Google Earth Engine reducers (ee.Reducer.sum()) on geodesic buffers around CAAQMS coordinates.",
        quality_status="VERIFIED_PROCESSED",
        allowed_prod=False,
        allowed_ablation=True,
        notes=f"Contains station-level 5km and 10km population exposure estimates. Station populations range from 338k to 3.1M within 5km, and up to 8.5M within 10km."
    )

    # --- 13. Open Waste Burning Emissions Inventory (OWBEII / HCL / Wasteburned) ---
    record(
        dataset_name="Open Waste Burning Emissions Inventory for India (OWBEII)",
        source="Sharma et al. / Research Group Open Waste Burning Inventory India",
        raw_path="backend/data/raw/OWBEII-mozart v1.01.txt, HCL.txt, Wasteburned.txt",
        processed_path="UNKNOWN (Tabular text)",
        role="C. POLLUTION/SOURCE INVESTIGATION, E. SPATIAL CONTEXT, G. RESEARCH/ABLATION ONLY",
        temporal_res="Annual inventory (Base year 2015)",
        spatial_res="0.1 x 0.1 degree (~10 km grid across India)",
        date_start="2015-01-01",
        date_end="2015-12-31",
        variables="Wasteburned (tonnes/month), HCl, NMVOC, CO, CO2, NOx, PM2.5, PM10 emissions by chemical speciation (MOZART mechanism)",
        units="tonnes/month / metric tons",
        crs="EPSG:4326 (0.1 degree grid)",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Static emission inventory prior: does not change dynamically. Static spatial prior.",
        license_name="Academic Research Open Data (Published scientific inventory)",
        provenance="Three text files (9.90 MB total) containing spatial gridded open waste burning emissions.",
        quality_status="ACQUIRED_RAW_TEXT",
        allowed_prod=False,
        allowed_ablation=True,
        notes="High domain value for winter municipal solid waste (MSW) burning source attribution in Delhi-NCR."
    )

    # --- 14. Episode Dynamics (Engineered Feature Set) ---
    ep_file = data_dir / "processed" / "fusion" / "delhi_forecasting_episode.csv"
    record(
        dataset_name="VayuNet Episode Dynamics (Derived Canonical Dataset)",
        source="VayuNet Feature Engineering Pipeline (Causal Temporal Rules)",
        raw_path="Computed from CPCB Delhi hourly ground observations",
        processed_path="backend/data/processed/fusion/delhi_forecasting_episode.csv",
        role="B. HISTORICAL TRAINING INPUT, A. FORECAST INPUT (at T_0)",
        temporal_res="1-hour (hourly)",
        spatial_res="Station-level (10 stations)",
        date_start="2022-01-01 00:00:00",
        date_end="2026-08-31 23:00:00",
        variables="pm25_delta_1h/3h/6h/12h/24h, pm25_acceleration_1h/3h/6h, pm25_mean/std/max, hours_since_150_onset, hours_since_250_onset, hours_above_150/250_24h, fraction_above_150/250_24h",
        units="ug/m3, ug/m3/h, hours, dimensionless ratio",
        crs="EPSG:4326",
        forecast_avail=False,
        hist_avail=True,
        latency_rule="Causal lag rule: constructed strictly from past PM2.5 observations up to T_0. Zero forward leakage.",
        license_name="Proprietary VayuNet Engineering",
        provenance="Engineered via canonical episode builder, merged into S6 production models for 6h and 72h.",
        quality_status="VERIFIED_CANONICAL",
        allowed_prod=True,
        allowed_ablation=True,
        notes="383,303 rows (177.46 MB). Core component of production 6h S6 architecture."
    )

    # Export CSV
    df_reg = pd.DataFrame(registry)
    csv_out = data_dir / "metadata" / "dataset_registry.csv"
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    df_reg.to_csv(csv_out, index=False)
    print(f"Saved dataset registry CSV with {len(df_reg)} datasets to: {csv_out}")

if __name__ == "__main__":
    main()
