"""
Spatial Feature Generator for VayuNet PM2.5 Forecasting (Experiment S2: Wind-Aware).

Computes concurrent spatial neighbor features for each station i at forecast origin t
using other stations' contemporaneous PM2.5 measurements, filtered and weighted by
wind direction and wind speed.

Guarantees:
- Strictly NO future data leakage.
- Self-station exclusion.
- Uses NWP wind forecasts valid at time t.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_FILE = BASE_DIR / "data" / "metadata" / "delhi_station_coordinates.csv"
PROCESSED_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"

SPATIAL_FEATURE_NAMES_S2 = [
    "upwind_pm25_mean",
    "upwind_pm25_max",
    "wind_aligned_pm25_transport",
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points in km using Haversine formula."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2
    )
    return float(2.0 * R * np.arcsin(np.sqrt(a)))


def calculate_initial_compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial compass bearing between two points.
    Returns bearing in degrees from true North.
    Formula: θ = atan2(sin(Δlong).cos(lat2),
                       cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    diff_long = math.radians(lon2 - lon1)

    x = math.sin(diff_long) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - (math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_long))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return float(compass_bearing)


def load_station_coordinates(
    metadata_path: Path = METADATA_FILE,
) -> pd.DataFrame:
    """Load and validate verified Delhi station coordinates metadata."""
    if not metadata_path.exists():
        raise FileNotFoundError(f"Coordinates file not found at {metadata_path}")

    df = pd.read_csv(metadata_path)
    required_cols = ["station_id", "latitude", "longitude"]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Required column '{col}' missing from {metadata_path}")

    return df


def compute_distance_matrix(
    coords_df: pd.DataFrame,
) -> Tuple[Dict[str, List[str]], Dict[str, List[float]], Dict[Tuple[str, str], float]]:
    """
    Compute pairwise Haversine distance matrix and ordered neighbors for each station.
    """
    stations = coords_df["station_id"].tolist()
    coords_map = {
        row["station_id"]: (float(row["latitude"]), float(row["longitude"]))
        for _, row in coords_df.iterrows()
    }

    dist_matrix: Dict[Tuple[str, str], float] = {}
    for s1 in stations:
        lat1, lon1 = coords_map[s1]
        for s2 in stations:
            lat2, lon2 = coords_map[s2]
            dist_matrix[(s1, s2)] = haversine_distance(lat1, lon1, lat2, lon2)

    neighbor_order: Dict[str, List[str]] = {}
    neighbor_dists: Dict[str, List[float]] = {}
    for s in stations:
        others = [o for o in stations if o != s]
        others_sorted = sorted(others, key=lambda o: dist_matrix[(s, o)])
        neighbor_order[s] = others_sorted
        neighbor_dists[s] = [dist_matrix[(s, o)] for o in others_sorted]

    return neighbor_order, neighbor_dists, dist_matrix


def compute_bearing_matrix(
    coords_df: pd.DataFrame,
) -> Dict[Tuple[str, str], float]:
    """
    Compute initial compass bearing from station1 to station2.
    Dict maps (source, target) -> bearing in degrees.
    """
    stations = coords_df["station_id"].tolist()
    coords_map = {
        row["station_id"]: (float(row["latitude"]), float(row["longitude"]))
        for _, row in coords_df.iterrows()
    }

    bearing_matrix: Dict[Tuple[str, str], float] = {}
    for source in stations:
        lat1, lon1 = coords_map[source]
        for target in stations:
            if source != target:
                lat2, lon2 = coords_map[target]
                bearing_matrix[(source, target)] = calculate_initial_compass_bearing(lat1, lon1, lat2, lon2)
            
    return bearing_matrix


def add_spatial_features(
    df: pd.DataFrame,
    coords_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Add Experiment S2 (wind-aware) spatial neighbor features to a Delhi forecasting DataFrame.
    """
    if coords_df is None:
        coords_df = load_station_coordinates()

    ts_col = "timestamp" if "timestamp" in df.columns else "Timestamp"
    if ts_col not in df.columns or "station_id" not in df.columns or "PM2.5" not in df.columns:
        raise ValueError(f"DataFrame must contain '{ts_col}', 'station_id', and 'PM2.5' columns.")
    if "wind_direction_10m" not in df.columns:
        raise ValueError(f"DataFrame must contain wind_direction_10m column.")

    stations = coords_df["station_id"].tolist()
    neighbor_order, neighbor_dists, dist_matrix = compute_distance_matrix(coords_df)
    bearing_matrix = compute_bearing_matrix(coords_df)

    pivot_pm25 = df.pivot_table(
        index=ts_col,
        columns="station_id",
        values="PM2.5",
        aggfunc="first",
    )
    pivot_wd = df.pivot_table(
        index=ts_col,
        columns="station_id",
        values="wind_direction_10m",
        aggfunc="first",
    )
    
    for s in stations:
        if s not in pivot_pm25.columns:
            pivot_pm25[s] = np.nan
        if s not in pivot_wd.columns:
            pivot_wd[s] = np.nan

    spatial_dfs = []
    
    for target in stations:
        others = neighbor_order[target]
        wd_target = pivot_wd[target].values
        
        # Wind blowing TOWARDS direction
        wind_to = (wd_target + 180) % 360
        
        N_timestamps = len(pivot_pm25)
        
        upwind_means = np.full(N_timestamps, np.nan)
        upwind_maxs = np.full(N_timestamps, np.nan)
        aligned_transports = np.full(N_timestamps, np.nan)
        
        # Calculate arrays per neighbor
        pm25_others = []
        cos_alpha_d_others = []
        is_upwind_others = []
        
        for source in others:
            dist = dist_matrix[(source, target)]
            bearing = bearing_matrix[(source, target)]
            pm25 = pivot_pm25[source].values
            
            alpha = np.abs(wind_to - bearing)
            alpha = np.where(alpha > 180, 360 - alpha, alpha)
            
            is_upwind = (alpha <= 45.0)
            
            # cosine alignment
            alpha_rad = np.radians(alpha)
            cos_alpha = np.cos(alpha_rad)
            cos_alpha_pos = np.clip(cos_alpha, 0, None)
            
            weight = cos_alpha_pos / dist
            
            pm25_others.append(pm25)
            is_upwind_others.append(is_upwind)
            cos_alpha_d_others.append(weight)
            
        pm25_others = np.array(pm25_others).T # shape (N_timestamps, 9)
        is_upwind_others = np.array(is_upwind_others).T
        cos_alpha_d_others = np.array(cos_alpha_d_others).T
        
        # Calculate upwind mean and max
        upwind_pm25 = np.where(is_upwind_others, pm25_others, np.nan)
        with np.errstate(all="ignore"):
            upwind_means = np.nanmean(upwind_pm25, axis=1)
            upwind_maxs = np.nanmax(upwind_pm25, axis=1)
            
            # Calculate wind aligned transport
            valid_mask = ~np.isnan(pm25_others)
            weights_matrix = valid_mask * cos_alpha_d_others
            weights_sum = np.sum(weights_matrix, axis=1)
            weighted_sum = np.nansum(pm25_others * cos_alpha_d_others, axis=1)
            aligned_transports = np.where(weights_sum > 0, weighted_sum / weights_sum, np.nan)

        st_feature_df = pd.DataFrame(
            {
                ts_col: pivot_pm25.index,
                "station_id": target,
                "upwind_pm25_mean": upwind_means,
                "upwind_pm25_max": upwind_maxs,
                "wind_aligned_pm25_transport": aligned_transports,
            }
        )
        spatial_dfs.append(st_feature_df)

    all_spatial_df = pd.concat(spatial_dfs, ignore_index=True)

    orig_cols = list(df.columns)
    merged_df = pd.merge(df, all_spatial_df, on=[ts_col, "station_id"], how="left")

    if len(merged_df) != len(df):
        raise RuntimeError(
            f"Row count mismatch after spatial merge: original={len(df)}, merged={len(merged_df)}"
        )

    for col in orig_cols:
        assert col in merged_df.columns, f"Original column '{col}' missing after merge!"

    return merged_df


def get_spatial_feature_names() -> List[str]:
    """Return list of Experiment S2 spatial feature column names."""
    return list(SPATIAL_FEATURE_NAMES_S2)
