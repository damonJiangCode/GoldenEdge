from datetime import datetime, timezone
import time
from pathlib import Path

import pandas as pd  # type: ignore
import MetaTrader5 as mt5  # type: ignore
import requests  # type: ignore


# META DATA
METADATA = {
    "account": 60089394,
    "password": "Jwz990118.",
    "server": "TradeMaxGlobal-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_1\\terminal64.exe",
    "log_file": f"VB_H4_V1_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "VB_H4_V1",
    "comment": "XAUUSD H4 Volatility Breakout: DC(18), Exit(10), SL(2.2ATR), Trail(3.2ATR), H1 ADX>=18, ATR ratio>=1.0",
}


# PARAMETERS
PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME": mt5.TIMEFRAME_H4,
    "H1_TIMEFRAME": mt5.TIMEFRAME_H1,
    "LOT": 0.01,
    "DONCHIAN_BREAKOUT_PERIOD": 18,
    "DONCHIAN_EXIT_PERIOD": 10,
    "ATR_PERIOD": 14,
    "ATR_RATIO_LOOKBACK": 100,
    "ATR_RATIO_MIN": 1.0,
    "ADX_PERIOD": 14,
    "H1_ADX_MIN": 18.0,
    "SL_ATR_MULTIPLIER": 2.2,
    "TRAIL_ATR_MULTIPLIER": 3.2,
    "BARS": 500,
    "H1_BARS": 2500,
    "RUNTIME_SECONDS": 60,
}


# TELEGRAM
TELEGRAM = {
    "BOT_TOKEN": "8231104565:AAGBVAaRM2IEtNLCeoyxoUs89peMZ8xzPrI",
    "CHAT_ID": "7262692073",
}
TELEGRAM["API"] = f"https://api.telegram.org/bot{TELEGRAM['BOT_TOKEN']}"


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


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / METADATA["log_file"]
STATE_FILE = LOG_DIR / f"{METADATA['title']}_state.txt"

LAST_SIGNAL_BAR_TIME = None


def log_message(message: str):
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        msg = f"❌ log_message() ERROR: {e}"
        print(msg)
        send_telegram_message(msg)


def load_last_signal_bar_time():
    try:
        if not STATE_FILE.exists():
            return None
        value = STATE_FILE.read_text(encoding="utf-8").strip()
        if not value:
            return None
        return pd.Timestamp(value)
    except Exception as e:
        msg = f"❌ load_last_signal_bar_time() ERROR: {e}"
        print(msg)
        log_message(msg)
        return None


def save_last_signal_bar_time(signal_bar_time):
    try:
        STATE_FILE.write_text(str(signal_bar_time), encoding="utf-8")
    except Exception as e:
        msg = f"❌ save_last_signal_bar_time() ERROR: {e}"
        print(msg)
        log_message(msg)


def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM['BOT_TOKEN']}/sendMessage"
        payload = {"chat_id": TELEGRAM["CHAT_ID"], "text": message}
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            msg = f"❌ send_telegram_message(): Failed to send telegram message: {response.status_code} - {response.text}"
            print(msg)
            log_message(msg)
    except Exception as e:
        msg = f"❌ send_telegram_message() ERROR: {e}"
        print(msg)
        log_message(msg)


def initialize_mt5():
    try:
        if not mt5.initialize(METADATA["path"]):  # type: ignore
            raise RuntimeError(f"❌ initialize_mt5(): Failed to initialize MT5: {mt5.last_error()}")  # type: ignore
        if not mt5.login(METADATA["account"], METADATA["password"], METADATA["server"]):  # type: ignore
            raise RuntimeError(f"❌ initialize_mt5(): Failed to log in MT5 account: {mt5.last_error()}")  # type: ignore
        if not mt5.symbol_select(PARAMETERS["SYMBOL"], True):  # type: ignore
            raise RuntimeError(f"❌ initialize_mt5(): Failed to select symbol {PARAMETERS['SYMBOL']}")

        account = mt5.account_info()  # type: ignore
        msg = (
            "✅ MT5 initialized and logged in successfully\n"
            f"Account: {account.login if account else METADATA['account']}\n"
            f"Server: {METADATA['server']}\n"
            f"Strategy: {METADATA['title']}"
        )
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


