import argparse
import pickle
from pathlib import Path

import pandas as pd
import talib

# --- STRATEGY CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
YEAR = 2017
INPUT_FILE = PROJECT_ROOT / "data" / "historical" / f"M5_{YEAR}.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "backtest_results" / f"R01_V1_{YEAR}_ml_filtered.csv"
MODEL_FILE = PROJECT_ROOT / "models" / f"R01_V1_{YEAR}" / "classifier.pkl"
INITIAL_BALANCE = 1000.0
LOT_SIZE = 0.01
CONTRACT_SIZE = 100
TP_MULT = 2.0
SL_MULT = 1.0
COMMISSION_PER_TRADE = 0.05  # USD per trade
PROB_THRESHOLD = 0.55

# --- EXECUTION MODEL ---
POINT = 0.01
SPREAD_COLUMN_IS_POINTS = True
FORCE_CLOSE_TIME = "23:55:00"
EPS = 1e-9

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="R01_V1 backtest with ML probability filter.")
    parser.add_argument("--input", type=Path, default=INPUT_FILE, help="Input OHLCV csv path.")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="Output csv path.")
    parser.add_argument("--model", type=Path, default=MODEL_FILE, help="Classifier pickle path.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=PROB_THRESHOLD,
        help="Trade only when predicted win probability >= threshold.",
    )
    return parser.parse_args()


def compute_m5_indicators(df_m5: pd.DataFrame) -> pd.DataFrame:
    df = df_m5.copy()
    df["rsi"] = talib.RSI(df["close"], timeperiod=14)
    df["ema"] = talib.EMA(df["close"], timeperiod=20)
    df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    df["bb_upper"], _, df["bb_lower"] = talib.BBANDS(df["close"], timeperiod=20)

    df["range_upper"] = df["ema"] + (df["atr"] * 1.5)
    df["range_lower"] = df["ema"] - (df["atr"] * 1.5)
    df["is_in_range"] = (df["bb_upper"] - df["bb_lower"]) < (df["atr"] * 5)
    df["vol_ma20"] = df["tick_volume"].rolling(20).mean()
    df["vol_std20"] = df["tick_volume"].rolling(20).std(ddof=0)
    df["vol_z"] = (
        (df["tick_volume"] - df["vol_ma20"])
        / df["vol_std20"].replace(0.0, pd.NA)
    )
    df["vol_z"] = df["vol_z"].fillna(0.0)

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def calc_signal(prev2: pd.Series, prev: pd.Series, curr: pd.Series) -> str | None:
    if not curr["is_in_range"]:
        return None

    rsi_up = prev2["rsi"] < prev["rsi"] < curr["rsi"]
    rsi_down = prev2["rsi"] > prev["rsi"] > curr["rsi"]
    rsi_overbought = prev["rsi"] >= 70 and curr["rsi"] >= 70
    rsi_oversold = prev["rsi"] <= 30 and curr["rsi"] <= 30
    rsi_signal = "short" if rsi_up and rsi_overbought else "long" if rsi_down and rsi_oversold else None

    touch_upper = prev["close"] > prev["range_upper"] and curr["close"] > curr["range_upper"]
    touch_lower = prev["close"] < prev["range_lower"] and curr["close"] < curr["range_lower"]

    if (rsi_signal == "short" and touch_upper) or (rsi_signal == "long" and touch_lower):
        return rsi_signal
    return None


