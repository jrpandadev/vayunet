"""
Google Earth Engine (Sentinel-5P) Service for VayuNet.
Retrieves Tropospheric NO2 column density & UV Aerosol Index.
Includes graceful fallback if Earth Engine authentication is pending.
"""

import os
import logging
from typing import Dict, Any, Optional

from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("vayunet.satellite")

EE_INITIALIZED = False
GCP_PROJECT = os.getenv("EE_PROJECT_ID", "vayunet-52a15")

def init_earth_engine(project: Optional[str] = None) -> bool:
    global EE_INITIALIZED
    if EE_INITIALIZED:
        return True

    proj = project or GCP_PROJECT
    try:
        import ee
        # Try initializing with local credentials
        ee.Initialize(project=proj)
        EE_INITIALIZED = True
        logger.info(f"Google Earth Engine initialized successfully with project: {proj}")
        return True
    except Exception as e:
        logger.warning(
            f"Earth Engine not initialized ({e}). "
            "Falling back to contextual baseline simulation."
        )
        EE_INITIALIZED = False
        return False


def get_sentinel5p_features(
    lat: float,
    lng: float,
    start_date: str = "2024-01-01",
    end_date: str = "2024-01-07"
) -> Dict[str, Any]:
    """
    Fetch Sentinel-5P NO2 column density and UV Aerosol Index for a given point.
    Returns schema matching docs/schema.json: evidence.satellite
    """
    if init_earth_engine():
        try:
            import ee
            point = ee.Geometry.Point([lng, lat])
            
            # Sentinel-5P OFFL NO2
            no2_col = (
                ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
                .filterBounds(point)
                .filterDate(start_date, end_date)
                .select("tropospheric_NO2_column_number_density")
            )
            
            # Sentinel-5P OFFL Aerosol Index
            aer_col = (
                ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_AER_AI")
                .filterBounds(point)
                .filterDate(start_date, end_date)
                .select("absorbing_aerosol_index")
            )
            
            count = no2_col.size().getInfo()
            if count > 0:
                mean_no2 = no2_col.mean().reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=point,
                    scale=1113.2
                ).getInfo().get("tropospheric_NO2_column_number_density") or 0.0

                mean_aer = aer_col.mean().reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=point,
                    scale=1113.2
                ).getInfo().get("absorbing_aerosol_index") or 0.0

                return {
                    "no2_index": round(float(mean_no2) * 1e6, 2),  # scaled for readability
                    "aerosol_index": round(float(mean_aer), 2),
                    "source": "Sentinel-5P",
                    "freshness": "fresh",
                    "live": True
                }
        except Exception as err:
            logger.warning(f"Live Earth Engine query failed ({err}). Using fallback values.")

    # Contextual / Baseline fallback (e.g. while auth is pending)
    # Scaled to typical urban corridor ranges
    return {
        "no2_index": 18.2,
        "aerosol_index": 1.3,
        "source": "Sentinel-5P",
        "freshness": "contextual",
        "live": False
    }


if __name__ == "__main__":
    print("Testing Satellite Service (Sentinel-5P)...")
    res = get_sentinel5p_features(lat=28.6139, lng=77.2090)
    print("Result:", res)
