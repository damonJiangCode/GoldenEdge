from datetime import timedelta, datetime, time as dtime
import time
import pandas as pd #type: ignore
import MetaTrader5 as mt5 #type: ignore
import talib #type: ignore
import os

# META DATA
METADATA = {
    "account": 5043351020,
    "password": "!v5zBdRb",
    "server": "MetaQuotes-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_3\\terminal64.exe",
    "log_file": f"RSI_BB_EMA_RANGE_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "RSI_BB_EMA_RANGE",
    "comment": "RSI(14; 70, 30; 3+2), BB(20), EMA(20), SL(1*ATR), TP(2*ATR)",
}

# PARAMETERS
PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME": mt5.TIMEFRAME_M5,
    "LOT": 0.01,
    "TP_MULTIPLIER": 2.0,
    "SL_MULTIPLIER": 1.0,
    "RSI_PERIOD": 14,
    "RSI_OVERBOUGHT": 70,
    "RSI_OVERSOLD": 30,
    "ATR_PERIOD": 14,
    "BB_PERIOD": 20,
    "EMA_PERIOD": 20,
    "RUNTIME_SECONDS": 20
}


# ==== get indicators ====
def get_data(bars=1000):
    try:
        rates = mt5.copy_rates_from_pos(PARAMETERS["SYMBOL"], PARAMETERS["TIMEFRAME"], 0, bars)  # type: ignore
        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(df["time"], unit="s")
        df["rsi"] = talib.RSI(df["close"], timeperiod=PARAMETERS["RSI_PERIOD"])  # type: ignore
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=PARAMETERS["ATR_PERIOD"])  # type: ignore
        df["ema"] = talib.EMA(df["close"], timeperiod=PARAMETERS["EMA_PERIOD"])  # type: ignore
        
        upper, middle, lower = talib.BBANDS(
            df["close"], timeperiod=PARAMETERS["BB_PERIOD"], nbdevup=2, nbdevdn=2, matype=0  # type: ignore
        )
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower

        # range upper/lower
        df["range_upper"] = df["ema"] + df["atr"] * 1.5
        df["range_lower"] = df["ema"] - df["atr"] * 1.5

        # in range 
        df["is_range"] = (df["bb_upper"] - df["bb_lower"]) < (df["atr"] * 5)
        
        return df.dropna()
    except Exception as e:
        msg = f"❌ get_data() ERROR: {e}"
        print(msg)
        log_message(msg)
        return pd.DataFrame()


# ==== log in the foler ====
LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR, METADATA["log_file"]
)


# ==== log message format ====
def log_message(msg: str):
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception as e:
        print(f"❌ log_message() ERROR: {e}")


# ==== MT5 initialization ====
ACCOUNT, PASSWORD, SERVER, MT5_PATH = METADATA["account"], METADATA["password"], METADATA["server"], METADATA["path"]
def initialize_mt5():
    try:
        if not mt5.initialize(path=MT5_PATH):  # type: ignore
            raise RuntimeError("❌ MT5 failed to initialize")
        if not mt5.login(ACCOUNT, PASSWORD, SERVER):  # type: ignore
            raise RuntimeError("❌ MT5 failed to log in")
    except Exception as e:
        msg = f"❌ initialize_mt5() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== market closing check ====
def is_close_to_market_close():
    try:
        now = datetime.now().time()
        if dtime(14, 59, 0) <= now <= dtime(14, 59, 1 + PARAMETERS["RUNTIME_SECONDS"]):
            print("market closing")
            log_message("market closing")
            return True
        return False
    except Exception as e:
        msg = f"❌ is_close_to_market_close() ERROR: {e}"
        print(msg)
        log_message(msg)
        return False
    

# ==== check positions ====
def has_positions():
    try:
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"]) # type: ignore

        if positions is None:
            msg = f"⚠️ positions_get() return None, possibly due to MT5 connection issues, error code: {mt5.last_error()}" #type: ignore
            print(msg)
            log_message(msg)
            return "error"    # error state

        if len(positions) == 0:
            return None       # no positions

        pos = positions[0]

        if pos.type == mt5.POSITION_TYPE_BUY:
            return "long"
        elif pos.type == mt5.POSITION_TYPE_SELL:
            return "short"
        else:
            return None

    except Exception as e:
        msg = f"❌ has_positions() ERROR: {e}"
        print(msg)
        log_message(msg)
        return "error"


