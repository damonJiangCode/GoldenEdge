import pandas as pd
import talib

# --- STRATEGY CONFIGURATION ---
INPUT_M5_FILE = "../../raw_data/XAUUSD_M5_2026_01.csv"
INPUT_M1_FILE = "../../raw_data/XAUUSD_M5_2026_01_M1.csv"
OUTPUT_FILE = "../backtest_results/R01_V1_2026_01.csv"
INITIAL_BALANCE = 1000.0
LOT_SIZE = 0.01
CONTRACT_SIZE = 100
TP_MULT = 2.0
SL_MULT = 1.0
COMMISSION_PER_TRADE = 0.05  # USD per trade

# --- EXECUTION MODEL (live-like approximation) ---
POINT = 0.01  # XAUUSD quote precision approximation
ENTRY_SLIPPAGE_POINTS = 1
EXIT_SLIPPAGE_POINTS = 1
FORCE_CLOSE_TIME = "23:59:59"  # align to UTC EOD behavior


def compute_m5_indicators(df_m5: pd.DataFrame) -> pd.DataFrame:
    df = df_m5.copy()
    df["rsi"] = talib.RSI(df["close"], timeperiod=14)
    df["ema"] = talib.EMA(df["close"], timeperiod=20)
    df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    df["bb_u"], _, df["bb_l"] = talib.BBANDS(df["close"], timeperiod=20)

    df["range_u"] = df["ema"] + (df["atr"] * 1.5)
    df["range_l"] = df["ema"] - (df["atr"] * 1.5)
    df["is_in_range"] = (df["bb_u"] - df["bb_l"]) < (df["atr"] * 5)

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

    rsi_signal = (
        "short" if rsi_up and rsi_overbought else "long" if rsi_down and rsi_oversold else None
    )

    touch_upper = prev["close"] > prev["range_u"] and curr["close"] > curr["range_u"]
    touch_lower = prev["close"] < prev["range_l"] and curr["close"] < curr["range_l"]

    if (rsi_signal == "short" and touch_upper) or (rsi_signal == "long" and touch_lower):
        return rsi_signal
    return None


def side_prices(row: pd.Series) -> tuple[float, float]:
    spread = float(row.get("spread", 0.0)) * POINT
    # MT5 rates are bid-based OHLC. Ask = Bid + spread.
    bid = float(row["open"])
    ask = bid + spread
    return bid, ask


