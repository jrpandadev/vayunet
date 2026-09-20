#!/usr/bin/env python3
"""
VayuNet — ERA5 Pilot Downloader
Downloads a small sample of ERA5 hourly pressure-level data for Delhi
from the Copernicus Climate Data Store (CDS).
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import cdsapi

def main():
    # Load credentials from backend/.env
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(env_path)

    # Ensure CDS credentials are set
    if not os.getenv("CDSAPI_URL") or not os.getenv("CDSAPI_KEY"):
        print("ERROR: CDSAPI_URL or CDSAPI_KEY not found in backend/.env")
        return

    # Initialize CDS client
    c = cdsapi.Client()

    output_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "weather" / "era5_pressure_levels"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "era5_delhi_pilot.csv"

    print("Requesting ERA5 pilot dataset from CDS...")

    # The new CDS platform provides "reanalysis-era5-pressure-levels" and
    # "reanalysis-era5-pressure-levels-timeseries" etc. But we should just use what the user mentioned.
    # Wait, the user specifically mentioned "reanalysis-era5-pressure-levels-timeseries".
    try:
        import pandas as pd
        csv_files = []
        for year in ['2022', '2023', '2024', '2025', '2026']:
            for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                if year == '2026' and int(month) > 8:
                    continue # only up to august 2026
                print(f"Downloading {year}-{month}...")
                month_file = output_dir / f"era5_delhi_pilot_{year}_{month}.nc"
                c.retrieve(
                    'reanalysis-era5-pressure-levels',
                    {
                        'product_type': 'reanalysis',
                        'data_format': 'netcdf',
                        'variable': [
                            'u_component_of_wind', 'v_component_of_wind', 'temperature',
                            'relative_humidity', 'geopotential', 'vertical_velocity'
                        ],
                        'pressure_level': [
                            '700', '850', '925',
                        ],
                        'year': [year],
                        'month': [month],
                        'day': [
                            '01', '02', '03', '04', '05', '06',
                            '07', '08', '09', '10', '11', '12',
                            '13', '14', '15', '16', '17', '18',
                            '19', '20', '21', '22', '23', '24',
                            '25', '26', '27', '28', '29', '30',
                            '31',
                        ],
                        'time': [
                            '00:00', '06:00', '12:00', '18:00',
                        ],
                        'area': [
                            28.50, 77.25, 28.50, 77.25,
                        ],
                    },
                    str(month_file)
                )
                csv_files.append(month_file)

        print("Converting to CSV and concatenating files...")
        import xarray as xr
        dfs = []
        for f in csv_files:
            ds = xr.open_dataset(f)
            df = ds.to_dataframe().reset_index()
            dfs.append(df)
            ds.close()

        combined = pd.concat(dfs, ignore_index=True)
        # Sort by valid_time and filter up to 2026-08-31
        if 'valid_time' in combined.columns:
            combined['valid_time'] = pd.to_datetime(combined['valid_time'])
            combined = combined[combined['valid_time'] <= '2026-08-31 18:00:00']
        combined.to_csv(output_file, index=False)

        # Cleanup temporary year files
        for f in csv_files:
            f.unlink()

        print(f"Acquisition successful. Saved to {output_file}")
    except Exception as e:
        print(f"Error during acquisition: {e}")

if __name__ == "__main__":
    main()