# RET CODE MESSAGES
RET_CODE_MESSAGES = {
    mt5.TRADE_RETCODE_DONE: "order success",
    mt5.TRADE_RETCODE_REQUOTE: "order re-quoted",
    mt5.TRADE_RETCODE_REJECT: "order rejected",
    mt5.TRADE_RETCODE_CANCEL: "order canceled",
    mt5.TRADE_RETCODE_PLACED: "order placed",
    mt5.TRADE_RETCODE_DONE_PARTIAL: "order partially filled",
    mt5.TRADE_RETCODE_ERROR: "order error",
    mt5.TRADE_RETCODE_TIMEOUT: "order timeout",
    mt5.TRADE_RETCODE_INVALID: "order invalid",
    mt5.TRADE_RETCODE_INVALID_VOLUME: "order invalid volume",
    mt5.TRADE_RETCODE_INVALID_PRICE: "order invalid price",
    mt5.TRADE_RETCODE_INVALID_STOPS: "order invalid stops",
    mt5.TRADE_RETCODE_NO_MONEY: "order no money",
    mt5.TRADE_RETCODE_PRICE_CHANGED: "order price changed",
    mt5.TRADE_RETCODE_PRICE_OFF: "order price off",
    mt5.TRADE_RETCODE_INVALID_EXPIRATION: "order invalid expiration",
    mt5.TRADE_RETCODE_ORDER_CHANGED: "order changed",
    mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "order too many requests",
}


# ==== close positions ====
def close_all_positions():
    try:
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"])  # type: ignore
        if positions is None or len(positions) == 0:
            msg = "⚠️ No positions to close"
            print(msg)
            log_message(msg)
            return
        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore
        if symbol_info is None:
            msg = f"❌ Failed to get {PARAMETERS['SYMBOL']} info, cannot close positions"
            print(msg)
            log_message(msg)
            return
        for position in positions:
            opposite_order_type = (
                mt5.ORDER_TYPE_SELL
                if position.type == mt5.POSITION_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )
            tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
            if tick is None:
                msg = "❌ Failed to get mt5.symbol_info_tick()"
                print(msg)
                log_message(msg)
                continue

            price = tick.bid if opposite_order_type == mt5.ORDER_TYPE_SELL else tick.ask
            digits = symbol_info.digits
            price = round(price, digits)

            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": PARAMETERS["SYMBOL"],
                "volume": position.volume,
                "type": opposite_order_type,
                "position": position.ticket,
                "price": price,
                "deviation": 50,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(close_request)  # type: ignore

            if result is None:
                msg = f"❌ Failed to close positions: \nResult: No return\nOrder #: {position.ticket}"
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                ret_msg = RET_CODE_MESSAGES.get(result.retcode, "Unknown error")
                msg = f"❌ Failed to close positions: \nResult: {ret_msg} ({result.retcode})\nOrder #: {position.ticket}"
            else:
                msg = f"✅ position closed, Order #: {position.ticket}"

            print(msg)
            log_message(msg)
    except Exception as e:
        msg = f"❌ close_all_positions() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== check trend signal ====
def check_trend_signal(df):
    pass
    

# === check range signal ===
def check_range_signal(df):
    try:
        if df.empty or len(df) < 5:
            return None
        last1 = df.iloc[-1]
        last2 = df.iloc[-2]
        last3 = df.iloc[-3]

        # in range check
        if not last1.get("is_range", False):
            return None
        
        # RSI signal
        rsi_up = last3["rsi"] < last2["rsi"] < last1["rsi"]
        rsi_down = last3["rsi"] > last2["rsi"] > last1["rsi"]
        rsi_overbought = (last2["rsi"] >= PARAMETERS["RSI_OVERBOUGHT"] and last1["rsi"] >= PARAMETERS["RSI_OVERBOUGHT"])
        rsi_oversold = (last2["rsi"] <= PARAMETERS["RSI_OVERSOLD"] and last1["rsi"] <= PARAMETERS["RSI_OVERSOLD"])
    
        rsi_signal = 'short' if rsi_up and rsi_overbought else 'long' if rsi_down and rsi_oversold else None

        # BB range touch check
        touch_upper = last2["close"] > last2["range_upper"] and last1["close"] > last1["range_upper"]
        touch_lower = last2["close"] < last2["range_lower"] and last1["close"] < last1["range_lower"]

        signal = rsi_signal if (rsi_signal == 'short' and touch_upper) or (rsi_signal == 'long' and touch_lower) else None

        return signal
    except Exception as e:
        msg = f"❌ check_trend_signal() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== place order ====
