"""
Build S7 causal FIRMS features.
Implements distance, temporal rolling, and wind-aligned transport features.
Ensures strict T_available <= T causality.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
FIRMS_FILE = BASE_DIR / "data/raw/firms_viirs.csv"
S5_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
OUTPUT_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s7_firms.csv"

DELHI_LAT = 28.6139
DELHI_LON = 77.2090

def haversine_vectorized(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def bearing_vectorized(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    initial_bearing = np.arctan2(x, y)
    initial_bearing = np.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

def process_firms():
    print("Loading FIRMS data...")
    df = pd.read_csv(FIRMS_FILE, dtype={'version': str, 'type': str})

    if 'confidence' in df.columns and df['confidence'].dtype == object:
        df = df[df['confidence'].isin(['n', 'h', 'N', 'H'])].copy()

    print("Parsing timestamps...")
    acq_time_str = df['acq_time'].astype(str).str.zfill(4)
    dt_str = df['acq_date'] + ' ' + acq_time_str
    df['T_obs'] = pd.to_datetime(dt_str, format='%Y-%m-%d %H%M', errors='coerce')
    df = df.dropna(subset=['T_obs']).copy()

    # 3-hour latency
    df['T_available'] = df['T_obs'] + pd.Timedelta(hours=3)
    df['T_avail_hour'] = df['T_available'].dt.floor('h')

    print("Computing distances and bearings...")
    df['distance'] = haversine_vectorized(DELHI_LAT, DELHI_LON, df['latitude'], df['longitude'])
    df['bearing'] = bearing_vectorized(DELHI_LAT, DELHI_LON, df['latitude'], df['longitude'])
    df['bearing_int'] = df['bearing'].round().astype(int) % 360

    df['radius_bin'] = np.where(df['distance'] <= 100, 'r100',
                       np.where(df['distance'] <= 200, 'r200',
                       np.where(df['distance'] <= 300, 'r300', 'out')))

    df = df[df['radius_bin'] != 'out'].copy()
    df['frp'] = pd.to_numeric(df['frp'], errors='coerce').fillna(0)

    return df

def build_features(fires_df, s5_df):
    print("Building hourly grid...")
    min_t = fires_df['T_avail_hour'].min()
    max_t = s5_df['timestamp'].max()

    grid = pd.DataFrame({'T_avail_hour': pd.date_range(start=min_t, end=max_t, freq='h')})
    grid.set_index('T_avail_hour', inplace=True)

    print("Aggregating base features...")
    base_agg = fires_df.groupby(['T_avail_hour', 'radius_bin'])['frp'].agg(['count', 'sum', 'max']).unstack()
    if isinstance(base_agg.columns, pd.MultiIndex):
        base_agg.columns = [f"{col[1]}_{col[0]}" for col in base_agg.columns]

    grid = grid.join(base_agg).fillna(0)

    print("Rolling base features...")
    windows = [24, 48, 72]
    features_list = []

    for w in windows:
        roll = grid.rolling(window=w, min_periods=1).sum()
        max_cols = [c for c in grid.columns if 'max' in c]
        if max_cols:
            roll[max_cols] = grid[max_cols].rolling(window=w, min_periods=1).max()
        roll.columns = [f"firms_{c}_{w}h" for c in roll.columns]
        features_list.append(roll)

    grid_rolled = pd.concat(features_list, axis=1)

    print("Building wind-aligned arrays...")
    wind_features = {}
    radii = ['r100', 'r200', 'r300']

    for r in radii:
        r_fires = fires_df[fires_df['radius_bin'] == r]
        pivot_sum = r_fires.groupby(['T_avail_hour', 'bearing_int'])['frp'].sum().unstack(fill_value=0)
        pivot_count = r_fires.groupby(['T_avail_hour', 'bearing_int'])['frp'].count().unstack(fill_value=0)

        for deg in range(360):
            if deg not in pivot_sum.columns:
                pivot_sum[deg] = 0
                pivot_count[deg] = 0

        pivot_sum = pivot_sum[range(360)].reindex(grid.index, fill_value=0)
        pivot_count = pivot_count[range(360)].reindex(grid.index, fill_value=0)

        arr_sum = pivot_sum.values
        arr_count = pivot_count.values

        for w in windows:
            wind_features[f"{r}_sum_{w}h"] = pd.DataFrame(arr_sum).rolling(window=w, min_periods=1).sum().values
            wind_features[f"{r}_count_{w}h"] = pd.DataFrame(arr_count).rolling(window=w, min_periods=1).sum().values

    print("Extracting S7 features for S5 rows...")
    s5_timestamps = s5_df['timestamp']
    grid_idx_map = {ts: i for i, ts in enumerate(grid.index)}

    s7_data = {'timestamp': s5_timestamps}

    for col in grid_rolled.columns:
        s7_data[col] = grid_rolled[col].reindex(s5_timestamps).values

    horizons = [6, 24, 72]

    for H in horizons:
        wind_col = f'nwp_wind_direction_10m_{H}h'
        if wind_col not in s5_df.columns:
            continue

        wind_dirs = s5_df[wind_col].values

        for w in windows:
            for r in radii:
                arr_sum = wind_features[f"{r}_sum_{w}h"]
                arr_count = wind_features[f"{r}_count_{w}h"]

                res_sum = np.zeros(len(s5_df))
                res_count = np.zeros(len(s5_df))

                for i, ts in enumerate(s5_timestamps):
                    wdir = wind_dirs[i]
                    if np.isnan(wdir):
                        continue
                    grid_i = grid_idx_map.get(ts)
                    if grid_i is None:
                        continue

                    wdir_int = int(round(wdir)) % 360
                    deg_min = wdir_int - 45
                    deg_max = wdir_int + 45

                    if deg_min < 0:
                        s = np.sum(arr_sum[grid_i, deg_min:]) + np.sum(arr_sum[grid_i, :deg_max+1])
                        c = np.sum(arr_count[grid_i, deg_min:]) + np.sum(arr_count[grid_i, :deg_max+1])
                    elif deg_max > 359:
                        s = np.sum(arr_sum[grid_i, deg_min:]) + np.sum(arr_sum[grid_i, :deg_max-359])
                        c = np.sum(arr_count[grid_i, deg_min:]) + np.sum(arr_count[grid_i, :deg_max-359])
                    else:
                        s = np.sum(arr_sum[grid_i, deg_min:deg_max+1])
                        c = np.sum(arr_count[grid_i, deg_min:deg_max+1])

                    res_sum[i] = s
                    res_count[i] = c

                s7_data[f"firms_upwind_{r}_sum_{w}h_{H}h_horizon"] = res_sum
                s7_data[f"firms_upwind_{r}_count_{w}h_{H}h_horizon"] = res_count

    s7_df = pd.DataFrame(s7_data)

    print(f"Saving S7 features to {OUTPUT_FILE}")
    s7_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Generated {len(s7_df.columns)-1} S7 features for {len(s7_df)} rows.")

def main():
    print("=" * 80)
    print("BUILDING S7 CAUSAL FIRMS FEATURES")
    print("=" * 80)

    start_time = time.time()

    s5_df = pd.read_csv(S5_FILE, parse_dates=['timestamp'])
    fires_df = process_firms()
    build_features(fires_df, s5_df)

    print(f"Done in {time.time()-start_time:.1f}s")

if __name__ == "__main__":
    main()
