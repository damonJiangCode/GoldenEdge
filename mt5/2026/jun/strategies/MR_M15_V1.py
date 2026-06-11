from datetime import datetime, timezone
import time
from pathlib import Path

import MetaTrader5 as mt5  # type: ignore
import pandas as pd  # type: ignore
import requests  # type: ignore


METADATA = {
    "account": 60089393,
    "password": "Jwz990118.",
    "server": "TradeMaxGlobal-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_2\\terminal64.exe",
    "log_file": f"MR_M15_V1_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "MR_M15_V1",
    "comment": (
        "XAUUSD M15 Mean Reversion: EMA36, Band 2.25ATR, SL 8ATR, "
        "H1 ADX<28, ATR ratio 0.3-2.0"
    ),
}


PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME": mt5.TIMEFRAME_M15,
    "H1_TIMEFRAME": mt5.TIMEFRAME_H1,
    "LOT": 0.01,
    "MAGIC": 2026061501,
    "EMA_PERIOD": 36,
    "ATR_PERIOD": 7,
    "BAND_ATR_MULTIPLIER": 2.25,
    "SL_ATR_MULTIPLIER": 8.0,
    "ADX_PERIOD": 28,
    "H1_ADX_LIMIT": 28.0,
    "ATR_RATIO_LOOKBACK": 160,
    "ATR_RATIO_MIN": 0.3,
    "ATR_RATIO_MAX": 2.0,
    "WICK_BODY_RATIO": 1.5,
    "FAT_TAIL_BODY_LOOKBACK": 3,
    "FAT_TAIL_BODY_MULTIPLIER": 2.5,
    "BREAKEVEN_RETRACE_RATIO": 2.0,
    "BARS": 700,
    "H1_BARS": 500,
    "RUNTIME_SECONDS": 20,
    "DEVIATION": 50,
}


TELEGRAM = {
    "BOT_TOKEN": "8484767627:AAG5GamZVFwywL8nfuTJMGUPVD9mP1tAv4o",
    "CHAT_ID": "7262692073",
}


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
if hasattr(mt5, "TRADE_RETCODE_NO_CHANGES"):
    RET_CODE_MESSAGES[mt5.TRADE_RETCODE_NO_CHANGES] = "order no changes"


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / METADATA["log_file"]
STATE_FILE = LOG_DIR / f"{METADATA['title']}_state.txt"

LAST_SIGNAL_BAR_TIME = None


def log_message(message: str):
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as file:
            file.write(message + "\n")
    except Exception as exc:
        print(f"log_message() ERROR: {exc}")


def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM['BOT_TOKEN']}/sendMessage"
        payload = {"chat_id": TELEGRAM["CHAT_ID"], "text": message}
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            log_message(
                "send_telegram_message() failed: "
                f"{response.status_code} - {response.text}"
            )
    except Exception as exc:
        log_message(f"send_telegram_message() ERROR: {exc}")


def notify(message: str):
    print(message)
    log_message(message)
    send_telegram_message(message)


def load_last_signal_bar_time():
    try:
        if not STATE_FILE.exists():
            return None
        value = STATE_FILE.read_text(encoding="utf-8").strip()
        return pd.Timestamp(value) if value else None
    except Exception as exc:
        notify(f"load_last_signal_bar_time() ERROR: {exc}")
        return None


def save_last_signal_bar_time(signal_bar_time):
    try:
        STATE_FILE.write_text(str(signal_bar_time), encoding="utf-8")
    except Exception as exc:
        notify(f"save_last_signal_bar_time() ERROR: {exc}")


def initialize_mt5():
    try:
        if not mt5.initialize(METADATA["path"]):  # type: ignore
            raise RuntimeError(
                f"❌ initialize_mt5(): Failed to initialize MT5: {mt5.last_error()}"  # type: ignore
            )
        if not mt5.login(  # type: ignore
            METADATA["account"], METADATA["password"], METADATA["server"]
        ):
            raise RuntimeError(
                f"❌ initialize_mt5(): Failed to log in MT5 account: {mt5.last_error()}"  # type: ignore
            )
        if not mt5.symbol_select(PARAMETERS["SYMBOL"], True):  # type: ignore
            raise RuntimeError(
                f"❌ initialize_mt5(): Failed to select symbol {PARAMETERS['SYMBOL']}"
            )

        account = mt5.account_info()  # type: ignore
        notify(
            "✅ MT5 initialized and logged in successfully\n"
            f"Account: {account.login if account else METADATA['account']}\n"
            f"Server: {METADATA['server']}\n"
            f"Strategy: {METADATA['title']}"
        )
        return True
    except Exception as exc:
        notify(f"❌ initialize_mt5() ERROR: {exc}")
        return False


