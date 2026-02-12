import pandas as pd
import talib
import numpy as np

# --- STRATEGY CONFIGURATION ---
INPUT_FILE = "../../raw_data/XAUUSD_M5_2023.csv"
OUTPUT_FILE = "../backtest_results/R01_V1_2023.csv"
INITIAL_BALANCE = 1000.0
LOT_SIZE = 0.01
CONTRACT_SIZE = 100
TP_MULT = 2.0
SL_MULT = 1.0
COMMISSION_PER_TRADE = 0.05  # $0.05 USD for 0.01 Lot

# --- TIME CONTROL ---
FORCE_CLOSE_TIME = "23:55:00"
LAST_SIGNAL_HOUR = 23


def r01_v1_backtest_with_commission():
    df = pd.read_csv(INPUT_FILE)
    df["time"] = pd.to_datetime(df["time"])

    # Technical Indicators
    df["rsi"] = talib.RSI(df["close"], timeperiod=14)
    df["ema"] = talib.EMA(df["close"], timeperiod=20)
    df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    df["bb_u"], _, df["bb_l"] = talib.BBANDS(df["close"], timeperiod=20)

    df["range_u"] = df["ema"] + (df["atr"] * 1.5)
    df["range_l"] = df["ema"] - (df["atr"] * 1.5)
    df["is_in_range"] = (df["bb_u"] - df["bb_l"]) < (df["atr"] * 5)

    df["hour"] = df["time"].dt.hour
    df["time_str"] = df["time"].dt.strftime("%H:%M:%S")

    df.dropna(inplace=True)
    df = df.reset_index(drop=True)

    current_balance = INITIAL_BALANCE
    trade_history = []
    total_rows = len(df)

    i = 2
    while i < total_rows - 1:
        curr = df.iloc[i]
        prev = df.iloc[i - 1]
        prev2 = df.iloc[i - 2]

        signal = None
        if curr["hour"] < LAST_SIGNAL_HOUR and curr["is_in_range"]:
            rsi_rising = prev2["rsi"] < prev["rsi"] < curr["rsi"]
            rsi_falling = prev2["rsi"] > prev["rsi"] > curr["rsi"]

            if rsi_rising and curr["rsi"] >= 70 and curr["close"] > curr["range_u"]:
                signal = "short"
            elif rsi_falling and curr["rsi"] <= 30 and curr["close"] < curr["range_l"]:
                signal = "long"

        if signal:
            entry_price = curr["close"]
            atr_v = curr["atr"]
            tp_price = (
                entry_price + (TP_MULT * atr_v)
                if signal == "long"
                else entry_price - (TP_MULT * atr_v)
            )
            sl_price = (
                entry_price - (SL_MULT * atr_v)
                if signal == "long"
                else entry_price + (SL_MULT * atr_v)
            )

            for j in range(i + 1, total_rows):
                fut = df.iloc[j]
                hit_tp = (signal == "long" and fut["high"] >= tp_price) or (
                    signal == "short" and fut["low"] <= tp_price
                )
                hit_sl = (signal == "long" and fut["low"] <= sl_price) or (
                    signal == "short" and fut["high"] >= sl_price
                )
                is_end_of_day = fut["time_str"] >= FORCE_CLOSE_TIME

                if hit_tp or hit_sl or is_end_of_day:
                    exit_price = (
                        tp_price if hit_tp else (sl_price if hit_sl else fut["close"])
                    )

                    # 1. Calculate Gross Profit
                    price_diff = (
                        (exit_price - entry_price)
                        if signal == "long"
                        else (entry_price - exit_price)
                    )
                    gross_pnl = price_diff * CONTRACT_SIZE * LOT_SIZE

                    # 2. Subtract Commission
                    net_pnl = gross_pnl - COMMISSION_PER_TRADE

                    current_balance += net_pnl

                    reason = "TP" if hit_tp else ("SL" if hit_sl else "EOD_FORCE_CLOSE")
                    trade_history.append(
                        {
                            "entry_time": curr["time"],
                            "exit_time": fut["time"],
                            "type": signal,
                            "gross_pnl": round(gross_pnl, 2),
                            "commission": COMMISSION_PER_TRADE,
                            "net_pnl": round(net_pnl, 2),
                            "balance": round(current_balance, 2),
                            "reason": reason,
                        }
                    )
                    i = j
                    break
        i += 1

    # Final Statistics
    res = pd.DataFrame(trade_history)

    # Write the results into a csv file
    res.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Detailed trade history saved to: {OUTPUT_FILE}")

    print("=" * 50)
    if not res.empty:
        total_comm = res["commission"].sum()
        print(f"REPORT             : R01_V1_Backtest with Commission")
        print(f"Total Trades       : {len(res)}")
        print(f"Win Rate           : {(res['net_pnl'] > 0).mean()*100:.2f}%")
        print(f"Total Commissions  : ${total_comm:.2f}")
        print(f"Final Balance      : ${current_balance:.2f}")
        print(f"Net PnL            : ${current_balance - INITIAL_BALANCE:.2f}")
        print(
            f"Net PnL Percentage : {(current_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100:.2f}%"
        )
    else:
        print("No trades found.")
    print("=" * 50)


if __name__ == "__main__":
    r01_v1_backtest_with_commission()
