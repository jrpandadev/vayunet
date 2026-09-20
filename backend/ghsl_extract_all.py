import ee
import pandas as pd
import datetime
import os
import time

os.makedirs('data/processed/exposure', exist_ok=True)
os.makedirs('reports/exposure', exist_ok=True)

print("Initializing Earth Engine...")
try:
    ee.Initialize(project='vayunet-52a15')
except Exception as e:
    print(f"Error initializing EE: {e}")
    exit(1)

dataset_id = "JRC/GHSL/P2023A/GHS_POP"
dataset = ee.ImageCollection(dataset_id)
image_2025 = dataset.filter(ee.Filter.eq('system:index', '2025')).first()
pop_band = image_2025.select('population_count')

def get_population(lon, lat, distance_m):
    geom = ee.Geometry.Point([lon, lat]).buffer(distance=distance_m)
    result = pop_band.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom,
        scale=100,
        maxPixels=1e9,
        bestEffort=False
    )
    return result.get('population_count').getInfo()

metadata_path = 'data/processed/delhi_ncr/ncr_station_metadata.csv'
df_meta = pd.read_csv(metadata_path)

# Filter for valid coordinates
df_valid = df_meta[df_meta['latitude'].notna() & df_meta['longitude'].notna()].copy()
print(f"Found {len(df_valid)} stations with valid coordinates out of {len(df_meta)}.")

results = []
failures = []

for idx, row in df_valid.iterrows():
    sid = row['station_id']
    sname = row['station_name']
    lat = row['latitude']
    lon = row['longitude']

    print(f"Processing {sid} ({sname})...")
    try:
        pop_5km = get_population(float(lon), float(lat), 5000)
        pop_10km = get_population(float(lon), float(lat), 10000)

        if pop_5km is None or pop_10km is None or pop_5km < 0 or pop_10km < 0 or pop_10km < pop_5km:
            raise ValueError(f"Invalid population extracted: 5km={pop_5km}, 10km={pop_10km}")

        results.append({
            "station_id": sid,
            "station_name": sname,
            "city": row['city'],
            "state": row['state'],
            "latitude": lat,
            "longitude": lon,
            "ghsl_dataset": dataset_id,
            "ghsl_year": 2025,
            "ghsl_resolution_m": 100,
            "population_5km": pop_5km,
            "population_10km": pop_10km,
            "extraction_method": "ee.Reducer.sum() on geodesic buffer",
            "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
    except Exception as e:
        print(f"  Failed for {sid}: {e}")
        failures.append({"station_id": sid, "reason": str(e)})

df_out = pd.DataFrame(results)
out_path = 'data/processed/exposure/ghsl_population_2025_100m.csv'
df_out.to_csv(out_path, index=False)
print(f"\nSaved {len(df_out)} successful extractions to {out_path}")

# Write audit report
min_5 = df_out['population_5km'].min() if not df_out.empty else "N/A"
max_5 = df_out['population_5km'].max() if not df_out.empty else "N/A"
med_5 = df_out['population_5km'].median() if not df_out.empty else "N/A"

min_10 = df_out['population_10km'].min() if not df_out.empty else "N/A"
max_10 = df_out['population_10km'].max() if not df_out.empty else "N/A"
med_10 = df_out['population_10km'].median() if not df_out.empty else "N/A"

excluded_count = len(df_meta) - len(df_valid) + len(failures)

audit_md = f"""# GHSL Population Extraction 2025 (100m) - Quality Audit

**Extraction Date**: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}
**Dataset**: `{dataset_id}` (Year: 2025, Resolution: 100m)

## Summary Statistics
- **Total stations processed (successful)**: {len(df_out)}
- **Total stations excluded**: {excluded_count}

### Exclusions
- **Missing/invalid coordinates in metadata**: {len(df_meta) - len(df_valid)}
- **Earth Engine extraction failures/invalid data**: {len(failures)}
"""
if failures:
    audit_md += "\n**Failure Reasons**:\n"
    for f in failures:
        audit_md += f"- `{f['station_id']}`: {f['reason']}\n"

audit_md += f"""
## Data Integrity Checks
- **Duplicate station IDs**: {df_out['station_id'].duplicated().sum() if not df_out.empty else 0}
- **Missing coordinates**: {(df_out['latitude'].isna().sum() + df_out['longitude'].isna().sum()) if not df_out.empty else 0}
- **Missing population values**: 0 (Filtered out if missing)
- **Negative population values**: 0 (Filtered out if < 0)
- **10 km < 5 km violations**: 0 (Filtered out if invalid)

## Population Distributions
| Buffer | Minimum | Median | Maximum |
|---|---|---|---|
| 5 km | {min_5} | {med_5} | {max_5} |
| 10 km | {min_10} | {med_10} | {max_10} |

## Provenance & Limitations
- **Source**: GHSL / JRC
- **Dataset**: GHSL Global population surfaces 1975-2030 (P2023A)
- **Platform**: Google Earth Engine
- **Methodology**: GHSL modeled/projected population estimate.
- **Notes**: The 2025 layer is a modeled projection and is the closest representation to 2026 available natively in the dataset. Values represent the sum of `population_count` in 100m pixels intersecting geodesic WGS-84 buffers.
"""

with open('reports/exposure/ghsl_population_2025_100m_audit.md', 'w') as f:
    f.write(audit_md)

print("Audit report written.")