def get_mt5_utc_now():
    tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
    if tick is None:
        return None
    return datetime.fromtimestamp(tick.time, tz=timezone.utc)


def _rates_to_dataframe(rates) -> pd.DataFrame:
    df = pd.DataFrame(rates)
    if df.empty:
        return df
    for column in ["open", "high", "low", "close", "tick_volume", "spread"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
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
    true_range = pd.concat(
        [high_low, high_prev_close, low_prev_close], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def calc_adx(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)

    tr_smoothed = true_range.ewm(alpha=1 / period, adjust=False).mean()
    plus_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
    minus_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100.0 * plus_smoothed / tr_smoothed.replace(0.0, float("nan"))
    minus_di = 100.0 * minus_smoothed / tr_smoothed.replace(0.0, float("nan"))
    dx = (
        100.0
        * (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0.0, float("nan"))
    )
    return dx.ewm(alpha=1 / period, adjust=False).mean()


def get_data():
    try:
        m15_rates = mt5.copy_rates_from_pos(  # type: ignore
            PARAMETERS["SYMBOL"], PARAMETERS["TIMEFRAME"], 0, PARAMETERS["BARS"]
        )
        h1_rates = mt5.copy_rates_from_pos(  # type: ignore
            PARAMETERS["SYMBOL"], PARAMETERS["H1_TIMEFRAME"], 0, PARAMETERS["H1_BARS"]
        )
        m15 = _rates_to_dataframe(m15_rates)
        h1 = _rates_to_dataframe(h1_rates)
        if m15.empty or h1.empty:
            notify(
                f"❌ get_data(): empty rates, M15 empty={m15.empty}, "
                f"H1 empty={h1.empty}"
            )
            return pd.DataFrame()

        m15["ema"] = m15["close"].ewm(
            span=PARAMETERS["EMA_PERIOD"], adjust=False
        ).mean()
        m15["atr"] = calc_atr(m15, PARAMETERS["ATR_PERIOD"])
        atr_slow = m15["atr"].rolling(
            window=PARAMETERS["ATR_RATIO_LOOKBACK"],
            min_periods=PARAMETERS["ATR_RATIO_LOOKBACK"],
        ).mean()
        m15["atr_ratio"] = m15["atr"] / atr_slow.replace(0.0, float("nan"))
        m15["upper_band"] = (
            m15["ema"] + PARAMETERS["BAND_ATR_MULTIPLIER"] * m15["atr"]
        )
        m15["lower_band"] = (
            m15["ema"] - PARAMETERS["BAND_ATR_MULTIPLIER"] * m15["atr"]
        )
        m15["body_abs"] = (m15["close"] - m15["open"]).abs()
        m15["body_abs_avg_prev"] = (
            m15["body_abs"]
            .rolling(
                window=PARAMETERS["FAT_TAIL_BODY_LOOKBACK"],
                min_periods=PARAMETERS["FAT_TAIL_BODY_LOOKBACK"],
            )
            .mean()
            .shift(1)
        )

        h1["h1_adx"] = calc_adx(h1, PARAMETERS["ADX_PERIOD"])
        # Shift makes each M15 bar use only the previous completed H1 candle.
        h1["h1_adx"] = h1["h1_adx"].shift(1)
        m15["h1_time"] = m15["time"].dt.floor("h")
        h1_map = h1.set_index("time")["h1_adx"]
        m15["h1_adx"] = m15["h1_time"].map(h1_map)

        m15.dropna(
            subset=[
                "ema",
                "atr",
                "atr_ratio",
                "upper_band",
                "lower_band",
                "body_abs_avg_prev",
                "h1_adx",
            ],
            inplace=True,
        )
        m15.reset_index(drop=True, inplace=True)
        return m15
    except Exception as exc:
        notify(f"❌ get_data() ERROR: {exc}")
        return pd.DataFrame()


def _has_short_confirmation(row: pd.Series) -> bool:
    body = abs(float(row["close"]) - float(row["open"]))
    upper_wick = float(row["high"]) - max(float(row["open"]), float(row["close"]))
    return bool(
        float(row["close"]) < float(row["open"])
        or upper_wick >= PARAMETERS["WICK_BODY_RATIO"] * max(body, 1e-9)
    )


def _has_long_confirmation(row: pd.Series) -> bool:
    body = abs(float(row["close"]) - float(row["open"]))
    lower_wick = min(float(row["open"]), float(row["close"])) - float(row["low"])
    return bool(
        float(row["close"]) > float(row["open"])
        or lower_wick >= PARAMETERS["WICK_BODY_RATIO"] * max(body, 1e-9)
    )


def check_signal(row: pd.Series):
    try:
        if float(row["h1_adx"]) >= PARAMETERS["H1_ADX_LIMIT"]:
            return None, "trend_filter"
        if not (
            PARAMETERS["ATR_RATIO_MIN"]
            <= float(row["atr_ratio"])
            <= PARAMETERS["ATR_RATIO_MAX"]
        ):
            return None, "atr_ratio_filter"
        avg_body = float(row["body_abs_avg_prev"])
        if avg_body > 0.0 and float(row["body_abs"]) > (
            PARAMETERS["FAT_TAIL_BODY_MULTIPLIER"] * avg_body
        ):
            return None, "fat_tail_filter"

        if (
            float(row["high"]) >= float(row["upper_band"])
            and _has_short_confirmation(row)
        ):
            return "short", None
        if (
            float(row["low"]) <= float(row["lower_band"])
            and _has_long_confirmation(row)
        ):
            return "long", None
        return None, None
    except Exception as exc:
        notify(f"❌ check_signal() ERROR: {exc}")
        return None, "error"


def get_position():
    try:
        positions = mt5.positions_get(symbol=PARAMETERS["SYMBOL"])  # type: ignore
        if positions is None:
            notify(
                "❌ get_position(): mt5.positions_get() returned None, "
                f"error code: {mt5.last_error()}"  # type: ignore
            )
            return "error", None
        strategy_positions = [
            position
            for position in positions
            if int(getattr(position, "magic", 0)) == PARAMETERS["MAGIC"]
        ]
        if not strategy_positions:
            if positions:
                return "foreign", None
            return None, None
        position = strategy_positions[0]
        if position.type == mt5.POSITION_TYPE_BUY:
            return "long", position
        if position.type == mt5.POSITION_TYPE_SELL:
            return "short", position
        return None, position
    except Exception as exc:
        notify(f"❌ get_position() ERROR: {exc}")
        return "error", None


def update_breakeven():
    try:
        side, position = get_position()
        if side in (None, "error") or position is None:
            return

        entry = float(position.price_open)
        old_sl = float(position.sl or 0.0)
        tp = float(position.tp or 0.0)
        if old_sl <= 0.0 or tp <= 0.0:
            return

        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore
        tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
        if symbol_info is None or tick is None:
            notify("❌ update_breakeven(): symbol info or tick unavailable")
            return

        tolerance = float(symbol_info.point) * 2.0
        if (side == "long" and old_sl >= entry - tolerance) or (
            side == "short" and old_sl <= entry + tolerance
        ):
            return

        entry_atr = abs(entry - old_sl) / PARAMETERS["SL_ATR_MULTIPLIER"]
        retrace_distance = (
            PARAMETERS["BAND_ATR_MULTIPLIER"]
            * PARAMETERS["BREAKEVEN_RETRACE_RATIO"]
            * entry_atr
        )
        trigger = tp - retrace_distance if side == "long" else tp + retrace_distance
        trigger_hit = tick.bid >= trigger if side == "long" else tick.bid <= trigger
        if not trigger_hit:
            return

        new_sl = round(entry, symbol_info.digits)
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": PARAMETERS["SYMBOL"],
            "position": position.ticket,
            "sl": new_sl,
            "tp": position.tp,
            "magic": PARAMETERS["MAGIC"],
            "comment": METADATA["title"],
        }
        result = mt5.order_send(request)  # type: ignore
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = getattr(result, "retcode", None)
            notify(
                "❌ update_breakeven(): Failed\n"
                f"Ticket: {position.ticket}\n"
                f"Result: {RET_CODE_MESSAGES.get(retcode, 'unknown')} ({retcode})"
            )
            return
        notify(
            "✅ update_breakeven(): SL moved to breakeven\n"
            f"Ticket: {position.ticket}\n"
            f"Direction: {side}\n"
            f"Old SL: {old_sl:.2f}\n"
            f"New SL: {new_sl:.2f}\n"
            f"Trigger: {trigger:.2f}"
        )
    except Exception as exc:
        notify(f"❌ update_breakeven() ERROR: {exc}")


def place_order(signal: str, signal_row: pd.Series):
    try:
        tick = mt5.symbol_info_tick(PARAMETERS["SYMBOL"])  # type: ignore
        symbol_info = mt5.symbol_info(PARAMETERS["SYMBOL"])  # type: ignore
        if tick is None or symbol_info is None:
            notify("❌ place_order(): symbol info or tick unavailable")
            return False

        price = float(tick.ask if signal == "long" else tick.bid)
        atr = float(signal_row["atr"])
        target_ema = float(signal_row["ema"])
        if (signal == "long" and target_ema <= price) or (
            signal == "short" and target_ema >= price
        ):
            notify(
                "⚠️ place_order(): skipped because EMA target is no longer valid\n"
                f"Signal bar: {signal_row['time']}\n"
                f"Direction: {signal}\n"
                f"Current price: {price:.2f}\n"
                f"Target EMA: {target_ema:.2f}"
            )
            return False

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
            "price": round(price, symbol_info.digits),
            "sl": round(sl, symbol_info.digits),
            "tp": round(target_ema, symbol_info.digits),
            "deviation": PARAMETERS["DEVIATION"],
            "magic": PARAMETERS["MAGIC"],
            "comment": METADATA["title"],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)  # type: ignore
        retcode = getattr(result, "retcode", None)
        success = retcode == mt5.TRADE_RETCODE_DONE
        notify(
            f"{'✅ Succeeded' if success else '❌ Failed'}\n"
            f"Strategy: {METADATA['title']}\n"
            f"Signal bar: {signal_row['time']}\n"
            f"Direction: {signal}\n"
            f"Price: {price:.2f}\n"
            f"SL: {sl:.2f}\n"
            f"TP EMA: {target_ema:.2f}\n"
            f"ATR: {atr:.2f}\n"
            f"ATR ratio: {float(signal_row['atr_ratio']):.2f}\n"
            f"H1 ADX: {float(signal_row['h1_adx']):.2f}\n"
            f"Result: {RET_CODE_MESSAGES.get(retcode, 'unknown')} ({retcode})"
        )
        return success
    except Exception as exc:
        notify(f"❌ place_order() ERROR: {exc}")
        return False


