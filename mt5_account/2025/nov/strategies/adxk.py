from datetime import timedelta, datetime, time as dtime
import time
import pandas as pd #type: ignore
import MetaTrader5 as mt5 #type: ignore
import talib #type: ignore
import requests #type: ignore
import os
from pathlib import Path



# ==== Telegram configurations ====
TELEGRAM_BOT_TOKEN = "8147556168:AAGX-4T7T9LKtxhhsBFjJzM6JHkCAJ-HnDQ"
TELEGRAM_CHAT_ID = "7262692073"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
last_update_id = -1
is_mt5_trading_enabled = True

# ==== MT5 configurations ====
ACCOUNT = 97408042
PASSWORD = "@mOd8lTf"
SERVER = "MetaQuotes-Demo"
MT5_PATH = r"C:\\Program Files\\MetaTrader 5_2\\terminal64.exe"
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

# ==== Params & indicators ====
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
LOT = 0.01
TP_MULTIPLIER = 10.0
SL_MULTIPLIER = 1.0
ADX_PERIOD = 14
ADX_K = 1
RSI_PERIOD = 14
RSI_OVERBOUGHT = 60
RSI_OVERSOLD = 40
ATR_PERIOD = 14
BB_PERIOD = 20
RUNTIME_SECONDS = 20
sent_morning_balance = None
sent_evening_balance = None


# ==== Logs folder ====
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"ADXK_{datetime.now().strftime('%m-%d__%H-%M')}.log"


# ==== Log message ====
def log_message(msg: str):
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception as e:
        print(f"❌ log_message() ERROR: {e}")


# ==== Telegram message ====
def send_telegram_message(msg: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            msg = f"❌ Telegram failed to send message: {response.status_code} - {response.text}"
            print(msg)
            log_message(msg)
    except Exception as e:
        msg = f"❌ send_telegram_message() ERROR: {e}"
        print(msg)
        log_message(msg)


# ==== Telegram initialization====
def init_last_update_id():
    global last_update_id
    try:
        response = requests.get(f"{TELEGRAM_API}/getUpdates", timeout=10)
        data = response.json()
        if data["ok"] and data["result"]:
            last_update_id = data["result"][-1]["update_id"] + 1
    except Exception as e:
        msg = f"Failed to initialize last_update_id : {e}"
        print(msg)
        log_message(msg)


# === Telegram commands ===
def check_telegram_command():
    global last_update_id
    global is_mt5_trading_enabled
    try:
        response = requests.get(f"{TELEGRAM_API}/getUpdates?offset={last_update_id}", timeout=10)
        data = response.json()
        if not data["ok"] or not data["result"]:
            return

        for update in data["result"]:
            update_id = update["update_id"]
            last_update_id = update_id + 1  

            message = update.get("message", {})
            text = message.get("text", "").strip().lower()
            print(f"Received command: {text}")
            log_message(f"Received command: {text}")
            sender_id = str(message.get("chat", {}).get("id"))

            if sender_id != TELEGRAM_CHAT_ID:
                print(f"Unauthorized sender ID: {sender_id}")
                log_message(f"Unauthorized sender ID: {sender_id}")
                continue
            
            if text == "help":
                msg = "1. Run\n" "2. Stop\n" "3. Balance"
            elif text == "1":
                if is_mt5_trading_enabled:
                    msg = "⚠️ Running"
                else:
                    is_mt5_trading_enabled = True
                    msg = "✅ Starting"
            elif text == "2":
                if is_mt5_trading_enabled:
                    is_mt5_trading_enabled = False
                    msg = "✅ Stoping"
                else:
                    msg = "⚠️ Paused"
            elif text == "3":
                account_info = mt5.account_info()  # type: ignore
                if account_info is None:
                    msg = "❌ Failed to get mt5.account_info()"
                else:
                    balance = account_info.balance
                    equity = account_info.equity
                    msg = f"Balance: {balance:.2f}\n" f"Equity: {equity:.2f}"
            else:
                continue 
            print(msg)
            log_message(msg)
            send_telegram_message(msg)

    except Exception as e:
        msg = f"❌ check_telegram_command ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== MT5 initialization ====
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
        send_telegram_message(msg)


# ==== Indicators getter ====
def get_data(bars=1000):
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, bars)  # type: ignore
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df["adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=ADX_PERIOD)  # type: ignore
        df["rsi"] = talib.RSI(df["close"], timeperiod=RSI_PERIOD)  # type: ignore
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=ATR_PERIOD)  # type: ignore
        upper, middle, lower = talib.BBANDS(
            df["close"], timeperiod=BB_PERIOD, nbdevup=2, nbdevdn=2, matype=0  # type: ignore
        )
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower
        df["bb_diff"] = upper - lower
        return df.dropna()
    except Exception as e:
        msg = f"❌ get_data() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return pd.DataFrame()


