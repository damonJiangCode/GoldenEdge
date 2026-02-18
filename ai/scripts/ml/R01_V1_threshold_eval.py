"""Evaluate classifier probability thresholds on test-period trade outcomes."""

from __future__ import annotations

from pathlib import Path
import argparse
import pickle

import numpy as np
import pandas as pd

# --- STRATEGY CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
YEAR = 2017
FEATURES_FILE = PROJECT_ROOT / "data" / "ml" / "features" / f"R01_V1_{YEAR}_features.csv"
LABELS_FILE = PROJECT_ROOT / "data" / "ml" / "labels" / f"R01_V1_{YEAR}_labels.csv"
MODEL_FILE = PROJECT_ROOT / "models" / f"R01_V1_{YEAR}" / "classifier.pkl"
OUT_DIR = PROJECT_ROOT / "models" / f"R01_V1_{YEAR}"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate threshold performance for R01_V1 classifier.")
    parser.add_argument("--features", type=Path, help="Path to features csv.")
    parser.add_argument("--labels", type=Path, help="Path to labels csv.")
    parser.add_argument("--model", type=Path, help="Path to classifier.pkl.")
    parser.add_argument("--out-dir", type=Path, help="Output directory for report files.")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Train split ratio used in training.")
    return parser.parse_args()


def preprocess_features(x: pd.DataFrame) -> pd.DataFrame:
    out = pd.get_dummies(x, drop_first=False)
    out = out.replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0.0)
    return out


def profit_factor(series: pd.Series) -> float:
    gross_profit = series[series > 0].sum()
    gross_loss = -series[series < 0].sum()
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def summarize_bucket(df: pd.DataFrame) -> dict:
    trades = int(len(df))
    pnl = df["label_net_pnl"]
    return {
        "trades": trades,
        "win_rate": float(df["label_win"].mean()) if trades else 0.0,
        "total_pnl": float(pnl.sum()) if trades else 0.0,
        "avg_pnl": float(pnl.mean()) if trades else 0.0,
        "profit_factor": profit_factor(pnl) if trades else 0.0,
    }


def main() -> None:
    args = parse_args()
    features_path = args.features or FEATURES_FILE
    labels_path = args.labels or LABELS_FILE
    model_path = args.model or MODEL_FILE
    out_dir = args.out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    x_raw = pd.read_csv(features_path)
    y = pd.read_csv(labels_path)
    if len(x_raw) != len(y):
        raise ValueError(f"Length mismatch: features={len(x_raw)}, labels={len(y)}")

    with model_path.open("rb") as f:
        payload = pickle.load(f)

    model = payload["model"]
    feature_columns = payload["feature_columns"]

    x = preprocess_features(x_raw)
    for col in feature_columns:
        if col not in x.columns:
            x[col] = 0.0
    x = x[feature_columns]

    if not hasattr(model, "predict_proba"):
        raise TypeError("Loaded classifier does not support predict_proba.")

    prob = model.predict_proba(x)[:, 1]

    split_idx = int(len(x) * args.train_ratio)
    eval_df = y.iloc[split_idx:].copy().reset_index(drop=True)
    eval_df["pred_win_prob"] = prob[split_idx:]

    thresholds = np.round(np.arange(0.50, 0.86, 0.05), 2)
    rows: list[dict] = []

    baseline = summarize_bucket(eval_df)
    rows.append(
        {
            "threshold": "all",
            "trade_rate": 1.0,
            **baseline,
        }
    )

    for t in thresholds:
        kept = eval_df[eval_df["pred_win_prob"] >= t]
        stats = summarize_bucket(kept)
        rows.append(
            {
                "threshold": float(t),
                "trade_rate": float(len(kept) / len(eval_df)) if len(eval_df) else 0.0,
                **stats,
            }
        )

    report = pd.DataFrame(rows)
    report_path = out_dir / "threshold_report.csv"
    pred_path = out_dir / "test_predictions.csv"
    report.to_csv(report_path, index=False)
    eval_df.to_csv(pred_path, index=False)

    numeric_thresholds = report[report["threshold"] != "all"].copy()
    best_by_pnl = numeric_thresholds.sort_values("total_pnl", ascending=False).head(1)
    best_by_pf = numeric_thresholds.sort_values("profit_factor", ascending=False).head(1)

    print("Threshold evaluation complete.")
    print(f"Report: {report_path}")
    print(f"Predictions: {pred_path}")
    if not best_by_pnl.empty:
        print("Best by total_pnl:")
        print(best_by_pnl.to_string(index=False))
    if not best_by_pf.empty:
        print("Best by profit_factor:")
        print(best_by_pf.to_string(index=False))


if __name__ == "__main__":
    main()