def build_signal_features(prev2: pd.Series, prev: pd.Series, curr: pd.Series, signal: str) -> dict:
    rsi_t = float(curr["rsi"])
    rsi_t1 = float(prev["rsi"])
    rsi_t2 = float(prev2["rsi"])
    bb_width_t = float(curr["bb_upper"] - curr["bb_lower"])
    close_t = float(curr["close"])
    ema_t = float(curr["ema"])
    range_upper_t = float(curr["range_upper"])
    range_lower_t = float(curr["range_lower"])

    touch_upper_flag = int(float(prev["close"]) > float(prev["range_upper"]) and close_t > range_upper_t)
    touch_lower_flag = int(float(prev["close"]) < float(prev["range_lower"]) and close_t < range_lower_t)
    rsi_overbought_flag = int(rsi_t1 >= 70 and rsi_t >= 70)
    rsi_oversold_flag = int(rsi_t1 <= 30 and rsi_t <= 30)

    open_t = float(curr["open"])
    high_t = float(curr["high"])
    low_t = float(curr["low"])
    atr_t = float(curr["atr"])
    body_t = (close_t - open_t) / max(atr_t, EPS)
    range_t = (high_t - low_t) / max(atr_t, EPS)
    upper_wick_t = (high_t - max(open_t, close_t)) / max(atr_t, EPS)
    lower_wick_t = (min(open_t, close_t) - low_t) / max(atr_t, EPS)
    close_pos_t = (close_t - low_t) / (high_t - low_t + EPS)
    ret_1_t = (close_t - float(prev["close"])) / max(atr_t, EPS)
    vol_z_t = float(curr["vol_z"])

    return {
        "signal_side": 1 if signal == "long" else 0,
        "rsi_t": rsi_t,
        "rsi_t1": rsi_t1,
        "rsi_t2": rsi_t2,
        "rsi_slope_1": rsi_t - rsi_t1,
        "rsi_slope_2": rsi_t1 - rsi_t2,
        "is_in_range_t": int(bool(curr["is_in_range"])),
        "atr_t": float(curr["atr"]),
        "bb_width_t": bb_width_t,
        "close_minus_ema_t": close_t - ema_t,
        "dist_to_range_upper_t": range_upper_t - close_t,
        "dist_to_range_lower_t": close_t - range_lower_t,
        "touch_upper_flag_t": touch_upper_flag,
        "touch_lower_flag_t": touch_lower_flag,
        "rsi_overbought_flag_t": rsi_overbought_flag,
        "rsi_oversold_flag_t": rsi_oversold_flag,
        "body_t": body_t,
        "range_t": range_t,
        "upper_wick_t": upper_wick_t,
        "lower_wick_t": lower_wick_t,
        "close_pos_t": close_pos_t,
        "ret_1_t": ret_1_t,
        "vol_z_t": vol_z_t,
    }


def get_spread_price(row: pd.Series) -> float:
    raw_spread = row["spread"]
    if pd.isna(raw_spread):
        raise ValueError("spread contains NaN; please clean input data first.")
    spread = float(raw_spread)
    if SPREAD_COLUMN_IS_POINTS:
        spread *= POINT
    return spread


def get_entry_price(row: pd.Series, signal: str) -> float:
    bid = float(row["open"])
    ask = bid + get_spread_price(row)
    return ask if signal == "long" else bid


def get_close_price(row: pd.Series, signal: str) -> float:
    bid = float(row["close"])
    ask = bid + get_spread_price(row)
    return bid if signal == "long" else ask


def get_entry_price_from_close(row: pd.Series, signal: str) -> float:
    bid = float(row["close"])
    ask = bid + get_spread_price(row)
    return ask if signal == "long" else bid


def standardize_like_feature_pipeline(x: pd.DataFrame) -> pd.DataFrame:
    # Match feature script behavior: train-slice mean/std, then scale full dataset.
    split_idx = int(len(x) * 0.7)
    x_train = x.iloc[:split_idx].copy()
    numeric_cols = x_train.select_dtypes(include=["number"]).columns.tolist()
    mu = x_train[numeric_cols].mean()
    sigma = x_train[numeric_cols].std(ddof=0).replace(0, 1.0)
    x_scaled = x.copy()
    x_scaled[numeric_cols] = (x_scaled[numeric_cols] - mu) / sigma
    return x_scaled


def predict_win_probability(trades: pd.DataFrame, model_path: Path) -> pd.Series:
    with model_path.open("rb") as f:
        payload = pickle.load(f)

    model = payload["model"]
    model_cols = payload["feature_columns"]

    x = trades[FEATURE_COLUMNS].copy()
    x = x.replace([float("inf"), float("-inf")], pd.NA).ffill().bfill().fillna(0.0)
    x = standardize_like_feature_pipeline(x)
    x = pd.get_dummies(x, drop_first=False).ffill().bfill().fillna(0.0)

    for col in model_cols:
        if col not in x.columns:
            x[col] = 0.0
    x = x[model_cols]
    return pd.Series(model.predict_proba(x)[:, 1], index=trades.index)


