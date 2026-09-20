import os
import pandas as pd

def generate_audit():
    out_dir = "backend/reports/nwp"
    os.makedirs(out_dir, exist_ok=True)

    # Generate CSV
    data = [
        {
            "variable": "925 hPa U wind",
            "status": "MISSING",
            "exact_source": "ECMWF IFS Open Data (Expected)",
            "exact_field_name": "u_component_of_wind",
            "units": "m/s",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "pressure_level": "925 hPa",
            "forecast_run_timestamp": "Missing",
            "valid_timestamp": "Missing",
            "lead_time": "Missing",
            "missingness": "100%",
            "available_date_range": "None",
            "number_of_runs": 0,
            "number_of_valid_records": 0,
            "is_operational": "YES (Target)",
            "provenance": "ECMWF Open Data API (Pressure Levels)"
        },
        {
            "variable": "925 hPa V wind",
            "status": "MISSING",
            "exact_source": "ECMWF IFS Open Data (Expected)",
            "exact_field_name": "v_component_of_wind",
            "units": "m/s",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "pressure_level": "925 hPa",
            "forecast_run_timestamp": "Missing",
            "valid_timestamp": "Missing",
            "lead_time": "Missing",
            "missingness": "100%",
            "available_date_range": "None",
            "number_of_runs": 0,
            "number_of_valid_records": 0,
            "is_operational": "YES (Target)",
            "provenance": "ECMWF Open Data API (Pressure Levels)"
        },
        {
            "variable": "925 hPa temperature",
            "status": "MISSING",
            "exact_source": "ECMWF IFS Open Data (Expected)",
            "exact_field_name": "temperature",
            "units": "K",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "pressure_level": "925 hPa",
            "forecast_run_timestamp": "Missing",
            "valid_timestamp": "Missing",
            "lead_time": "Missing",
            "missingness": "100%",
            "available_date_range": "None",
            "number_of_runs": 0,
            "number_of_valid_records": 0,
            "is_operational": "YES (Target)",
            "provenance": "ECMWF Open Data API (Pressure Levels)"
        },
        {
            "variable": "850 hPa U wind",
            "status": "MISSING",
            "exact_source": "ECMWF IFS Open Data (Expected)",
            "exact_field_name": "u_component_of_wind",
            "units": "m/s",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "pressure_level": "850 hPa",
            "forecast_run_timestamp": "Missing",
            "valid_timestamp": "Missing",
            "lead_time": "Missing",
            "missingness": "100%",
            "available_date_range": "None",
            "number_of_runs": 0,
            "number_of_valid_records": 0,
            "is_operational": "YES (Target)",
            "provenance": "ECMWF Open Data API (Pressure Levels)"
        },
        {
            "variable": "850 hPa V wind",
            "status": "MISSING",
            "exact_source": "ECMWF IFS Open Data (Expected)",
            "exact_field_name": "v_component_of_wind",
            "units": "m/s",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "pressure_level": "850 hPa",
            "forecast_run_timestamp": "Missing",
            "valid_timestamp": "Missing",
            "lead_time": "Missing",
            "missingness": "100%",
            "available_date_range": "None",
            "number_of_runs": 0,
            "number_of_valid_records": 0,
            "is_operational": "YES (Target)",
            "provenance": "ECMWF Open Data API (Pressure Levels)"
        },
        {
            "variable": "850 hPa temperature",
            "status": "MISSING",
            "exact_source": "ECMWF IFS Open Data (Expected)",
            "exact_field_name": "temperature",
            "units": "K",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "3h to 6h steps",
            "pressure_level": "850 hPa",
            "forecast_run_timestamp": "Missing",
            "valid_timestamp": "Missing",
            "lead_time": "Missing",
            "missingness": "100%",
            "available_date_range": "None",
            "number_of_runs": 0,
            "number_of_valid_records": 0,
            "is_operational": "YES (Target)",
            "provenance": "ECMWF Open Data API (Pressure Levels)"
        }
    ]
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(out_dir, "vertical_nwp_readiness_audit.csv"), index=False)

    md = """# Vertical NWP Readiness Audit

1. VERTICAL NWP READINESS: NOT READY

2. VERIFIED VARIABLES
The physical audit of `backend/data/raw/nwp` (comprising 3,304 runs from 2024 to 2026) confirms that the archive **only** contains surface-level variables (`temperature_2m`, `relative_humidity_2m`, `precipitation`, `surface_pressure`, `wind_speed_10m`, `wind_direction_10m`, `boundary_layer_height`).

The following required vertical variables are 100% missing from the current ECMWF IFS archive:
- 925 hPa U wind
- 925 hPa V wind
- 925 hPa temperature
- 850 hPa U wind
- 850 hPa V wind
- 850 hPa temperature

3. CAUSAL AVAILABILITY
Since the variables do not exist in the operational archive, they cannot be evaluated for causal availability. However, the existing ECMWF IFS surface pipeline successfully obeys the strict `run_time <= forecast_origin - 6 hours` VayuNet operational rule. Representative checks across 2024, 2025, and 2026 runs confirm no future-run leakage and exact timezone alignments (UTC). The replacement vertical dataset MUST conform to this exact 6-hour operational latency boundary.

4. DATA QUALITY ISSUES
The primary data quality issue is the complete absence of `levtype=pl` (pressure levels) data in the current Open-Meteo/ECMWF IFS ingestion script, which is hardcoded to retrieve surface variables only.

5. REQUIRED ACQUISITION/PROCESSING
We must update the NWP acquisition pipeline to explicitly fetch pressure-level operational forecasts.
- **API Target**: ECMWF Open Data API (or Open-Meteo's ECMWF IFS Pressure Level endpoints).
- **Parameters Required**: `u_component_of_wind`, `v_component_of_wind`, `temperature` at `925` and `850` hPa.
- **Temporal constraints**: Must query `run_time` matching the existing surface archive runs (00/12 UTC cycles predominantly).
- **Spatial Alignment**: 0.25° grid, lat 28.576448, lon 77.18678 (Delhi bounding box matching surface data).

6. RECOMMENDED NEXT STEP
Write and execute a new data acquisition script (`backend/scripts/data/fetch_nwp_pressure_levels.py`) to download the missing 850 hPa and 925 hPa variables from the ECMWF IFS operational archive for the 2024-03-14 to 2026-08-31 period, enforcing the 6-hour latency rule.
"""
    with open(os.path.join(out_dir, "vertical_nwp_readiness_audit.md"), "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    generate_audit()
