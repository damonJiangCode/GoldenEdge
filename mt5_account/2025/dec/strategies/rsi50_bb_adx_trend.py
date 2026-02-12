from datetime import timedelta, datetime, time as dtime
import time
import pandas as pd #type: ignore
import MetaTrader5 as mt5 #type: ignore
import talib #type: ignore
import os

# META DATA
METADATA = {
    "account": 5043350964,
    "password": "3*EnDxMx",
    "server": "MetaQuotes-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_2\\terminal64.exe",
    "log_file": f"RSI50_BB_ADX_TREND_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "RSI50_BB_ADX_TREND",
    "comment": "RSI(14; 50, 50), BB(20; 3), ADX(14; 25)",
}

# PARAMETERS
PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME": mt5.TIMEFRAME_M5,
    "LOT": 0.01,
    "TP_MULTIPLIER": 1.8,
    "SL_MULTIPLIER": 0.3,
    "RSI_PERIOD": 14,
    "RSI_OVERBOUGHT": 50,
    "RSI_OVERSOLD": 50,
    "ADX_PERIOD": 14,
    "ADX_THRESHOLD": 25,
    "ATR_PERIOD": 14,
    "BB_PERIOD": 20,
    "RUNTIME_SECONDS": 20
}


# ==== get indicators ====
def get_data(bars=1000):
    try:
        rates = mt5.copy_rates_from_pos(
            PARAMETERS["SYMBOL"], PARAMETERS["TIMEFRAME"], 0, bars
        )  # type: ignore

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")

        # ==== ORIGINAL INDICATORS (keep the same) ====
        df["rsi"] = talib.RSI(df["close"], timeperiod=PARAMETERS["RSI_PERIOD"])  # type: ignore
        df["adx"] = talib.ADX(
            df["high"], df["low"], df["close"], timeperiod=PARAMETERS["ADX_PERIOD"]
        )  # type: ignore
        df["atr"] = talib.ATR(
            df["high"], df["low"], df["close"], timeperiod=PARAMETERS["ATR_PERIOD"]
        )  # type: ignore

        upper, middle, lower = talib.BBANDS(
            df["close"], 
            timeperiod=PARAMETERS["BB_PERIOD"], 
            nbdevup=2, 
            nbdevdn=2, 
            matype=0
        )
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower
        df["bb_diff"] = upper - lower


        # ==== NEW: RSI previous bar for crossover detection ====
        df["rsi_shift"] = df["rsi"].shift(1)

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
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"])

        if positions is None:
            msg = f"⚠️ positions_get() return None, possibly due to MT5 connection issues, error code: {mt5.last_error()}"
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


def check_trend_signal(df):
    try:
        # ---------------------------
        # 最新K线
        # ---------------------------
        rsi_prev = df.iloc[-2]["rsi"]
        rsi_now  = df.iloc[-1]["rsi"]

        close_prev = df.iloc[-2]["close"]
        close_now  = df.iloc[-1]["close"]

        bb_mid_prev = df.iloc[-2]["bb_middle"]
        bb_mid_now  = df.iloc[-1]["bb_middle"]

        bb_diff_prev = df.iloc[-2]["bb_diff"]
        bb_diff_now  = df.iloc[-1]["bb_diff"]

        adx_now = df.iloc[-1]["adx"]

        # ---------------------------
        # 1. ADX趋势过滤
        # ---------------------------
        if adx_now < PARAMETERS["ADX_THRESHOLD"]:
            return None   # 没趋势，不做


        # ---------------------------
        # 2. 布林带开口（趋势增强）
        # ---------------------------
        bb_expanding = bb_diff_now > bb_diff_prev   # 开口扩大
        

        # ---------------------------
        # 3. RSI 动能突破
        #    - 上穿50 → 多头动能增强
        #    - 下穿50 → 空头动能增强
        # ---------------------------
        long_rsi_signal  = rsi_prev < 50 and rsi_now > 50
        short_rsi_signal = rsi_prev > 50 and rsi_now < 50


        # ---------------------------
        # 4. 价格趋势确认（突破中轨）
        # ---------------------------
        long_price_trend  = close_prev < bb_mid_prev and close_now > bb_mid_now
        short_price_trend = close_prev > bb_mid_prev and close_now < bb_mid_now


        # ---------------------------
        # 5. 最终信号组合
        # 必须满足：
        #  - RSI 动能突破
        #  - 价格突破布林中轨
        #  - 布林带开口扩大（趋势增强）
        #  - ADX 已过滤过
        # ---------------------------

        if bb_expanding:
            if long_rsi_signal and long_price_trend:
                return "long"
            if short_rsi_signal and short_price_trend:
                return "short"

        return None

    except Exception as e:
        msg = f"❌ check_trend_signal() ERROR: {e}"
        print(msg)
        log_message(msg)
        return None



# === check range signal ===
def check_range_signal(df):
    pass


# ==== place order ====
def place_order(signal, atr, df):
    try:
        tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])
        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])

        if tick is None or symbol_info is None:
            log_message("❌ Failed to get market data")
            return

        digits = symbol_info.digits

        # ====== 价格获取 ======
        price = tick.ask if signal == "long" else tick.bid

        # ====== 选最近结构当止损 ======
        recent_lows  = df["low"].iloc[-10:]
        recent_highs = df["high"].iloc[-10:]

        if signal == "long":
            structure_sl = recent_lows.min()          # 最近最低点
            sl = structure_sl - atr * 0.3             # 给 0.3 ATR 缓冲
        else:
            structure_sl = recent_highs.max()
            sl = structure_sl + atr * 0.3

        sl = round(sl, digits)

        # ====== 根据 RR 计算 TP ======
        risk = abs(price - sl)
        tp = price + risk * 1.5 if signal == "long" else price - risk * 1.5
        tp = round(tp, digits)

        order_type = mt5.ORDER_TYPE_BUY if signal == "long" else mt5.ORDER_TYPE_SELL

        # ====== 下单 request ======
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": PARAMETERS["SYMBOL"],
            "volume": PARAMETERS["LOT"],
            "type": order_type,
            "price": round(price, digits),
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 88888,            # EA 必须有 magic number
            "comment": "EA_TREND_ORDER",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        # ========== 输出结果 ==========
        if result is None:
            msg = "❌ No result from order_send()"
        elif result.retcode == mt5.TRADE_RETCODE_DONE:
            msg = (
                f"✅ Order placed successfully!\n"
                f"Type: {signal.upper()}\n"
                f"Price: {price}\n"
                f"SL: {sl}\n"
                f"TP: {tp}\n"
                f"Order ID: {result.order}"
            )
        else:
            msg = f"❌ Order failed: {result.retcode} | {RET_CODE_MESSAGES.get(result.retcode, 'Unknown')}"

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
        signal = check_trend_signal(df)

        timestamp = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] $:{mt5.account_info().balance}  ---  ADX[-1]:{df.iloc[-1]['adx']:.2f}  ---  RSI[-1]:{df.iloc[-1]['rsi']:.2f} | RSI[-2]:{df.iloc[-2]['rsi']:.2f}  ---  BB_DIFF[-1]:{df.iloc[-1]['bb_diff']:.2f} | BB_DIFF[-2]:{df.iloc[-2]['bb_diff']:.2f}  ---  ATR:{df.iloc[-1]['atr']:.2f}"  # type: ignore
        short_msg = f"[{timestamp}] --- {METADATA['title']} --- ${mt5.account_info().balance}" #type: ignore
        print(short_msg)
        log_message(msg)

        if signal:
            atr = df.iloc[-1]["atr"]
            place_order(signal, atr, df)
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