# ==== Check closing market ====
def is_close_to_market_close():
    try:
        now = datetime.now().time()
        if dtime(14, 59, 58-RUNTIME_SECONDS) <= now <= dtime(14, 59, 59):
            print("market closed")
            log_message("market closed")
            send_telegram_message("market closed")
            return True
        return False
    except Exception as e:
        msg = f"❌ is_close_to_market_close() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return False


# ==== Check positions ====
def has_positions():
    try:
        positions = mt5.positions_get(symbol=SYMBOL)  # type: ignore
        if positions is None:
            msg = "⚠️ Failed to query positions from mt5"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return None

        if len(positions) == 0:
            return None

        pos = positions[0]  
        direction = "long" if pos.type == mt5.POSITION_TYPE_BUY else "short" if pos.type == mt5.POSITION_TYPE_SELL else None
        return direction
    except Exception as e:
        msg = f"❌ has_positions() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== Close positions ====
def close_all_positions():
    try:
        positions = mt5.positions_get(symbol=SYMBOL)  # type: ignore
        if positions is None or len(positions) == 0:
            msg = "⚠️ No positions to close"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        symbol_info = mt5.symbol_info(SYMBOL)  # type: ignore
        if symbol_info is None:
            msg = f"❌ Failed to get {SYMBOL} info, cannot close positions"
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

            tick = mt5.symbol_info_tick(SYMBOL)  # type: ignore
            if tick is None:
                msg = "❌ Failed to get mt5.symbol_info_tick()"
                print(msg)
                log_message(msg)
                send_telegram_message(msg)
                continue

            price = tick.bid if opposite_order_type == mt5.ORDER_TYPE_SELL else tick.ask
            digits = symbol_info.digits
            price = round(price, digits)

            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
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
                msg = f"❌ Failed to close positions: \nResult: No return\nTicket#: {position.ticket}"
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                ret_msg = RET_CODE_MESSAGES.get(result.retcode, "Unknown error")
                msg = f"❌ Failed to close positions: \nResult: {ret_msg} ({result.retcode})\nTicket#: {position.ticket}"
            else:
                msg = f"✅ position closed, Ticket#: {position.ticket}"

            print(msg)
            log_message(msg)
            send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ close_all_positions() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== Update break-even stop loss ====