def run_backtest() -> None:
    df_m5 = pd.read_csv(INPUT_M5_FILE)
    df_m1 = pd.read_csv(INPUT_M1_FILE)

    df_m5["time"] = pd.to_datetime(df_m5["time"], utc=True)
    df_m1["time"] = pd.to_datetime(df_m1["time"], utc=True)

    df_m5.sort_values("time", inplace=True)
    df_m1.sort_values("time", inplace=True)
    df_m5.reset_index(drop=True, inplace=True)
    df_m1.reset_index(drop=True, inplace=True)

    df_m5 = compute_m5_indicators(df_m5)

    m1_times = df_m1["time"].values
    balance = INITIAL_BALANCE
    trades: list[dict] = []

    i = 2
    while i < len(df_m5):
        prev2 = df_m5.iloc[i - 2]
        prev = df_m5.iloc[i - 1]
        curr = df_m5.iloc[i]

        signal = calc_signal(prev2, prev, curr)
        if signal is None:
            i += 1
            continue

        # Use closed M5 bar to form signal, then execute on next M1 bar.
        signal_time = curr["time"] + pd.Timedelta(minutes=5)
        entry_idx = m1_times.searchsorted(signal_time.to_datetime64(), side="left")
        if entry_idx >= len(df_m1):
            break

        entry_row = df_m1.iloc[entry_idx]
        entry_time = entry_row["time"]

        # Do not open new position during the EOD force-close second.
        cutoff_dt = pd.to_datetime(f"{entry_time.date()} {FORCE_CLOSE_TIME}", utc=True)
        if entry_time >= cutoff_dt:
            i += 1
            continue

        entry_bid, entry_ask = side_prices(entry_row)
        entry_slip = ENTRY_SLIPPAGE_POINTS * POINT
        entry_price = entry_ask + entry_slip if signal == "long" else entry_bid - entry_slip

        atr_v = float(curr["atr"])
        tp_price = entry_price + TP_MULT * atr_v if signal == "long" else entry_price - TP_MULT * atr_v
        sl_price = entry_price - SL_MULT * atr_v if signal == "long" else entry_price + SL_MULT * atr_v

        exit_idx = None
        exit_price = None
        exit_reason = None

        for j in range(entry_idx + 1, len(df_m1)):
            bar = df_m1.iloc[j]
            bt = bar["time"]
            spread = float(bar.get("spread", 0.0)) * POINT

            high_mid = float(bar["high"])
            low_mid = float(bar["low"])
            open_mid = float(bar["open"])

            if signal == "long":
                # Long exits are triggered on bid prices.
                high_bid = high_mid
                low_bid = low_mid
                hit_tp = high_bid >= tp_price
                hit_sl = low_bid <= sl_price
            else:
                # Short exits are triggered on ask prices.
                high_ask = high_mid + spread
                low_ask = low_mid + spread
                hit_tp = low_ask <= tp_price
                hit_sl = high_ask >= sl_price

            is_eod = bt >= cutoff_dt

            if hit_tp or hit_sl or is_eod:
                if hit_tp and hit_sl:
                    # If both are touched in one M1 bar, choose the level closer
                    # to the bar open as a neutral first-touch approximation.
                    if signal == "long":
                        open_ref = open_mid
                    else:
                        open_ref = open_mid + spread
                    if abs(tp_price - open_ref) < abs(open_ref - sl_price):
                        raw_exit = tp_price
                        exit_reason = "TP"
                    else:
                        raw_exit = sl_price
                        exit_reason = "SL"
                elif hit_sl:
                    raw_exit = sl_price
                    exit_reason = "SL"
                elif hit_tp:
                    raw_exit = tp_price
                    exit_reason = "TP"
                else:
                    # Use bar close for EOD liquidation.
                    close_bid = float(bar["close"])
                    close_ask = close_bid + spread
                    raw_exit = close_bid if signal == "long" else close_ask
                    exit_reason = "EOD_FORCE_CLOSE"

                exit_slip = EXIT_SLIPPAGE_POINTS * POINT
                exit_price = raw_exit - exit_slip if signal == "long" else raw_exit + exit_slip
                exit_idx = j
                break

        if exit_idx is None or exit_price is None:
            break

        if signal == "long":
            gross_pnl = (exit_price - entry_price) * CONTRACT_SIZE * LOT_SIZE
        else:
            gross_pnl = (entry_price - exit_price) * CONTRACT_SIZE * LOT_SIZE

        net_pnl = gross_pnl - COMMISSION_PER_TRADE
        balance += net_pnl

        trades.append(
            {
                "signal_time": signal_time,
                "entry_time": entry_time,
                "exit_time": df_m1.iloc[exit_idx]["time"],
                "type": signal,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "tp_price": round(tp_price, 4),
                "sl_price": round(sl_price, 4),
                "gross_pnl": round(gross_pnl, 2),
                "commission": COMMISSION_PER_TRADE,
                "net_pnl": round(net_pnl, 2),
                "balance": round(balance, 2),
                "reason": exit_reason,
            }
        )

        # Move M5 pointer to bar containing the exit time (single-position mode).
        exit_time = df_m1.iloc[exit_idx]["time"]
        i = int(df_m5["time"].searchsorted(exit_time, side="right"))

    res = pd.DataFrame(trades)
    res.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Detailed trade history saved to: {OUTPUT_FILE}")

    print("=" * 50)
    if not res.empty:
        total_comm = res["commission"].sum()
        print("REPORT             : R01_V1 M5-signal + M1-execution")
        print(f"Total Trades       : {len(res)}")
        print(f"Win Rate           : {(res['net_pnl'] > 0).mean() * 100:.2f}%")
        print(f"Total Commissions  : ${total_comm:.2f}")
        print(f"Final Balance      : ${balance:.2f}")
        print(f"Net PnL            : ${balance - INITIAL_BALANCE:.2f}")
        print(f"Net PnL Percentage : {(balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100:.2f}%")
        print(f"Exit TP/SL/EOD     : {res['reason'].value_counts().to_dict()}")
    else:
        print("No trades found.")
    print("=" * 50)


if __name__ == "__main__":
    run_backtest()
