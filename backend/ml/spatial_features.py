"""
Spatial Feature Generator for VayuNet PM2.5 Forecasting (Experiment S1: No Wind).

Computes concurrent spatial neighbor features for each station i at forecast origin t
using other stations contemporaneous PM2.5 measurements (timestamp t only).

Guarantees:
- Strictly NO future data leakage: only concurrent timestamp t measurements are used.
- Self-station exclusion: a station is never its own neighbor.
- Haversine great-circle distance calculated from official OpenAQ/CPCB station coordinates.
- Preserves original dataset row count and order.

Feature definitions:
- nearest_neighbor_pm25: PM2.5 at the closest other station at time t.
- nearest_neighbor_distance_km: Distance (km) to the closest station.
- neighbor_pm25_mean_2: Mean PM2.5 across the 2 nearest stations at time t.
- neighbor_pm25_mean_3: Mean PM2.5 across the 3 nearest stations at time t.
- neighbor_pm25_max_3: Max PM2.5 across the 3 nearest stations at time t.
- distance_weighted_neighbor_pm25: Inverse-distance-weighted PM2.5 across all valid neighbors at time t.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_FILE = BASE_DIR / "data" / "metadata" / "delhi_station_coordinates.csv"
PROCESSED_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"

SPATIAL_FEATURE_NAMES_S1 = [
    "nearest_neighbor_pm25",
    "nearest_neighbor_distance_km",
    "neighbor_pm25_mean_2",
    "neighbor_pm25_mean_3",
    "neighbor_pm25_max_3",
    "distance_weighted_neighbor_pm25",
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
    Returns:
        neighbor_order: Dict mapping station -> list of other stations sorted by distance (closest first)
        neighbor_dists: Dict mapping station -> list of distances (km) to other stations
        dist_matrix: Dict mapping (station1, station2) -> distance (km)
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


def add_spatial_features(
    df: pd.DataFrame,
    coords_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Add Experiment S1 (no wind) spatial neighbor features to a Delhi forecasting DataFrame.

    Parameters:
        df: DataFrame containing at least 'timestamp', 'station_id', and 'PM2.5' columns.
        coords_df: Optional DataFrame of station coordinates. If None, loaded from METADATA_FILE.

    Returns:
        DataFrame with original columns preserved and spatial feature columns added.
    """
    if coords_df is None:
        coords_df = load_station_coordinates()

    ts_col = "timestamp" if "timestamp" in df.columns else "Timestamp"
    if ts_col not in df.columns or "station_id" not in df.columns or "PM2.5" not in df.columns:
        raise ValueError(f"DataFrame must contain '{ts_col}', 'station_id', and 'PM2.5' columns.")

    stations = coords_df["station_id"].tolist()
    neighbor_order, neighbor_dists, _ = compute_distance_matrix(coords_df)

    pivot_pm25 = df.pivot_table(
        index=ts_col,
        columns="station_id",
        values="PM2.5",
        aggfunc="first",
    )

    for s in stations:
        if s not in pivot_pm25.columns:
            pivot_pm25[s] = np.nan

    spatial_dfs = []
    for s in stations:
        others = neighbor_order[s]
        dists = np.array(neighbor_dists[s], dtype=float)
        inv_dists = 1.0 / dists

        other_vals = pivot_pm25[others].values

        with np.errstate(all="ignore"):
            nn_pm25 = other_vals[:, 0]
            nn_dist = dists[0]

            mean_2 = np.nanmean(other_vals[:, :2], axis=1)
            mean_3 = np.nanmean(other_vals[:, :3], axis=1)

            all_nan_3 = np.isnan(other_vals[:, :3]).all(axis=1)
            max_3 = np.where(all_nan_3, np.nan, np.nanmax(other_vals[:, :3], axis=1))

            valid_mask = ~np.isnan(other_vals)
            weights_matrix = valid_mask * inv_dists
            weights_sum = np.sum(weights_matrix, axis=1)
            weighted_sum = np.nansum(other_vals * inv_dists, axis=1)
            idw = np.where(weights_sum > 0, weighted_sum / weights_sum, np.nan)

        st_feature_df = pd.DataFrame(
            {
                ts_col: pivot_pm25.index,
                "station_id": s,
                "nearest_neighbor_pm25": nn_pm25,
                "nearest_neighbor_distance_km": nn_dist,
                "neighbor_pm25_mean_2": mean_2,
                "neighbor_pm25_mean_3": mean_3,
                "neighbor_pm25_max_3": max_3,
                "distance_weighted_neighbor_pm25": idw,
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
    """Return list of Experiment S1 spatial feature column names."""
    return list(SPATIAL_FEATURE_NAMES_S1)
