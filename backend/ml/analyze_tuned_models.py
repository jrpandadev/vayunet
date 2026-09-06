import os
import sys
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, precision_score, recall_score

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
MODELS_DIR = BASE_DIR / "models"
HORIZON_METADATA_FILE = MODELS_DIR / "horizon_features.json"
REPORTS_DIR = BASE_DIR / "reports" / "tuned_model_analysis"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}
HORIZONS = ["6h", "24h", "72h"]

REGIME_BINS = [
    ("GOOD_SAT", 0, 60),
    ("MODERATE", 60, 150),
    ("POOR_VPOOR", 150, 250),
    ("SEVERE", 250, np.inf),
]

def load_data():
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["timestamp"])
    if 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)
    
    with open(HORIZON_METADATA_FILE, "r") as f:
        horizon_features = json.load(f)["horizon_features"]
        
    val_end = pd.to_datetime("2025-08-30 15:00:00")
    test_end = pd.to_datetime("2026-08-31 23:00:00")
    
    test_df = df_encoded[(df_encoded["Timestamp"] >= val_end) & (df_encoded["Timestamp"] <= test_end)].copy()
    
    # We also need the original df with station_id for episode tracking
    test_df_raw = df[(df["Timestamp"] >= val_end) & (df["Timestamp"] <= test_end)].copy()
    
    return test_df, test_df_raw, horizon_features

def regime_label(val):
    for name, lo, hi in REGIME_BINS:
        if lo <= val < hi:
            return name
    return "SEVERE"

def evaluate_predictions(y_true, y_pred):
    err = y_pred - y_true
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "Bias": float(np.mean(err)),
        "MedAE": float(np.median(np.abs(err))),
    }

