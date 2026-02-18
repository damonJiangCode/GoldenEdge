"""Build baseline ML features/labels for R01_V1."""

from pathlib import Path
import argparse
import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "signal_side",
    "rsi_t",
    "rsi_t1",
    "rsi_t2",
    "rsi_slope_1",
    "rsi_slope_2",
    "is_in_range_t",
    "atr_t",
    "bb_width_t",
    "close_minus_ema_t",
    "dist_to_range_upper_t",
    "dist_to_range_lower_t",
    "touch_upper_flag_t",
    "touch_lower_flag_t",
    "rsi_overbought_flag_t",
    "rsi_oversold_flag_t",
    "body_t",
    "range_t",
    "upper_wick_t",
    "lower_wick_t",
    "close_pos_t",
    "ret_1_t",
    "vol_z_t",
]

# --- STRATEGY CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
YEAR = 2017
INPUT_FILE = PROJECT_ROOT / "data" / "backtest_results" / f"R01_V1_{YEAR}.csv"
FEATURES_OUT_FILE = (
    PROJECT_ROOT / "data" / "ml" / "features" / f"R01_V1_{YEAR}_features.csv"
)
LABELS_OUT_FILE = PROJECT_ROOT / "data" / "ml" / "labels" / f"R01_V1_{YEAR}_labels.csv"


def load_backtest_data(input_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    for col in ["signal_time", "entry_time", "exit_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df


def build_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["label_win"] = (out["net_pnl"] > 0).astype(int)
    out["label_net_pnl"] = out["net_pnl"].astype(float)

    sl_dist = (out["entry_price"] - out["sl_price"]).abs()
    out["label_r"] = np.where(sl_dist > 0, out["net_pnl"] / sl_dist, np.nan)
    return out


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing feature columns: {missing}")

    x = df[FEATURE_COLUMNS].copy()
    x = x.replace([np.inf, -np.inf], np.nan)
    x = x.ffill().bfill().fillna(0.0)
    return x


def scale_features_time_aware(
    x: pd.DataFrame, train_ratio: float = 0.7
) -> tuple[pd.DataFrame, int]:
    split_idx = int(len(x) * train_ratio)
    x_train = x.iloc[:split_idx].copy()

    numeric_cols = x_train.select_dtypes(include=["number"]).columns.tolist()
    mu = x_train[numeric_cols].mean()
    sigma = x_train[numeric_cols].std(ddof=0).replace(0, 1.0)

    x_scaled = x.copy()
    x_scaled[numeric_cols] = (x_scaled[numeric_cols] - mu) / sigma
    return x_scaled, split_idx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate R01_V1 ML feature/label datasets."
    )
    parser.add_argument("--input", type=Path, help="Path to backtest csv.")
    parser.add_argument(
        "--features-out", type=Path, help="Path for output features csv."
    )
    parser.add_argument("--labels-out", type=Path, help="Path for output labels csv.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_csv = args.input or INPUT_FILE
    features_out = args.features_out or FEATURES_OUT_FILE
    labels_out = args.labels_out or LABELS_OUT_FILE

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Input: {input_csv}")
    print(f"Features out: {features_out}")
    print(f"Labels out: {labels_out}")

    df = load_backtest_data(input_csv)
    print(f"Rows: {len(df)}, Columns: {len(df.columns)}")

    df = build_labels(df)
    y = df[["label_win", "label_net_pnl", "label_r"]].copy()
    print("Label summary:")
    print(y.describe(include="all"))

    x = build_features(df)
    x_scaled, split_idx = scale_features_time_aware(x)
    print(f"Feature matrix shape: {x_scaled.shape}")
    print(f"Train rows: {split_idx}, Test rows: {len(x_scaled) - split_idx}")

    features_out.parent.mkdir(parents=True, exist_ok=True)
    labels_out.parent.mkdir(parents=True, exist_ok=True)
    x_scaled.to_csv(features_out, index=False)
    y.to_csv(labels_out, index=False)

    print(f"Saved features -> {features_out}")
    print(f"Saved labels   -> {labels_out}")


if __name__ == "__main__":
    main()