def get_mt5_utc_now():
    try:
        tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
        if tick is None:
            return None
        return datetime.fromtimestamp(tick.time, tz=timezone.utc)
    except Exception as e:
        msg = f"❌ get_mt5_utc_now() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return None


def _rates_to_dataframe(rates) -> pd.DataFrame:
    df = pd.DataFrame(rates)
    if df.empty:
        return df
    for col in ["open", "high", "low", "close", "tick_volume", "spread"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df.sort_values("time", inplace=True)
    df.drop_duplicates(subset=["time"], inplace=True)
    df.dropna(subset=["time", "open", "high", "low", "close"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_prev_close = (df["high"] - df["close"].shift(1)).abs()
    low_prev_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def calc_adx(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)

    tr_smoothed = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_dm_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
    minus_dm_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False).mean()

    plus_di = 100.0 * plus_dm_smoothed / tr_smoothed.replace(0.0, float("nan"))
    minus_di = 100.0 * minus_dm_smoothed / tr_smoothed.replace(0.0, float("nan"))
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, float("nan"))
    return dx.ewm(alpha=1 / period, adjust=False).mean()


def get_data():
    try:
        h4_rates = mt5.copy_rates_from_pos(  # type: ignore
            PARAMETERS["SYMBOL"], PARAMETERS["TIMEFRAME"], 0, PARAMETERS["BARS"]
        )
        h1_rates = mt5.copy_rates_from_pos(  # type: ignore
            PARAMETERS["SYMBOL"], PARAMETERS["H1_TIMEFRAME"], 0, PARAMETERS["H1_BARS"]
        )
        h4 = _rates_to_dataframe(h4_rates)
        h1 = _rates_to_dataframe(h1_rates)
        if h4.empty or h1.empty:
            msg = f"❌ get_data(): empty rates, H4 empty={h4.empty}, H1 empty={h1.empty}"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return pd.DataFrame()

        h4["atr"] = calc_atr(h4, PARAMETERS["ATR_PERIOD"])
        atr_slow = h4["atr"].rolling(
            window=PARAMETERS["ATR_RATIO_LOOKBACK"],
            min_periods=PARAMETERS["ATR_RATIO_LOOKBACK"],
        ).mean()
        h4["atr_ratio"] = h4["atr"] / atr_slow.replace(0.0, float("nan"))

        n = PARAMETERS["DONCHIAN_BREAKOUT_PERIOD"]
        m = PARAMETERS["DONCHIAN_EXIT_PERIOD"]
        h4["donchian_high_n"] = h4["high"].rolling(window=n, min_periods=n).max().shift(1)
        h4["donchian_low_n"] = h4["low"].rolling(window=n, min_periods=n).min().shift(1)
        h4["donchian_exit_high_m"] = h4["high"].rolling(window=m, min_periods=m).max().shift(1)
        h4["donchian_exit_low_m"] = h4["low"].rolling(window=m, min_periods=m).min().shift(1)

        h1["h1_adx"] = calc_adx(h1, PARAMETERS["ADX_PERIOD"])
        h1_adx = h1[["time", "h1_adx"]].dropna().sort_values("time")
        h4 = pd.merge_asof(h4.sort_values("time"), h1_adx, on="time", direction="backward")

        h4.dropna(
            subset=[
                "atr",
                "atr_ratio",
                "donchian_high_n",
                "donchian_low_n",
                "donchian_exit_high_m",
                "donchian_exit_low_m",
                "h1_adx",
            ],
            inplace=True,
        )
        h4.reset_index(drop=True, inplace=True)
        return h4
    except Exception as e:
        msg = f"❌ get_data() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return pd.DataFrame()


def get_position():
    try:
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"])  # type: ignore
        if positions is None:
            msg = f"❌ get_position(): mt5.positions_get() returned None, error code: {mt5.last_error()}"  # type: ignore
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return "error", None
        if len(positions) == 0:
            return None, None

        pos = positions[0]
        if pos.type == mt5.POSITION_TYPE_BUY:
            return "long", pos
        if pos.type == mt5.POSITION_TYPE_SELL:
            return "short", pos
        return None, pos
    except Exception as e:
        msg = f"❌ get_position() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return "error", None


def has_positions():
    side, _ = get_position()
    return side


def check_signal(row: pd.Series):
    try:
        atr_ratio_ok = float(row["atr_ratio"]) >= PARAMETERS["ATR_RATIO_MIN"]
        adx_ok = float(row["h1_adx"]) >= PARAMETERS["H1_ADX_MIN"]
        hit_up = float(row["high"]) >= float(row["donchian_high_n"])
        hit_dn = float(row["low"]) <= float(row["donchian_low_n"])

        if not atr_ratio_ok:
            return None, "atr_ratio_filter"
        if not adx_ok:
            return None, "adx_filter"
        if hit_up and hit_dn:
            return None, "both_breakout_same_bar"
        if hit_up:
            return "long", None
        if hit_dn:
            return "short", None
        return None, None
    except Exception as e:
        msg = f"❌ check_signal() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
        return None, "error"


def update_trailing_stop(df: pd.DataFrame):
    try:
        current_position, position = get_position()
        if current_position in (None, "error") or position is None:
            return

        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore
        if symbol_info is None:
            msg = f"❌ update_trailing_stop(): Failed to get {PARAMETERS['SYMBOL']} info"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        open_time = pd.to_datetime(position.time, unit="s", utc=True)
        active_df = df[df["time"] >= open_time]
        if active_df.empty:
            active_df = df.tail(1)

        last = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        atr_now = float(last["atr"])
        old_sl = float(position.sl or 0.0)
        if old_sl <= 0:
            return

        if current_position == "long":
            highest_since_entry = float(active_df["high"].max())
            new_sl = highest_since_entry - PARAMETERS["TRAIL_ATR_MULTIPLIER"] * atr_now
            if new_sl <= old_sl:
                return
        else:
            lowest_since_entry = float(active_df["low"].min())
            new_sl = lowest_since_entry + PARAMETERS["TRAIL_ATR_MULTIPLIER"] * atr_now
            if new_sl >= old_sl:
                return

        new_sl = round(new_sl, symbol_info.digits)
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": PARAMETERS["SYMBOL"],
            "position": position.ticket,
            "sl": new_sl,
            "tp": position.tp,
            "comment": METADATA["title"],
        }
        result = mt5.order_send(request)  # type: ignore
        if result is None:
            msg = f"❌ update_trailing_stop(): no return, Order #: {position.ticket}"
        elif result.retcode != mt5.TRADE_RETCODE_DONE:
            ret_msg = RET_CODE_MESSAGES.get(result.retcode, "Unknown error")
            msg = (
                f"❌ update_trailing_stop(): Failed\n"
                f"Order #: {position.ticket}\n"
                f"Old SL: {old_sl:.2f}\n"
                f"New SL: {new_sl:.2f}\n"
                f"Result: {ret_msg} ({result.retcode})"
            )
        else:
            msg = (
                f"✅ update_trailing_stop(): SL moved\n"
                f"Order #: {position.ticket}\n"
                f"Direction: {current_position}\n"
                f"Old SL: {old_sl:.2f}\n"
                f"New SL: {new_sl:.2f}\n"
                f"ATR: {atr_now:.2f}"
            )
        print(msg)
        log_message(msg)
        send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ update_trailing_stop() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)



