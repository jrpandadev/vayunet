import os
import json
import pandas as pd
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"

info = {}

# 1. CPCB Delhi
cpcb_files = list((data_dir / "raw" / "delhi").glob("*.csv"))
if cpcb_files:
    df_sample = pd.read_csv(cpcb_files[0], nrows=10)
    info["cpcb_delhi"] = {
        "file_count": len(cpcb_files),
        "columns": list(df_sample.columns),
        "sample_file": cpcb_files[0].name
    }

# 2. CPCB Delhi NCR
ncr_manifest = data_dir / "raw" / "delhi_ncr" / "_dataset_manifest.csv"
if ncr_manifest.exists():
    df_m = pd.read_csv(ncr_manifest)
    info["cpcb_delhi_ncr"] = {
        "manifest_rows": len(df_m),
        "manifest_cols": list(df_m.columns),
        "stations_count": df_m["station"].nunique() if "station" in df_m.columns else None,
        "date_min": str(df_m["start_date"].min()) if "start_date" in df_m.columns else None,
        "date_max": str(df_m["end_date"].max()) if "end_date" in df_m.columns else None,
    }

# 3. Open-Meteo Weather
weather_file = data_dir / "raw" / "weather" / "delhi_weather_2022_2026.csv"
if weather_file.exists():
    df_w = pd.read_csv(weather_file)
    info["open_meteo_weather"] = {
        "rows": len(df_w),
        "columns": list(df_w.columns),
        "time_min": str(df_w["time"].min()) if "time" in df_w.columns else None,
        "time_max": str(df_w["time"].max()) if "time" in df_w.columns else None,
    }

# 4. ERA5 pilot
era5_file = data_dir / "raw" / "weather" / "era5_pressure_levels" / "era5_delhi_pilot.csv"
if era5_file.exists():
    df_e = pd.read_csv(era5_file)
    t_col = "valid_time" if "valid_time" in df_e.columns else "time"
    info["era5_pilot"] = {
        "rows": len(df_e),
        "columns": list(df_e.columns),
        "levels": list(df_e["pressure_level"].unique()) if "pressure_level" in df_e.columns else None,
        "time_min": str(df_e[t_col].min()) if t_col in df_e.columns else None,
        "time_max": str(df_e[t_col].max()) if t_col in df_e.columns else None,
    }

# 5. S5P NO2
s5p_file = data_dir / "raw" / "satellite" / "delhi_s5p_no2.csv"
if s5p_file.exists():
    df_s5p = pd.read_csv(s5p_file)
    info["s5p_no2"] = {
        "rows": len(df_s5p),
        "columns": list(df_s5p.columns),
        "time_min": str(df_s5p["date"].min()) if "date" in df_s5p.columns else str(df_s5p["timestamp"].min()) if "timestamp" in df_s5p.columns else None,
        "time_max": str(df_s5p["date"].max()) if "date" in df_s5p.columns else str(df_s5p["timestamp"].max()) if "timestamp" in df_s5p.columns else None,
    }

# 6. MODIS MAIAC Manifest
maiac_m = data_dir / "raw" / "satellite" / "modis_maiac" / "_mcd19a2_manifest.csv"
if maiac_m.exists():
    df_mm = pd.read_csv(maiac_m)
    info["modis_maiac_manifest"] = {
        "rows": len(df_mm),
        "columns": list(df_mm.columns),
        "status_counts": df_mm["status"].value_counts().to_dict() if "status" in df_mm.columns else None,
    }

# 7. FIRMS VIIRS
firms_file = data_dir / "raw" / "firms_viirs.csv"
if firms_file.exists():
    df_f = pd.read_csv(firms_file, nrows=100)
    # count total rows
    with open(firms_file, "r", encoding="utf-8") as f:
        row_count = sum(1 for _ in f) - 1
    info["firms_viirs"] = {
        "rows": row_count,
        "columns": list(df_f.columns),
    }

# 8. Exposure GHSL
ghsl_file = data_dir / "processed" / "exposure" / "ghsl_population_2025_100m.csv"
if ghsl_file.exists():
    df_g = pd.read_csv(ghsl_file)
    info["ghsl_population"] = {
        "rows": len(df_g),
        "columns": list(df_g.columns),
        "data": df_g.to_dict(orient="records")
    }

# 9. Emissions TXT files (OWBEII / HCL / Wasteburned)
for name, fname in [("hcl", "HCL.txt"), ("owbeii", "OWBEII-mozart v1.01.txt"), ("wasteburned", "Wasteburned.txt")]:
    txt_path = data_dir / "raw" / fname
    if txt_path.exists():
        with open(txt_path, "r", encoding="latin-1") as f:
            lines = [f.readline() for _ in range(10)]
        info[name] = {
            "first_lines": [l.strip() for l in lines[:5]]
        }

# 10. Processed NCR Parquet
ncr_p = data_dir / "processed" / "delhi_ncr" / "ncr_caaqms_hourly.parquet"
if ncr_p.exists():
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(ncr_p)
    info["processed_ncr_hourly"] = {
        "rows": pf.metadata.num_rows,
        "columns": pf.metadata.num_columns,
        "column_names": pf.schema.names
    }

# 11. Processed Fusion datasets
fusion_dir = data_dir / "processed" / "fusion"
info["fusion_datasets"] = {}
for fpath in fusion_dir.glob("*.csv"):
    df_head = pd.read_csv(fpath, nrows=5)
    info["fusion_datasets"][fpath.name] = {
        "columns": list(df_head.columns),
        "col_count": len(df_head.columns),
    }

with open(base_dir / "reports" / "data_inventory" / "detailed_dataset_profiles.json", "w") as f:
    json.dump(info, f, indent=2)

print("Saved detailed dataset profiles.")
