"""
Analyze weather-enhanced XGBoost models vs baseline.
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
MODELS_DIR = BASE_DIR / "models"
WEATHER_FEATURES_FILE = MODELS_DIR / "xgb_weather_feature_metadata.json"
BASELINE_FEATURES_FILE = MODELS_DIR / "features.json"

REPORTS_DIR = BASE_DIR / "reports" / "weather_model_analysis"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}
HORIZONS = ["6h", "24h", "72h"]

REGIME_BINS = [
    ("LOW", 0, 60),
    ("MODERATE", 60, 120),
    ("HIGH", 120, 250),
    ("SEVERE", 250, np.inf),
]

OPEN_METEO_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "boundary_layer_height"
]

def load_data():
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["timestamp"])
    if 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)

    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)

    with open(WEATHER_FEATURES_FILE, "r") as f:
        weather_feature_cols = json.load(f)
        
    with open(BASELINE_FEATURES_FILE, "r") as f:
        baseline_feature_cols = json.load(f)

    n = len(df_encoded)
    train_end = int(n * 0.70)
    val_end = train_end + int(n * 0.15)
    test_df = df_encoded.iloc[val_end:].copy()

    return test_df, weather_feature_cols, baseline_feature_cols

def regime_label(val):
    for name, lo, hi in REGIME_BINS:
        if lo <= val < hi:
            return name
    return "SEVERE"

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    test_df, wf_cols, bf_cols = load_data()
    
    weather_models = {h: joblib.load(MODELS_DIR / f"xgb_weather_pm25_{h}.joblib") for h in HORIZONS}
    baseline_models = {h: joblib.load(MODELS_DIR / f"xgb_pm25_{h}.joblib") for h in HORIZONS}
    
    summary_lines = []
    def log(msg, also_print=True):
        if also_print:
            print(msg)
        summary_lines.append(msg)
        
    log("======================================================================")
    log("WEATHER MODEL ANALYSIS")
    log("======================================================================")
    log(f"Test period : {test_df['Timestamp'].min()} to {test_df['Timestamp'].max()}")
    log(f"Test rows   : {len(test_df)}")
    
    # Pre-calculate predictions
    preds_weather = {}
    preds_baseline = {}
    actuals = {}
    masks = {}
    
    X_test_w = test_df[wf_cols]
    X_test_b = test_df[bf_cols]
    
    for h in HORIZONS:
        y = test_df[TARGETS[h]]
        m = y.notna()
        preds_weather[h] = weather_models[h].predict(X_test_w)
        preds_baseline[h] = baseline_models[h].predict(X_test_b)
        actuals[h] = y
        masks[h] = m

    log("\n" + "="*70)
    log("1. FEATURE IMPORTANCE")
    log("="*70)
    
    om_contribution_by_horizon = {}
    
    for h in HORIZONS:
        log(f"\n--- Horizon: {h} ---")
        booster = weather_models[h].get_booster()
        gain_scores = booster.get_score(importance_type="gain")
        weight_scores = booster.get_score(importance_type="weight")
        cover_scores = booster.get_score(importance_type="cover")
        
        # Map internal fN back to actual features
        def map_fn(f_name):
            if f_name.startswith('f') and f_name[1:].isdigit():
                idx = int(f_name[1:])
                if idx < len(wf_cols):
                    return wf_cols[idx]
            return f_name
            
        imp_data = []
        for fn_internal in gain_scores.keys():
            feat = map_fn(fn_internal)
            g = gain_scores.get(fn_internal, 0)
            w = weight_scores.get(fn_internal, 0)
            c = cover_scores.get(fn_internal, 0)
            imp_data.append({"feature": feat, "gain": g, "weight": w, "cover": c})
            
        df_imp = pd.DataFrame(imp_data).sort_values("gain", ascending=False).reset_index(drop=True)
        # Re-rank after dropping
        df_imp["rank"] = df_imp.index + 1
        
        df_imp.to_csv(REPORTS_DIR / f"feature_importance_{h}.csv", index=False)
        
        log("Top 25 Features by Gain:")
        for i, row in df_imp.head(25).iterrows():
            log(f"  {row['rank']:2d}. {row['feature']:25s} gain={row['gain']:8.2f} (w={row['weight']})")
            
        log("\nOpen-Meteo Features Rank & Importance:")
        om_gain_total = 0
        total_gain = df_imp["gain"].sum()
        for omf in OPEN_METEO_FEATURES:
            row = df_imp[df_imp["feature"] == omf]
            if not row.empty:
                r = row.iloc[0]
                log(f"  {r['rank']:2d}. {r['feature']:25s} gain={r['gain']:8.2f} ({(r['gain']/total_gain)*100:5.2f}%)")
                om_gain_total += r['gain']
            else:
                log(f"  --. {omf:25s} gain=    0.00 ( 0.00%)")
                
        cpcb_gain_total = total_gain - om_gain_total
        om_pct = (om_gain_total / total_gain) * 100 if total_gain > 0 else 0
        cpcb_pct = (cpcb_gain_total / total_gain) * 100 if total_gain > 0 else 0
        
        log(f"\nGrouped Contribution ({h}):")
        log(f"  CPCB features   : total_gain = {cpcb_gain_total:10.2f} ({cpcb_pct:.2f}%)")
        log(f"  Open-Meteo      : total_gain = {om_gain_total:10.2f} ({om_pct:.2f}%)")
        
        om_contribution_by_horizon[h] = om_pct
        
    log("\n" + "="*70)
    log("2. COMPARING WEATHER CONTRIBUTION BY HORIZON")
    log("="*70)
    for h in HORIZONS:
        log(f"  {h} : {om_contribution_by_horizon[h]:.2f}% of model gain from Open-Meteo features")

    log("\n" + "="*70)
    log("3. REGIME COMPARISON (Baseline vs Weather)")
    log("="*70)
    
    regime_results = []
    
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_pw = preds_weather[h][m]
        y_pb = preds_baseline[h][m]
        labels = np.array([regime_label(v) for v in y_t])
        
        log(f"\n--- Horizon: {h} ---")
        log(f"  {'Regime':10s} | {'N':>6s} | {'BaseMAE':>8s} | {'WeatMAE':>8s} | {'BaseRMSE':>9s} | {'WeatRMSE':>9s} | {'BaseBias':>9s} | {'WeatBias':>9s}")
        
        for rname, _, _ in REGIME_BINS:
            sel = labels == rname
            if sel.sum() == 0:
                continue
            
            n_val = int(sel.sum())
            b_mae = mean_absolute_error(y_t[sel], y_pb[sel])
            w_mae = mean_absolute_error(y_t[sel], y_pw[sel])
            b_rmse = np.sqrt(mean_squared_error(y_t[sel], y_pb[sel]))
            w_rmse = np.sqrt(mean_squared_error(y_t[sel], y_pw[sel]))
            b_bias = float(np.mean(y_pb[sel] - y_t[sel]))
            w_bias = float(np.mean(y_pw[sel] - y_t[sel]))
            
            log(f"  {rname:10s} | {n_val:6d} | {b_mae:8.2f} | {w_mae:8.2f} | {b_rmse:9.2f} | {w_rmse:9.2f} | {b_bias:9.2f} | {w_bias:9.2f}")
            
            regime_results.append({
                "horizon": h, "regime": rname, "n": n_val,
                "baseline_mae": b_mae, "weather_mae": w_mae,
                "baseline_rmse": b_rmse, "weather_rmse": w_rmse,
                "baseline_bias": b_bias, "weather_bias": w_bias
            })
            
    df_reg = pd.DataFrame(regime_results)
    df_reg.to_csv(REPORTS_DIR / "regime_comparison.csv", index=False)
    
    log("\n" + "="*70)
    log("4. EXTREME POLLUTION (>=250) COMPARISON")
    log("="*70)
    
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        sel = y_t >= 250
        if sel.sum() == 0:
            continue
            
        y_t_ext = y_t[sel]
        y_pb_ext = preds_baseline[h][m][sel]
        y_pw_ext = preds_weather[h][m][sel]
        
        b_mae = mean_absolute_error(y_t_ext, y_pb_ext)
        w_mae = mean_absolute_error(y_t_ext, y_pw_ext)
        b_bias = float(np.mean(y_pb_ext - y_t_ext))
        w_bias = float(np.mean(y_pw_ext - y_t_ext))
        
        log(f"  {h} (n={sel.sum()}): BaseMAE={b_mae:.2f}, WeatherMAE={w_mae:.2f} | BaseBias={b_bias:.2f}, WeatherBias={w_bias:.2f}")

    log("\n" + "="*70)
    log("INTERPRETATION RULES MET")
    log("======================================================================")
    log("- Feature importance is predictive importance, NOT causation.")
    log("- Weather features represent one Delhi reference location, NOT station-specific weather.")
    
    with open(REPORTS_DIR / "summary.txt", "w") as f:
        f.write("\n".join(summary_lines))
        
    print(f"\nAnalysis saved to {REPORTS_DIR}")

if __name__ == "__main__":
    main()
