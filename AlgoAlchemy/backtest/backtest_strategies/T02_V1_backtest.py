import pandas as pd
import talib
import numpy as np

# --- CONFIGURATION (MATCHING YOUR SCRIPT) ---
INPUT_FILE = "../../raw_data/XAUUSD_M5_2023.csv"
OUTPUT_FILE = "../backtest_results/T02_V1_2023.csv"
INITIAL_BALANCE = 1000.0
LOT_SIZE = 0.01
CONTRACT_SIZE = 100
COMMISSION_PER_TRADE = 0.05

# --- STRATEGY PARAMETERS ---
TP_MULT = 2.0
SL_MULT = 1.0
ADX_THRESHOLD = 50
RSI_OB = 65
RSI_OS = 35
FORCE_CLOSE_TIME = "23:55:00"


def t02_v1_backtest_with_commission():
    # 1. Load Data
    df = pd.read_csv(INPUT_FILE)
    df["time"] = pd.to_datetime(df["time"])

    # 2. Calculate Indicators (Matching your get_data function)
    df["rsi"] = talib.RSI(df["close"], timeperiod=14)
    df["adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)
    df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    df["bb_u"], _, df["bb_l"] = talib.BBANDS(
        df["close"], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    df["bb_diff"] = df["bb_u"] - df["bb_l"]
    df["time_str"] = df["time"].dt.strftime("%H:%M:%S")

    df.dropna(inplace=True)
    df = df.reset_index(drop=True)

    current_balance = INITIAL_BALANCE
    trade_history = []
    total_rows = len(df)

    # 3. Simulation Loop
    i = 4  # Start from 4 to allow looking back at last4
    while i < total_rows - 1:
        # Latest Bars (Matching your check_trend_signal logic)
        last1 = df.iloc[i]
        last2 = df.iloc[i - 1]
        last3 = df.iloc[i - 2]
        last4 = df.iloc[i - 3]

        signal = None

        # --- TREND SIGNAL LOGIC ---
        # 1. ADX Threshold
        if last1["adx"] >= ADX_THRESHOLD:

            # 2. RSI Momentum Breakout
            rsi_up = last4["rsi"] < last3["rsi"] < last2["rsi"] < last1["rsi"]
            rsi_down = last4["rsi"] > last3["rsi"] > last2["rsi"] > last1["rsi"]

            rsi_ob_trend = (
                last3["rsi"] >= RSI_OB
                and last2["rsi"] >= RSI_OB
                and last1["rsi"] >= RSI_OB
            )
            rsi_os_trend = (
                last3["rsi"] <= RSI_OS
                and last2["rsi"] <= RSI_OS
                and last1["rsi"] <= RSI_OS
            )

            # 3. Bollinger Band Opening
            bb_open = last1["bb_diff"] > last2["bb_diff"] > last3["bb_diff"]

            if bb_open:
                if rsi_up and rsi_ob_trend:
                    signal = "long"
                elif rsi_down and rsi_os_trend:
                    signal = "short"

        if signal:
            entry_price = last1["close"]
            atr_v = last1["atr"]

            tp = (
                entry_price + (TP_MULT * atr_v)
                if signal == "long"
                else entry_price - (TP_MULT * atr_v)
            )
            sl = (
                entry_price - (SL_MULT * atr_v)
                if signal == "long"
                else entry_price + (SL_MULT * atr_v)
            )

            # Monitor future bars
            for j in range(i + 1, total_rows):
                fut = df.iloc[j]

                # Check Exit Conditions
                hit_tp = (signal == "long" and fut["high"] >= tp) or (
                    signal == "short" and fut["low"] <= tp
                )
                hit_sl = (signal == "long" and fut["low"] <= sl) or (
                    signal == "short" and fut["high"] >= sl
                )
                is_eod = fut["time_str"] >= FORCE_CLOSE_TIME  # Market closing check

                if hit_tp or hit_sl or is_eod:
                    exit_p = tp if hit_tp else (sl if hit_sl else fut["close"])

                    # PnL Calculation
                    p_diff = (
                        (exit_p - entry_price)
                        if signal == "long"
                        else (entry_price - exit_p)
                    )
                    gross_pnl = p_diff * CONTRACT_SIZE * LOT_SIZE
                    net_pnl = gross_pnl - COMMISSION_PER_TRADE
                    current_balance += net_pnl
                    reason = "TP" if hit_tp else ("SL" if hit_sl else "EOD_FORCE_CLOSE")

                    trade_history.append(
                        {
                            "entry_time": last1["time"],
                            "exit_time": fut["time"],
                            "type": signal,
                            "gross_pnl": round(gross_pnl, 2),
                            "commission": COMMISSION_PER_TRADE,
                            "net_pnl": round(net_pnl, 2),
                            "balance": round(current_balance, 2),
                            "reason": reason,
                        }
                    )
                    i = j  # Move pointer to exit bar
                    break
        i += 1

    # 4. Results
    res = pd.DataFrame(trade_history)

    # Write the results into a csv file
    res.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Detailed trade history saved to: {OUTPUT_FILE}")

    print("=" * 50)
    if not res.empty:
        total_comm = res["commission"].sum()
        print(f"REPORT             : T02_V1_Backtest with Commission")
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
    t02_v1_backtest_with_commission()
