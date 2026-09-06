import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
METADATA_FILE = BASE_DIR / 'data' / 'metadata' / 'delhi_station_coordinates.csv'
PROCESSED_FILE = BASE_DIR / 'data' / 'processed' / 'delhi_forecasting_weather.csv'

if not PROCESSED_FILE.exists():
    PROCESSED_FILE = BASE_DIR / 'data' / 'processed' / 'delhi_forecasting.csv'

REQUIRED_COLUMNS = [
    'station_id',
    'station_name',
    'agency',
    'latitude',
    'longitude',
    'coordinate_source',
    'source_year',
]

LAT_MIN, LAT_MAX = 28.3, 28.9
LON_MIN, LON_MAX = 76.8, 77.4


def validate() -> bool:
    print('=' * 70)
    print('VAYUNET STATION COORDINATE METADATA VALIDATOR')
    print('=' * 70)

    passed = True

    # 1. File existence
    print(f'1. Checking file existence: {METADATA_FILE}')
    if not METADATA_FILE.exists():
        print(f'   [FAIL] Metadata file not found at {METADATA_FILE}')
        return False
    print('   [PASS] Metadata file found.')

    df = pd.read_csv(METADATA_FILE)

    # 2. Required columns check
    print('\n2. Checking required columns...')
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        print(f'   [FAIL] Missing columns: {missing_cols}')
        passed = False
    else:
        print(f'   [PASS] All {len(REQUIRED_COLUMNS)} required columns present.')

    # 3. Check for missing values
    print('\n3. Checking for missing / NaN values...')
    null_counts = df[REQUIRED_COLUMNS].isnull().sum().sum() if not missing_cols else 1
    if null_counts > 0:
        print(f'   [FAIL] Found {null_counts} missing value(s) in metadata.')
        passed = False
    else:
        print('   [PASS] Zero missing values detected.')

    # 4. Check for duplicate station_ids
    print('\n4. Checking station_id uniqueness...')
    dups = df['station_id'].duplicated().sum() if 'station_id' in df.columns else 1
    if dups > 0:
        print(f'   [FAIL] Found {dups} duplicate station_id(s).')
        passed = False
    else:
        print(f'   [PASS] All {len(df)} station_ids are unique.')

    # 5. Check for duplicate coordinate pairs
    print('\n5. Checking coordinate pair uniqueness...')
    if 'latitude' in df.columns and 'longitude' in df.columns:
        coord_dups = df.duplicated(subset=['latitude', 'longitude']).sum()
        if coord_dups > 0:
            print(f'   [FAIL] Found {coord_dups} duplicate coordinate pair(s).')
            passed = False
        else:
            print('   [PASS] All coordinate pairs are unique.')

    # 6. Coordinate range check (Delhi Bounding Box)
    print('\n6. Validating coordinate ranges (Delhi Bounding Box: Lat [28.3, 28.9], Lon [76.8, 77.4])...')
    if 'latitude' in df.columns and 'longitude' in df.columns:
        out_of_bounds = df[
            (df['latitude'] < LAT_MIN) | (df['latitude'] > LAT_MAX) |
            (df['longitude'] < LON_MIN) | (df['longitude'] > LON_MAX)
        ]
        if len(out_of_bounds) > 0:
            print(f'   [FAIL] {len(out_of_bounds)} station(s) out of bounds:')
            print(out_of_bounds[['station_id', 'latitude', 'longitude']])
            passed = False
        else:
            print(f'   [PASS] All {len(df)} stations fall within valid Delhi NCR coordinates.')

    # 7. Check alignment with processed dataset
    print(f'\n7. Verifying alignment with dataset: {PROCESSED_FILE.name}...')
    if PROCESSED_FILE.exists():
        data_df = pd.read_csv(PROCESSED_FILE, usecols=['station_id'])
        dataset_stations = set(data_df['station_id'].unique())
        meta_stations = set(df['station_id'].unique()) if 'station_id' in df.columns else set()

        print(f'   Dataset stations count: {len(dataset_stations)}')
        print(f'   Metadata stations count: {len(meta_stations)}')

        diff_meta = dataset_stations - meta_stations
        diff_data = meta_stations - dataset_stations

        if diff_meta or diff_data:
            if diff_meta:
                print(f'   [FAIL] Stations in dataset but missing in metadata: {diff_meta}')
            if diff_data:
                print(f'   [FAIL] Stations in metadata but missing in dataset: {diff_data}')
            passed = False
        else:
            print('   [PASS] Exact station_id match between metadata and dataset.')
    else:
        print('   [WARNING] Processed dataset not found; skipped dataset alignment check.')

    print('\n' + '=' * 70)
    if passed:
        print('OVERALL RESULT: PASS')
        print('Station coordinate metadata is valid and aligned.')
    else:
        print('OVERALL RESULT: FAIL')
        print('Errors detected in station coordinate metadata.')
    print('=' * 70)

    return passed


if __name__ == '__main__':
    success = validate()
    sys.exit(0 if success else 1)