def place_order(signal: str, atr: float, signal_row: pd.Series):
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
            price - PARAMETERS["SL_ATR_MULTIPLIER"] * atr
            if signal == "long"
            else price + PARAMETERS["SL_ATR_MULTIPLIER"] * atr
        )
        order_type = mt5.ORDER_TYPE_BUY if signal == "long" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": PARAMETERS["SYMBOL"],
            "volume": PARAMETERS["LOT"],
            "type": order_type,
            "price": round(price, digits),
            "sl": round(sl, digits),
            "deviation": 50,
            "comment": METADATA["title"],
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
                f"Strategy: {METADATA['title']}\n"
                f"Signal Bar: {signal_row['time']}\n"
                f"Order #: {result.order}\n"
                f"Direction: {'Buy' if signal == 'long' else 'Sell'}\n"
                f"Price: {price:.2f}\n"
                f"SL: {sl:.2f}\n"
                f"ATR: {atr:.2f}\n"
                f"ATR Ratio: {float(signal_row['atr_ratio']):.2f}\n"
                f"H1 ADX: {float(signal_row['h1_adx']):.2f}\n"
                f"DC High: {float(signal_row['donchian_high_n']):.2f}\n"
                f"DC Low: {float(signal_row['donchian_low_n']):.2f}\n"
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