def recompute_balance(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["balance"] = (INITIAL_BALANCE + out["net_pnl"].cumsum()).round(2)
    return out


def print_report(name: str, res: pd.DataFrame) -> None:
    print("=" * 50)
    print(f"REPORT             : {name}")
    if res.empty:
        print("No trades found.")
    else:
        total_comm = res["commission"].sum()
        final_balance = float(res["balance"].iloc[-1])
        print(f"Total Trades       : {len(res)}")
        print(f"Win Rate           : {(res['net_pnl'] > 0).mean() * 100:.2f}%")
        print(f"Total Commissions  : ${total_comm:.2f}")
        print(f"Final Balance      : ${final_balance:.2f}")
        print(f"Net PnL            : ${final_balance - INITIAL_BALANCE:.2f}")
        print(f"Net PnL Percentage : {(final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100:.2f}%")
        print(f"Exit TP/SL/EOD     : {res['reason'].value_counts().to_dict()}")
    print("=" * 50)


def run_backtest(input_file: Path) -> pd.DataFrame:
    df_m5 = pd.read_csv(input_file)
    if "spread" not in df_m5.columns:
        raise ValueError("Input CSV must include 'spread' column.")
    if df_m5["spread"].isna().any():
        raise ValueError("Input CSV has NaN in 'spread' column.")

    df_m5["time"] = pd.to_datetime(df_m5["time"], utc=True)
    df_m5.sort_values("time", inplace=True)
    df_m5.reset_index(drop=True, inplace=True)
    df_m5 = compute_m5_indicators(df_m5)

    balance = INITIAL_BALANCE
    trades: list[dict] = []

    i = 2
    while i < len(df_m5) - 1:
        prev2 = df_m5.iloc[i - 2]
        prev = df_m5.iloc[i - 1]
        curr = df_m5.iloc[i]

        signal = calc_signal(prev2, prev, curr)
        if signal is None:
            i += 1
            continue

        signal_time = curr["time"]
        entry_idx = i + 1
        entry_row = df_m5.iloc[entry_idx]
        entry_time = entry_row["time"]

        cutoff_dt = pd.to_datetime(f"{entry_time.date()} {FORCE_CLOSE_TIME}", utc=True)
        if entry_time >= cutoff_dt:
            i += 1
            continue

        entry_price = get_entry_price(entry_row, signal)
        current_signal = signal
        current_signal_time = signal_time
        current_entry_time = entry_time
        current_entry_price = entry_price
        current_features = build_signal_features(prev2, prev, curr, current_signal)

        atr_v = float(curr["atr"])
        current_tp_price = (
            current_entry_price + TP_MULT * atr_v
            if current_signal == "long"
            else current_entry_price - TP_MULT * atr_v
        )
        current_sl_price = (
            current_entry_price - SL_MULT * atr_v
            if current_signal == "long"
            else current_entry_price + SL_MULT * atr_v
        )

        for j in range(entry_idx + 1, len(df_m5)):
            bar = df_m5.iloc[j]
            bt = bar["time"]
            spread = get_spread_price(bar)

            high_bid = float(bar["high"])
            low_bid = float(bar["low"])

            if current_signal == "long":
                hit_tp = high_bid >= current_tp_price
                hit_sl = low_bid <= current_sl_price
            else:
                high_ask = high_bid + spread
                low_ask = low_bid + spread
                hit_tp = low_ask <= current_tp_price
                hit_sl = high_ask >= current_sl_price

            is_eod = bt >= cutoff_dt

            if hit_tp or hit_sl or is_eod:
                if hit_tp and hit_sl:
                    raw_exit = current_sl_price
                    exit_reason = "SL"
                elif hit_sl:
                    raw_exit = current_sl_price
                    exit_reason = "SL"
                elif hit_tp:
                    raw_exit = current_tp_price
                    exit_reason = "TP"
                else:
                    close_bid = float(bar["close"])
                    close_ask = close_bid + spread
                    raw_exit = close_bid if current_signal == "long" else close_ask
                    exit_reason = "EOD_FORCE_CLOSE"

                exit_price = raw_exit
                if current_signal == "long":
                    gross_pnl = (exit_price - current_entry_price) * CONTRACT_SIZE * LOT_SIZE
                else:
                    gross_pnl = (current_entry_price - exit_price) * CONTRACT_SIZE * LOT_SIZE

                net_pnl = gross_pnl - COMMISSION_PER_TRADE
                balance += net_pnl
                trades.append(
                    {
                        "signal_time": current_signal_time,
                        "entry_time": current_entry_time,
                        "exit_time": bar["time"],
                        "type": current_signal,
                        "entry_price": round(current_entry_price, 4),
                        "exit_price": round(exit_price, 4),
                        "tp_price": round(current_tp_price, 4),
                        "sl_price": round(current_sl_price, 4),
                        "gross_pnl": round(gross_pnl, 2),
                        "commission": COMMISSION_PER_TRADE,
                        "net_pnl": round(net_pnl, 2),
                        "balance": round(balance, 2),
                        "reason": exit_reason,
                        **current_features,
                    }
                )
                i = j + 1
                break

            if j >= 2:
                rev_prev2 = df_m5.iloc[j - 2]
                rev_prev = df_m5.iloc[j - 1]
                rev_curr = df_m5.iloc[j]
                reverse_signal = calc_signal(rev_prev2, rev_prev, rev_curr)

                if reverse_signal is not None and reverse_signal != current_signal:
                    reverse_exit_price = get_close_price(bar, current_signal)
                    if current_signal == "long":
                        gross_pnl = (reverse_exit_price - current_entry_price) * CONTRACT_SIZE * LOT_SIZE
                    else:
                        gross_pnl = (current_entry_price - reverse_exit_price) * CONTRACT_SIZE * LOT_SIZE

                    net_pnl = gross_pnl - COMMISSION_PER_TRADE
                    balance += net_pnl

                    trades.append(
                        {
                            "signal_time": current_signal_time,
                            "entry_time": current_entry_time,
                            "exit_time": bar["time"],
                            "type": current_signal,
                            "entry_price": round(current_entry_price, 4),
                            "exit_price": round(reverse_exit_price, 4),
                            "tp_price": round(current_tp_price, 4),
                            "sl_price": round(current_sl_price, 4),
                            "gross_pnl": round(gross_pnl, 2),
                            "commission": COMMISSION_PER_TRADE,
                            "net_pnl": round(net_pnl, 2),
                            "balance": round(balance, 2),
                            "reason": "REVERSE",
                            **current_features,
                        }
                    )

                    current_signal = reverse_signal
                    current_signal_time = bar["time"]
                    current_entry_time = bar["time"]
                    current_entry_price = get_entry_price_from_close(bar, current_signal)
                    current_features = build_signal_features(rev_prev2, rev_prev, rev_curr, current_signal)

                    rev_atr = float(rev_curr["atr"])
                    current_tp_price = (
                        current_entry_price + TP_MULT * rev_atr
                        if current_signal == "long"
                        else current_entry_price - TP_MULT * rev_atr
                    )
                    current_sl_price = (
                        current_entry_price - SL_MULT * rev_atr
                        if current_signal == "long"
                        else current_entry_price + SL_MULT * rev_atr
                    )
        else:
            break

    return pd.DataFrame(trades)


def main() -> None:
    args = parse_args()
    trades = run_backtest(args.input)
    print_report("R01_V1 base trades (before ML filter)", trades)

    if trades.empty:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        trades.to_csv(args.output, index=False)
        print(f"Detailed trade history saved to: {args.output}")
        return

    trades["pred_win_prob"] = predict_win_probability(trades, args.model)
    filtered = trades[trades["pred_win_prob"] >= args.threshold].copy()
    filtered = recompute_balance(filtered)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(args.output, index=False)
    print(f"Detailed trade history saved to: {args.output}")
    print_report(f"R01_V1 ML-filtered trades (threshold={args.threshold})", filtered)


if __name__ == "__main__":
    main()
