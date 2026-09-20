import ee
import pandas as pd
import datetime
import os

# Create directories
os.makedirs('data/processed/exposure', exist_ok=True)
os.makedirs('reports/exposure', exist_ok=True)

# 1. Initialization
try:
    ee.Initialize(project='vayunet-52a15')
except Exception as e:
    print(f"Error initializing EE: {e}")
    exit(1)

# 2. Pilot Station info
station_id = "CPCB_1430"
station_name = "Rohini"
city = "Delhi"
state = "Delhi"
lat = 28.732528
lon = 77.119920

print(f"Running Pilot Extraction for {station_name} ({station_id})")

# 3. Create geometries (geodesic buffers)
point = ee.Geometry.Point([lon, lat])
buffer_5km = point.buffer(distance=5000)
buffer_10km = point.buffer(distance=10000)

# 4. Load dataset
dataset_id = "JRC/GHSL/P2023A/GHS_POP"
dataset = ee.ImageCollection(dataset_id)

# Filter to 2025
image_2025 = dataset.filter(ee.Filter.eq('system:index', '2025')).first()

# Select the population band
pop_band = image_2025.select('population_count')

# 5. Extract population
def get_population(geometry):
    result = pop_band.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=100, # 100m resolution
        maxPixels=1e9,
        bestEffort=False
    )
    return result.get('population_count').getInfo()

print("Calculating 5km population...")
pop_5km = get_population(buffer_5km)
print("Calculating 10km population...")
pop_10km = get_population(buffer_10km)

print(f"5km Population: {pop_5km}")
print(f"10km Population: {pop_10km}")

# 6. Validation
validation_status = "PASS"
reasons = []

if pop_5km is None or pd.isna(pop_5km):
    validation_status = "FAIL"
    reasons.append("5km population is null/NaN")
elif pop_5km < 0:
    validation_status = "FAIL"
    reasons.append("5km population is negative")

if pop_10km is None or pd.isna(pop_10km):
    validation_status = "FAIL"
    reasons.append("10km population is null/NaN")
elif pop_10km < 0:
    validation_status = "FAIL"
    reasons.append("10km population is negative")

if pop_5km is not None and pop_10km is not None and pop_10km < pop_5km:
    validation_status = "FAIL"
    reasons.append("10km population < 5km population")

# 7. Write to CSV
csv_data = [{
    "station_id": station_id,
    "station_name": station_name,
    "city": city,
    "state": state,
    "latitude": lat,
    "longitude": lon,
    "ghsl_dataset": dataset_id,
    "ghsl_year": 2025,
    "ghsl_resolution_m": 100,
    "population_band": "population_count",
    "buffer_km": 5,
    "population_estimate": pop_5km,
    "extraction_method": "ee.Reducer.sum() on geodesic buffer"
}, {
    "station_id": station_id,
    "station_name": station_name,
    "city": city,
    "state": state,
    "latitude": lat,
    "longitude": lon,
    "ghsl_dataset": dataset_id,
    "ghsl_year": 2025,
    "ghsl_resolution_m": 100,
    "population_band": "population_count",
    "buffer_km": 10,
    "population_estimate": pop_10km,
    "extraction_method": "ee.Reducer.sum() on geodesic buffer"
}]

df = pd.DataFrame(csv_data)
df.to_csv('data/processed/exposure/ghsl_pilot_station.csv', index=False)

# 8. Write Report
report_md = f"""# GHSL Population Extraction Pilot Report

**Station**: {station_id} ({station_name})
**Coordinates**: {lat}, {lon}
**Extraction Timestamp**: {datetime.datetime.now(datetime.timezone.utc).isoformat()}

## Earth Engine Query Details
- **Dataset ID**: `{dataset_id}`
- **Band**: `population_count`
- **Year Selected**: 2025
- **Resolution**: 100 m
- **Buffer Construction**: Geodesic buffers (`ee.Geometry.Point().buffer()`) in WGS-84

## Population Results
- **5 km Buffer Population**: {pop_5km}
- **10 km Buffer Population**: {pop_10km}

## Validation Checks
- **Validation Status**: **{validation_status}**
- **Checks Performed**:
  - Population is numeric: {'PASS' if pop_5km is not None else 'FAIL'}
  - Population >= 0: {'PASS' if pop_5km >= 0 else 'FAIL'}
  - 10 km population >= 5 km population: {'PASS' if pop_10km >= pop_5km else 'FAIL'}
  - Extraction uses 2025 GHSL layer: PASS (Filtered by `system:index` = '2025')
  - Extraction uses 100 m layer: PASS (`scale=100` specified in reducer)
- **Failure Reasons**: {', '.join(reasons) if reasons else 'None'}
"""

with open('reports/exposure/ghsl_pilot_report.md', 'w') as f:
    f.write(report_md)

print(f"Validation status: {validation_status}")
print("Pilot outputs written.")