def extract_episodes(df, pm25_col="PM2.5", threshold=150, min_hours=12):
    """Find episodes of PM2.5 >= threshold for >= min_hours continuous hours per station."""
    episodes = []
    
    for station, group in df.groupby("station_id"):
        group = group.sort_values("Timestamp").reset_index()
        
        is_high = (group[pm25_col] >= threshold).astype(int)
        
        # Identify continuous blocks
        block_ids = (is_high != is_high.shift(1)).cumsum()
        
        for block_id, block_data in group.groupby(block_ids):
            if block_data[pm25_col].iloc[0] >= threshold and len(block_data) >= min_hours:
                episodes.append({
                    "station_id": station,
                    "start": block_data["Timestamp"].min(),
                    "end": block_data["Timestamp"].max(),
                    "duration_hours": len(block_data),
                    "peak_actual": block_data[pm25_col].max(),
                    "indices": block_data.index.tolist(),
                    "original_indices": block_data["index"].tolist()
                })
    return episodes

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    test_df, test_df_raw, horizon_features = load_data()
    
    models = {h: joblib.load(MODELS_DIR / f"xgb_weather_pm25_{h}_tuned.joblib") for h in HORIZONS}
    
    summary_lines = []
    def log(msg, also_print=True):
        if also_print: print(msg)
        summary_lines.append(msg)
        
    log("======================================================================")
    log("TUNED MODEL ANALYSIS: EXTREME POLLUTION & REGIMES")
    log("======================================================================")
    
    preds = {}
    actuals = {}
    masks = {}
    
    for h in HORIZONS:
        y = test_df[TARGETS[h]]
        m = y.notna()
        X = test_df[horizon_features[h]]
        preds[h] = models[h].predict(X)
        actuals[h] = y
        masks[h] = m
        
        # Add predictions back to the raw DataFrame for episode tracking
        test_df_raw[f"pred_{h}"] = np.nan
        test_df_raw.loc[m, f"pred_{h}"] = preds[h][m]
        test_df_raw.loc[m, f"actual_{h}"] = y[m]

    # 1. OVERALL METRICS
    log("\n1. OVERALL METRICS")
    log("----------------------------------------------------------------------")
    for h in HORIZONS:
        m = masks[h]
        metrics = evaluate_predictions(actuals[h][m], preds[h][m])
        log(f"Horizon {h:3s} | MAE: {metrics['MAE']:.2f} | RMSE: {metrics['RMSE']:.2f} | R²: {metrics['R2']:.3f} | Bias: {metrics['Bias']:.2f} | MedAE: {metrics['MedAE']:.2f}")

    # 2. POLLUTION REGIMES
    log("\n2. POLLUTION REGIMES")
    log("----------------------------------------------------------------------")
    
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        labels = np.array([regime_label(v) for v in y_t])
        
        log(f"\n--- Horizon: {h} ---")
        log(f"{'Regime':12s} | {'N':>6s} | {'MAE':>8s} | {'RMSE':>8s} | {'Bias':>8s}")
        for rname, _, _ in REGIME_BINS:
            sel = labels == rname
            if sel.sum() == 0: continue
            
            n_val = int(sel.sum())
            r_mae = mean_absolute_error(y_t[sel], y_p[sel])
            r_rmse = np.sqrt(mean_squared_error(y_t[sel], y_p[sel]))
            r_bias = float(np.mean(y_p[sel] - y_t[sel]))
            log(f"{rname:12s} | {n_val:6d} | {r_mae:8.2f} | {r_rmse:8.2f} | {r_bias:8.2f}")

    # 3. EXTREME EVENT PERFORMANCE
    log("\n3. EXTREME EVENT PERFORMANCE")
    log("----------------------------------------------------------------------")
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        
        log(f"\n--- Horizon: {h} ---")
        for threshold in [150, 250]:
            sel = y_t >= threshold
            n_val = int(sel.sum())
            if n_val == 0: continue
            
            r_mae = mean_absolute_error(y_t[sel], y_p[sel])
            r_rmse = np.sqrt(mean_squared_error(y_t[sel], y_p[sel]))
            r_bias = float(np.mean(y_p[sel] - y_t[sel]))
            pct_above_150 = np.mean(y_p[sel] >= 150) * 100
            
            log(f"Actual >= {threshold:3d} | N: {n_val:5d} | MAE: {r_mae:6.2f} | RMSE: {r_rmse:6.2f} | Bias: {r_bias:7.2f} | Predicted >= 150: {pct_above_150:5.1f}%")
            
        # Classification metrics for >= 150
        y_true_cls = (y_t >= 150).astype(int)
        y_pred_cls = (y_p >= 150).astype(int)
        precision = precision_score(y_true_cls, y_pred_cls, zero_division=0)
        recall = recall_score(y_true_cls, y_pred_cls, zero_division=0)
        log(f"Classification Metrics (Threshold 150) -> Precision: {precision:.3f}, Recall: {recall:.3f}")

    # 4. CONTINUOUS POLLUTION EPISODES
    log("\n4. CONTINUOUS POLLUTION EPISODES (>=150 µg/m³ for >=12 hours)")
    log("----------------------------------------------------------------------")
    
    # We will use PM2.5 column to detect episodes, but to evaluate forecasting, 
    # we should ideally look at the target variable for each horizon.
    # However, "PM2.5 >= 150 for 12 hours" usually applies to the current PM2.5.
    # We'll detect episodes on current PM2.5, and see how well the models forecasted the peak of those episodes.
    episodes = extract_episodes(test_df_raw, pm25_col="PM2.5", threshold=150, min_hours=12)
    
    log(f"Total continuous episodes detected in test period: {len(episodes)}")
    
    if episodes:
        for h in HORIZONS:
            anticipated_count = 0
            peak_actuals = []
            peak_preds = []
            underpreds = []
            
            for ep in episodes:
                # Extract the horizon's actuals and preds during this episode
                # Note: target_pm25_6h is the PM2.5 6 hours in the future.
                # So if we want to see if the 6h model anticipated this episode,
                # we look at the predictions made *for* this episode time window.
                # That means looking at the target_pm25_6h and pred_6h for rows where the Timestamp is inside the episode.
                
                # To get predictions *for* this episode window from the model, we actually need to look at rows 
                # where the target timestamp falls in the episode. Since our rows are indexed by the *prediction time*,
                # target_pm25_6h is PM2.5 at Timestamp + 6h.
                # So the model's prediction *for* time T is pred_6h at row T - 6h.
                # To simplify, we already have target_pm25_6h and pred_6h on the row T-6h, representing the value at T.
                # Let's just find the max pred_6h for rows where actual_6h is part of the episode.
                
                # Actually, an easier way: test_df_raw already aligns actual_h and pred_h.
                # Wait, actual_h on row t is the PM2.5 at t+h. 
                # So the "actual" PM2.5 at t+h corresponds to some time in the episode.
                # Let's just use the episode's original_indices to slice the data.
                ep_data = test_df_raw.loc[ep["original_indices"]]
                
                # Did the model predict >= 150 for this time period?
                # The PM2.5 values in ep_data["PM2.5"] are >= 150.
                # Which predictions were made FOR these times?
                # For horizon 6h, the prediction made at T-6h is pred_6h[T-6h].
                # We can just look up the target_pm25_6h and pred_6h where target timestamp falls in the episode.
                # But calculating that perfectly is tricky. Instead, let's look at the predictions made *during* the episode.
                # Wait, the prompt says "how many the model anticipates". That means prediction *for* the episode.
                
                # Let's shift the predictions forward by horizon to align with observation time.
                h_hours = int(h.replace('h', ''))
                
                # We can align by Timestamp.
                # Create a temporary series of predictions indexed by their target time.
                target_times = test_df_raw["Timestamp"] + pd.Timedelta(hours=h_hours)
                preds_for_target = pd.Series(test_df_raw[f"pred_{h}"].values, index=target_times)
                
                # Now filter preds_for_target for times within the episode
                ep_preds = preds_for_target.loc[(preds_for_target.index >= ep["start"]) & (preds_for_target.index <= ep["end"])]
                
                if len(ep_preds) == 0 or ep_preds.isna().all():
                    continue
                    
                peak_pred = ep_preds.max()
                peak_actual = ep["peak_actual"]
                
                if peak_pred >= 150:
                    anticipated_count += 1
                    
                peak_actuals.append(peak_actual)
                peak_preds.append(peak_pred)
                underpreds.append(peak_actual - peak_pred)
                
            anticipation_rate = anticipated_count / len(episodes) * 100
            avg_peak_actual = np.mean(peak_actuals) if peak_actuals else 0
            avg_peak_pred = np.mean(peak_preds) if peak_preds else 0
            avg_underpred = np.mean(underpreds) if underpreds else 0
            
            log(f"\n  Horizon: {h}")
            log(f"    Anticipated (Predicted peak >= 150): {anticipated_count}/{len(episodes)} ({anticipation_rate:.1f}%)")
            log(f"    Average Peak Actual                : {avg_peak_actual:.1f} µg/m³")
            log(f"    Average Peak Predicted             : {avg_peak_pred:.1f} µg/m³")
            log(f"    Average Peak Underprediction       : {avg_underpred:.1f} µg/m³")

    with open(REPORTS_DIR / "extreme_pollution_analysis.txt", "w") as f:
        f.write("\n".join(summary_lines))
        
    print(f"\nAnalysis saved to {REPORTS_DIR}")

if __name__ == "__main__":
    main()
