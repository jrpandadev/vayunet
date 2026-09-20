import os
import pandas as pd

def generate_reports():
    datasets = [
        {
            "dataset_name": "CPCB CAAQMS Delhi (10 Core Stations)",
            "source": "CPCB / DPCC",
            "raw_location": "data/raw/delhi/",
            "processed_location": "data/processed/delhi_forecasting.csv",
            "temporal_coverage": "2022-01-01 to 2026-08-31",
            "spatial_coverage": "Delhi (10 Stations)",
            "spatial_resolution": "Point level",
            "temporal_resolution": "Hourly",
            "causal_availability": "100%",
            "latency_assumption": "T0 (Immediate at origin)",
            "preprocessing_status": "Completed",
            "feature_representation": "Autoregressive PM2.5/PM10 lags",
            "proposed_role": "FORECAST_FEATURE",
            "enter_forecast": "YES",
            "enter_investigation": "YES",
            "limitations": "Frequent missing values requiring imputation.",
            "provenance": "Official government monitors",
            "current_experiment_result": "Canonical S0 baseline",
            "final_status": "PRODUCTION"
        },
        {
            "dataset_name": "VayuNet Episode Dynamics",
            "source": "Derived from CPCB",
            "raw_location": "N/A",
            "processed_location": "data/processed/fusion/delhi_forecasting_episode.csv",
            "temporal_coverage": "2022-01-01 to 2026-08-31",
            "spatial_coverage": "Delhi (10 Stations)",
            "spatial_resolution": "Point level",
            "temporal_resolution": "Hourly",
            "causal_availability": "100%",
            "latency_assumption": "T0 (Immediate at origin)",
            "preprocessing_status": "Completed",
            "feature_representation": "Episode duration, acceleration, regime fraction",
            "proposed_role": "FORECAST_FEATURE",
            "enter_forecast": "YES",
            "enter_investigation": "YES",
            "limitations": "Highly correlated with raw PM2.5 lags",
            "provenance": "VayuNet Feature Engineering",
            "current_experiment_result": "Promoted in S6",
            "final_status": "PRODUCTION"
        },
        {
            "dataset_name": "Open-Meteo Historical Weather",
            "source": "Open-Meteo / ERA5",
            "raw_location": "data/raw/weather/delhi_weather_2022_2026.csv",
            "processed_location": "data/processed/delhi_forecasting_weather.csv",
            "temporal_coverage": "2022-01-01 to 2026-08-31",
            "spatial_coverage": "Delhi Region",
            "spatial_resolution": "0.1 degree",
            "temporal_resolution": "Hourly",
            "causal_availability": "N/A (Historical Only)",
            "latency_assumption": "Prohibited as future input",
            "preprocessing_status": "Completed",
            "feature_representation": "Historical meteorology",
            "proposed_role": "RETAINED_RESEARCH",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Contains forward-looking reanalysis data (data leakage risk).",
            "provenance": "ERA5 reanalysis",
            "current_experiment_result": "Baseline training",
            "final_status": "ARCHIVED"
        },
        {
            "dataset_name": "ECMWF IFS Operational NWP Forecasts",
            "source": "ECMWF Open Data",
            "raw_location": "data/raw/nwp/",
            "processed_location": "data/processed/fusion/delhi_forecasting_s5_nwp.csv",
            "temporal_coverage": "2024-03-14 to 2026-08-31",
            "spatial_coverage": "Delhi Region",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "causal_availability": "99%+ (Major cycles)",
            "latency_assumption": "6h buffer from run_time",
            "preprocessing_status": "Completed",
            "feature_representation": "nwp_[variable]_[horizon]",
            "proposed_role": "FORECAST_FEATURE",
            "enter_forecast": "YES",
            "enter_investigation": "NO",
            "limitations": "Missing minor cycles (06/18 UTC)",
            "provenance": "Operational forecasting system",
            "current_experiment_result": "Promoted in S5",
            "final_status": "PRODUCTION"
        },
        {
            "dataset_name": "Sentinel-5P TROPOMI Tropospheric NO2",
            "source": "ESA / GEE",
            "raw_location": "data/raw/satellite/delhi_s5p_no2.csv",
            "processed_location": "data/processed/fusion/delhi_forecasting_satellite.csv",
            "temporal_coverage": "2022-01-01 to 2026-08-26",
            "spatial_coverage": "Delhi Region",
            "spatial_resolution": "3.5 x 5.5 km",
            "temporal_resolution": "Daily",
            "causal_availability": "Operational (with gaps)",
            "latency_assumption": "24h operational latency",
            "preprocessing_status": "Completed",
            "feature_representation": "satellite_no2_latest, satellite_no2_age_hours",
            "proposed_role": "FORECAST_FEATURE",
            "enter_forecast": "YES",
            "enter_investigation": "YES",
            "limitations": "Cloud cover missingness",
            "provenance": "Copernicus Satellite",
            "current_experiment_result": "Promoted in S4",
            "final_status": "PRODUCTION"
        },
        {
            "dataset_name": "MODIS MCD19A2 V061 MAIAC AOD",
            "source": "NASA LP DAAC",
            "raw_location": "data/raw/satellite/modis_maiac/",
            "processed_location": "data/processed/satellite/delhi_mcd19a2_maiac_station_aod.parquet",
            "temporal_coverage": "2022-01-01 to 2023-12-31",
            "spatial_coverage": "Tile h24v06",
            "spatial_resolution": "1 km grid",
            "temporal_resolution": "Daily overpass",
            "causal_availability": "~60% (Station level)",
            "latency_assumption": "48h operational latency + 72h window",
            "preprocessing_status": "Completed",
            "feature_representation": "modis_aod_latest, modis_aod_age_hours",
            "proposed_role": "REJECTED_FORECAST_FEATURE",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "High sparsity at station level; caused MAE degradation.",
            "provenance": "NASA EOS",
            "current_experiment_result": "Rejected in S8",
            "final_status": "REJECTED"
        },
        {
            "dataset_name": "NASA FIRMS VIIRS Active Fire Detections",
            "source": "NASA LANCE FIRMS",
            "raw_location": "data/raw/firms_viirs.csv",
            "processed_location": "data/processed/fusion/delhi_forecasting_s7_firms.csv",
            "temporal_coverage": "2022-01-01 to 2026-08-31",
            "spatial_coverage": "Bounding Box (Delhi + Upwind)",
            "spatial_resolution": "375 m pixel",
            "temporal_resolution": "Daily overpasses",
            "causal_availability": "High",
            "latency_assumption": "3h NRT latency / 48h SP latency",
            "preprocessing_status": "Completed",
            "feature_representation": "Distance bins, rolling FRP, wind alignment",
            "proposed_role": "REJECTED_FORECAST_FEATURE",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Overfit forecasting models; highly sparse extreme events.",
            "provenance": "NASA LANCE",
            "current_experiment_result": "Rejected in S7",
            "final_status": "REJECTED"
        },
        {
            "dataset_name": "OpenStreetMap Northern Zone",
            "source": "Geofabrik / OSM",
            "raw_location": "data/raw/northern-zone-260910-free.gpkg/",
            "processed_location": "Pending",
            "temporal_coverage": "2026-09-10 (Static)",
            "spatial_coverage": "North India",
            "spatial_resolution": "Vector",
            "temporal_resolution": "Static",
            "causal_availability": "100% (Static)",
            "latency_assumption": "N/A",
            "preprocessing_status": "Pending",
            "feature_representation": "N/A",
            "proposed_role": "SOURCE_CONTEXT",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Not temporally dynamic.",
            "provenance": "Crowdsourced vector map",
            "current_experiment_result": "None",
            "final_status": "PENDING"
        },
        {
            "dataset_name": "OpenStreetMap Central Zone",
            "source": "Geofabrik / OSM",
            "raw_location": "data/raw/central-zone-260910-free.gpkg/",
            "processed_location": "Pending",
            "temporal_coverage": "2026-09-10 (Static)",
            "spatial_coverage": "Central India",
            "spatial_resolution": "Vector",
            "temporal_resolution": "Static",
            "causal_availability": "100% (Static)",
            "latency_assumption": "N/A",
            "preprocessing_status": "Pending",
            "feature_representation": "N/A",
            "proposed_role": "SOURCE_CONTEXT",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Not temporally dynamic.",
            "provenance": "Crowdsourced vector map",
            "current_experiment_result": "None",
            "final_status": "PENDING"
        },
        {
            "dataset_name": "CPCB CAAQMS Delhi-NCR (Regional Grid)",
            "source": "CPCB / Regional Boards",
            "raw_location": "data/raw/delhi_ncr/",
            "processed_location": "data/processed/delhi_ncr/ncr_caaqms_hourly.parquet",
            "temporal_coverage": "2022-01-01 to 2026-08-31",
            "spatial_coverage": "Delhi-NCR (69 stations)",
            "spatial_resolution": "Point level",
            "temporal_resolution": "Hourly",
            "causal_availability": "TBD",
            "latency_assumption": "T0 (Immediate at origin)",
            "preprocessing_status": "Completed",
            "feature_representation": "Regional upstream interpolation",
            "proposed_role": "NOT_READY",
            "enter_forecast": "YES",
            "enter_investigation": "YES",
            "limitations": "Requires complex spatial graph modeling.",
            "provenance": "Official government monitors",
            "current_experiment_result": "Pending",
            "final_status": "PENDING"
        },
        {
            "dataset_name": "GHSL Population 2025 (100m Exposure)",
            "source": "JRC GHSL",
            "raw_location": "GEE JRC/GHSL/P2023A/GHS_POP",
            "processed_location": "data/processed/exposure/ghsl_population_2025_100m.csv",
            "temporal_coverage": "2025 Epoch",
            "spatial_coverage": "Global",
            "spatial_resolution": "100m grid",
            "temporal_resolution": "Static",
            "causal_availability": "100%",
            "latency_assumption": "N/A",
            "preprocessing_status": "Completed",
            "feature_representation": "5km/10km buffer pop sum",
            "proposed_role": "EXPOSURE_RISK",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Static representation of population",
            "provenance": "JRC",
            "current_experiment_result": "None",
            "final_status": "READY"
        },
        {
            "dataset_name": "Open Waste Burning Inventories (OWBEII)",
            "source": "Sharma et al.",
            "raw_location": "data/raw/OWBEII-mozart v1.01.txt",
            "processed_location": "N/A",
            "temporal_coverage": "2015 Annual Baseline",
            "spatial_coverage": "India",
            "spatial_resolution": "0.1 degree",
            "temporal_resolution": "Annual",
            "causal_availability": "100%",
            "latency_assumption": "N/A",
            "preprocessing_status": "Raw",
            "feature_representation": "N/A",
            "proposed_role": "SOURCE_CONTEXT",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Highly outdated (2015).",
            "provenance": "Academic research",
            "current_experiment_result": "None",
            "final_status": "PENDING"
        },
        {
            "dataset_name": "ERA5 Pressure-Level Pilot (Delhi Point)",
            "source": "Copernicus CDS",
            "raw_location": "data/raw/weather/era5_pressure_levels/era5_delhi_pilot.csv",
            "processed_location": "data/processed/weather/era5_vertical_features.parquet",
            "temporal_coverage": "2022-01-01 to 2026-08-31",
            "spatial_coverage": "Delhi Point",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "Hourly",
            "causal_availability": "N/A",
            "latency_assumption": "Leakage",
            "preprocessing_status": "Completed",
            "feature_representation": "Wind shear, dθ/dz",
            "proposed_role": "RETAINED_RESEARCH",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Reanalysis product; leaks future.",
            "provenance": "ERA5",
            "current_experiment_result": "Ablation blocked by leakage",
            "final_status": "ARCHIVED"
        },
        {
            "dataset_name": "ECMWF CDS GRIB Bulk Archive",
            "source": "Copernicus CDS",
            "raw_location": "data/raw/2cfd8dfef8800741a21fc57927ee70e1.grib",
            "processed_location": "N/A",
            "temporal_coverage": "Unknown",
            "spatial_coverage": "Regional",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "Unknown",
            "causal_availability": "N/A",
            "latency_assumption": "N/A",
            "preprocessing_status": "Unprocessed",
            "feature_representation": "N/A",
            "proposed_role": "RETAINED_RESEARCH",
            "enter_forecast": "NO",
            "enter_investigation": "YES",
            "limitations": "Raw binary archive",
            "provenance": "ECMWF",
            "current_experiment_result": "None",
            "final_status": "ARCHIVED"
        }
    ]

    out_dir = "backend/reports/fusion"
    os.makedirs(out_dir, exist_ok=True)

    df = pd.DataFrame(datasets)
    df.to_csv(os.path.join(out_dir, "vayunet_multisource_feature_registry.csv"), index=False)

    md = "# VayuNet Multi-Source Fusion Specification\n\n"
    md += "## 1. Objective\n"
    md += "Transition VayuNet from isolated ablation experiments to a unified multi-source environmental intelligence architecture, establishing clear boundaries between operational forecasting inputs, retrospective investigation evidence, and exposure risk modeling.\n\n"
    md += "## 2. Dataset Classification & Roles\n\n"

    for d in datasets:
        md += f"### {d['dataset_name']}\n"
        md += f"- **Source**: {d['source']}\n"
        md += f"- **Role**: `{d['proposed_role']}`\n"
        md += f"- **Raw Location**: {d['raw_location']}\n"
        md += f"- **Processed Location**: {d['processed_location']}\n"
        md += f"- **Temporal Coverage**: {d['temporal_coverage']}\n"
        md += f"- **Spatial Coverage**: {d['spatial_coverage']}\n"
        md += f"- **Spatial Resolution**: {d['spatial_resolution']}\n"
        md += f"- **Temporal Resolution**: {d['temporal_resolution']}\n"
        md += f"- **Causal Availability**: {d['causal_availability']}\n"
        md += f"- **Latency Assumption**: {d['latency_assumption']}\n"
        md += f"- **Preprocessing Status**: {d['preprocessing_status']}\n"
        md += f"- **Feature Representation**: {d['feature_representation']}\n"
        md += f"- **Enters Forecasting Model?**: {d['enter_forecast']}\n"
        md += f"- **Enters Investigation Layer?**: {d['enter_investigation']}\n"
        md += f"- **Known Limitations**: {d['limitations']}\n"
        md += f"- **Provenance**: {d['provenance']}\n"
        md += f"- **Current Experiment Result**: {d['current_experiment_result']}\n"
        md += f"- **Final Status**: {d['final_status']}\n\n"

    md += "## 3. Proposed Feature Architecture\n\n"

    groups = {
        "A. Ground observations": [],
        "B. Historical pollution dynamics": [],
        "C. Current meteorology": [],
        "D. Future NWP meteorology": [],
        "E. Satellite atmospheric observations": [],
        "F. Potential emission/source context": [],
        "G. Spatial context": [],
        "H. Exposure/risk": []
    }

    proposed_features = [
        {"group": "A. Ground observations", "source": "CPCB Delhi", "name": "PM2.5_lag_1h", "time": "T0 - 1h", "causal": "Strict trailing", "spatial": "Station Exact", "missing": "Impute/FFill", "layer": "FORECAST"},
        {"group": "B. Historical pollution dynamics", "source": "VayuNet Pipeline", "name": "fraction_above_150_24h", "time": "[T0-24h, T0]", "causal": "Strict trailing", "spatial": "Station Exact", "missing": "Zero fill", "layer": "FORECAST"},
        {"group": "D. Future NWP meteorology", "source": "ECMWF IFS", "name": "nwp_surface_pressure_24h", "time": "T0 + 24h", "causal": "Run time <= T0 - 6h", "spatial": "Grid interpolation", "missing": "Drop", "layer": "FORECAST"},
        {"group": "E. Satellite atmospheric observations", "source": "S5P", "name": "satellite_no2_latest", "time": "T0 (Latest valid)", "causal": "Obs Time <= T0 - 24h", "spatial": "Grid point", "missing": "FFill with Age", "layer": "FORECAST"},
        {"group": "F. Potential emission/source context", "source": "FIRMS VIIRS", "name": "fire_count_300km_rolling_24h", "time": "[T0-24h, T0]", "causal": "Obs Time <= T0 - 3h (NRT) / 48h (SP)", "spatial": "Distance Buffer", "missing": "Zero fill", "layer": "INVESTIGATION (Rejected from Forecast)"},
        {"group": "E. Satellite atmospheric observations", "source": "MODIS MAIAC", "name": "modis_aod_latest", "time": "[T0-72h, T0-48h]", "causal": "Obs Time <= T0 - 48h", "spatial": "Station Exact", "missing": "Drop", "layer": "INVESTIGATION (Rejected from Forecast)"},
        {"group": "G. Spatial context", "source": "OSM", "name": "road_density_5km", "time": "Static", "causal": "N/A", "spatial": "Station Buffer", "missing": "N/A", "layer": "INVESTIGATION"},
        {"group": "H. Exposure/risk", "source": "GHSL", "name": "population_10km", "time": "Static", "causal": "N/A", "spatial": "Station Buffer", "missing": "N/A", "layer": "EXPOSURE"}
    ]

    for pf in proposed_features:
        groups[pf["group"]].append(pf)

    for g, feats in groups.items():
        md += f"### {g}\n"
        if not feats:
            md += "*No explicit canonical features mapped yet.*\n\n"
        else:
            for f in feats:
                md += f"- **Feature**: `{f['name']}`\n"
                md += f"  - Source: {f['source']}\n"
                md += f"  - Reference Time: {f['time']}\n"
                md += f"  - Causal Rule: {f['causal']}\n"
                md += f"  - Spatial Alignment: {f['spatial']}\n"
                md += f"  - Missing Data Policy: {f['missing']}\n"
                md += f"  - Layer: **{f['layer']}**\n\n"

    md += "## 4. Final Sets\n\n"

    md += "### 1. FINAL FORECAST FEATURE SET CANDIDATE\n"
    md += "- CPCB Delhi PM2.5/PM10 Lags\n- ECMWF Operational NWP\n- Sentinel-5P NO2\n- VayuNet Episode Dynamics\n\n"

    md += "### 2. FINAL INVESTIGATION EVIDENCE SET CANDIDATE\n"
    md += "- NASA FIRMS Active Fires (Upwind Biomass)\n- MODIS MAIAC AOD (Aerosol mapping)\n- Open Waste Burning Inventories\n- Open-Meteo ERA5 Reanalysis\n\n"

    md += "### 3. FINAL SOURCE CONTEXT SET\n"
    md += "- OpenStreetMap (Road density, industrial zones)\n- OWBEII Waste inventories\n\n"

    md += "### 4. FINAL EXPOSURE/RISK SET\n"
    md += "- GHSL Population 2025\n\n"

    md += "### 5. DATASETS STILL REQUIRING AUDIT\n"
    md += "- CPCB Delhi-NCR Regional Grid (Pending spatial modeling)\n- OSM Extractions\n\n"

    md += "### 6. DATASETS CURRENTLY REJECTED FOR FORECASTING\n"
    md += "- MODIS MAIAC AOD (Rejected in S8)\n- NASA FIRMS Active Fires (Rejected in S7)\n- ERA5 Pressure Levels (Leakage)\n\n"

    md += "### 7. NEXT EXPERIMENT RECOMMENDATION\n"
    md += "Proceed with constructing the unified Evidence Investigation Layer, enabling VayuNet to contextualize high-pollution forecasts by linking NWP transport vectors with the rejected forecasting features (FIRMS, MODIS, OSM) to explain *why* pollution is occurring without polluting the causal ML forecaster.\n\n"

    with open(os.path.join(out_dir, "vayunet_multisource_fusion_spec.md"), "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    generate_reports()