def place_order(signal, atr):
    try:
        tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
        if tick is None:
            msg = "❌ Failed to get mt5.symbol_info_tick(), cannot place order"
            print(msg)
            log_message(msg)
            return

        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore
        if symbol_info is None:
            msg = f"❌ Failed to get mt5.symbol_info({PARAMETERS['SYMBOL']}), cannot place order"
            print(msg)
            log_message(msg)
            return

        price = tick.ask if signal == "long" else tick.bid
        digits = symbol_info.digits
        sl = (
            price - PARAMETERS["SL_MULTIPLIER"] * atr
            if signal == "long"
            else price + PARAMETERS["SL_MULTIPLIER"] * atr
        )
        tp = (
            price + PARAMETERS["TP_MULTIPLIER"] * atr
            if signal == "long"
            else price - PARAMETERS["TP_MULTIPLIER"] * atr
        )
        order_type = mt5.ORDER_TYPE_BUY if signal == "long" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": PARAMETERS["SYMBOL"],
            "volume": PARAMETERS["LOT"],
            "type": order_type,
            "price": round(price, digits),
            "sl": round(sl, digits),
            "tp": round(tp, digits),
            "deviation": 50,
            "comment": "TMGM-ORDER",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)  # type: ignore

        if result is None:
            msg = "❌ Failed to place order: no return result"
        elif hasattr(result, "retcode"):
            retcode_msg = RET_CODE_MESSAGES.get(result.retcode, "Unknown error")
            msg = (
                f"{'✅ Succeeded' if result.retcode == mt5.TRADE_RETCODE_DONE else '❌ Failed'}\n"
                f"Order #: {result.order}\n"
                f"Direction: {'Buy' if signal == 'long' else 'Sell'}\n"
                f"Price: {price:.2f}\n"
                f"SL: {sl:.2f}\n"
                f"TP: {tp:.2f}\n"
                f"Result: {retcode_msg} ({result.retcode})\n"
            )
        else:
            msg = f"❌ Failed to place order: unknown return format {result}"

        print(msg)
        log_message(msg)
    except Exception as e:
        msg = f"❌ place_order() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== ea ====
def run():
    try:
        if is_close_to_market_close():
            pos = has_positions()
            if pos == "error":
                return

            if pos:
                for _ in range(3):
                    if not has_positions():
                        break
                    close_all_positions()
                    time.sleep(1)

                log_message("⏸ Market closed, pause trading for 1 hour...")
                time.sleep(3540)

            return


        df = get_data()
        signal = check_range_signal(df)

        timestamp = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        if df.empty:
            print(f"[{timestamp}] get_data returned empty")
            log_message(f"[{timestamp}] get_data returned empty")
            return
        last1 = df.iloc[-1]
        last2 = df.iloc[-2]
        last3 = df.iloc[-3]
        msg = f"[{timestamp}] $:{mt5.account_info().balance}  ---  RSI[-1]:{last1['rsi']:.2f} | RSI[-2]:{last2['rsi']:.2f} | RSI[-3]:{last3['rsi']:.2f}  ---  IS_RANGE:{last1['is_range']} | RANGE_UPPER:{last1['range_upper']} | RANGE_LOWER:{last1['range_lower']}  ---  ATR:{last1['atr']:.2f}"  # type: ignore
        short_msg = f"[{timestamp}] --- {METADATA['title']} --- ${mt5.account_info().balance}" #type: ignore
        print(short_msg)
        log_message(msg)

        if signal:
            current_position = has_positions()
            if current_position == "error":
                log_message(f"[{timestamp}] has_positions returned error, skipping trading cycle")
                return
            # If there is an existing position in the opposite direction, close it first
            if current_position is not None:
                if current_position != signal:
                    close_all_positions()
                    # wait and re-check positions
                    time.sleep(1.5)
                    if has_positions() not in (None, "error"):
                        log_message(f"[{timestamp}] positions still present after close_all_positions(); abort new order")
                        return
                else:
                    log_message(f"[{timestamp}] already have position in same direction ({current_position}), skip")
                    return
            place_order(signal, df)
    except Exception as e:
        msg = f"❌ run() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== main ====
def main():
    try:
        initialize_mt5()
        while True:
            run()
            time.sleep(PARAMETERS["RUNTIME_SECONDS"])
    except Exception as e:
        msg = f"❌ main() ERROR: {e}"
        print(msg)
        log_message(msg)


if __name__ == "__main__":
    main()
