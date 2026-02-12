from datetime import timedelta, datetime, time as dtime
import time
import pandas as pd #type: ignore
import MetaTrader5 as mt5 #type: ignore
import talib #type: ignore
import os
import requests #type: ignore

# META DATA
METADATA = {
    "account": 101838442,
    "password": "@u2oJxDp",
    "server": "MetaQuotes-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_4\\terminal64.exe",
    "log_file": f"R01_V1_1_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "R01_V1_1",
}

# PARAMETERS
PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME": mt5.TIMEFRAME_M5,
    "LOT": 0.01,
    "TP_MULTIPLIER": 1.8,
    "TP_MAX_MULTIPLIER": 2.5,
    "SL_MULTIPLIER": 1.0,
    "RSI_PERIOD": 14,
    "RSI_OVERBOUGHT": 70,
    "RSI_OVERSOLD": 30,
    "ATR_PERIOD": 14,
    "BB_PERIOD": 20,
    "EMA_PERIOD": 20,
    "RUNTIME_SECONDS": 20
}

# TELEGRAM
TELEGRAM = {
    "BOT_TOKEN": "8547451784:AAEARcFVIPhYS9VMxDPrf6JtPTg2PzKYA14",
    "CHAT_ID": "7262692073"
}
TELEGRAM['API'] = f"https://api.telegram.org/bot{TELEGRAM['BOT_TOKEN']}"

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




# ==== telegram send message ====
def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM['BOT_TOKEN']}/sendMessage"
        payload = {"chat_id": TELEGRAM['CHAT_ID'], "text": message}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            msg = f"❌ send_telegram_message(): Failed to send telegram message: {response.status_code} - {response.text}"
            print(msg)
            log_message(msg)
    except Exception as e:
        msg = f"❌ send_telegram_message() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== get indicators ====
def get_data(bars=1000):
    try:
        rates = mt5.copy_rates_from_pos(PARAMETERS["SYMBOL"], PARAMETERS["TIMEFRAME"], 0, bars)  # type: ignore
        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(df["time"], unit="s")
        df["rsi"] = talib.RSI(df["close"], timeperiod=PARAMETERS["RSI_PERIOD"])  # type: ignore
        df["bb_upper"], df["bb_middle"], df["bb_lower"] = talib.BBANDS(
            df["close"], timeperiod=PARAMETERS["BB_PERIOD"], nbdevup=2, nbdevdn=2, matype=0  # type: ignore
        )
        df["ema"] = talib.EMA(df["close"], timeperiod=PARAMETERS["EMA_PERIOD"])  # type: ignore
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=PARAMETERS["ATR_PERIOD"])  # type: ignore

        # range upper/lower
        df["range_upper"] = df["ema"] + df["atr"] * 1.5
        df["range_lower"] = df["ema"] - df["atr"] * 1.5

        # is in range 
        df['bb_width'] = df["bb_upper"] - df["bb_lower"]
        ema_delta = df["ema"].diff(10).abs()

        df["is_in_range"] = (
            (df['bb_width'] < df["atr"] * 3) &
            (ema_delta < df["atr"])
        )

        
        return df.dropna()
    except Exception as e:
        msg = f"❌ get_data() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return pd.DataFrame()


# ==== log in the foler ====
LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR, METADATA["log_file"]
)


# ==== log message format ====
def log_message(message: str):
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        msg = f"❌ log_message() ERROR: {e}"
        print(msg)
        send_telegram_message(msg)


# ==== initialize mt5 ====
def initialize_mt5():
    try:
        if not mt5.initialize(METADATA["path"]):  # type: ignore
            raise RuntimeError("❌ initialize_mt5(): Failed to initialize MT5")
        if not mt5.login(METADATA["account"], METADATA["password"], METADATA["server"]):  # type: ignore
            raise RuntimeError("❌ initialize_mt5(): Failed to log in MT5 account")
        msg = "✅ MT5 initialized and logged in successfully"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return True
    except Exception as e:
        msg = f"❌ initialize_mt5() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return False


# ==== market closing check ====
def is_close_to_market_close():
    try:
        now = datetime.now().time()
        if dtime(15, 59, 0) <= now <= dtime(15, 59, 1 + PARAMETERS["RUNTIME_SECONDS"]):
            msg = "⏳ Market is closing soon."
            print(msg)      
            log_message(msg)
            send_telegram_message(msg)
            return True
        return False
    except Exception as e:
        msg = f"❌ is_close_to_market_close() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== check positions ====
