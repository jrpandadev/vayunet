import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DATA_S5 = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"
DATA_EPISODE = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_episode.csv"
MODEL_DIR = ROOT / "models"

def load_data() -> pd.DataFrame:
    s5 = pd.read_csv(DATA_S5)
    episode = pd.read_csv(DATA_EPISODE)
    s5["timestamp"] = pd.to_datetime(s5["timestamp"])
    episode["timestamp"] = pd.to_datetime(episode["timestamp"])
    keys = ["timestamp", "station_id"]

    episode_extra = [c for c in episode.columns if c not in s5.columns]
    merged = s5.merge(episode[keys + episode_extra], on=keys, how="left", validate="one_to_one")
    return merged.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

def generate_predictions(df):
    cfg = {
        "model": MODEL_DIR / "xgb_vayunet_pm25_24h_s5_production.joblib"
    }
    model = joblib.load(cfg["model"])
    if hasattr(model, "feature_names_in_"):
        base_features = list(model.feature_names_in_)
    else:
        base_features = list(model.get_booster().feature_names)

    X = df[base_features]
    pred = np.full(len(df), np.nan, dtype=float)
    valid_rows = X.notna().any(axis=1)
    if valid_rows.any():
        pred[valid_rows.to_numpy()] = model.predict(X.loc[valid_rows])
    return pred

def compare_periods():
    print("Loading data...")
    df = load_data()
    df["pred_24h"] = generate_predictions(df)

    winter_mask = (df["timestamp"] >= "2025-11-01") & (df["timestamp"] < "2026-02-01")
    summer_mask = (df["timestamp"] >= "2026-05-01") & (df["timestamp"] < "2026-07-01")

    winter_df = df[winter_mask]
    summer_df = df[summer_mask]

    def analyze_period(d):
        res = {}
        y = d["target_pm25_24h"].dropna()
        p = d["pred_24h"].dropna()

        res["Actual PM2.5 Mean"] = y.mean()
        res["Actual PM2.5 Median"] = y.median()
        res["Actual PM2.5 95th"] = np.percentile(y, 95) if len(y) else np.nan
        res["Actual PM2.5 99th"] = np.percentile(y, 99) if len(y) else np.nan

        res["Pred PM2.5 Mean"] = p.mean()
        res["Pred PM2.5 Median"] = p.median()
        res["Pred PM2.5 95th"] = np.percentile(p, 95) if len(p) else np.nan
        res["Pred PM2.5 99th"] = np.percentile(p, 99) if len(p) else np.nan

        res["Freq >= 150"] = (y >= 150).mean()
        res["Freq >= 250"] = (y >= 250).mean()

        if "nwp_temperature_2m_24h" in d:
            res["Temp Mean (C)"] = d["nwp_temperature_2m_24h"].mean()
        if "nwp_relative_humidity_2m_24h" in d:
            res["RH Mean (%)"] = d["nwp_relative_humidity_2m_24h"].mean()
        if "nwp_wind_speed_10m_24h" in d:
            res["Wind Speed Mean (m/s)"] = d["nwp_wind_speed_10m_24h"].mean()
        if "nwp_wind_direction_10m_24h" in d:
            res["Wind Dir Mean (deg)"] = d["nwp_wind_direction_10m_24h"].mean()
        if "nwp_boundary_layer_height_24h" in d:
            res["PBL Height Mean (m)"] = d["nwp_boundary_layer_height_24h"].mean()

        nwp_cols = [c for c in d.columns if c.startswith("nwp_")]
        if nwp_cols:
            res["NWP Avail %"] = d[nwp_cols].notna().all(axis=1).mean() * 100

        sat_cols = [c for c in d.columns if c.startswith("satellite_")]
        if sat_cols:
            res["Satellite Avail %"] = d[sat_cols].notna().any(axis=1).mean() * 100

        pm10_cols = [c for c in d.columns if "PM10" in c]
        if pm10_cols:
            res["PM10 Avail %"] = d[pm10_cols].notna().any(axis=1).mean() * 100

        ep_cols = [c for c in d.columns if "pm25_delta" in c or "hours_since" in c]
        if ep_cols:
            res["Episode Avail %"] = d[ep_cols].notna().any(axis=1).mean() * 100

        return res

    w_stats = analyze_period(winter_df)
    s_stats = analyze_period(summer_df)

    comp = pd.DataFrame([w_stats, s_stats], index=["Winter (Nov-Jan)", "Summer (May-Jun)"]).T

    print("\n============================================================")
    print("WINTER ERROR AUDIT")
    print("============================================================\n")
    print(comp.to_string(float_format="%.2f"))

if __name__ == "__main__":
    compare_periods()
