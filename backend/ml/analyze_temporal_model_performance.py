import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

# ============================================================
# Temporal Model Performance Audit
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_S5 = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"
DATA_EPISODE = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_episode.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports" / "temporal_performance"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

HORIZONS = {
    6: {
        "target": "target_pm25_6h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_6h_s6_production.joblib",
    },
    24: {
        "target": "target_pm25_24h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_24h_s5_production.joblib",
    },
    72: {
        "target": "target_pm25_72h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_72h_s6_production.joblib",
    },
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

def generate_predictions(df, horizon, cfg):
    model = joblib.load(cfg["model"])
    base_features = get_base_features(model)
    X = df[base_features]
    pred = np.full(len(df), np.nan, dtype=float)
    valid_rows = X.notna().any(axis=1)
    if valid_rows.any():
        pred[valid_rows.to_numpy()] = model.predict(X.loc[valid_rows])
    return pred

def get_season(month):
    if month in [12, 1, 2]: return 'Winter'
    elif month in [3, 4, 5]: return 'Summer'
    elif month in [6, 7, 8, 9]: return 'Monsoon'
    else: return 'Post-Monsoon'

def get_regime(val):
    if val < 60: return '<60'
    elif val < 150: return '60-150'
    elif val < 250: return '150-250'
    else: return '>=250'

def calculate_metrics(group, target_col, pred_col):
    valid = group.dropna(subset=[target_col, pred_col])
    if len(valid) == 0:
        return np.nan, np.nan, np.nan, 0
    y = valid[target_col]
    p = valid[pred_col]
    mae = mean_absolute_error(y, p)
    rmse = np.sqrt(mean_squared_error(y, p))
    bias = np.mean(p - y)
    return mae, rmse, bias, len(valid)

def generate_report(test_df):
    metrics_by_month = []
    metrics_by_season = []
    metrics_by_hour = []
    metrics_by_regime = []

    # Pre-calculate grouping columns
    test_df['month_str'] = test_df['timestamp'].dt.strftime('%Y-%m')
    test_df['month'] = test_df['timestamp'].dt.month
    test_df['season'] = test_df['month'].apply(get_season)
    test_df['hour'] = test_df['timestamp'].dt.hour

    # Evaluate each horizon
    horizons = [6, 24, 72]

    def process_grouping(group_col, output_list, sort_keys=None):
        grouped = test_df.groupby(group_col)
        for name, group in grouped:
            row = {group_col: name}
            for h in horizons:
                target = f"target_pm25_{h}h"
                pred = f"pred_{h}h"
                mae, rmse, bias, count = calculate_metrics(group, target, pred)
                row[f"{h}h MAE"] = mae
                row[f"{h}h RMSE"] = rmse
                row[f"{h}h Bias"] = bias
                row[f"{h}h Count"] = count
            output_list.append(row)

    process_grouping('month_str', metrics_by_month)
    process_grouping('season', metrics_by_season)
    process_grouping('hour', metrics_by_hour)

    # Regime (based on actual PM2.5 of the target)
    for h in horizons:
        target = f"target_pm25_{h}h"
        test_df[f"regime_{h}h"] = test_df[target].apply(lambda x: get_regime(x) if pd.notna(x) else np.nan)

    # For regime, we need to do it slightly differently because each horizon has its own regime
    regimes = ['<60', '60-150', '150-250', '>=250']
    for r in regimes:
        row = {'regime': r}
        for h in horizons:
            target = f"target_pm25_{h}h"
            pred = f"pred_{h}h"
            group = test_df[test_df[f"regime_{h}h"] == r]
            mae, rmse, bias, count = calculate_metrics(group, target, pred)
            row[f"{h}h MAE"] = mae
            row[f"{h}h RMSE"] = rmse
            row[f"{h}h Bias"] = bias
            row[f"{h}h Count"] = count
        metrics_by_regime.append(row)

    df_month = pd.DataFrame(metrics_by_month).sort_values('month_str')

    # Custom sort for season
    season_order = {'Winter': 0, 'Summer': 1, 'Monsoon': 2, 'Post-Monsoon': 3}
    df_season = pd.DataFrame(metrics_by_season)
    df_season['order'] = df_season['season'].map(season_order)
    df_season = df_season.sort_values('order').drop('order', axis=1)

    df_hour = pd.DataFrame(metrics_by_hour).sort_values('hour')
    df_regime = pd.DataFrame(metrics_by_regime)

    # Save CSVs
    df_month.to_csv(REPORT_DIR / "temporal_performance_by_month.csv", index=False)
    df_season.to_csv(REPORT_DIR / "temporal_performance_by_season.csv", index=False)
    df_hour.to_csv(REPORT_DIR / "temporal_performance_by_hour.csv", index=False)
    df_regime.to_csv(REPORT_DIR / "temporal_performance_regimes.csv", index=False)

    # Rolling 30-day
    # Sort by timestamp
    test_df_sorted = test_df.sort_values('timestamp')
    rolling_metrics = []

    # Since we have multiple stations, we group by daily frequency across all stations
    daily = test_df_sorted.set_index('timestamp').resample('D')

    # This is a bit tricky to do rolling RMSE correctly (not mean of daily RMSE).
    # We will just iterate over days and take the window
    dates = pd.date_range(test_df['timestamp'].min().normalize(), test_df['timestamp'].max().normalize())

    for dt in dates:
        start = dt - pd.Timedelta(days=30)
        end = dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        window = test_df[(test_df['timestamp'] >= start) & (test_df['timestamp'] <= end)]

        row = {'date': dt.strftime('%Y-%m-%d')}
        for h in horizons:
            target = f"target_pm25_{h}h"
            pred = f"pred_{h}h"
            mae, rmse, bias, count = calculate_metrics(window, target, pred)
            row[f"{h}h MAE"] = mae
            row[f"{h}h RMSE"] = rmse
        rolling_metrics.append(row)

    df_rolling = pd.DataFrame(rolling_metrics)
    df_rolling.to_csv(REPORT_DIR / "temporal_performance_rolling.csv", index=False)

    # Markdown Report
    with open(REPORT_DIR / "temporal_performance_report.md", "w", encoding="utf-8") as f:
        f.write("# Temporal Performance Audit\n\n")
        f.write("Evaluation on untouched test set: 2025-08-30 to 2026-08-31\n\n")

        f.write("## 1. Performance by Month\n\n```text\n")
        f.write(df_month.to_string(index=False, float_format="%.2f"))
        f.write("\n```\n\n")

        f.write("## 2. Performance by Season\n\n```text\n")
        f.write(df_season.to_string(index=False, float_format="%.2f"))
        f.write("\n```\n\n")

        f.write("## 3. Performance by Regime\n\n```text\n")
        f.write(df_regime.to_string(index=False, float_format="%.2f"))
        f.write("\n```\n\n")

    print(f"\nSaved CSVs and report to {REPORT_DIR}")

    print("\nSummary by Month:")
    print(df_month[['month_str', '6h MAE', '6h RMSE', '24h MAE', '24h RMSE', '72h MAE', '72h RMSE']].to_string(index=False, float_format="%.2f"))
    print("\nSummary by Season:")
    print(df_season[['season', '6h MAE', '6h RMSE', '24h MAE', '24h RMSE', '72h MAE', '72h RMSE']].to_string(index=False, float_format="%.2f"))
    print("\nSummary by Regime:")
    print(df_regime[['regime', '6h Bias', '24h Bias', '72h Bias']].to_string(index=False, float_format="%.2f"))

def main():
    print("Loading data...")
    df = load_data()

    # Create test mask
    test_mask = (df["timestamp"] >= VALID_END) & (df["timestamp"] <= TEST_END)
    test_df = df[test_mask].copy()

    for horizon, cfg in HORIZONS.items():
        print(f"Generating predictions for {horizon}h...")
        pred = generate_predictions(df, horizon, cfg)
        test_df[f"pred_{horizon}h"] = pred[test_mask]

    print("Calculating temporal metrics...")
    generate_report(test_df)

if __name__ == "__main__":
    main()