def run():
    global LAST_SIGNAL_BAR_TIME

    try:
        if LAST_SIGNAL_BAR_TIME is None:
            LAST_SIGNAL_BAR_TIME = load_last_signal_bar_time()

        df = get_data()
        utc_now = get_mt5_utc_now()
        if utc_now is None:
            msg = "❌ run(): Failed to get MT5 UTC time, skipping cycle"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return
        timestamp = utc_now.strftime("%Y-%m-%d %H:%M:%S")

        if df.empty or len(df) < 3:
            msg = f"❌ run(): [{timestamp}] get_data returned empty or insufficient data"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        update_trailing_stop(df)

        signal_row = df.iloc[-2]
        current_row = df.iloc[-1]
        signal, reject_reason = check_signal(signal_row)
        account = mt5.account_info()  # type: ignore
        balance = account.balance if account else 0.0
        equity = account.equity if account else 0.0

        log_msg = (
            f"[{timestamp}] $:{balance:.2f} EQUITY:{equity:.2f}"
            f"  ---  SIGNAL_BAR:{signal_row['time']}"
            f"  ---  CLOSE: ({float(signal_row['close']):.2f}, {float(current_row['close']):.2f})"
            f"  ---  HIGH/LOW: ({float(signal_row['high']):.2f}, {float(signal_row['low']):.2f})"
            f"  ---  DC_HIGH/LOW: ({float(signal_row['donchian_high_n']):.2f}, {float(signal_row['donchian_low_n']):.2f})"
            f"  ---  EXIT_DC_HIGH/LOW: ({float(signal_row['donchian_exit_high_m']):.2f}, {float(signal_row['donchian_exit_low_m']):.2f})"
            f"  ---  ATR:{float(signal_row['atr']):.2f}"
            f"  ---  ATR_RATIO:{float(signal_row['atr_ratio']):.2f}"
            f"  ---  H1_ADX:{float(signal_row['h1_adx']):.2f}"
            f"  ---  SIGNAL:{signal}"
            f"  ---  REJECT:{reject_reason}"
        )
        short_msg = f"[{timestamp}] --- {METADATA['title']} --- ${balance:.2f}"
        print(short_msg)
        log_message(log_msg)

        if signal not in ("long", "short"):
            return

        signal_bar_time = signal_row["time"]
        if LAST_SIGNAL_BAR_TIME == signal_bar_time:
            return

        current_position = has_positions()
        if current_position == "error":
            msg = f"❌ run(): [{timestamp}] has_positions returned error, skipping trading cycle"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            return

        if current_position is not None:
            msg = f"⚠️ [{timestamp}] already have open position ({current_position}), skip new signal ({signal})"
            print(msg)
            log_message(msg)
            send_telegram_message(msg)
            LAST_SIGNAL_BAR_TIME = signal_bar_time
            save_last_signal_bar_time(signal_bar_time)
            return

        place_order(signal, float(signal_row["atr"]), signal_row)
        LAST_SIGNAL_BAR_TIME = signal_bar_time
        save_last_signal_bar_time(signal_bar_time)
    except Exception as e:
        msg = f"❌ run() ERROR: {e}"
        print(msg)
        log_message(msg)
        send_telegram_message(msg)



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
