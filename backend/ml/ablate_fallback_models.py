import json
import warnings
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DATA_S5 = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"
DATA_EPISODE = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_episode.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports" / "fallback_ablation"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

VALID_START = pd.Timestamp("2024-10-01 13:00:00")
TEST_START = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

EPISODE_FEATURES = [
    "pm25_delta_1h", "pm25_delta_3h", "pm25_delta_6h", "pm25_delta_12h", "pm25_delta_24h",
    "pm25_acceleration_1h", "pm25_acceleration_3h", "pm25_acceleration_6h",
    "pm25_mean_6h", "pm25_mean_12h", "pm25_mean_24h", "pm25_std_6h", "pm25_std_24h",
    "pm25_max_6h", "pm25_max_24h", "hours_since_150_onset", "hours_since_250_onset",
    "hours_above_150_24h", "hours_above_250_24h", "fraction_above_150_24h", "fraction_above_250_24h",
]

# Strict Base (S1): PM2.5 history + time + coordinates
S1_FEATURES = [
    "PM2.5", "PM2.5_lag_1h", "PM2.5_lag_3h", "PM2.5_lag_6h", "PM2.5_lag_12h",
    "PM2.5_lag_24h", "PM2.5_lag_48h", "PM2.5_lag_72h",
    "PM2.5_roll_mean_6h", "PM2.5_roll_mean_24h", "PM2.5_roll_std_24h",
    "hour", "day_of_week", "day_of_year", "month", "is_weekend",
    "station_id_anand vihar", "station_id_aya nagar", "station_id_bawana",
    "station_id_ito", "station_id_jahangirpuri", "station_id_narela",
    "station_id_punjabi bagh", "station_id_r k puram", "station_id_vivek vihar",
    "station_id_wazirpur"
]

def load_data() -> pd.DataFrame:
    print("Loading data...")
    s5 = pd.read_csv(DATA_S5)
    episode = pd.read_csv(DATA_EPISODE)
    s5["timestamp"] = pd.to_datetime(s5["timestamp"])
    episode["timestamp"] = pd.to_datetime(episode["timestamp"])
    keys = ["timestamp", "station_id"]

    episode_extra = [c for c in episode.columns if c not in s5.columns]
    merged = s5.merge(episode[keys + episode_extra], on=keys, how="left", validate="one_to_one")
    return merged.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

def train_model(df, features, target_col):
    params = {
        'n_estimators': 300,
        'learning_rate': 0.05,
        'max_depth': 8,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'tree_method': 'hist',
        'random_state': 42,
        'n_jobs': -1
    }

    train_mask = df["timestamp"] < VALID_START
    X_train = df.loc[train_mask, features]
    y_train = df.loc[train_mask, target_col]

    valid_train = X_train.notna().any(axis=1) & y_train.notna()

    model = XGBRegressor(**params)
    t0 = time.time()
    model.fit(X_train[valid_train], y_train[valid_train])
    fit_time = time.time() - t0

    return model, fit_time

def evaluate(model, df, features, target_col):
    test_mask = (df["timestamp"] >= TEST_START) & (df["timestamp"] <= TEST_END)

    X_test = df.loc[test_mask, features]
    y_test = df.loc[test_mask, target_col]

    valid_test = X_test.notna().any(axis=1) & y_test.notna()

    y = y_test[valid_test].to_numpy()
    p = model.predict(X_test[valid_test])

    mae = mean_absolute_error(y, p)
    rmse = np.sqrt(mean_squared_error(y, p))
    r2 = r2_score(y, p)
    bias = np.mean(p - y)

    y_150 = (y >= 150).astype(int)
    p_150 = (p >= 150).astype(int)
    from sklearn.metrics import recall_score
    rec_150 = recall_score(y_150, p_150, zero_division=0)

    y_250 = (y >= 250).astype(int)
    p_250 = (p >= 250).astype(int)
    rec_250 = recall_score(y_250, p_250, zero_division=0)

    timestamps = df.loc[test_mask, "timestamp"][valid_test]
    winter_mask = (timestamps >= "2025-11-01") & (timestamps < "2026-02-01")
    if winter_mask.any():
        winter_mae = mean_absolute_error(y[winter_mask], p[winter_mask])
    else:
        winter_mae = np.nan

    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Bias": bias,
        "Recall>=150": rec_150,
        "Recall>=250": rec_250,
        "Winter MAE": winter_mae
    }

def get_frozen_features(model_path):
    m = joblib.load(model_path)
    if hasattr(m, "feature_names_in_"): return list(m.feature_names_in_)
    return list(m.get_booster().feature_names)

def main():
    df = load_data()

    champions = {
        6: MODEL_DIR / "xgb_vayunet_pm25_6h_s6_production.joblib",
        24: MODEL_DIR / "xgb_vayunet_pm25_24h_s5_production.joblib",
        72: MODEL_DIR / "xgb_vayunet_pm25_72h_s6_production.joblib"
    }

    results = []

    for h in [6, 24, 72]:
        print(f"\nEvaluating Horizon {h}h...")
        target = f"target_pm25_{h}h"
        champ_path = champions[h]

        champ_model = joblib.load(champ_path)
        champ_features = get_frozen_features(champ_path)
        print(f"  Evaluating Frozen Champion (features: {len(champ_features)})...")
        champ_metrics = evaluate(champ_model, df, champ_features, target)
        champ_metrics["Model"] = f"S{6 if h in [6,72] else 5} Champion"
        champ_metrics["Horizon"] = f"{h}h"
        champ_metrics["TrainTime"] = 0.0
        results.append(champ_metrics)

        if h in [6, 72]:
            s5_features = [f for f in champ_features if f not in EPISODE_FEATURES]
            print(f"  Training S5 Fallback (features: {len(s5_features)})...")
            s5_model, s5_time = train_model(df, s5_features, target)
            s5_metrics = evaluate(s5_model, df, s5_features, target)
            s5_metrics["Model"] = "S5 Fallback (No Episode)"
            s5_metrics["Horizon"] = f"{h}h"
            s5_metrics["TrainTime"] = s5_time
            results.append(s5_metrics)

        s1_feats = [f for f in S1_FEATURES if f in df.columns]
        print(f"  Training S1 Fallback (features: {len(s1_feats)})...")
        s1_model, s1_time = train_model(df, s1_feats, target)
        s1_metrics = evaluate(s1_model, df, s1_feats, target)
        s1_metrics["Model"] = "S1 Fallback (Base Only)"
        s1_metrics["Horizon"] = f"{h}h"
        s1_metrics["TrainTime"] = s1_time
        results.append(s1_metrics)

    res_df = pd.DataFrame(results)
    cols = ["Horizon", "Model", "MAE", "RMSE", "R2", "Bias", "Recall>=150", "Recall>=250", "Winter MAE", "TrainTime"]
    res_df = res_df[cols]

    print("\n=========================================================================")
    print("FALLBACK ABLATION RESULTS (TEST SET: 2025-08-30 to 2026-08-31)")
    print("=========================================================================\n")
    print(res_df.to_string(index=False, float_format="%.3f"))

    res_df.to_csv(REPORT_DIR / "fallback_ablation_metrics.csv", index=False)
    print(f"\nSaved full results to {REPORT_DIR / 'fallback_ablation_metrics.csv'}")

if __name__ == "__main__":
    main()