def has_positions():
    try:
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"]) # type: ignore

        if positions is None:
            msg = f"❌ has_positions(): mt5.positions_get() return None, error code: {mt5.last_error()}" #type: ignore
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
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
        send_telegram_message(msg)
        return "error"


# ==== close positions ====
def close_all_positions():
    try:
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"])  # type: ignore

        if positions is None:
            msg = f"❌ close_all_positions(): MetaTrader5.positions_get() return None, error code - {mt5.last_error()}" #type: ignore
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return   

        if len(positions) == 0:
            msg = "⚠️ close_all_positioins(): No positions to close"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return
        
        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore

        if symbol_info is None:
            msg = f"❌ close_all_positions(): Failed to get {PARAMETERS['SYMBOL']} info, cannot close positions"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return
        
        for position in positions:
            opposite_order_type = (
                mt5.ORDER_TYPE_SELL
                if position.type == mt5.POSITION_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )

            tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
            if tick is None:
                msg = "❌ close_all_positions(): Failed to get mt5.symbol_info_tick()"
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
                msg = f"❌ close_all_positions(): Failed to close positions: \nResult: No return\nOrder #: {position.ticket}"
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                ret_msg = RET_CODE_MESSAGES.get(result.retcode, "Unknown error")
                msg = f"❌ close_all_positions(): Failed to close positions: \nResult: {ret_msg} ({result.retcode})\nOrder #: {position.ticket}"
            else:
                msg = f"✅ close_all_positions(): position closed, Order #: {position.ticket}"

            print(msg)
            log_message(msg)
            send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ close_all_positions() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== check trend signal ====
def check_trend_signal(df: pd.DataFrame):
    pass
    

# === check range signal ===
def check_range_signal(df: pd.DataFrame):
    try:
        if df.empty or len(df) < 5:
            msg = "❌ check_range_signal(): DataFrame is empty or has insufficient data"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return None
        
        # ---------------------------
        # latest bars
        # ---------------------------
        last1 = df.iloc[-1]
        last2 = df.iloc[-2]
        last3 = df.iloc[-3]

        # ---------------------------
        # 1. in range: bb width between 5 * atr
        # ---------------------------
        if not last1["is_in_range"]:
            return None
        
        # ---------------------------
        # 2. rsi momentum reversal
        #   - increasing and overbought -> short 
        #   - decreasing and oversold -> long 
        # ---------------------------
        rsi_turn_down = last3["rsi"] < last2["rsi"] > last1["rsi"]
        rsi_turn_up   = last3["rsi"] > last2["rsi"] < last1["rsi"]
        rsi_short_cond = rsi_turn_down and last2["rsi"] >= PARAMETERS["RSI_OVERBOUGHT"]
        rsi_long_cond  = rsi_turn_up   and last2["rsi"] <= PARAMETERS["RSI_OVERSOLD"]

        # ---------------------------
        # 3. price touch range upper/lower
        # ---------------------------
        touch_upper = (
        last2["high"] > last2["range_upper"]
            and last2["close"] < last2["range_upper"]
        )

        touch_lower = (
        last2["low"] < last2["range_lower"]
            and last2["close"] > last2["range_lower"]
        )

        # ---------------------------
        # 4. final signal
        # must satisfy:
        #  - in range market
        #  - rsi momentum reversal
        #  - price touch range upper/lower
        # ---------------------------
        signal = None
        if (rsi_short_cond and touch_upper):
            signal = 'short'
        elif (rsi_long_cond and touch_lower):
            signal = 'long'
        else:
            signal = None

        return signal
    except Exception as e:
        msg = f"❌ check_trend_signal() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== place order ====
