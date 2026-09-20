import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# ============================================================
# S8-B3 — Alert Persistence / Deduplication
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_S5 = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"
DATA_EPISODE = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_episode.csv"
MODEL_DIR = ROOT / "models"

SEED = 42
EXTREME_THRESHOLD = 250.0

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

HORIZONS = {
    6: {
        "target": "target_pm25_6h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_6h_s6_production.joblib",
        "buckets": [1, 3, 6]
    },
    24: {
        "target": "target_pm25_24h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_24h_s5_production.joblib",
        "buckets": [6, 12, 24]
    }
}

EPISODE_FEATURES = [
    "pm25_delta_1h", "pm25_delta_3h", "pm25_delta_6h", "pm25_delta_12h", "pm25_delta_24h",
    "pm25_acceleration_1h", "pm25_acceleration_3h", "pm25_acceleration_6h",
    "pm25_mean_6h", "pm25_mean_12h", "pm25_mean_24h", "pm25_std_6h", "pm25_std_24h",
    "pm25_max_6h", "pm25_max_24h", "hours_since_150_onset", "hours_since_250_onset",
    "hours_above_150_24h", "hours_above_250_24h", "fraction_above_150_24h", "fraction_above_250_24h",
]

def load_data() -> pd.DataFrame:
    s5 = pd.read_csv(DATA_S5)
    episode = pd.read_csv(DATA_EPISODE)
    s5["timestamp"] = pd.to_datetime(s5["timestamp"])
    episode["timestamp"] = pd.to_datetime(episode["timestamp"])
    keys = ["timestamp", "station_id"]
    episode_extra = [c for c in EPISODE_FEATURES if c in episode.columns and c not in s5.columns]
    merged = s5.merge(episode[keys + episode_extra], on=keys, how="left", validate="one_to_one")
    return merged.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

def get_base_features(model) -> list[str]:
    if hasattr(model, "feature_names_in_"): return list(model.feature_names_in_)
    return list(model.get_booster().feature_names)

def get_events(df, test_start, test_end):
    events = []
    df = df.sort_values(["station_id", "timestamp"]).copy()
    for station, group in df.groupby("station_id"):
        group = group.set_index("timestamp").sort_index()
        is_severe = group["PM2.5"] >= EXTREME_THRESHOLD
        is_severe_shifted = is_severe.shift(1, fill_value=False)
        onset_mask = is_severe & ~is_severe_shifted
        onset_times = group.index[onset_mask]
        for t_onset in onset_times:
            if test_start <= t_onset <= test_end:
                events.append({"station_id": station, "t_onset": t_onset})
    return pd.DataFrame(events)

def evaluate_binary_simple(y_true, probability, threshold):
    predicted = probability >= threshold
    from sklearn.metrics import precision_score, recall_score, f1_score
    return {
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
    }

def threshold_search(y_true, probability):
    thresholds = [x/100.0 for x in range(5, 96, 5)]
    results = []
    for t in thresholds:
        r = evaluate_binary_simple(y_true, probability, t)
        r["threshold"] = t
        results.append(r)
    eligible = [r for r in results if r["precision"] >= 0.40]
    if eligible:
        best = max(eligible, key=lambda r: (r["recall"], r["f1"], r["precision"]))
    else:
        best = max(results, key=lambda r: (r["f1"], r["recall"]))
    return best["threshold"]

def get_alert_episodes(alert_series, target_series):
    shifted = alert_series.shift(1, fill_value=False)
    onset_mask = alert_series & ~shifted
    episode_id = onset_mask.cumsum()
    active_rows = alert_series == True

    if not active_rows.any():
        return 0, 0, 0

    episodes = []
    for ep_id, group in target_series[active_rows].groupby(episode_id[active_rows]):
        is_true = (group >= EXTREME_THRESHOLD).any()
        episodes.append(is_true)

    total = len(episodes)
    n_true = sum(episodes)
    n_false = total - n_true
    return total, n_true, n_false

def apply_policies(pred_series):
    pred = pred_series.astype(int)
    pol_a = pred == 1
    pol_b = (pred == 1) & (pred.shift(1, fill_value=0) == 1)
    pol_c = (pred == 1) & (pred.shift(1, fill_value=0) == 1) & (pred.shift(2, fill_value=0) == 1)
    pol_d = pred.rolling(3, min_periods=1).sum() >= 2
    return {"Policy A": pol_a, "Policy B": pol_b, "Policy C": pol_c, "Policy D": pol_d}