def update_sl(df):
    positions = mt5.positions_get(symbol=SYMBOL) # type: ignore
    if not positions:
        return None  

    tick = mt5.symbol_info_tick(SYMBOL) # type: ignore
    if not tick:
        return None

    atr = df.iloc[-1]["atr"]
    symbol_info = mt5.symbol_info(SYMBOL) # type: ignore
    digits = symbol_info.digits if symbol_info else 2

    for pos in positions:
        is_long = pos.type == mt5.POSITION_TYPE_BUY
        current_price = tick.bid if is_long else tick.ask
        entry_price = pos.price_open
        current_sl = round(pos.sl, digits)

        profit_points = (current_price - entry_price) if is_long else (entry_price - current_price)

        profit_atr = profit_points / atr  

        locked_atr = max(0, (profit_atr // 1) * 0.5)

        if locked_atr == 0:
            continue  

        new_sl = round((entry_price + locked_atr * atr if is_long else entry_price - locked_atr * atr), digits)

        if (is_long and new_sl > current_sl) or (not is_long and new_sl < current_sl):
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "sl": new_sl,
                "tp": pos.tp,  
            }
            profits = new_sl - entry_price if is_long else entry_price - new_sl
            result = mt5.order_send(request) # type: ignore
            retcode_msg = RET_CODE_MESSAGES.get(result.retcode, "unknown error")

            msg = (
                f"🔒 Lock profit\n"
                f"Ticket #: {pos.ticket}\n"
                f"Direction: {'Buy' if is_long else 'Sell'}\n"
                f"Profit: {profits:.2f}\n"
                f"SL: {new_sl}\n"
                f"Result: {retcode_msg} ({result.retcode})"
                )

            print(msg)
            log_message(msg)
            send_telegram_message(msg)

    return


# ==== Check signal ====
def check_signal(df):
    try:
        positions = mt5.positions_get(symbol=SYMBOL)  # type: ignore
        if positions:
            if is_mt5_trading_enabled:
                update_sl(df)
        
        # ADX filter
        adx_now = df.iloc[-1]["adx"]
        adx_mean = df["adx"].tail(100).mean()

        if adx_now > adx_mean * ADX_K:
            return None
        
        # RSI signal
        rsi_up = df.iloc[-3]["rsi"] < df.iloc[-2]["rsi"] < df.iloc[-1]["rsi"]
        rsi_down = df.iloc[-3]["rsi"] > df.iloc[-2]["rsi"] > df.iloc[-1]["rsi"]
        rsi_overbought_trend = (
            df.iloc[-3]["rsi"] >= RSI_OVERBOUGHT and df.iloc[-2]["rsi"] >= RSI_OVERBOUGHT and df.iloc[-1]["rsi"] >= RSI_OVERBOUGHT
        )
        rsi_oversold_trend = (
            df.iloc[-3]["rsi"] <= RSI_OVERSOLD and df.iloc[-2]["rsi"] <= RSI_OVERSOLD and df.iloc[-1]["rsi"] <= RSI_OVERSOLD
        )
        # buy reverse in range market
        rsi_signal = 'short' if rsi_up and rsi_overbought_trend else 'long' if rsi_down and rsi_oversold_trend else None

        # BB signal
        bb_open = (
            df.iloc[-1]["bb_diff"] > df.iloc[-2]["bb_diff"] > df.iloc[-3]["bb_diff"]
        )
        bb_signal = True if bb_open else None

        # signal check
        signal = rsi_signal if rsi_signal and bb_signal else None

        return signal
    except Exception as e:
        msg = f"❌ check_signal() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== Place order ====
def place_order(signal, atr):
    try:
        tick = mt5.symbol_info_tick(SYMBOL)  # type: ignore
        if tick is None:
            msg = f"❌ Failed to get mt5.symbol_info_tick({SYMBOL}), cannot place order"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        symbol_info = mt5.symbol_info(SYMBOL)  # type: ignore
        if symbol_info is None:
            msg = f"❌ Failed to get mt5.symbol_info({SYMBOL}), cannot place grid order"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        price = tick.ask if signal == "long" else tick.bid
        digits = symbol_info.digits
        tp = (
            price + TP_MULTIPLIER * atr
            if signal == "long"
            else price - TP_MULTIPLIER * atr
        )
        sl = (
            price - SL_MULTIPLIER * atr
            if signal == "long"
            else price + SL_MULTIPLIER * atr
        )
        
        order_type = mt5.ORDER_TYPE_BUY if signal == "long" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": LOT,
            "type": order_type,
            "price": round(price, digits),
            "sl": round(sl, digits),
            "tp": round(tp, digits),
            "deviation": 50,
            "comment": "M5-LP",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)  # type: ignore

        if result is None:
            msg = "❌ Failed to place order, no return result"
        elif hasattr(result, "retcode"):
            retcode_msg = RET_CODE_MESSAGES.get(result.retcode, "Unknown error")
            msg = (
                f"{'✅ Succeeded' if result.retcode == mt5.TRADE_RETCODE_DONE else '❌ Failed'}\n"
                f"Ticket #: {result.order}\n"
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
        send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ place_order() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== balance report ====
def check_and_send_daily_balance_report():
    try:
        global sent_morning_balance, sent_evening_balance

        now = datetime.now()
        today = now.date()
        current_time = now.time()

        if dtime(6, 0, 0) <= current_time < dtime(6, 0, 1 + RUNTIME_SECONDS):
            if sent_morning_balance != today:
                account_info = mt5.account_info()  # type: ignore
                if account_info is None:
                    msg = "❌ Failed to get mt5.account_info(), cannot send morning report"
                    print(msg)
                    log_message(msg)
                    send_telegram_message(msg)
                    return

                balance = account_info.balance
                equity = account_info.equity

                msg = f"🌅\n" f"Balance: {balance:.2f}\n" f"Equity: {equity:.2f}"
                print(msg)
                log_message(msg)
                send_telegram_message(msg)
                sent_morning_balance = today

        if dtime(21, 0, 0) <= current_time < dtime(21, 0, 1 + RUNTIME_SECONDS):
            if sent_evening_balance != today:
                account_info = mt5.account_info()  # type: ignore
                if account_info is None:
                    msg = "❌ Failed to get mt5.account_info(), cannot send evening report"
                    print(msg)
                    log_message(msg)
                    send_telegram_message(msg)
                    return

                balance = account_info.balance
                equity = account_info.equity

                msg = f"🌙\n" f"Balance: {balance:.2f}\n" f"Equity: {equity:.2f}"
                print(msg)
                log_message(msg)
                send_telegram_message(msg)
                sent_evening_balance = today
        return
    except Exception as e:
        msg = f"❌ check_and_send_daily_balance_report() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== Algorithm ====
def run():
    try:
        check_telegram_command()
        check_and_send_daily_balance_report()
        if is_close_to_market_close():
            # close positions
            position_direction = has_positions()
            if position_direction:
                max_attempts = 3  
                attempt = 0
                while attempt < max_attempts and has_positions():
                    close_all_positions()
                    attempt += 1
            msg = "⏸ Market closed, pause trading for 1 hour..."
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            time.sleep(3540)
            return

        df = get_data()
        signal = check_signal(df)

        timestamp = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        msg = f"[{timestamp}] $:{mt5.account_info().balance}  ---  ADX[-1]:{df.iloc[-1]['adx']:.2f} | ADX[mean]:{df['adx'].tail(100).mean():.2f} --- RSI[-1]:{df.iloc[-1]['rsi']:.2f} | RSI[-2]:{df.iloc[-2]['rsi']:.2f} | RSI[-3]:{df.iloc[-3]['rsi']:.2f}  ---  BB_DIFF[-1]:{df.iloc[-1]['bb_diff']:.2f} | BB_DIFF[-2]:{df.iloc[-2]['bb_diff']:.2f} | BB_DIFF[-3]:{df.iloc[-3]['bb_diff']:.2f}  ---  ATR:{df.iloc[-1]['atr']:.2f}"  # type: ignore
        short_msg = f"[{timestamp}] --- ADXK --- $:{mt5.account_info().balance}" # type: ignore
        print(short_msg)
        log_message(msg)

        if signal:
            if not is_mt5_trading_enabled:
                return

            atr = df.iloc[-1]["atr"]
            if has_positions() is None: place_order(signal, atr) 
    except Exception as e:
        msg = f"❌ run() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


# ==== Main ====
def main():
    try:
        init_last_update_id()
        initialize_mt5()
        while True:
            run()
            time.sleep(RUNTIME_SECONDS)
    except Exception as e:
        msg = f"❌ main() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)


if __name__ == "__main__":
    main()
