import pandas as pd
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent

    # File paths
    s0_path = base_dir / "reports" / "final_weather_evaluation" / "tuned_models_final_test_results.csv"
    s3_path = base_dir / "reports" / "satellite" / "s3_final_test_results.csv"
    s4_path = base_dir / "reports" / "satellite" / "s4_final_test_results.csv"

    # Read data
    s0_df = pd.read_csv(s0_path)
    s3_df = pd.read_csv(s3_path)
    s4_df = pd.read_csv(s4_path)

    # Process S0
    s0_df = s0_df.rename(columns={
        "Horizon": "horizon",
        "Final Test MAE": "s0_mae",
        "Final Test RMSE": "s0_rmse",
        "Final Test R2": "s0_r2",
        "Final Test Bias": "s0_bias",
        "Final Test MedAE": "s0_medae"
    })
    s0_df = s0_df[["horizon", "s0_mae", "s0_rmse", "s0_r2", "s0_bias", "s0_medae"]]

    # Process S3
    s3_df = s3_df.rename(columns={
        "mae": "s3_mae",
        "rmse": "s3_rmse",
        "r2": "s3_r2",
        "bias": "s3_bias",
        "medae": "s3_medae"
    })
    s3_df = s3_df[["horizon", "s3_mae", "s3_rmse", "s3_r2", "s3_bias", "s3_medae"]]

    # Process S4
    s4_df = s4_df.rename(columns={
        "mae": "s4_mae",
        "rmse": "s4_rmse",
        "r2": "s4_r2",
        "bias": "s4_bias",
        "medae": "s4_medae"
    })
    s4_df = s4_df[["horizon", "s4_mae", "s4_rmse", "s4_r2", "s4_bias", "s4_medae"]]

    # Merge
    merged = s0_df.merge(s3_df, on="horizon").merge(s4_df, on="horizon")

    # Save
    out_path = base_dir / "reports" / "satellite" / "final_model_comparison.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)

    print("=" * 70)
    print("FINAL MODEL COMPARISON (S0 vs S3 vs S4)")
    print("=" * 70)

    for horizon in ["6h", "24h", "72h"]:
        row = merged[merged["horizon"] == horizon].iloc[0]
        print(f"\n{horizon}:")
        print("S0 vs S3 vs S4")
        print(f"MAE:   {row['s0_mae']:.4f} -> {row['s3_mae']:.4f} -> {row['s4_mae']:.4f}")
        print(f"RMSE:  {row['s0_rmse']:.4f} -> {row['s3_rmse']:.4f} -> {row['s4_rmse']:.4f}")
        print(f"R²:    {row['s0_r2']:.4f} -> {row['s3_r2']:.4f} -> {row['s4_r2']:.4f}")
        print(f"Bias:  {row['s0_bias']:.4f} -> {row['s3_bias']:.4f} -> {row['s4_bias']:.4f}")
        print(f"MedAE: {row['s0_medae']:.4f} -> {row['s3_medae']:.4f} -> {row['s4_medae']:.4f}")

    print(f"\nSaved comparison to {out_path}")

if __name__ == "__main__":
    main()