def run_horizon_analysis(df, horizon, cfg):
    print(f"\n{'='*72}\nHORIZON: {horizon}h\n{'='*72}")
    target = cfg["target"]

    # 1. Base prediction
    model_prod = joblib.load(cfg["model"])
    base_features = get_base_features(model_prod)
    pred = np.full(len(df), np.nan, dtype=float)
    X_base = df[base_features]
    valid_rows = X_base.notna().any(axis=1)
    if valid_rows.any():
        pred[valid_rows.to_numpy()] = model_prod.predict(X_base.loc[valid_rows])

    pred_col = f"prod_pred_{horizon}h"
    df = df.copy()
    df[pred_col] = pred

    # 2. Gate B features
    features = list(dict.fromkeys([pred_col] + EPISODE_FEATURES))

    # 3. Splits
    valid_target = df[target].notna()
    train_mask = valid_target & (df["timestamp"] < TRAIN_END) & df[pred_col].notna()
    valid_mask = valid_target & (df["timestamp"] >= TRAIN_END) & (df["timestamp"] < VALID_END) & df[pred_col].notna()
    test_mask = valid_target & (df["timestamp"] >= VALID_END) & (df["timestamp"] <= TEST_END) & df[pred_col].notna()

    X_train = df.loc[train_mask, features]
    y_train = (df.loc[train_mask, target] >= EXTREME_THRESHOLD).astype(np.int8)

    X_valid = df.loc[valid_mask, features]
    y_valid = (df.loc[valid_mask, target] >= EXTREME_THRESHOLD).astype(np.int8)

    X_test = df.loc[test_mask, features]
    y_test = (df.loc[test_mask, target] >= EXTREME_THRESHOLD).astype(np.int8)

    train_usable = X_train.notna().any(axis=1)
    X_train = X_train.loc[train_usable]
    y_train = y_train[train_usable]

    valid_usable = X_valid.notna().any(axis=1)
    X_valid = X_valid.loc[valid_usable]
    y_valid = y_valid[valid_usable]

    test_usable = X_test.notna().any(axis=1)
    X_test = X_test.loc[test_usable]
    y_test = y_test[test_usable]

    # 4. Train model
    positives = int(y_train.sum())
    negatives = int(len(y_train) - positives)
    model = XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.03, min_child_weight=5,
        subsample=0.9, colsample_bytree=0.8, reg_lambda=1.0, objective="binary:logistic",
        eval_metric="aucpr", tree_method="hist", device="cuda", random_state=SEED,
        scale_pos_weight=negatives/positives, n_jobs=1
    )
    model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)

    # 5. Threshold
    valid_prob = model.predict_proba(X_valid)[:, 1]
    best_thresh = threshold_search(y_valid, valid_prob)

    # 6. Test Predictions
    test_prob = model.predict_proba(X_test)[:, 1]
    test_pred_bool = test_prob >= best_thresh

    # 7. Persistence Evaluation
    df_test_full = df.loc[test_mask].copy()
    df_test_full["predicted_bool"] = False
    df_test_full.loc[X_test.index, "predicted_bool"] = test_pred_bool
    df_test_full["target_actual"] = df_test_full[target]

    events_df = get_events(df, VALID_END, TEST_END)

    df_test_full = df_test_full.sort_values(["station_id", "timestamp"])

    policies_results = {"Policy A": [], "Policy B": [], "Policy C": [], "Policy D": []}
    for station, group in df_test_full.groupby("station_id"):
        pols = apply_policies(group["predicted_bool"])
        for pol_name, pol_series in pols.items():
            policies_results[pol_name].append(pol_series)

    for pol_name in policies_results:
        df_test_full[pol_name] = pd.concat(policies_results[pol_name])

    df_test_indexed = df_test_full.set_index(["station_id", "timestamp"]).sort_index()

    for pol_name in ["Policy A", "Policy B", "Policy C", "Policy D"]:
        print(f"\n{'-'*60}")
        print(f"{pol_name}")
        print(f"{'-'*60}")

        total_eps = 0
        true_eps = 0
        false_eps = 0

        for station, group in df_test_full.groupby("station_id"):
            tot, tr, fa = get_alert_episodes(group[pol_name], group["target_actual"])
            total_eps += tot
            true_eps += tr
            false_eps += fa

        print(f"Total alert episodes : {total_eps}")
        print(f"True alert episodes  : {true_eps}")
        print(f"False alert episodes : {false_eps}")

        # Lead time evaluation
        event_lead_times = []
        for _, row in events_df.iterrows():
            station = row["station_id"]
            t_onset = row["t_onset"]

            t_start = t_onset - pd.Timedelta(hours=horizon)
            t_end = t_onset - pd.Timedelta(hours=1)

            try:
                preds = df_test_indexed.loc[station].loc[t_start:t_end]
            except KeyError:
                event_lead_times.append(None)
                continue

            alarms = preds[preds[pol_name] == True]
            if len(alarms) > 0:
                earliest_alarm = alarms.index.min()
                lt = (t_onset - earliest_alarm).total_seconds() / 3600.0
                event_lead_times.append(lt)
            else:
                event_lead_times.append(None)

        total_events = len(events_df)
        detected_all = [lt for lt in event_lead_times if lt is not None]
        n_detected_all = len(detected_all)
        n_missed_all = total_events - n_detected_all
        det_rate_all = n_detected_all / total_events if total_events > 0 else 0.0

        fa_per_event = false_eps / n_detected_all if n_detected_all > 0 else 0.0

        print(f"\nDetection Metrics:")
        print(f"Total physical severe events: {total_events}")
        print(f"Detected severe events      : {n_detected_all}")
        print(f"Missed severe events        : {n_missed_all}")
        print(f"Event detection rate        : {det_rate_all:.4f}")
        print(f"False alerts / detected ev  : {fa_per_event:.4f}")

        for b in cfg["buckets"]:
            detected_lts = [lt for lt in event_lead_times if lt is not None and lt >= b]
            n_det = len(detected_lts)

            if n_det > 0:
                med_lt = np.median(detected_lts)
                mean_lt = np.mean(detected_lts)
                p25_lt = np.percentile(detected_lts, 25)
                min_lt = np.min(detected_lts)
                max_lt = np.max(detected_lts)
            else:
                med_lt = mean_lt = p25_lt = min_lt = max_lt = 0.0

            print(f"\n  Bucket: >={b}h before onset")
            print(f"    Detected            : {n_det}")
            print(f"    Median lead time    : {med_lt:.1f}h")
            print(f"    Mean lead time      : {mean_lt:.1f}h")
            print(f"    25th pctl lead time : {p25_lt:.1f}h")
            print(f"    Min/Max lead time   : {min_lt:.1f}h / {max_lt:.1f}h")

def main():
    print("Loading data...")
    df = load_data()
    for horizon in [6, 24]:
        run_horizon_analysis(df, horizon, HORIZONS[horizon])

if __name__ == "__main__":
    main()
