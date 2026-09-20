import os
import glob
import json
from pathlib import Path

def audit_directory(path):
    p = Path(path)
    if not p.exists():
        return {"exists": False}

    files = [f for f in p.glob('**/*') if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)
    extensions = {}
    for f in files:
        ext = f.suffix.lower()
        extensions[ext] = extensions.get(ext, 0) + 1

    return {
        "exists": True,
        "total_files": len(files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024**2), 2),
        "extensions": extensions,
        "sample_files": [f.name for f in files[:5]]
    }

def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    targets = {
        "raw_cpcb_delhi": data_dir / "raw" / "delhi",
        "raw_cpcb_delhi_ncr": data_dir / "raw" / "delhi_ncr",
        "raw_weather_openmeteo": data_dir / "raw" / "weather",
        "raw_weather_era5_pilot": data_dir / "raw" / "weather" / "era5_pressure_levels",
        "raw_nwp_ecmwf": data_dir / "raw" / "nwp",
        "raw_satellite_s5p": data_dir / "raw" / "satellite" / "delhi_s5p_no2.csv",
        "raw_satellite_modis_maiac": data_dir / "raw" / "satellite" / "modis_maiac",
        "raw_firms_viirs_j1": data_dir / "raw" / "DL_FIRE_J1V-C2_803251",
        "raw_firms_viirs_j2": data_dir / "raw" / "DL_FIRE_J2V-C2_803252",
        "raw_firms_viirs_sv": data_dir / "raw" / "DL_FIRE_SV-C2_803253",
        "raw_firms_viirs_combined": data_dir / "raw" / "firms_viirs.csv",
        "raw_osm_northern": data_dir / "raw" / "northern-zone-260910-free.gpkg",
        "raw_osm_central": data_dir / "raw" / "central-zone-260910-free.gpkg",
        "raw_grib_large": data_dir / "raw" / "2cfd8dfef8800741a21fc57927ee70e1.grib",
        "raw_emissions_txt": [data_dir / "raw" / "HCL.txt", data_dir / "raw" / "OWBEII-mozart v1.01.txt", data_dir / "raw" / "Wasteburned.txt"],
        "processed_delhi_forecasting": data_dir / "processed" / "delhi_forecasting.csv",
        "processed_delhi_weather": data_dir / "processed" / "delhi_forecasting_weather.csv",
        "processed_delhi_ncr": data_dir / "processed" / "delhi_ncr",
        "processed_exposure": data_dir / "processed" / "exposure",
        "processed_fusion": data_dir / "processed" / "fusion",
        "canonical_kaggle_parquet": data_dir / "kaggle" / "vayunet_forecasting_kaggle.parquet",
    }

    results = {}
    for name, path in targets.items():
        if isinstance(path, list):
            results[name] = {
                "files": [
                    {
                        "path": str(p),
                        "exists": p.exists(),
                        "size_mb": round(p.stat().st_size / (1024**2), 2) if p.exists() else 0
                    }
                    for p in path
                ]
            }
        elif path.is_file():
            results[name] = {
                "type": "file",
                "exists": path.exists(),
                "size_bytes": path.stat().st_size,
                "size_mb": round(path.stat().st_size / (1024**2), 2),
                "name": path.name,
            }
        else:
            results[name] = audit_directory(path)

    print(json.dumps(results, indent=2))
    with open(base_dir / "reports" / "data_inventory" / "raw_inventory_scan.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