def place_order(signal: str, atr: float, df: pd.DataFrame = pd.DataFrame()):
    try:
        tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
        if tick is None:
            msg = "❌ place_order(): Failed to get mt5.symbol_info_tick(), cannot place order"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore
        if symbol_info is None:
            msg = f"❌ place_order(): Failed to get mt5.symbol_info({PARAMETERS['SYMBOL']}), cannot place order"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        price = tick.ask if signal == "long" else tick.bid
        digits = symbol_info.digits
        sl = (
            price - PARAMETERS["SL_MULTIPLIER"] * atr
            if signal == "long"
            else price + PARAMETERS["SL_MULTIPLIER"] * atr
        )
        tp_multiplier = PARAMETERS["TP_MAX_MULTIPLIER"] if df.iloc[-1]['bb_width'] < atr * 2 else PARAMETERS["TP_MULTIPLIER"]
        tp = (
            price + tp_multiplier * atr
            if signal == "long"
            else price - tp_multiplier * atr
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
            msg = "❌ place_order(): Failed to place order: no return result"
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
            msg = f"❌ place_order(): Failed to place order: unknown return format {result}"

        print(msg)
        log_message(msg)
        send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ place_order() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== ea ====
def run():
    try:
        if is_close_to_market_close():
            pos = has_positions()
            if pos == "error":
                msg = "❌ run(): has_positions() returned error during market close check, skipping position close"
                print(msg)
                log_message(msg)
                send_telegram_message(msg)
                return

            if pos:
                for _ in range(3):
                    if not has_positions():
                        break
                    close_all_positions()
                    time.sleep(1)
                msg = "⏸ Market is closing soon, no positions to close."
                print(msg)      
                log_message(msg)
                send_telegram_message(msg)
            # time.sleep(3540)
            return

        df = get_data()
        signal = check_range_signal(df)

        timestamp = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        if df.empty:
            msg = f"❌ run(): [{timestamp}] get_data returned empty"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return
        last1 = df.iloc[-1]
        last2 = df.iloc[-2]
        last3 = df.iloc[-3]
        msg = (
            f"[{timestamp}] $:{mt5.account_info().balance}  ---  CLOSE: ({last2['close']:.2f}, {last1['close']:.2f})"
            f"  ---  RANGE: ({last1['is_in_range']:.2f})"
            f"  ---  RSI:({last3['rsi']:.2f}, {last2['rsi']:.2f}, {last1['rsi']:.2f})"
            f"  ---  RANGE_UPP: ({last2['range_upper']:.2f}, {last1['range_upper']:.2f})"
            f"  ---  RANGE_LOW: ({last2['range_lower']:.2f}, {last1['range_lower']:.2f})"
            f"  ---  ATR: {last1['atr']:.2f}"  # type: ignore
        )
        short_msg = f"[{timestamp}] --- {METADATA['title']} --- ${mt5.account_info().balance}" #type: ignore
        print(short_msg)
        log_message(msg)
        

        if signal in ("long", "short"):
            current_position = has_positions()
            if current_position == "error":
                msg = f"❌ run(): [{timestamp}] has_positions returned error, skipping trading cycle"
                print(msg)
                log_message(msg)
                send_telegram_message(msg)
                return
            # If there is an existing position in the opposite direction, close it first
            if current_position is not None:
                if current_position != signal:
                    close_all_positions()
                    msg = f"⚠️ [{timestamp}] existing position in opposite direction ({current_position}), closing it first"
                    print(msg)
                    log_message(msg)
                    send_telegram_message(msg)
                    
                    # wait and re-check positions
                    time.sleep(1.5)
                    if has_positions() not in (None, "error"):
                        msg = f"⚠️ [{timestamp}] positions still present after close_all_positions(); abort new order"
                        print(msg)
                        log_message(msg)
                        send_telegram_message(msg)
                        return
                else:
                    msg = f"⚠️ [{timestamp}] already have position in same direction ({current_position}), skip"
                    print(msg)
                    log_message(msg)
                    send_telegram_message(msg)
                    return
            atr = last1["atr"]
            place_order(signal, atr)
    except Exception as e:
        msg = f"❌ run() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        

# ==== main ====
def main():
    try:
        if not initialize_mt5():
            msg = "❌ main(): initialize_mt5() failed, exiting"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return
        while True:
            run()
            time.sleep(PARAMETERS["RUNTIME_SECONDS"])

    except KeyboardInterrupt:
        msg = "⏹️ KeyboardInterrupt: manual stop"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)

    except Exception as e:
        msg = f"❌ main() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
    
    finally:
        try:
            mt5.shutdown()  # type: ignore
            msg = "🔌 MT5 shutdown completed"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
        except Exception:
            pass


if __name__ == "__main__":
    main()
