from pathlib import Path
import ee
import pandas as pd


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ID = "vayunet-52a15"

STATION_FILE = Path("data/metadata/delhi_station_coordinates.csv")
OUTPUT_FILE = Path("data/raw/satellite/delhi_s5p_no2.csv")

COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"
BAND = "tropospheric_NO2_column_number_density"


# ---------------------------------------------------------------------
# Earth Engine initialization
# ---------------------------------------------------------------------

ee.Initialize(project=PROJECT_ID)


# ---------------------------------------------------------------------
# Load station metadata
# ---------------------------------------------------------------------

stations = pd.read_csv(STATION_FILE)

required_columns = {"station_id", "latitude", "longitude"}

missing = required_columns - set(stations.columns)

if missing:
    raise ValueError(
        f"Station metadata is missing required columns: {sorted(missing)}"
    )

stations = stations[
    ["station_id", "latitude", "longitude"]
].drop_duplicates()

if stations.empty:
    raise ValueError("No station records found.")

print(f"Loaded {len(stations)} stations.")


# ---------------------------------------------------------------------
# Convert stations to an Earth Engine FeatureCollection
# ---------------------------------------------------------------------

features = []

for row in stations.itertuples(index=False):
    point = ee.Geometry.Point([row.longitude, row.latitude])

    feature = ee.Feature(
        point,
        {
            "station_id": str(row.station_id),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
        },
    )

    features.append(feature)

station_fc = ee.FeatureCollection(features)
delhi_bounds = station_fc.geometry().bounds()


# ---------------------------------------------------------------------
# Extract station observations chunked by year & spatially filtered
# ---------------------------------------------------------------------

print("Sentinel-5P collection:", COLLECTION)
print("Band:", BAND)


def extract_for_period(start_str, end_str):
    print(f"Extracting period: {start_str} -> {end_str}...")
    sub_collection = (
        ee.ImageCollection(COLLECTION)
        .filterDate(start_str, end_str)
        .filterBounds(delhi_bounds)
        .select(BAND)
    )

    image_count = sub_collection.size().getInfo()
    print(f"  Images covering Delhi: {image_count}")
    if image_count == 0:
        return pd.DataFrame()

    def extract_image(image):
        timestamp = image.date().format("YYYY-MM-dd'T'HH:mm:ss")
        sampled = image.sampleRegions(
            collection=station_fc,
            properties=["station_id", "latitude", "longitude"],
            scale=1000,
            geometries=False,
        )
        return sampled.map(lambda feature: feature.set("timestamp", timestamp))

    observations = sub_collection.map(extract_image).flatten()
    data = observations.getInfo()

    rows = []
    for feature in data["features"]:
        properties = feature["properties"]
        rows.append(
            {
                "station_id": properties.get("station_id"),
                "timestamp": properties.get("timestamp"),
                "latitude": properties.get("latitude"),
                "longitude": properties.get("longitude"),
                "tropospheric_no2": properties.get(BAND),
            }
        )
    return pd.DataFrame(rows)


years = [
    ("2022-01-01", "2023-01-01"),
    ("2023-01-01", "2024-01-01"),
    ("2024-01-01", "2025-01-01"),
    ("2025-01-01", "2026-01-01"),
    ("2026-01-01", "2026-09-01"),
]

all_dfs = []
for start_p, end_p in years:
    sub_df = extract_for_period(start_p, end_p)
    if not sub_df.empty:
        all_dfs.append(sub_df)

if not all_dfs:
    raise RuntimeError("Earth Engine returned zero station observations.")

df = pd.concat(all_dfs, ignore_index=True)


# ---------------------------------------------------------------------
# Clean / validate basic structure
# ---------------------------------------------------------------------

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce",
    utc=True,
)

df["tropospheric_no2"] = pd.to_numeric(
    df["tropospheric_no2"],
    errors="coerce",
)

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)


# ---------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUTPUT_FILE,
    index=False,
)

print()
print("Extraction complete.")
print(f"Rows: {len(df):,}")
print(f"Stations: {df['station_id'].nunique()}")
print(f"Output: {OUTPUT_FILE}")
print(f"Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(
    f"Valid NO2 observations: "
    f"{df['tropospheric_no2'].notna().sum():,}"
)
print(
    f"Missing NO2 observations: "
    f"{df['tropospheric_no2'].isna().sum():,}"
)
