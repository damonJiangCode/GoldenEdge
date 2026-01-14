from datetime import timedelta, datetime, time as dtime
import time
import pandas as pd #type: ignore
import MetaTrader5 as mt5 #type: ignore
import talib #type: ignore
import os
import requests #type: ignore

# META DATA
METADATA = {
    "account": 10009099423,
    "password": "!jDfYaR2",
    "server": "MetaQuotes-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_4\\terminal64.exe",
    "log_file": f"EMA_MACD_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "EMA_MACD",
    "comment": "EMA(50, 200), MACD(12, 26, 9), SL(1.5*ATR), TP(2*ATR)",
}

# PARAMETERS
PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME": mt5.TIMEFRAME_M5,
    "LOT": 0.01,
    "TP_MULTIPLIER": 2.0,
    "SL_MULTIPLIER": 1.0,
    "ATR_PERIOD": 14,
    "EMA_FAST_PERIOD": 50,
    "EMA_SLOW_PERIOD": 200,
    "MACD_FAST_PERIOD": 12,
    "MACD_SLOW_PERIOD": 26,
    "MACD_SIGNAL_PERIOD": 9,
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
        df["macd"], df["macdsignal"], df["macdhist"] = talib.MACD(df["close"], fastperiod=PARAMETERS["MACD_FAST_PERIOD"], slowperiod=PARAMETERS["MACD_SLOW_PERIOD"], signalperiod=PARAMETERS["MACD_SIGNAL_PERIOD"])  # type: ignore
        df["ema_fast"] = talib.EMA(df["close"], timeperiod=PARAMETERS["EMA_FAST_PERIOD"])  # type: ignore
        df["ema_slow"] = talib.EMA(df["close"], timeperiod=PARAMETERS["EMA_SLOW_PERIOD"])  # type: ignore
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=PARAMETERS["ATR_PERIOD"])  # type: ignore

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
        if dtime(14, 59, 0) <= now <= dtime(14, 59, 1 + PARAMETERS["RUNTIME_SECONDS"]):
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
            msg = f"❌ close_all_positions(): Failed to get {PARAMETERS["SYMBOL"]} info, cannot close positions"
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
    try:
        if df.empty or len(df) < 200:
            msg = "❌ check_trend_signal(): DataFrame is empty or has insufficient data"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return None
        
        last1 = df.iloc[-1]
        last2 = df.iloc[-2]

        # EMA filter
        ema_trend = None
        if last1["ema_fast"] > last1["ema_slow"]:
            ema_trend = "long"
        elif last1["ema_fast"] < last1["ema_slow"]:
            ema_trend = "short"

        # MACD signal
        macd_signal = None
        if last1["macd"] < 0 and last2["macd"] < last2["macdsignal"] and last1["macd"] > last1["macdsignal"]:
            macd_signal = "long"
        elif last1["macd"] > 0 and last2["macd"] > last2["macdsignal"] and last1["macd"] < last1["macdsignal"]:
            macd_signal = "short"

        # signal check
        signal = None
        if ema_trend == "long" and macd_signal == "long":
            signal = "long"
        if ema_trend == "short" and macd_signal == "short":
            signal = "short"

        return signal
    except Exception as e:
        msg = f"❌ check_trend_signal() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
    

# === check range signal ===
def check_range_signal(df: pd.DataFrame):
    pass


# ==== place order ====
def place_order(signal: str, atr: float):
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
            msg = f"❌ place_order(): Failed to get mt5.symbol_info({PARAMETERS["SYMBOL"]}), cannot place order"
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
                time.sleep(3540)
            return

        df = get_data()
        signal = check_trend_signal(df)

        timestamp = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        if df.empty:
            msg = f"❌ run(): [{timestamp}] get_data returned empty"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return
        last1 = df.iloc[-1]
        last2 = df.iloc[-2]
        msg = f"[{timestamp}] $:{mt5.account_info().balance}  ---  EMA50:{last2['ema_fast']:.2f}; {last1['ema_fast']:.2f} | EMA200:{last2['ema_slow']:.2f}; {last1['ema_slow']:.2f}  ---  MACD:{last2['macd']:.2f}; {last1['macd']:.2f} | MACD_SIGNAL:{last2['macdsignal']:.2f}, {last1['macdsignal']:.2f} | MACD_HIST:{last2['macdhist']:.2f}; {last1['macdhist']:.2f}  --- ATR:{last1['atr']:.2f}"  # type: ignore
        short_msg = f"[{timestamp}] --- {METADATA["title"]} --- ${mt5.account_info().balance}" #type: ignore
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