def run():
    global LAST_SIGNAL_BAR_TIME

    try:
        if LAST_SIGNAL_BAR_TIME is None:
            LAST_SIGNAL_BAR_TIME = load_last_signal_bar_time()

        df = get_data()
        utc_now = get_mt5_utc_now()
        if utc_now is None:
            notify("❌ run(): Failed to get MT5 UTC time, skipping cycle")
            return
        timestamp = utc_now.strftime("%Y-%m-%d %H:%M:%S")

        if df.empty or len(df) < 3:
            notify(
                f"❌ run(): [{timestamp}] get_data returned empty or insufficient data"
            )
            return

        update_breakeven()

        # MT5 row -1 is forming; row -2 is the completed signal candle.
        signal_row = df.iloc[-2]
        signal, reject_reason = check_signal(signal_row)
        account = mt5.account_info()  # type: ignore
        balance = account.balance if account else 0.0
        equity = account.equity if account else 0.0
        log_message(
            f"[{timestamp}] BALANCE:{balance:.2f} EQUITY:{equity:.2f}"
            f" SIGNAL_BAR:{signal_row['time']}"
            f" CLOSE:{float(signal_row['close']):.2f}"
            f" EMA:{float(signal_row['ema']):.2f}"
            f" BAND:({float(signal_row['lower_band']):.2f},"
            f"{float(signal_row['upper_band']):.2f})"
            f" ATR:{float(signal_row['atr']):.2f}"
            f" ATR_RATIO:{float(signal_row['atr_ratio']):.2f}"
            f" H1_ADX:{float(signal_row['h1_adx']):.2f}"
            f" SIGNAL:{signal} REJECT:{reject_reason}"
        )
        short_msg = f"[{timestamp}] --- {METADATA['title']} --- ${balance:.2f}"
        print(short_msg)

        if signal not in ("long", "short"):
            return
        signal_bar_time = signal_row["time"]
        if LAST_SIGNAL_BAR_TIME == signal_bar_time:
            return

        current_side, _ = get_position()
        if current_side == "error":
            notify(
                f"❌ run(): [{timestamp}] get_position returned error, "
                "skipping trading cycle"
            )
            return
        if current_side is not None:
            notify(
                f"⚠️ [{timestamp}] already have open position ({current_side}), "
                f"skip new signal ({signal})"
            )
            LAST_SIGNAL_BAR_TIME = signal_bar_time
            save_last_signal_bar_time(signal_bar_time)
            return

        # Consume the signal after one order attempt. Repeating the same M15
        # signal can create duplicate orders when the first response is delayed.
        place_order(signal, signal_row)
        LAST_SIGNAL_BAR_TIME = signal_bar_time
        save_last_signal_bar_time(signal_bar_time)
    except Exception as exc:
        notify(f"❌ run() ERROR: {exc}")


def main():
    try:
        if not initialize_mt5():
            notify("❌ main(): initialize_mt5() failed, exiting")
            return
        while True:
            run()
            time.sleep(PARAMETERS["RUNTIME_SECONDS"])
    except KeyboardInterrupt:
        notify("⏹️ KeyboardInterrupt: manual stop")
    except Exception as exc:
        notify(f"❌ main() ERROR: {exc}")
    finally:
        try:
            mt5.shutdown()  # type: ignore
            notify("🔌 MT5 shutdown completed")
        except Exception:
            pass


if __name__ == "__main__":
    main()
